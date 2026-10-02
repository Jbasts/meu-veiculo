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
    importar-fotos [--pasta] copia para o banco as fotos que ainda estão só
                             na antiga pasta (nada é apagado)
    carregar-exemplo         grava dados de exemplo no banco de DEMONSTRAÇÃO
                             (DB_NOME_DEMO); nunca no de desenvolvimento.
                             --recomecar apaga o banco de demonstração antes
    testar-email DESTINO     envia uma mensagem de teste com a configuração
                             de e-mail do .env e explica o erro, se houver

Use --teste para agir no banco de teste em vez do de desenvolvimento.
"""

import argparse
import getpass
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

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
from app.services.email_service import (
    EnviadorArquivo,
    MensagemEmail,
    conferir_configuracao_smtp,
    criar_enviador,
    explicar_falha_de_envio,
)
from app.services.erros import ErroDeNegocio
from app.services.validacao import normalizar_email
from app.services.importacao_fotos_service import ImportacaoFotosService
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
    if len({cfg.db_nome, cfg.db_nome_teste, cfg.db_nome_demo}) < 3:
        raise SystemExit("DB_NOME, DB_NOME_TESTE e DB_NOME_DEMO precisam ser diferentes.")

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

        for nome in (cfg.db_nome, cfg.db_nome_teste, cfg.db_nome_demo):
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


def cmd_importar_fotos(args: argparse.Namespace) -> None:
    exigir_senha_da_aplicacao()
    pasta = args.pasta or obter_configuracoes().pasta_fotos
    engine = criar_engine(nome_do_banco(args))
    try:
        with abrir_sessao(engine) as sessao:
            relatorio = ImportacaoFotosService(UnidadeDeTrabalho(sessao), FotoRepository(sessao),
                                               ArquivoFotoRepository(pasta)).importar()
    finally:
        engine.dispose()
    print(f"Pasta lida: {relatorio.pasta}")
    print(f"Fotos copiadas para o banco agora: {len(relatorio.importadas)}")
    for descricao in relatorio.importadas:
        print(f"  - {descricao}")
    print(f"Fotos sem imagem no banco e sem arquivo na pasta: {len(relatorio.sem_arquivo)}")
    for descricao in relatorio.sem_arquivo:
        print(f"  - {descricao}")
    if relatorio.sem_arquivo:
        print("Elas aparecem na galeria como 'Imagem indisponível'. Se tiver os arquivos (por "
              "exemplo, num backup da antiga pasta storage), coloque-os na pasta e rode de novo; "
              "ou apague essas fotos pela tela.")
    if relatorio.invalidos:
        print(f"Arquivos vazios ou acima de 10 MB (não copiados): {len(relatorio.invalidos)}")
        for descricao in relatorio.invalidos:
            print(f"  - {descricao}")
    print(f"Arquivos na pasta que não são de nenhuma foto: {len(relatorio.arquivos_sem_foto)}")
    for caminho in relatorio.arquivos_sem_foto:
        print(f"  - {caminho}")
    print("Nenhum arquivo foi apagado. As fotos são lidas só do banco; a pasta pode ser apagada "
          "depois de você conferir as fotos no app.")


def nome_do_banco_demo() -> str:
    """Trava: a carga de exemplo só grava num banco próprio, nunca no de verdade."""
    cfg = obter_configuracoes()
    nome = cfg.db_nome_demo
    if not nome.endswith("_demo") or nome in (cfg.db_nome, cfg.db_nome_teste):
        raise SystemExit(
            f"Trava de segurança: DB_NOME_DEMO='{nome}' precisa terminar em '_demo' e ser "
            "diferente de DB_NOME e DB_NOME_TESTE. A carga de exemplo nunca grava nos seus dados.")
    return nome


def cmd_carregar_exemplo(args: argparse.Namespace) -> None:
    nome = nome_do_banco_demo()
    exigir_senha_da_aplicacao()
    try:
        # Precisa do cliente de teste do FastAPI (requirements-dev.txt).
        from demonstracao.carga_exemplo import EMAIL_ADMIN, EMAIL_PADRAO, SENHA_EXEMPLO, carregar
    except ModuleNotFoundError as erro:
        raise SystemExit(f"Falta uma biblioteca de desenvolvimento ({erro.name}). Rode: "
                         ".\\.venv\\Scripts\\python.exe -m pip install -r requirements-dev.txt")
    engine = criar_engine(nome)
    try:
        try:
            with engine.connect() as conexao:
                conexao.execute(sqlalchemy.text("SELECT 1"))
        except sqlalchemy.exc.OperationalError:
            raise SystemExit(f"Não consegui abrir o banco '{nome}'. Ele é criado pelo "
                             "'gerenciar.py criar-bancos' (rode de novo: nada é apagado nos outros).")
        if args.recomecar:
            with engine.begin() as conexao:
                conexao.execute(sqlalchemy.text("DROP SCHEMA IF EXISTS public CASCADE"))
                conexao.execute(sqlalchemy.text("CREATE SCHEMA public"))
            print(f"Banco '{nome}' esvaziado.")
        # Sem reconfigurar o log do Alembic: banco só de demonstração, nada a relatar.
        migrar(engine=engine, backup=False, configurar_logs=False)
        with engine.connect() as conexao:
            contas = conexao.execute(sqlalchemy.text("SELECT count(*) FROM usuario")).scalar()
        if contas:
            raise SystemExit(f"O banco '{nome}' já tem {contas} conta(s). Para apagar tudo e "
                             "carregar de novo: gerenciar.py carregar-exemplo --recomecar")
        resumo = carregar(engine)
    finally:
        engine.dispose()
    print(f"Dados de exemplo gravados no banco '{nome}': {resumo.veiculos} veículos, "
          f"{resumo.registros} registros e {resumo.fotos} fotos.")
    print(f"Entre com {EMAIL_ADMIN} (administradora) ou {EMAIL_PADRAO}; senha: {SENHA_EXEMPLO}")
    print("Para abrir o sistema com estes dados, veja a seção 20 do README.")


def cmd_testar_email(args: argparse.Namespace) -> None:
    """Não usa o banco. Mostra a configuração sem a senha e, se o envio
    falhar, explica o motivo (o fluxo de "Esqueci a senha" não mostra erros)."""
    cfg = obter_configuracoes()
    try:
        destino = normalizar_email(args.destino)
    except ErroDeNegocio:
        raise SystemExit(f"ERRO: '{args.destino}' não é um e-mail válido.")
    print(f"Modo: {cfg.email_modo}")
    if cfg.email_modo == "smtp":
        print(f"Servidor: {cfg.smtp_host or '(vazio)'}, porta {cfg.smtp_porta}, "
              f"segurança {cfg.smtp_seguranca}")
        print(f"Usuário: {cfg.smtp_usuario or '(nenhum)'}; senha: "
              f"{'preenchida' if cfg.smtp_senha.get_secret_value() else 'vazia'}")
    print(f"Remetente: {cfg.email_remetente}")
    print(f"Links dos e-mails começam com: {cfg.url_frontend.rstrip('/')}")
    problemas = conferir_configuracao_smtp(cfg)
    if problemas:
        print("\nCorrija no backend\\.env antes de testar:", file=sys.stderr)
        for problema in problemas:
            print(f"- {problema}", file=sys.stderr)
        raise SystemExit(1)
    agora = datetime.now(ZoneInfo(FUSO_HORARIO)).strftime("%d/%m/%Y %H:%M")
    mensagem = MensagemEmail(
        para=destino,
        assunto="Meu Veículo: e-mail de teste",
        texto=("Olá!\n\nEste é um e-mail de teste do Meu Veículo, enviado em "
               f"{agora} pelo comando gerenciar.py testar-email.\n"
               "Se ele chegou, a recuperação de senha e os convites também vão chegar.\n\n"
               f"Endereço do sistema: {cfg.url_frontend.rstrip('/')}\n"),
    )
    enviador = criar_enviador(cfg)
    try:
        resultado = enviador.enviar(mensagem)
    except Exception as erro:  # noqa: BLE001 - qualquer falha vira orientação
        print(f"\nERRO: o e-mail não foi enviado. {explicar_falha_de_envio(erro)}", file=sys.stderr)
        raise SystemExit(1)
    if isinstance(enviador, EnviadorArquivo):
        print(f"\nModo arquivo: nada saiu do computador. Mensagem gravada em {resultado}")
        print("Para enviar de verdade, use EMAIL_MODO=smtp (README, seção 10.2).")
    else:
        print(f"\nEnviado para {destino}. Confira a caixa de entrada (e a pasta de spam).")


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
        ("importar-fotos", cmd_importar_fotos, "copia para o banco fotos que ainda estão na pasta"),
        ("carregar-exemplo", cmd_carregar_exemplo, "grava dados de exemplo no banco de demonstração"),
        ("testar-email", cmd_testar_email, "envia um e-mail de teste com a configuração do .env"),
    ):
        p = sub.add_parser(nome, help=ajuda)
        p.set_defaults(funcao=funcao)
        if nome not in ("criar-bancos", "carregar-exemplo", "testar-email"):
            p.add_argument("--teste", action="store_true", help="usar o banco de teste")
        if nome == "promover-admin":
            p.add_argument("email", help="e-mail da conta (criada antes pela tela 'Criar conta')")
        if nome == "carregar-exemplo":
            p.add_argument("--recomecar", action="store_true",
                           help="apaga tudo do banco de demonstração antes de carregar")
        if nome == "testar-email":
            p.add_argument("destino", help="e-mail que vai receber a mensagem de teste")
        if nome == "importar-fotos":
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
