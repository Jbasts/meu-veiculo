"""Tabelas plano_manutencao e manutencao (SQL original + migration 0004) e os
objetos calculados da aba "Pendentes".

Plano: o que se repete ("troca de óleo a cada 10.000 km ou 12 meses").
    data_base / km_base: de onde o intervalo é contado enquanto não houver
    manutenção realizada do plano. Planos antigos podem estar sem base.

Manutenção: o que foi feito (realizada) ou está marcado (agendada).
    A situação "em dia / próxima / atrasada" não é gravada: o banco calcula
    (view vw_situacao_manutencao e função classificar_prazo).
    garantia_km é um LIMITE DO HODÔMETRO ("garantia até os 95.000 km"), não
    uma distância de cobertura.
    proxima_data / proxima_km: lembrete manual, só para manutenção avulsa
    realizada. Em manutenção de plano, quem define a próxima é o plano.
    valor: total. Com itens (migration 0005), é sempre a soma deles; sem
    itens, é o valor informado à mão.

Item da manutenção (migration 0005): uma peça ou um serviço de mão de obra,
com nome e valor. Apagar a manutenção apaga os itens.
"""

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, ForeignKeyConstraint, Numeric, SmallInteger, String
from sqlalchemy import Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

SISTEMAS = ("motor", "transmissao", "suspensao", "freios", "direcao", "pneus", "eletrica",
            "arrefecimento", "ar_condicionado", "carroceria", "interior", "outros")

STATUS_REALIZADA = "realizada"
STATUS_AGENDADA = "agendada"

SITUACAO_ATRASADA = "atrasada"
SITUACAO_PROXIMA = "proxima"
SITUACAO_EM_DIA = "em_dia"
SITUACAO_SEM_BASE = "sem_base"

ITEM_PECA = "peca"
ITEM_MAO_DE_OBRA = "mao_de_obra"
TIPOS_DE_ITEM = (ITEM_PECA, ITEM_MAO_DE_OBRA)

TIPO_PLANO = "plano"          # obrigação recorrente de um plano ativo
TIPO_AGENDADA = "agendada"    # manutenção agendada sem plano ativo
TIPO_LEMBRETE = "lembrete"    # "próxima" informada numa manutenção avulsa realizada


class PlanoManutencao(Base):
    __tablename__ = "plano_manutencao"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String(100))
    sistema: Mapped[str] = mapped_column(String(20), server_default=text("'outros'"))
    intervalo_km: Mapped[int | None]
    intervalo_meses: Mapped[int | None] = mapped_column(SmallInteger)
    ativo: Mapped[bool] = mapped_column(server_default=text("true"))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    data_base: Mapped[date | None]
    km_base: Mapped[int | None]


class Manutencao(Base):
    __tablename__ = "manutencao"
    __table_args__ = (
        # O plano precisa ser do MESMO veículo (chave composta da migration 0004).
        ForeignKeyConstraint(["plano_id", "veiculo_id"],
                             ["plano_manutencao.id", "plano_manutencao.veiculo_id"]),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    plano_id: Mapped[int | None]
    descricao: Mapped[str] = mapped_column(String(150))
    sistema: Mapped[str] = mapped_column(String(20), server_default=text("'outros'"))
    status: Mapped[str] = mapped_column(String(10), server_default=text("'realizada'"))
    data: Mapped[date] = mapped_column(server_default=func.current_date())
    quilometragem: Mapped[int | None]
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2), server_default=text("0"))
    oficina: Mapped[str | None] = mapped_column(String(120))
    garantia_ate: Mapped[date | None]
    garantia_km: Mapped[int | None]
    proxima_data: Mapped[date | None]
    proxima_km: Mapped[int | None]
    observacao: Mapped[str | None] = mapped_column(Text)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def realizada(self) -> bool:
        return self.status == STATUS_REALIZADA


class ManutencaoItem(Base):
    __tablename__ = "manutencao_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    manutencao_id: Mapped[int] = mapped_column(ForeignKey("manutencao.id", ondelete="CASCADE"))
    tipo: Mapped[str] = mapped_column(String(12))  # peca | mao_de_obra
    nome: Mapped[str] = mapped_column(String(150))
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


@dataclass(frozen=True)
class SituacaoPlano:
    """Uma linha da view vw_situacao_manutencao (só planos ativos)."""

    plano_id: int
    situacao: str
    referencia_data: date | None
    referencia_km: int | None
    proxima_data: date | None
    proxima_km: int | None
    km_restantes: int | None
    dias_restantes: int | None


@dataclass(frozen=True)
class Pendencia:
    """Uma obrigação da aba "Pendentes". Cada obrigação aparece uma única vez."""

    tipo: str
    situacao: str
    titulo: str
    sistema: str
    plano_id: int | None
    manutencao_id: int | None
    proxima_data: date | None
    proxima_km: int | None
    dias_restantes: int | None
    km_restantes: int | None
    intervalo_km: int | None = None
    intervalo_meses: int | None = None
    # Plano que já tem manutenção agendada: mostrada junto, não como outro alerta.
    agendada_id: int | None = None
    agendada_data: date | None = None
