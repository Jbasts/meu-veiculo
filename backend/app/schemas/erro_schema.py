"""Formato JSON padrão das respostas de erro da API."""

from pydantic import BaseModel


class ErroResposta(BaseModel):
    # Texto em português para mostrar na tela.
    mensagem: str
    # Mensagem por campo do formulário, quando o erro é de um campo específico.
    campos: dict[str, str] | None = None


class ErroComCodigo(ErroResposta):
    # Identifica um caso que a tela trata de um jeito próprio
    # (ex.: "email_nao_confirmado"). Só usado quando o erro tem código.
    codigo: str
