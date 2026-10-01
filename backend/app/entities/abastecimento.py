"""Tabela abastecimento (SQL original + migrations 0008, 0009 e 0010).

combustivel: gasolina, etanol, diesel, gnv ou eletrica (recarga).
litros: a quantidade abastecida, na unidade do combustível (litros; m³ no
    GNV; kWh na eletricidade). A coluna é a mesma.
tipo: um dos tipos do combustível (TIPOS_DO_COMBUSTIVEL, 0010); vazio nos
    abastecimentos antigos (não informado) e no GNV.
valor_total: litros × valor_litro arredondado meio para cima, ou o valor do
    cupom quando difere no máximo R$ 50,00 (CHECK da 0009).
tanque_cheio: o consumo é calculado entre dois abastecimentos de tanque cheio.
A quilometragem vira leitura do hodômetro (migration 0003).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

GASOLINA = "gasolina"
ETANOL = "etanol"
DIESEL = "diesel"
GNV = "gnv"
ELETRICA = "eletrica"  # recarga; "eletrica" cabe nos 10 caracteres da coluna
COMBUSTIVEIS = (GASOLINA, ETANOL, DIESEL, GNV, ELETRICA)

# Tabela da Paula (01/10/2026): tipos de cada combustível. GNV não tem tipo.
TIPOS_DO_COMBUSTIVEL: dict[str, tuple[str, ...]] = {
    GASOLINA: ("comum", "comum_aditivada", "premium", "premium_aditivada"),
    ETANOL: ("comum", "aditivado", "premium", "premium_aditivado"),
    DIESEL: ("s10", "s10_aditivado", "s500", "s500_aditivado"),
    GNV: (),
    ELETRICA: ("ac", "dc"),
}

# Combustíveis aceitos conforme o tipo do veículo (veiculo.tipo_combustivel).
COMBUSTIVEIS_DO_VEICULO: dict[str, tuple[str, ...]] = {
    "flex": (GASOLINA, ETANOL),
    "gasolina": (GASOLINA,),
    "etanol": (ETANOL,),
    "diesel": (DIESEL,),
    "gnv": (GNV, GASOLINA, ETANOL),  # kit GNV em carro a gasolina/flex
    "hibrido": (GASOLINA, ELETRICA),  # decisão da Paula: inclui o híbrido plug-in
    "eletrico": (ELETRICA,),
}


class Abastecimento(Base):
    __tablename__ = "abastecimento"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    data: Mapped[date] = mapped_column(server_default=func.current_date())
    quilometragem: Mapped[int]
    combustivel: Mapped[str] = mapped_column(String(10))
    tipo: Mapped[str | None] = mapped_column(String(20))
    litros: Mapped[Decimal] = mapped_column(Numeric(7, 3))
    valor_litro: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    valor_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tanque_cheio: Mapped[bool] = mapped_column(server_default=text("true"))
    posto: Mapped[str | None] = mapped_column(String(80))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
