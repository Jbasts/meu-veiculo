"""Acesso à tabela usuario."""

from sqlalchemy import select
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session

from app.entities.usuario import PERFIL_PADRAO, Usuario
from app.repositories.erros import EmailJaCadastrado, UltimoAdministrador, dica_do_erro

INDICE_EMAIL_UNICO = "usuario_email_unico"


def _restricao_violada(erro: IntegrityError) -> str | None:
    diagnostico = getattr(erro.orig, "diag", None)
    return getattr(diagnostico, "constraint_name", None)


class UsuarioRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        return self._sessao.get(Usuario, usuario_id)

    def buscar_por_email(self, email_normalizado: str) -> Usuario | None:
        return self._sessao.scalar(select(Usuario).where(Usuario.email == email_normalizado))

    def criar(self, nome: str, email_normalizado: str, senha_hash: str) -> Usuario:
        """Cria sempre com perfil padrão e conta ativa."""
        usuario = Usuario(
            nome=nome, email=email_normalizado, senha_hash=senha_hash,
            perfil=PERFIL_PADRAO, ativo=True,
        )
        self._sessao.add(usuario)
        try:
            # SAVEPOINT: se o e-mail já existir, só esta inserção é desfeita.
            with self._sessao.begin_nested():
                self._sessao.flush()
        except IntegrityError as erro:
            if _restricao_violada(erro) == INDICE_EMAIL_UNICO:
                raise EmailJaCadastrado() from None
            raise
        return usuario

    def atualizar_senha(self, usuario: Usuario, senha_hash: str) -> None:
        usuario.senha_hash = senha_hash
        self._sessao.flush()

    def definir_perfil(self, usuario: Usuario, perfil: str) -> None:
        usuario.perfil = perfil
        self._sessao.flush()

    def bloquear(self, usuario_id: int) -> Usuario | None:
        """Busca e segura a linha até o fim da transação (alterações do admin em sequência)."""
        return self._sessao.scalar(
            select(Usuario).where(Usuario.id == usuario_id).with_for_update()
            .execution_options(populate_existing=True)
        )

    def alterar_acesso(self, usuario: Usuario, perfil: str, ativo: bool) -> None:
        """Perfil e conta ativa. O banco recusa deixar o sistema sem admin ativo."""
        usuario.perfil = perfil
        usuario.ativo = ativo
        try:
            # SAVEPOINT: se o trigger do último admin recusar, só isto é desfeito.
            with self._sessao.begin_nested():
                self._sessao.flush()
        except DBAPIError as erro:
            if dica_do_erro(erro) == "ultimo_admin":
                self._sessao.refresh(usuario)
                raise UltimoAdministrador() from None
            raise
