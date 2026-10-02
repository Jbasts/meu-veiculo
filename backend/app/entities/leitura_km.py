"""Tabela leitura_km (migration 0003): histórico de leituras do hodômetro.

data_leitura é o dia em que o hodômetro marcava aquele valor; criado_em é
quando a leitura foi digitada. Uma leitura errada não é apagada: fica
anulada (anulada_em) e deixa de contar; a leitura que a substitui aponta
para ela em corrige_id.
"""

from datetime import date, datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

ORIGEM_CADASTRO = "cadastro"
ORIGEM_MANUAL = "manual"
ORIGEM_LEGADO = "legado"
# Leituras que o usuário corrige na própria tela de quilometragem. As demais
# vêm de um abastecimento, manutenção, diagnóstico ou marcação do tanque e são
# corrigidas lá.
ORIGENS_EDITAVEIS = (ORIGEM_CADASTRO, ORIGEM_MANUAL, ORIGEM_LEGADO)


class LeituraKm(Base):
    __tablename__ = "leitura_km"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    quilometragem: Mapped[int]
    # Só a leitura herdada ("legado") fica sem data: ela é desconhecida.
    data_leitura: Mapped[date | None]
    origem: Mapped[str] = mapped_column(String(15))
    origem_id: Mapped[int | None]
    corrige_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("leitura_km.id", ondelete="SET NULL"))
    anulada_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    motivo_anulacao: Mapped[str | None] = mapped_column(String(200))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def valida(self) -> bool:
        return self.anulada_em is None

    @property
    def editavel(self) -> bool:
        return self.valida and self.origem in ORIGENS_EDITAVEIS
