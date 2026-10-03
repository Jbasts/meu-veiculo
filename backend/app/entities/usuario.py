"""Tabela usuario (SQL original, com o e-mail normalizado pela migration 0002
e o veículo em uso da migration 0003)."""

from dataclasses import dataclass
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
    # Migration 0014: conta criada pela tela só entra depois de confirmar o e-mail.
    email_confirmado: Mapped[bool] = mapped_column(server_default=text("false"))
    email_confirmado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ultimo_acesso: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Veículo selecionado nas telas. O banco garante que é um veículo do próprio usuário.
    veiculo_em_uso_id: Mapped[int | None]

    @property
    def eh_admin(self) -> bool:
        return self.perfil == PERFIL_ADMIN


@dataclass(frozen=True)
class UsuarioResumo:
    """Linha da view vw_usuario_resumo (sem senha_hash) para a administração."""

    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool
    ultimo_acesso: datetime | None
    criado_em: datetime
    veiculos_ativos: int
    veiculos: int
