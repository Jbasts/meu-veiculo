"""Conexão com o PostgreSQL.

Toda conexão aberta pelo backend fixa o fuso America/Sao_Paulo. Assim,
CURRENT_DATE e os DEFAULT CURRENT_DATE do banco dão a data de Brasília,
mesmo que o servidor do PostgreSQL esteja configurado em outro fuso.
"""

from functools import lru_cache

import psycopg
from sqlalchemy import URL, Engine, create_engine

from app.config import FUSO_HORARIO, Configuracoes, obter_configuracoes


def montar_url(nome_banco: str | None = None, cfg: Configuracoes | None = None) -> URL:
    cfg = cfg or obter_configuracoes()
    return URL.create(
        drivername="postgresql+psycopg",
        username=cfg.db_usuario,
        password=cfg.db_senha.get_secret_value(),
        host=cfg.db_host,
        port=cfg.db_porta,
        database=nome_banco or cfg.db_nome,
    )


def criar_engine(nome_banco: str | None = None, cfg: Configuracoes | None = None) -> Engine:
    return create_engine(
        montar_url(nome_banco, cfg),
        connect_args={
            "options": f"-c timezone={FUSO_HORARIO}",
            "connect_timeout": 5,
        },
        pool_pre_ping=True,
    )


def conectar_psycopg(
    nome_banco: str | None = None,
    cfg: Configuracoes | None = None,
    autocommit: bool = False,
) -> psycopg.Connection:
    """Conexão direta (sem SQLAlchemy), usada pelos comandos de manutenção do banco."""
    cfg = cfg or obter_configuracoes()
    return psycopg.connect(
        host=cfg.db_host,
        port=cfg.db_porta,
        user=cfg.db_usuario,
        password=cfg.db_senha.get_secret_value(),
        dbname=nome_banco or cfg.db_nome,
        options=f"-c timezone={FUSO_HORARIO}",
        connect_timeout=5,
        autocommit=autocommit,
    )


@lru_cache
def obter_engine() -> Engine:
    """Engine do banco de desenvolvimento, criada uma vez só."""
    return criar_engine()
