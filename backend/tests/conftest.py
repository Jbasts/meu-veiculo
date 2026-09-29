"""Configuração comum dos testes.

Os testes usam o PostgreSQL de verdade, no banco de TESTE (DB_NOME_TESTE do
.env). Esse banco é apagado e recriado várias vezes durante os testes, por
isso há uma trava: o nome precisa terminar em "_teste" e ser diferente do
banco de desenvolvimento.
"""

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import OperationalError

from app.banco.conexao import conectar_psycopg, criar_engine
from app.banco.migracoes import migrar
from app.banco.sql_original import ESQUEMA_REFERENCIA, sql_original_para_executar
from app.config import obter_configuracoes


def nome_banco_teste() -> str:
    cfg = obter_configuracoes()
    nome = cfg.db_nome_teste
    if not nome.endswith("_teste") or nome == cfg.db_nome:
        pytest.exit(
            f"Trava de segurança: DB_NOME_TESTE='{nome}' precisa terminar em '_teste' "
            "e ser diferente de DB_NOME. Os testes apagam esse banco.",
            returncode=2,
        )
    return nome


@pytest.fixture(scope="session")
def engine_teste() -> Engine:
    engine = criar_engine(nome_banco_teste())
    try:
        with engine.connect() as conexao:
            conexao.execute(text("SELECT 1"))
    except OperationalError:
        pytest.exit(
            "Não consegui conectar ao banco de teste. Confira se o PostgreSQL está rodando, "
            "se backend/.env está preenchido e se você já rodou 'gerenciar.py criar-bancos'.",
            returncode=2,
        )
    yield engine
    engine.dispose()


def esvaziar(engine: Engine) -> None:
    """Apaga tudo do banco de teste e deixa o esquema public vazio."""
    with engine.begin() as conexao:
        conexao.execute(text("DROP SCHEMA IF EXISTS public CASCADE"))
        conexao.execute(text(f'DROP SCHEMA IF EXISTS "{ESQUEMA_REFERENCIA}" CASCADE'))
        conexao.execute(text("CREATE SCHEMA public"))


def criar_com_sql_original_sem_controle(engine: Engine) -> None:
    """Simula um banco antigo: SQL original rodado à mão, sem Alembic."""
    with conectar_psycopg(engine.url.database) as conexao:
        conexao.execute(sql_original_para_executar())
        conexao.commit()


@pytest.fixture
def banco_vazio(engine_teste: Engine) -> Engine:
    esvaziar(engine_teste)
    return engine_teste


@pytest.fixture
def banco_migrado(engine_teste: Engine) -> Engine:
    esvaziar(engine_teste)
    migrar(engine=engine_teste, backup=False, configurar_logs=False)
    return engine_teste
