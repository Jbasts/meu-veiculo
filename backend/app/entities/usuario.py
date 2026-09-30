"""Tabela usuario (SQL original, com o e-mail normalizado pela migration 0002)."""

from datetime import datetime

from sqlalchemy import DateTime, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

PERFIL_ADMIN = "admin"
PERFIL_PADRAO = "padrao"


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120))
    # Sempre sem espaços nas pontas e em minúsculas (CHECK no banco).
    email: Mapped[str] = mapped_column(String(160))
    # Hash Argon2id. Nunca sai do backend (nenhum schema de resposta tem este campo).
    senha_hash: Mapped[str] = mapped_column(String(255))
    perfil: Mapped[str] = mapped_column(String(10), server_default=text("'padrao'"))
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def eh_admin(self) -> bool:
        return self.perfil == PERFIL_ADMIN
