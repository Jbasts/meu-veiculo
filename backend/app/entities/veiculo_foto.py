"""Tabela veiculo_foto (SQL original): metadados das fotos.

O arquivo em si fica na pasta de fotos do backend (PASTA_FOTOS), fora do
PostgreSQL; aqui vai só o caminho relativo, com nome gerado pelo backend.
Os vínculos (projeto, diagnóstico, manutenção) começam a ser usados nas
etapas desses módulos.
"""

from dataclasses import dataclass
from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

TAMANHO_MAXIMO_BYTES = 10_485_760  # 10 MB, o mesmo limite do CHECK do banco


class VeiculoFoto(Base):
    __tablename__ = "veiculo_foto"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    arquivo: Mapped[str] = mapped_column(String(255), unique=True)
    tipo_mime: Mapped[str] = mapped_column(String(20))
    tamanho_bytes: Mapped[int]
    legenda: Mapped[str | None] = mapped_column(String(150))
    data_foto: Mapped[date] = mapped_column(server_default=func.current_date())
    principal: Mapped[bool] = mapped_column(server_default=text("false"))
    # As chaves estrangeiras destes vínculos existem no banco; aqui elas serão
    # declaradas quando as entities Projeto, Diagnostico e Manutencao existirem.
    projeto_id: Mapped[int | None]
    momento: Mapped[str | None] = mapped_column(String(6))
    diagnostico_id: Mapped[int | None]
    manutencao_id: Mapped[int | None]
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@dataclass(frozen=True)
class ImagemPronta:
    """Imagem já conferida e regravada pelo backend, pronta para guardar."""

    conteudo: bytes
    tipo_mime: str
    extensao: str
