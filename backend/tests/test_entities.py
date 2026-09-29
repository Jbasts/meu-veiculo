"""Cada entity mapeada precisa bater com a tabela real criada pelas migrations.

Na etapa 1 ainda não há entity de tabela (elas chegam com cada módulo);
a partir da etapa 2, este teste passa a conferir Usuario, Veiculo etc.
"""

import ast
from pathlib import Path

from sqlalchemy import inspect

import app.entities  # noqa: F401  (carrega o pacote das entities)
from app.entities.base import Base


def test_cada_entity_bate_com_a_tabela_do_banco(banco_migrado):
    inspetor = inspect(banco_migrado)
    tabelas_do_banco = set(inspetor.get_table_names()) | set(inspetor.get_view_names())
    problemas = []
    for tabela in Base.metadata.sorted_tables:
        if tabela.name not in tabelas_do_banco:
            problemas.append(f"{tabela.name}: tabela não existe no banco")
            continue
        colunas_banco = {c["name"]: c for c in inspetor.get_columns(tabela.name)}
        for coluna in tabela.columns:
            real = colunas_banco.get(coluna.name)
            if real is None:
                problemas.append(f"{tabela.name}.{coluna.name}: coluna não existe no banco")
            elif bool(real["nullable"]) != bool(coluna.nullable):
                problemas.append(
                    f"{tabela.name}.{coluna.name}: nullable na entity={coluna.nullable}, "
                    f"no banco={real['nullable']}"
                )
    assert not problemas, "\n".join(problemas)


def test_nenhum_codigo_cria_tabelas_pelas_entities():
    """Quem cria tabelas são as migrations; nenhum código chama create_all()."""
    pasta_app = Path(__file__).resolve().parent.parent / "app"
    chamadas = []
    for arquivo in pasta_app.rglob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            if (isinstance(no, ast.Call) and isinstance(no.func, ast.Attribute)
                    and no.func.attr in ("create_all", "drop_all")):
                chamadas.append(f"{arquivo.name}:{no.lineno}")
    assert not chamadas, chamadas
