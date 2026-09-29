"""Formato JSON padrão das respostas de erro da API."""

from pydantic import BaseModel


class ErroResposta(BaseModel):
    # Texto em português para mostrar na tela.
    mensagem: str
