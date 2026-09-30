"""Tabela sessao (migration 0002): uma linha por login.

O navegador guarda o token num cookie; o banco guarda só o SHA-256 dele.
Quem ler o banco não consegue se passar pelo usuário.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base
from app.entities.usuario import Usuario


class Sessao(Base):
    __tablename__ = "sessao"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    criada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ultimo_uso_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revogada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_revogacao: Mapped[str | None] = mapped_column(String(30))


@dataclass(frozen=True)
class SessaoAtual:
    """Quem está fazendo a requisição e por qual sessão."""

    usuario: Usuario
    sessao_id: int
