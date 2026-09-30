"""Acesso à tabela tentativa_acesso (limite de tentativas)."""

from datetime import timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.entities.tentativa_acesso import TentativaAcesso

GUARDAR_POR = timedelta(days=1)


class TentativaAcessoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def registrar(self, tipo: str, chave_email: str | None, ip: str | None, sucesso: bool) -> None:
        self._sessao.execute(
            delete(TentativaAcesso).where(TentativaAcesso.criado_em < func.now() - GUARDAR_POR)
        )
        self._sessao.add(TentativaAcesso(tipo=tipo, chave_email=chave_email, ip=ip, sucesso=sucesso))
        self._sessao.flush()

    def contar(self, tipo: str, janela: timedelta, *, chave_email: str | None = None,
               ip: str | None = None, somente_falhas: bool = False) -> int:
        consulta = select(func.count()).select_from(TentativaAcesso).where(
            TentativaAcesso.tipo == tipo,
            TentativaAcesso.criado_em > func.now() - janela,
        )
        if chave_email is not None:
            consulta = consulta.where(TentativaAcesso.chave_email == chave_email)
        if ip is not None:
            consulta = consulta.where(TentativaAcesso.ip == ip)
        if somente_falhas:
            consulta = consulta.where(TentativaAcesso.sucesso.is_(False))
        return self._sessao.scalar(consulta) or 0
