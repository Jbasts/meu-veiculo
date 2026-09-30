"""Formatos JSON de cadastro, login e senha.

Entradas usam extra="forbid": um campo que não existe no formulário (por
exemplo "perfil": "admin") faz a requisição ser recusada. Os limites de
tamanho aqui só evitam textos gigantes; as regras (8 caracteres, e-mail
válido...) ficam nos services, com mensagens em português.
"""

from pydantic import BaseModel, ConfigDict, Field


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CadastroEntrada(_Entrada):
    nome: str = Field(max_length=300)
    email: str = Field(max_length=320)
    senha: str = Field(max_length=1000)
    confirmacao_senha: str = Field(max_length=1000)


class LoginEntrada(_Entrada):
    email: str = Field(max_length=320)
    senha: str = Field(max_length=1000)


class AlterarSenhaEntrada(_Entrada):
    senha_atual: str = Field(max_length=1000)
    nova_senha: str = Field(max_length=1000)
    confirmacao_senha: str = Field(max_length=1000)


class RecuperarSenhaEntrada(_Entrada):
    email: str = Field(max_length=320)


class RedefinirSenhaEntrada(_Entrada):
    token: str = Field(max_length=300)
    nova_senha: str = Field(max_length=1000)
    confirmacao_senha: str = Field(max_length=1000)


class UsuarioResposta(BaseModel):
    """Dados da conta que podem ir para a tela. Nunca inclui senha_hash."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool


class MensagemResposta(BaseModel):
    mensagem: str
