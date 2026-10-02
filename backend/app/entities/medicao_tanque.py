"""Tabela medicao_tanque (migration 0012): marcação do tanque sem abastecer.

A Paula registra, de preferência no início de cada mês, a quilometragem e o
que o marcador mostra. nivel é em oitavos do tanque (0 = vazio, 2 = 1/4,
3 = "1,5/4", 4 = meio, 8 = cheio). A quilometragem vira leitura do hodômetro
(trigger da 0012), como a do abastecimento.
"""

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, SmallInteger, func
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

OITAVOS_DO_TANQUE = 8


class MedicaoTanque(Base):
    __tablename__ = "medicao_tanque"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    data: Mapped[date]
    quilometragem: Mapped[int]
    nivel: Mapped[int] = mapped_column(SmallInteger)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
