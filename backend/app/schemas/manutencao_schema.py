"""Formatos JSON de planos de manutenção, manutenções e pendências.

Como nos outros módulos: entradas com extra="forbid" (veiculo_id e ativo não
vêm da tela), datas "AAAA-MM-DD" e dinheiro como texto ("280.00").
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.veiculo_schema import Dinheiro


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------- planos

class PlanoEntrada(_Entrada):
    nome: str = Field(max_length=300)
    sistema: str = Field(max_length=30)
    intervalo_km: int | None = None
    intervalo_meses: int | None = None
    # De onde o intervalo é contado enquanto não há manutenção realizada do plano.
    data_base: date | None = None
    km_base: int | None = None


class PlanoResposta(BaseModel):
    id: int
    veiculo_id: int
    nome: str
    sistema: str
    intervalo_km: int | None
    intervalo_meses: int | None
    data_base: date | None
    km_base: int | None
    ativo: bool
    criado_em: datetime
    # Calculados pelo banco; todos null quando o plano está inativo.
    situacao: str | None          # atrasada | proxima | em_dia | sem_base
    referencia_data: date | None  # o mais recente entre a base e a última manutenção
    referencia_km: int | None
    proxima_data: date | None
    proxima_km: int | None
    dias_restantes: int | None
    km_restantes: int | None


# ----------------------------------------------------------------- manutenções

class ItemEntrada(_Entrada):
    tipo: str = Field(max_length=20)   # peca | mao_de_obra
    nome: str = Field(max_length=500)
    valor: Dinheiro | None = None


class ItemResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo: str
    nome: str
    valor: Decimal


class ManutencaoEntrada(_Entrada):
    descricao: str = Field(max_length=500)
    sistema: str = Field(max_length=30)
    status: str = Field(max_length=20)
    data: date
    quilometragem: int | None = None
    # Só sem itens. Com itens, o total é a soma deles (calculada pelo backend).
    valor: Dinheiro | None = None
    oficina: str | None = Field(default=None, max_length=500)
    plano_id: int | None = None
    garantia_ate: date | None = None
    garantia_km: int | None = None  # limite do hodômetro, não distância
    proxima_data: date | None = None
    proxima_km: int | None = None
    observacao: str | None = Field(default=None, max_length=5000)
    # A lista inteira: na edição, substitui os itens que a manutenção tinha.
    itens: list[ItemEntrada] = Field(default_factory=list, max_length=200)


class ManutencaoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    plano_id: int | None
    descricao: str
    sistema: str
    status: str
    data: date
    quilometragem: int | None
    valor: Decimal
    oficina: str | None
    garantia_ate: date | None
    garantia_km: int | None
    proxima_data: date | None
    proxima_km: int | None
    observacao: str | None
    criado_em: datetime


class DiagnosticoLigadoResposta(BaseModel):
    """Diagnóstico resolvido por esta manutenção, ou à espera dela (agendada)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    titulo: str
    status: str
    gravidade: str
    data_identificacao: date


class ManutencaoDetalheResposta(ManutencaoResposta):
    plano_nome: str | None
    # vigente | vencida | sem_informacao | nao_se_aplica
    garantia_situacao: str
    garantia_explicacao: str
    total_fotos: int
    itens: list[ItemResposta]
    # null quando não há itens: só o total, sem detalhamento (não é zero).
    total_pecas: Decimal | None
    total_mao_de_obra: Decimal | None
    diagnosticos: list[DiagnosticoLigadoResposta]


class PaginaManutencoes(BaseModel):
    itens: list[ManutencaoResposta]
    total: int
    pagina: int
    por_pagina: int


# ------------------------------------------------------------------ pendências

class PendenciaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo: str       # plano | agendada | lembrete
    situacao: str   # atrasada | proxima | em_dia | sem_base
    titulo: str
    sistema: str
    plano_id: int | None
    manutencao_id: int | None
    proxima_data: date | None
    proxima_km: int | None
    dias_restantes: int | None
    km_restantes: int | None
    intervalo_km: int | None
    intervalo_meses: int | None
    agendada_id: int | None
    agendada_data: date | None


class PendentesResposta(BaseModel):
    km_atual: int
    itens: list[PendenciaResposta]
