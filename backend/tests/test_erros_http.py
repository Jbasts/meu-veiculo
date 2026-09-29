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
    assert resposta.json() == {"mensagem": erro.mensagem}
