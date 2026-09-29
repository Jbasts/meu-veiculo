"""Controle das migrations: em que versão o banco está e como atualizá-lo.

Três situações possíveis para um banco:
- "vazio": nenhuma tabela no esquema public. Instalação nova: use migrar().
- "sem_controle": tem tabelas, mas não tem a tabela alembic_version. Foi
  criado antes do controle de migrations (por exemplo, rodando o SQL
  original no pgAdmin). Use adotar_banco_existente(); nunca rode o SQL
  original de novo.
- "controlado": tem alembic_version. migrar() aplica só o que falta.
"""

from dataclasses import dataclass, field
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, text

from app.banco.backup import fazer_backup
from app.banco.conexao import conectar_psycopg, criar_engine
from app.banco.sql_original import Diferencas, comparar_com_original
from app.config import PASTA_BACKEND

CAMINHO_ALEMBIC_INI = PASTA_BACKEND / "alembic.ini"
REVISAO_SQL_ORIGINAL = "0001"


class ErroMigracao(Exception):
    pass


class EstruturaDiferente(ErroMigracao):
    def __init__(self, diferencas: Diferencas):
        self.diferencas = diferencas
        super().__init__(
            "A estrutura do banco não é igual à do SQL original. Nada foi alterado.\n"
            + diferencas.descrever()
        )


@dataclass
class EstadoBanco:
    situacao: str
    versao_atual: str | None
    versao_mais_recente: str
    pendentes: list[str] = field(default_factory=list)


def config_alembic(engine: Engine | None = None, configurar_logs: bool = True) -> Config:
    cfg = Config(str(CAMINHO_ALEMBIC_INI))
    cfg.attributes["configurar_logs"] = configurar_logs
    if engine is not None:
        cfg.attributes["engine"] = engine
    return cfg


def versao_mais_recente() -> str:
    cabeca = ScriptDirectory.from_config(config_alembic()).get_current_head()
    if cabeca is None:
        raise ErroMigracao("Nenhuma migration encontrada em backend/migrations/versions.")
    return cabeca


def ler_estado(engine: Engine) -> EstadoBanco:
    scripts = ScriptDirectory.from_config(config_alembic())
    cabeca = versao_mais_recente()
    with engine.connect() as conexao:
        tem_controle = conexao.execute(
            text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
        ).scalar()
        quantidade_objetos = conexao.execute(
            text(
                "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
                "WHERE n.nspname = 'public' AND c.relkind IN ('r', 'v', 'm', 'p')"
            )
        ).scalar()
        atual = MigrationContext.configure(conexao).get_current_revision() if tem_controle else None

    if tem_controle:
        situacao = "controlado"
    elif quantidade_objetos:
        situacao = "sem_controle"
    else:
        situacao = "vazio"

    pendentes: list[str] = []
    if situacao != "sem_controle":
        # iterate_revisions vai da mais nova para a mais antiga.
        pendentes = [
            rev.revision for rev in scripts.iterate_revisions(cabeca, atual or "base")
        ][::-1]
    return EstadoBanco(situacao, atual, cabeca, pendentes)


def migrar(nome_banco: str | None = None, *, engine: Engine | None = None,
           backup: bool = True, configurar_logs: bool = True) -> tuple[EstadoBanco, Path | None]:
    """Aplica as migrations pendentes. Devolve o estado final e o backup feito (se houve)."""
    engine = engine or criar_engine(nome_banco)
    estado = ler_estado(engine)
    if estado.situacao == "sem_controle":
        raise ErroMigracao(
            "Este banco já tem tabelas, mas não tem registro de migrations. "
            "Não vou rodar o SQL original de novo. Faça um backup "
            "('python gerenciar.py backup') e depois rode "
            "'python gerenciar.py adotar-banco-existente'."
        )
    if not estado.pendentes:
        return estado, None
    arquivo_backup = None
    if backup and estado.situacao == "controlado":
        arquivo_backup = fazer_backup(engine.url.database, motivo="antes_de_migrar")
    command.upgrade(config_alembic(engine, configurar_logs), "head")
    return ler_estado(engine), arquivo_backup


def adotar_banco_existente(nome_banco: str | None = None, *, engine: Engine | None = None,
                           configurar_logs: bool = True) -> EstadoBanco:
    """Registra a 0001 como aplicada num banco criado com o SQL original.

    Só registra se a estrutura for idêntica à do SQL original; caso
    contrário, lista as diferenças e não altera nada.
    """
    engine = engine or criar_engine(nome_banco)
    estado = ler_estado(engine)
    if estado.situacao == "vazio":
        raise ErroMigracao("O banco está vazio. Para instalar, use 'python gerenciar.py migrar'.")
    if estado.situacao == "controlado":
        raise ErroMigracao(
            f"Este banco já tem controle de migrations (versão {estado.versao_atual}). "
            "Use 'python gerenciar.py migrar'."
        )
    with conectar_psycopg(engine.url.database) as conexao:
        diferencas = comparar_com_original(conexao)
        conexao.rollback()
    if not diferencas.iguais:
        raise EstruturaDiferente(diferencas)
    command.stamp(config_alembic(engine, configurar_logs), REVISAO_SQL_ORIGINAL)
    return ler_estado(engine)
