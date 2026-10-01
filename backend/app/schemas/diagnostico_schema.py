"""Formatos JSON dos diagnósticos (problemas), anotações e resolução.

Como nos outros módulos: entradas com extra="forbid" (veiculo_id, status e
manutencao_id não vêm do formulário: mudam só pelas ações), datas "AAAA-MM-DD"
e dinheiro como texto ("280.00").
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.manutencao_schema import ManutencaoDetalheResposta


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class DiagnosticoEntrada(_Entrada):
    titulo: str = Field(max_length=500)
    descricao: str | None = Field(default=None, max_length=5000)
    sistema: str = Field(max_length=30)
    gravidade: str = Field(max_length=20)  # baixa | media | alta | critica
    data_identificacao: date
    quilometragem: int | None = None


class AcompanhamentoEntrada(_Entrada):
    status: str = Field(max_length=20)  # aberto | em_observacao


class DescarteEntrada(_Entrada):
    motivo: str | None = Field(default=None, max_length=5000)
    data: date | None = None  # vazio = hoje


class NotaEntrada(_Entrada):
    texto: str = Field(max_length=5000)
    data: date | None = None  # vazio = hoje


class VinculoEntrada(_Entrada):
    manutencao_id: int = Field(ge=1, le=2_147_483_647)


class ManutencaoLigadaResposta(BaseModel):
    """Resumo da manutenção que resolveu (realizada) ou vai resolver (agendada)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    status: str
    data: date
    valor: Decimal


class NotaResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    data: date
    texto: str
    criado_em: datetime


class GarantiaResposta(BaseModel):
    """Manutenção do mesmo sistema que estava em garantia na data do problema."""

    manutencao_id: int
    descricao: str
    data: date
    explicacao: str


class DiagnosticoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    titulo: str
    descricao: str | None
    sistema: str
    gravidade: str
    status: str  # aberto | em_observacao | resolvido | descartado
    data_identificacao: date
    quilometragem: int | None
    data_resolucao: date | None
    solucao: str | None  # motivo do descarte
    manutencao_id: int | None
    criado_em: datetime


class DiagnosticoResumoResposta(DiagnosticoResposta):
    total_notas: int
    manutencao: ManutencaoLigadaResposta | None


class DiagnosticoDetalheResposta(DiagnosticoResposta):
    notas: list[NotaResposta]  # da mais recente para a mais antiga
    manutencao: ManutencaoLigadaResposta | None
    garantias: list[GarantiaResposta]
    total_fotos: int


class PaginaDiagnosticos(BaseModel):
    itens: list[DiagnosticoResumoResposta]
    total: int
    pagina: int
    por_pagina: int


class ResolucaoResposta(BaseModel):
    diagnostico: DiagnosticoDetalheResposta
    manutencao: ManutencaoDetalheResposta
