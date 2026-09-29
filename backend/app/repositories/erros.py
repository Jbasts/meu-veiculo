"""Erros da camada de acesso ao banco.

O repository traduz os erros técnicos do driver (que podem conter host,
usuário e detalhes internos) para estes erros simples. Assim, os services
não dependem do SQLAlchemy e nada técnico vaza para a resposta da API.
"""


class ErroRepositorio(Exception):
    pass


class BancoIndisponivel(ErroRepositorio):
    """Não foi possível falar com o PostgreSQL."""
