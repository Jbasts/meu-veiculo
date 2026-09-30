"""Tabela tentativa_acesso (migration 0002): base do limite de tentativas.

Guarda o SHA-256 do e-mail (não o e-mail) e o endereço de rede.
Linhas com mais de 1 dia são apagadas automaticamente.
"""

from datetime import datetime

from sqlalchemy import CHAR, BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

TIPO_LOGIN = "login"
TIPO_RECUPERACAO = "recuperacao"


class TentativaAcesso(Base):
    __tablename__ = "tentativa_acesso"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(12))
    chave_email: Mapped[str | None] = mapped_column(CHAR(64))
    ip: Mapped[str | None] = mapped_column(String(45))
    sucesso: Mapped[bool]
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
