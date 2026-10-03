"""Acesso à tabela recuperacao_senha."""

from datetime import timedelta

from sqlalchemy import func, update
from sqlalchemy.orm import Session

from app.entities.recuperacao_senha import RecuperacaoSenha


class RecuperacaoSenhaRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def criar(self, usuario_id: int, token_hash: str, validade: timedelta,
              finalidade: str = "recuperacao") -> None:
        self._sessao.add(RecuperacaoSenha(
            usuario_id=usuario_id, token_hash=token_hash, finalidade=finalidade,
            expira_em=func.now() + validade,
        ))
        self._sessao.flush()

    def cancelar_pendentes(self, usuario_id: int) -> None:
        """Um link novo invalida os anteriores ainda não usados."""
        self._sessao.execute(
            update(RecuperacaoSenha)
            .where(RecuperacaoSenha.usuario_id == usuario_id,
                   RecuperacaoSenha.usado_em.is_(None),
                   RecuperacaoSenha.cancelado_em.is_(None))
            .values(cancelado_em=func.now())
            .execution_options(synchronize_session=False)
        )

    def consumir(self, token_hash: str, finalidades: tuple[str, ...]) -> int | None:
        """Marca o link como usado e devolve o id do usuário, numa única instrução.

        Se duas requisições chegarem juntas com o mesmo link, o PostgreSQL
        faz a segunda esperar a primeira; quando a primeira grava usado_em,
        a condição "usado_em IS NULL" deixa de valer e a segunda não recebe
        nada. Ou seja: o link funciona uma única vez. "finalidades": um link
        de confirmação de e-mail não troca senha, e vice-versa.
        """
        return self._sessao.execute(
            update(RecuperacaoSenha)
            .where(RecuperacaoSenha.token_hash == token_hash,
                   RecuperacaoSenha.finalidade.in_(finalidades),
                   RecuperacaoSenha.usado_em.is_(None),
                   RecuperacaoSenha.cancelado_em.is_(None),
                   RecuperacaoSenha.expira_em > func.now())
            .values(usado_em=func.now())
            .returning(RecuperacaoSenha.usuario_id)
            .execution_options(synchronize_session=False)
        ).scalar()
