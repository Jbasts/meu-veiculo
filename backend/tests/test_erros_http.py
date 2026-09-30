"""Tradução dos erros de negócio para códigos HTTP."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.controllers.erros_http import registrar_tratadores_de_erro
from app.services.erros import (
    AcessoNegado,
    Conflito,
    DadosInvalidos,
    ErroDeNegocio,
    MuitasTentativas,
    NaoAutenticado,
    NaoEncontrado,
)


@pytest.mark.parametrize(
    ("erro", "codigo"),
    [
        (DadosInvalidos("Placa inválida."), 422),
        (NaoAutenticado("Entre na sua conta."), 401),
        (AcessoNegado("Você não tem permissão."), 403),
        (NaoEncontrado("Veículo não encontrado."), 404),
        (Conflito("E-mail já cadastrado."), 409),
        (ErroDeNegocio("Não foi possível concluir."), 400),
    ],
)
def test_erro_de_negocio_vira_codigo_http(erro, codigo):
    app = FastAPI()
    registrar_tratadores_de_erro(app)

    @app.get("/falha")
    def falha():
        raise erro

    resposta = TestClient(app).get("/falha")
    assert resposta.status_code == codigo
    assert resposta.json() == {"mensagem": erro.mensagem, "campos": None}


def test_erro_com_campo_indica_o_campo():
    app = FastAPI()
    registrar_tratadores_de_erro(app)

    @app.get("/falha")
    def falha():
        raise DadosInvalidos("E-mail inválido.", campo="email")

    assert TestClient(app).get("/falha").json() == {
        "mensagem": "E-mail inválido.", "campos": {"email": "E-mail inválido."}
    }


def test_muitas_tentativas_vira_429():
    app = FastAPI()
    registrar_tratadores_de_erro(app)

    @app.get("/falha")
    def falha():
        raise MuitasTentativas("Aguarde.")

    assert TestClient(app).get("/falha").status_code == 429


def test_erro_de_formato_em_portugues_por_campo():
    from pydantic import BaseModel, ConfigDict

    class Entrada(BaseModel):
        model_config = ConfigDict(extra="forbid")
        email: str

    app = FastAPI()
    registrar_tratadores_de_erro(app)

    @app.post("/dados")
    def dados(entrada: Entrada):
        return {}

    corpo = TestClient(app).post("/dados", json={"perfil": "admin"}).json()
    assert corpo == {
        "mensagem": "Confira os dados enviados.",
        "campos": {"email": "Campo obrigatório.", "perfil": "Campo não permitido."},
    }
