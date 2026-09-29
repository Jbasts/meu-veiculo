"""Tradução dos erros de negócio (services) para respostas HTTP.

Um service levanta, por exemplo, NaoEncontrado("Veículo não encontrado.");
aqui ele vira HTTP 404 com {"mensagem": "Veículo não encontrado."}.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.schemas.erro_schema import ErroResposta
from app.services.erros import (
    AcessoNegado,
    Conflito,
    DadosInvalidos,
    ErroDeNegocio,
    NaoAutenticado,
    NaoEncontrado,
)

CODIGO_HTTP: dict[type[ErroDeNegocio], int] = {
    DadosInvalidos: 422,
    NaoAutenticado: 401,
    AcessoNegado: 403,
    NaoEncontrado: 404,
    Conflito: 409,
}


def codigo_http(erro: ErroDeNegocio) -> int:
    for classe in type(erro).__mro__:
        if classe in CODIGO_HTTP:
            return CODIGO_HTTP[classe]
    return 400


async def tratar_erro_de_negocio(_requisicao: Request, erro: Exception) -> JSONResponse:
    assert isinstance(erro, ErroDeNegocio)
    corpo = ErroResposta(mensagem=erro.mensagem)
    return JSONResponse(status_code=codigo_http(erro), content=corpo.model_dump())


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    app.add_exception_handler(ErroDeNegocio, tratar_erro_de_negocio)
