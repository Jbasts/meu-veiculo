"""Tabelas diagnostico e diagnostico_nota (SQL original + migration 0006).

Diagnóstico: um problema do dia a dia ("barulho na suspensão dianteira").
    status: aberto | em_observacao | resolvido | descartado.
    manutencao_id: a manutenção ligada. A situação precisa combinar com a dela
    (conferido por trigger na migration 0006):
      resolvido            -> manutenção realizada (a que resolveu);
      aberto/em observação -> manutenção agendada (a prevista para resolver);
      descartado           -> sem manutenção.
    data_resolucao: dia em que foi resolvido (a data da manutenção) ou descartado.
    solucao: motivo informado ao descartar.
    A quilometragem, se informada, vira leitura do hodômetro (migration 0003).

Anotação: o que foi observado ao longo do tempo, com data.
"""

from datetime import date, datetime

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

ABERTO = "aberto"
EM_OBSERVACAO = "em_observacao"
RESOLVIDO = "resolvido"
DESCARTADO = "descartado"
STATUS_EM_ABERTO = (ABERTO, EM_OBSERVACAO)
STATUS_ENCERRADOS = (RESOLVIDO, DESCARTADO)

GRAVIDADES = ("baixa", "media", "alta", "critica")

FILTRO_ABERTOS = "abertos"        # aberto e em observação
FILTRO_RESOLVIDOS = "resolvidos"  # resolvido e descartado
FILTRO_TODOS = "todos"


class Diagnostico(Base):
    __tablename__ = "diagnostico"
    __table_args__ = (
        # A manutenção precisa ser do MESMO veículo (chave composta da migration 0006).
        ForeignKeyConstraint(["manutencao_id", "veiculo_id"],
                             ["manutencao.id", "manutencao.veiculo_id"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    titulo: Mapped[str] = mapped_column(String(150))
    descricao: Mapped[str | None] = mapped_column(Text)
    sistema: Mapped[str] = mapped_column(String(20), server_default=text("'outros'"))
    gravidade: Mapped[str] = mapped_column(String(10), server_default=text("'media'"))
    status: Mapped[str] = mapped_column(String(15), server_default=text("'aberto'"))
    data_identificacao: Mapped[date] = mapped_column(server_default=func.current_date())
    quilometragem: Mapped[int | None]
    data_resolucao: Mapped[date | None]
    solucao: Mapped[str | None] = mapped_column(Text)
    manutencao_id: Mapped[int | None]
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def em_aberto(self) -> bool:
        return self.status in STATUS_EM_ABERTO


class DiagnosticoNota(Base):
    __tablename__ = "diagnostico_nota"

    id: Mapped[int] = mapped_column(primary_key=True)
    diagnostico_id: Mapped[int] = mapped_column(ForeignKey("diagnostico.id", ondelete="CASCADE"))
    data: Mapped[date] = mapped_column(server_default=func.current_date())
    texto: Mapped[str] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
