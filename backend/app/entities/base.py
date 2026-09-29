"""Base das entities que mapeiam as tabelas do PostgreSQL.

As entities DESCREVEM tabelas que já existem; elas não criam nem alteram
nada no banco. Quem cria e muda tabelas são sempre as migrations
(backend/migrations). Por isso, nunca use Base.metadata.create_all().

Cada tabela ganha a sua entity na etapa do módulo correspondente
(Usuario na etapa 2, Veiculo na etapa 3...). O teste
tests/test_entities.py confere se cada entity bate com as colunas reais.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
