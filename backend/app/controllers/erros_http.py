"""Tradução de erros para respostas HTTP, sempre no formato
{"mensagem": "...", "campos": {"campo": "..."}}.

- Erros de negócio (services): NaoEncontrado("Veículo não encontrado.")
  vira HTTP 404 com {"mensagem": "Veículo não encontrado."}.
- Erros de formato (campo faltando, texto longo demais, campo não
  permitido): viram HTTP 422 com mensagens em português por campo.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas.erro_schema import ErroResposta
from app.services.erros import (
    AcessoNegado,
    Conflito,
    DadosInvalidos,
    ErroDeNegocio,
    MuitasTentativas,
    NaoAutenticado,
    NaoEncontrado,
)

CODIGO_HTTP: dict[type[ErroDeNegocio], int] = {
    DadosInvalidos: 422,
    NaoAutenticado: 401,
    AcessoNegado: 403,
    NaoEncontrado: 404,
    Conflito: 409,
    MuitasTentativas: 429,
}

MENSAGENS_DE_FORMATO = {
    "missing": "Campo obrigatório.",
    "extra_forbidden": "Campo não permitido.",
    "string_too_long": "Texto longo demais.",
    "string_type": "Informe um texto.",
    "int_parsing": "Informe um número inteiro.",
    "int_type": "Informe um número inteiro.",
    "int_from_float": "Informe um número inteiro.",
    "greater_than_equal": "Número fora do intervalo permitido.",
    "less_than_equal": "Número fora do intervalo permitido.",
    "date_type": "Data inválida.",
    "date_parsing": "Data inválida.",
    "date_from_datetime_parsing": "Data inválida.",
    "date_from_datetime_inexact": "Data inválida.",
    "decimal_parsing": "Valor em dinheiro inválido.",
    "decimal_type": "Valor em dinheiro inválido.",
    "bool_parsing": "Informe sim ou não.",
    "json_invalid": "Os dados enviados não estão em formato JSON válido.",
    "model_attributes_type": "Envie os dados em formato JSON.",
    "dict_type": "Envie os dados em formato JSON.",
}


def codigo_http(erro: ErroDeNegocio) -> int:
    for classe in type(erro).__mro__:
        if classe in CODIGO_HTTP:
            return CODIGO_HTTP[classe]
    return 400


async def tratar_erro_de_negocio(_requisicao: Request, erro: Exception) -> JSONResponse:
    assert isinstance(erro, ErroDeNegocio)
    corpo = ErroResposta(
        mensagem=erro.mensagem,
        campos={erro.campo: erro.mensagem} if erro.campo else None,
    )
    return JSONResponse(status_code=codigo_http(erro), content=corpo.model_dump())


async def tratar_erro_de_formato(_requisicao: Request, erro: Exception) -> JSONResponse:
    assert isinstance(erro, RequestValidationError)
    campos: dict[str, str] = {}
    for detalhe in erro.errors():
        local = [str(parte) for parte in detalhe.get("loc", ())
                 if parte not in ("body", "path", "query")]
        nome = ".".join(local) or "corpo"
        campos.setdefault(nome, MENSAGENS_DE_FORMATO.get(detalhe.get("type", ""), "Valor inválido."))
    corpo = ErroResposta(mensagem="Confira os dados enviados.", campos=campos)
    return JSONResponse(status_code=422, content=corpo.model_dump())


def registrar_tratadores_de_erro(app: FastAPI) -> None:
    app.add_exception_handler(ErroDeNegocio, tratar_erro_de_negocio)
    app.add_exception_handler(RequestValidationError, tratar_erro_de_formato)
