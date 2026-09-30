"""Acesso à tabela sessao. Datas e prazos usam o relógio do PostgreSQL (now())."""

from datetime import timedelta

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.entities.sessao import Sessao
from app.entities.usuario import Usuario

# O uso da sessão (e o "último acesso" do usuário) é gravado no máximo a cada 5 minutos.
INTERVALO_REGISTRO_USO = timedelta(minutes=5)


class SessaoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def criar(self, usuario_id: int, token_hash: str, validade: timedelta) -> Sessao:
        registro = Sessao(usuario_id=usuario_id, token_hash=token_hash,
                          expira_em=func.now() + validade)
        self._sessao.add(registro)
        self._sessao.flush()
        return registro

    def buscar_valida(self, token_hash: str) -> tuple[Sessao, Usuario] | None:
        """Sessão não revogada e não expirada, com o dono (ativo ou não)."""
        linha = self._sessao.execute(
            select(Sessao, Usuario)
            .join(Usuario, Usuario.id == Sessao.usuario_id)
            .where(
                Sessao.token_hash == token_hash,
                Sessao.revogada_em.is_(None),
                Sessao.expira_em > func.now(),
            )
        ).first()
        return (linha[0], linha[1]) if linha else None

    def registrar_uso(self, sessao_id: int, usuario_id: int) -> None:
        resultado = self._sessao.execute(
            update(Sessao)
            .where(Sessao.id == sessao_id,
                   Sessao.ultimo_uso_em < func.now() - INTERVALO_REGISTRO_USO)
            .values(ultimo_uso_em=func.now())
            .execution_options(synchronize_session=False)
        )
        if resultado.rowcount:
            self.registrar_acesso(usuario_id)

    def registrar_acesso(self, usuario_id: int) -> None:
        self._sessao.execute(
            update(Usuario).where(Usuario.id == usuario_id).values(ultimo_acesso=func.now())
            .execution_options(synchronize_session=False)
        )

    def revogar(self, sessao_id: int, motivo: str) -> None:
        self._sessao.execute(
            update(Sessao)
            .where(Sessao.id == sessao_id, Sessao.revogada_em.is_(None))
            .values(revogada_em=func.now(), motivo_revogacao=motivo)
            .execution_options(synchronize_session=False)
        )

    def revogar_do_usuario(self, usuario_id: int, motivo: str,
                           exceto_sessao_id: int | None = None) -> int:
        condicoes = [Sessao.usuario_id == usuario_id, Sessao.revogada_em.is_(None)]
        if exceto_sessao_id is not None:
            condicoes.append(Sessao.id != exceto_sessao_id)
        resultado = self._sessao.execute(
            update(Sessao).where(*condicoes)
            .values(revogada_em=func.now(), motivo_revogacao=motivo)
            .execution_options(synchronize_session=False)
        )
        return resultado.rowcount
