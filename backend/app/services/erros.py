"""Erros de regra de negócio.

Os services levantam estes erros; os controllers os traduzem para o código
HTTP correspondente (veja app/controllers/erros_http.py). Assim, o service
não precisa saber nada de HTTP, e a mesma regra vale para qualquer tela.

A mensagem é escrita para a pessoa que usa o sistema, em português, e nunca
deve conter senha, token ou detalhes internos. "campo" indica qual campo do
formulário deve mostrar a mensagem (opcional).
"""


class ErroDeNegocio(Exception):
    def __init__(self, mensagem: str, campo: str | None = None):
        self.mensagem = mensagem
        self.campo = campo
        super().__init__(mensagem)


class DadosInvalidos(ErroDeNegocio):
    """Os dados enviados não obedecem a uma regra (HTTP 422)."""


class NaoAutenticado(ErroDeNegocio):
    """É preciso entrar no sistema (HTTP 401)."""


class AcessoNegado(ErroDeNegocio):
    """A pessoa está logada, mas não pode fazer isto (HTTP 403)."""


class NaoEncontrado(ErroDeNegocio):
    """O registro não existe ou não pertence a quem pediu (HTTP 404)."""


class Conflito(ErroDeNegocio):
    """Choque com um dado existente, como e-mail repetido (HTTP 409)."""


class MuitasTentativas(ErroDeNegocio):
    """Limite de tentativas atingido; tente mais tarde (HTTP 429)."""
