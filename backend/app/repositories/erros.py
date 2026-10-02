"""Erros da camada de acesso ao banco.

O repository traduz os erros técnicos do driver (que podem conter host,
usuário e detalhes internos) para estes erros simples. Assim, os services
não dependem do SQLAlchemy e nada técnico vaza para a resposta da API.
"""


class ErroRepositorio(Exception):
    pass


class BancoIndisponivel(ErroRepositorio):
    """Não foi possível falar com o PostgreSQL."""


class EmailJaCadastrado(ErroRepositorio):
    """O índice único usuario_email_unico recusou o e-mail."""


class PlacaJaCadastrada(ErroRepositorio):
    """A restrição UNIQUE (usuario_id, placa) recusou a placa."""


class UltimoAdministrador(ErroRepositorio):
    """O trigger garantir_admin_ativo (migration 0002) recusou deixar o sistema sem admin ativo."""


def dica_do_erro(erro: Exception) -> str | None:
    """HINT de um RAISE EXCEPTION do banco (ex.: 'ultimo_admin'), ou None."""
    diagnostico = getattr(getattr(erro, "orig", None), "diag", None)
    return getattr(diagnostico, "message_hint", None)


def restricao_violada(erro: Exception) -> str | None:
    """Nome da restrição do banco que causou o erro (None se não houver)."""
    diagnostico = getattr(getattr(erro, "orig", None), "diag", None)
    return getattr(diagnostico, "constraint_name", None)
