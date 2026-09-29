"""Garante o fluxo Route → Controller → Service → Repository → PostgreSQL.

Lê os "import" de cada arquivo de backend/app e falha se uma camada usar
algo que não deveria (por exemplo, um service importando FastAPI ou uma
route falando direto com um repository).
"""

import ast
from pathlib import Path

import pytest

PASTA_APP = Path(__file__).resolve().parent.parent / "app"

CAMADAS = ("routes", "controllers", "services", "repositories", "entities", "schemas", "banco")

# O que cada camada NÃO pode importar (prefixos de módulo).
PROIBIDOS: dict[str, tuple[str, ...]] = {
    "routes": ("app.services", "app.repositories", "app.banco", "app.entities",
               "sqlalchemy", "psycopg"),
    "controllers": ("app.repositories", "app.banco", "app.routes", "app.dependencias",
                    "sqlalchemy", "psycopg"),
    "services": ("fastapi", "starlette", "sqlalchemy", "psycopg", "app.controllers",
                 "app.routes", "app.schemas", "app.dependencias", "app.banco"),
    "repositories": ("fastapi", "starlette", "app.controllers", "app.routes",
                     "app.services", "app.schemas", "app.dependencias"),
    "entities": ("fastapi", "starlette", "psycopg", "app.controllers", "app.routes",
                 "app.services", "app.repositories", "app.schemas", "app.banco",
                 "app.dependencias"),
    "schemas": ("sqlalchemy", "psycopg", "app.controllers", "app.routes", "app.services",
                "app.repositories", "app.banco", "app.dependencias"),
    "banco": ("fastapi", "starlette", "app.controllers", "app.routes", "app.services",
              "app.repositories", "app.schemas", "app.dependencias", "app.entities"),
}

# Exceções permitidas de propósito.
PERMITIDOS: dict[str, tuple[str, ...]] = {
    # O service controla a transação pela UnidadeDeTrabalho (sem usar SQLAlchemy direto).
    "services": ("app.banco.sessao",),
}


def modulos_importados(codigo: str) -> list[str]:
    modulos: list[str] = []
    for no in ast.walk(ast.parse(codigo)):
        if isinstance(no, ast.Import):
            modulos += [alias.name for alias in no.names]
        elif isinstance(no, ast.ImportFrom):
            if no.level:
                modulos.append("." * no.level + (no.module or ""))
            else:
                modulos.append(no.module or "")
    return modulos


def _casa(modulo: str, prefixo: str) -> bool:
    return modulo == prefixo or modulo.startswith(prefixo + ".")


def violacoes(camada: str, codigo: str) -> list[str]:
    problemas = []
    for modulo in modulos_importados(codigo):
        if modulo.startswith("."):
            problemas.append(f"import relativo '{modulo}' (use 'from app....')")
            continue
        if any(_casa(modulo, p) for p in PERMITIDOS.get(camada, ())):
            continue
        for prefixo in PROIBIDOS[camada]:
            if _casa(modulo, prefixo):
                problemas.append(f"importa '{modulo}'")
    return problemas


def arquivos_da_camada(camada: str) -> list[Path]:
    return sorted((PASTA_APP / camada).rglob("*.py"))


def test_estrutura_de_pastas_existe():
    for camada in CAMADAS:
        assert (PASTA_APP / camada / "__init__.py").is_file(), f"falta app/{camada}/"
    assert (PASTA_APP / "config.py").is_file()
    assert (PASTA_APP / "main.py").is_file()


@pytest.mark.parametrize("camada", CAMADAS)
def test_camada_respeita_as_dependencias(camada):
    problemas = []
    for arquivo in arquivos_da_camada(camada):
        for problema in violacoes(camada, arquivo.read_text(encoding="utf-8")):
            problemas.append(f"{arquivo.relative_to(PASTA_APP.parent)}: {problema}")
    assert not problemas, "\n".join(problemas)


def test_main_so_monta_a_aplicacao():
    codigo = (PASTA_APP / "main.py").read_text(encoding="utf-8")
    proibidos = ("app.services", "app.repositories", "app.banco", "sqlalchemy", "psycopg")
    assert not [m for m in modulos_importados(codigo) if any(_casa(m, p) for p in proibidos)]


def test_verificador_detecta_violacao():
    """O próprio teste precisa acusar quando alguém fura a regra."""
    assert violacoes("services", "from fastapi import HTTPException") == ["importa 'fastapi'"]
    assert violacoes("routes", "from app.repositories.x import Y") == [
        "importa 'app.repositories.x'"
    ]
    assert violacoes("services", "from app.banco.conexao import obter_engine")
    assert violacoes("services", "from app.banco.sessao import UnidadeDeTrabalho") == []
    assert violacoes("controllers", "from .x import y")
