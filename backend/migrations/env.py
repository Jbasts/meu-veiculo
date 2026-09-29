"""Ambiente do Alembic.

O banco alvo vem do .env (DB_NOME). Para outro banco, o gerenciar.py passa
"-x banco=<nome>" (é assim que os testes usam o banco de teste).
Cada migration roda na própria transação: se uma falhar, só ela é desfeita
e as anteriores continuam registradas como aplicadas.
"""

from logging.config import fileConfig

from alembic import context

from app.banco.conexao import criar_engine

config = context.config

if config.config_file_name is not None and config.attributes.get("configurar_logs", True):
    fileConfig(config.config_file_name)


def executar_online() -> None:
    nome_banco = context.get_x_argument(as_dictionary=True).get("banco")
    engine = config.attributes.get("engine") or criar_engine(nome_banco)
    with engine.connect() as conexao:
        context.configure(
            connection=conexao,
            target_metadata=None,
            transaction_per_migration=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit(
        "Modo offline não é usado neste projeto: as migrations rodam direto no banco."
    )

executar_online()
