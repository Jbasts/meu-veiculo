"""Formato JSON padrão das respostas de erro da API."""

from pydantic import BaseModel


class ErroResposta(BaseModel):
    # Texto em português para mostrar na tela.
    mensagem: str
    # Mensagem por campo do formulário, quando o erro é de um campo específico.
    campos: dict[str, str] | None = None
