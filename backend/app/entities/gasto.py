"""Tabela gasto (SQL original + migration 0007) e as linhas de despesa do mês.

Gasto: despesa avulsa do veículo (IPVA, seguro, multa, estacionamento...).
    data: o dia do gasto (lançamento).
    pago / data_pagamento: um gasto pago entra nas despesas no mês do
        pagamento. Gastos pagos antigos podem ter data_pagamento vazia (a
        data não é inventada); esses contam pela data do gasto.
    data_vencimento: obrigatório enquanto pendente (CHECK da 0007).

Despesa: uma linha da view vw_despesa (manutenção realizada, abastecimento,
gasto pago ou item de projeto), cada valor contado uma vez só.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

CATEGORIAS_DE_GASTO = ("ipva", "licenciamento", "seguro", "multa", "estacionamento", "pedagio",
                       "lavagem", "acessorios", "outros")
# Categorias que vêm de outras tabelas, no resumo do mês.
CATEGORIA_MANUTENCAO = "manutencao"
CATEGORIA_COMBUSTIVEL = "combustivel"
CATEGORIA_PROJETO = "projeto"

TIPO_MANUTENCAO = "manutencao"
TIPO_ABASTECIMENTO = "abastecimento"
TIPO_GASTO = "gasto"
TIPO_PROJETO = "projeto"


class Gasto(Base):
    __tablename__ = "gasto"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    categoria: Mapped[str] = mapped_column(String(20))
    descricao: Mapped[str | None] = mapped_column(String(150))
    data: Mapped[date] = mapped_column(server_default=func.current_date())
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    data_vencimento: Mapped[date | None]
    pago: Mapped[bool] = mapped_column(server_default=text("true"))
    data_pagamento: Mapped[date | None]
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@dataclass(frozen=True)
class Despesa:
    """Uma despesa efetivada do mês (linha de vw_despesa)."""

    tipo: str        # manutencao | abastecimento | gasto | projeto
    origem_id: int
    data: date
    categoria: str
    descricao: str | None
    valor: Decimal
    projeto_id: int | None = None  # só nos itens de projeto (migration 0011)
