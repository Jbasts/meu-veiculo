"""Comandos de manutenção do banco do Meu Veículo.

Rode sempre na pasta backend, com o Python do ambiente virtual:

    .\\.venv\\Scripts\\python.exe gerenciar.py <comando>

Comandos:
    criar-bancos             cria o usuário da aplicação e os bancos de
                             desenvolvimento e de teste (pede a senha do postgres)
    estado                   mostra a versão do banco e as migrations pendentes
    migrar                   aplica as migrations pendentes (faz backup antes,
                             se o banco já tiver migrations aplicadas)
    adotar-banco-existente   registra um banco criado com o SQL original,
                             sem rodar o script de novo
    backup                   grava uma cópia do banco na pasta backend/backups
    promover-admin EMAIL     torna administradora uma conta já cadastrada
                             (é o único jeito de criar o primeiro admin)
    limpar-fotos [--apagar]  compara a pasta de fotos com o banco: lista os
                             arquivos sem registro e, com --apagar, apaga-os

Use --teste para agir no banco de teste em vez do de desenvolvimento.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

import psycopg
import sqlalchemy.exc
from psycopg import sql

from app.banco.backup import BackupFalhou, fazer_backup
from app.banco.conexao import criar_engine
from app.banco.migracoes import ErroMigracao, adotar_banco_existente, ler_estado, migrar
from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao
from app.banco.sql_original import SqlOriginalAlterado
from app.config import FUSO_HORARIO, obter_configuracoes
from app.repositories.arquivo_foto_repository import ArquivoFotoRepository
from app.repositories.foto_repository import FotoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.repositories.veiculo_repository import VeiculoRepository
from app.services.erros import ErroDeNegocio
from app.services.foto_service import FotoService
from app.services.usuario_service import UsuarioService

DESCRICAO_SITUACAO = {
    "vazio": "vazio (nenhuma tabela)",
    "sem_controle": "tem tabelas, mas SEM registro de migrations",
    "controlado": "com controle de migrations",
}


def nome_do_banco(args: argparse.Namespace) -> str:
    cfg = obter_configuracoes()
    return cfg.db_nome_teste if args.teste else cfg.db_nome


def exigir_senha_da_aplicacao() -> None:
    if not obter_configuracoes().db_senha.get_secret_value():
        raise SystemExit(
            "DB_SENHA está vazia em backend/.env. Copie o .env.example para .env "
            "e escolha uma senha para o usuário da aplicação."
        )


def cmd_criar_bancos(_args: argparse.Namespace) -> None:
    cfg = obter_configuracoes()
    exigir_senha_da_aplicacao()
    if cfg.db_nome == cfg.db_nome_teste:
        raise SystemExit("DB_NOME e DB_NOME_TESTE precisam ser diferentes.")

    senha_admin = os.environ.get("PG_ADMIN_SENHA") or getpass.getpass(
        f"Senha do usuário '{cfg.pg_admin_usuario}' do PostgreSQL (não aparece ao digitar): "
    )
    try:
        conexao = psycopg.connect(
            host=cfg.db_host, port=cfg.db_porta, user=cfg.pg_admin_usuario,
            password=senha_admin, dbname="postgres", autocommit=True, connect_timeout=5,
        )
    except psycopg.OperationalError:
        raise SystemExit(
            f"Não consegui entrar como '{cfg.pg_admin_usuario}'. Confira a senha "
            "(é a que você definiu ao instalar o PostgreSQL) e se o serviço está rodando."
        )

    with conexao:
        usuario = sql.Identifier(cfg.db_usuario)
        senha = sql.Literal(cfg.db_senha.get_secret_value())
        existe = conexao.execute(
            "SELECT 1 FROM pg_roles WHERE rolname = %s", (cfg.db_usuario,)
        ).fetchone()
        if existe:
            conexao.execute(sql.SQL("ALTER ROLE {} WITH LOGIN PASSWORD {}").format(usuario, senha))
            print(f"Usuário '{cfg.db_usuario}' já existia: senha atualizada com a do .env.")
        else:
            conexao.execute(
                sql.SQL(
                    "CREATE ROLE {} WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE PASSWORD {}"
                ).format(usuario, senha)
            )
            print(f"Usuário '{cfg.db_usuario}' criado (sem poderes de administrador).")

        for nome in (cfg.db_nome, cfg.db_nome_teste):
            banco = sql.Identifier(nome)
            existe = conexao.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (nome,)
            ).fetchone()
            if existe:
                print(f"Banco '{nome}' já existia: nada foi apagado.")
            else:
                conexao.execute(
                    sql.SQL("CREATE DATABASE {} OWNER {} ENCODING 'UTF8' TEMPLATE template0")
                    .format(banco, usuario)
                )
                print(f"Banco '{nome}' criado.")
            conexao.execute(
                sql.SQL("ALTER DATABASE {} SET timezone TO {}").format(banco, sql.Literal(FUSO_HORARIO))
            )
            conexao.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(banco))
            conexao.execute(sql.SQL("GRANT ALL ON DATABASE {} TO {}").format(banco, usuario))
    print("Pronto. Próximo passo: .\\.venv\\Scripts\\python.exe gerenciar.py migrar")


def cmd_estado(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    nome = nome_do_banco(args)
    estado = ler_estado(criar_engine(nome))
    print(f"Banco: {nome}")
    print(f"Situação: {DESCRICAO_SITUACAO[estado.situacao]}")
    print(f"Versão aplicada: {estado.versao_atual or 'nenhuma'}")
    print(f"Versão mais recente: {estado.versao_mais_recente}")
    if estado.situacao == "sem_controle":
        print("Próximo passo: faça backup e rode 'gerenciar.py adotar-banco-existente'.")
    elif estado.pendentes:
        print(f"Pendentes: {', '.join(estado.pendentes)}")
    else:
        print("Nenhuma migration pendente.")


def cmd_migrar(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    nome = nome_do_banco(args)
    antes = ler_estado(criar_engine(nome))
    estado, arquivo_backup = migrar(nome)
    if arquivo_backup:
        print(f"Backup feito antes de migrar: {arquivo_backup}")
    if antes.pendentes:
        print(f"Aplicadas em '{nome}': {', '.join(antes.pendentes)}")
    else:
        print(f"'{nome}' já estava na versão mais recente ({estado.versao_atual}).")
    print(f"Versão atual: {estado.versao_atual}")


def cmd_adotar(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    nome = nome_do_banco(args)
    estado = adotar_banco_existente(nome)
    print(f"Banco '{nome}' conferido: estrutura idêntica ao SQL original.")
    print(f"Registrado na versão {estado.versao_atual}, sem executar o script de novo.")
    if estado.pendentes:
        print(f"Migrations pendentes: {', '.join(estado.pendentes)}. Rode 'gerenciar.py migrar'.")


def cmd_backup(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    arquivo = fazer_backup(nome_do_banco(args), motivo="manual")
    print(f"Backup gravado em: {arquivo}")


def cmd_promover_admin(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    engine = criar_engine(nome_do_banco(args))
    try:
        with abrir_sessao(engine) as sessao:
            service = UsuarioService(UnidadeDeTrabalho(sessao), UsuarioRepository(sessao))
            promovida = service.promover_a_admin(args.email)
    finally:
        engine.dispose()
    if promovida:
        print(f"A conta {args.email.strip().lower()} agora é administradora.")
    else:
        print(f"A conta {args.email.strip().lower()} já era administradora. Nada mudou.")


def cmd_limpar_fotos(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    pasta = args.pasta or obter_configuracoes().pasta_fotos
    engine = criar_engine(nome_do_banco(args))
    try:
        with abrir_sessao(engine) as sessao:
            service = FotoService(UnidadeDeTrabalho(sessao), VeiculoRepository(sessao),
                                  FotoRepository(sessao), ArquivoFotoRepository(pasta))
            relatorio = service.limpar_orfaos(apagar=args.apagar)
    finally:
        engine.dispose()
    print(f"Pasta de fotos: {pasta}")
    print(f"Arquivos sem registro no banco (com mais de 1 hora): {len(relatorio.arquivos_orfaos)}")
    for caminho in relatorio.arquivos_orfaos:
        print(f"  - {caminho}")
    if relatorio.arquivos_orfaos:
        if args.apagar:
            print(f"Apagados: {relatorio.apagados}")
        else:
            print("Nada foi apagado. Para apagar, rode de novo com --apagar.")
    print(f"Fotos no banco sem arquivo na pasta: {len(relatorio.fotos_sem_arquivo)}")
    for caminho in relatorio.fotos_sem_arquivo:
        print(f"  - {caminho}")
    if relatorio.fotos_sem_arquivo:
        print("Essas fotos aparecem na galeria sem imagem. Restaure os arquivos de um backup "
              "da pasta de fotos ou apague as fotos pela tela.")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Comandos do banco do Meu Veículo.")
    sub = parser.add_subparsers(dest="comando", required=True)
    for nome, funcao, ajuda in (
        ("criar-bancos", cmd_criar_bancos, "cria usuário da aplicação e bancos"),
        ("estado", cmd_estado, "mostra versão e migrations pendentes"),
        ("migrar", cmd_migrar, "aplica migrations pendentes"),
        ("adotar-banco-existente", cmd_adotar, "registra banco criado com o SQL original"),
        ("backup", cmd_backup, "grava cópia do banco em backend/backups"),
        ("promover-admin", cmd_promover_admin, "torna administradora uma conta já cadastrada"),
        ("limpar-fotos", cmd_limpar_fotos, "lista (ou apaga) arquivos de foto sem registro"),
    ):
        p = sub.add_parser(nome, help=ajuda)
        p.set_defaults(funcao=funcao)
        if nome != "criar-bancos":
            p.add_argument("--teste", action="store_true", help="usar o banco de teste")
        if nome == "promover-admin":
            p.add_argument("email", help="e-mail da conta (criada antes pela tela 'Criar conta')")
        if nome == "limpar-fotos":
            p.add_argument("--apagar", action="store_true",
                           help="apaga os arquivos sem registro (sem isso, só lista)")
            p.add_argument("--pasta", type=Path, default=None,
                           help="pasta das fotos (padrão: PASTA_FOTOS do .env)")

    args = parser.parse_args(argv)
    try:
        args.funcao(args)
    except (ErroMigracao, BackupFalhou, SqlOriginalAlterado) as erro:
        print(f"ERRO: {erro}", file=sys.stderr)
        raise SystemExit(1)
    except ErroDeNegocio as erro:
        print(f"ERRO: {erro.mensagem}", file=sys.stderr)
        raise SystemExit(1)
    except (psycopg.OperationalError, sqlalchemy.exc.OperationalError):
        print("ERRO: não consegui conectar ao PostgreSQL. Confira se o serviço está rodando "
              "e os dados de backend/.env (DB_HOST, DB_PORTA, DB_USUARIO, DB_SENHA).",
              file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
