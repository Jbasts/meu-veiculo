"""Apoio aos testes de veículos, quilometragem e fotos."""

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import text

from app.main import app
from tests.auth_utils import (
    CaixaDeEntrada,
    cadastrar,
    executar_sql,
    ligar_app_ao_banco,
    novo_aparelho,
)

CIVIC = {
    "marca": "Honda", "modelo": "Civic", "versao": None, "ano": 2020, "placa": "ABC-1234",
    "cor": None, "tipo_combustivel": "flex", "quilometragem": 85000,
    "data_aquisicao": "2022-03-15", "valor_aquisicao": "65000.00", "km_aquisicao": 22000,
    "capacidade_tanque": "56.0",
}


def dados_veiculo(**alteracoes) -> dict:
    return {**CIVIC, **alteracoes}


def dados_edicao(**alteracoes) -> dict:
    dados = dados_veiculo(**alteracoes)
    dados.pop("quilometragem")
    return dados


def criar_veiculo(cliente: TestClient, **alteracoes) -> dict:
    resposta = cliente.post("/api/veiculos", json=dados_veiculo(**alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def imagem(formato: str = "JPEG", tamanho: tuple[int, int] = (80, 60), cor="red", **opcoes) -> bytes:
    saida = io.BytesIO()
    modo = "RGBA" if formato == "PNG" else "RGB"
    Image.new(modo, tamanho, cor).save(saida, formato, **opcoes)
    return saida.getvalue()


def enviar_foto(cliente: TestClient, veiculo_id: int, conteudo: bytes | None = None,
                nome: str = "foto.jpg", tipo: str = "image/jpeg", **campos):
    conteudo = imagem() if conteudo is None else conteudo
    return cliente.post(
        f"/api/veiculos/{veiculo_id}/fotos",
        files={"arquivo": (nome, conteudo, tipo)},
        data={chave: str(valor) for chave, valor in campos.items()},
    )


@pytest.fixture
def pasta_fotos(tmp_path):
    return tmp_path / "fotos"


@pytest.fixture
def banco(banco_migrado, pasta_fotos):
    """Banco de teste migrado, com a API ligada a ele.

    pasta_fotos é uma pasta temporária vazia: desde a 0013 a API não usa pasta
    nenhuma, e os testes conferem que nada é gravado nela."""
    ligar_app_ao_banco(banco_migrado, CaixaDeEntrada())
    yield banco_migrado
    app.dependency_overrides.clear()


@pytest.fixture
def paula(banco) -> TestClient:
    cliente = novo_aparelho()
    assert cadastrar(cliente, email="paula@email.com", nome="Paula").status_code == 201
    return cliente


@pytest.fixture
def rafael(banco) -> TestClient:
    cliente = novo_aparelho()
    assert cadastrar(cliente, email="rafael@email.com", nome="Rafael").status_code == 201
    return cliente


@pytest.fixture
def admin(banco) -> TestClient:
    cliente = novo_aparelho()
    assert cadastrar(cliente, email="admin@email.com", nome="Admin").status_code == 201
    executar_sql(banco, "UPDATE usuario SET perfil = 'admin' WHERE email = 'admin@email.com'")
    return cliente


def arquivos_na_pasta(pasta) -> list[str]:
    if not pasta.is_dir():
        return []
    return sorted(p.relative_to(pasta).as_posix() for p in pasta.rglob("*") if p.is_file())


def imagens_no_banco(engine) -> int:
    """Quantas imagens estão guardadas no PostgreSQL (tabela foto_conteudo)."""
    with engine.connect() as conexao:
        return conexao.scalar(text("SELECT count(*) FROM foto_conteudo"))
