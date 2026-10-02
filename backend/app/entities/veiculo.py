"""Tabela veiculo (SQL original + migrations 0003 e 0012).

- placa: sempre em maiúsculas, sem hífen e sem espaços (CHECK no banco);
  única por dono (usuario_id, placa), não no sistema inteiro.
- quilometragem e data_leitura_km: calculadas pelo banco a partir da tabela
  leitura_km (maior leitura válida). O backend nunca altera esses dois campos
  direto; ele registra ou corrige leituras.
- capacidade_tanque: litros do tanque de combustível líquido (0012). Vazio
  nos veículos antigos (a tela pede para informar) e no elétrico.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

COMBUSTIVEIS = ("flex", "gasolina", "etanol", "diesel", "gnv", "hibrido", "eletrico")


class Veiculo(Base):
    __tablename__ = "veiculo"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))
    marca: Mapped[str] = mapped_column(String(60))
    modelo: Mapped[str] = mapped_column(String(80))
    versao: Mapped[str | None] = mapped_column(String(80))
    ano: Mapped[int] = mapped_column(SmallInteger)
    placa: Mapped[str] = mapped_column(String(8))
    cor: Mapped[str | None] = mapped_column(String(40))
    tipo_combustivel: Mapped[str] = mapped_column(String(10), server_default=text("'flex'"))
    quilometragem: Mapped[int] = mapped_column(server_default=text("0"))
    data_leitura_km: Mapped[date | None]
    km_aquisicao: Mapped[int | None]
    data_aquisicao: Mapped[date | None]
    valor_aquisicao: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    capacidade_tanque: Mapped[Decimal | None] = mapped_column(Numeric(5, 1))
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@dataclass(frozen=True)
class VeiculoComDono:
    """Veículo com o nome do dono, para a lista "Todos os veículos" do admin."""

    id: int
    usuario_id: int
    marca: str
    modelo: str
    ano: int
    placa: str
    ativo: bool
    dono_nome: str
    dono_ativo: bool
