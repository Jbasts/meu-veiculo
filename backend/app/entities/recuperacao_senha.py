"""Tabela recuperacao_senha (migration 0002): links de uso único para definir senha.

finalidade "recuperacao" = "Esqueci minha senha";
finalidade "convite" = conta criada pelo administrador (etapa 9).
"""

from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base


class RecuperacaoSenha(Base):
    __tablename__ = "recuperacao_senha"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    finalidade: Mapped[str] = mapped_column(String(12), server_default=text("'recuperacao'"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    usado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
