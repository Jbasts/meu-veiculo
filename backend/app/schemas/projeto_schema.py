"""Formatos JSON dos projetos de melhoria e dos gastos do projeto.

Entradas com extra="forbid": o status e a data de conclusão não vêm do
formulário (mudam pelas ações), e totais nunca vêm da tela.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.veiculo_schema import Dinheiro


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjetoEntrada(_Entrada):
    nome: str = Field(max_length=500)
    descricao: str | None = Field(default=None, max_length=5000)
    categoria: str = Field(max_length=20)       # exterior | interior | mecanica | som | outros
    orcamento: Dinheiro | None = None
    data_prevista: date | None = None


class ProjetoNovoEntrada(ProjetoEntrada):
    status: str = Field(default="planejado", max_length=20)  # planejado | em_andamento


class ConclusaoEntrada(_Entrada):
    data_conclusao: date | None = None  # vazio = hoje


class ItemEntrada(_Entrada):
    descricao: str = Field(max_length=500)
    data: date
    valor: Dinheiro | None = None


class ItemResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    descricao: str
    data: date
    valor: Decimal


class ProjetoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    nome: str
    descricao: str | None
    categoria: str
    orcamento: Decimal | None
    data_prevista: date | None
    status: str                 # planejado | em_andamento | concluido | cancelado
    data_conclusao: date | None
    criado_em: datetime


class ProjetoResumoResposta(ProjetoResposta):
    gasto: Decimal                  # soma dos itens
    percentual: int | None          # do orçamento; null sem orçamento ou com orçamento zero
    diferenca: Decimal | None       # orçamento − gasto (negativa = excedido); null sem orçamento
    quantidade_itens: int
    foto_antes_id: int | None       # a primeira (mais antiga) de cada momento
    foto_depois_id: int | None


class ProjetoDetalheResposta(ProjetoResumoResposta):
    itens: list[ItemResposta]
    fotos_antes: list[int]
    fotos_depois: list[int]
    total_fotos: int                # todas as fotos ligadas ao projeto (com ou sem momento)


class ContagemPorStatus(BaseModel):
    planejado: int
    em_andamento: int
    concluido: int
    cancelado: int


class PaginaProjetos(BaseModel):
    itens: list[ProjetoResumoResposta]
    total: int
    pagina: int
    por_pagina: int
    por_status: ContagemPorStatus
