"""Formato JSON da tela Histórico."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class EventoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo: str                    # manutencao | abastecimento | gasto | projeto | diagnostico
    origem_id: int               # id para abrir o detalhe (item de projeto: abre projeto_id)
    data: date
    descricao: str
    valor: Decimal | None        # null no diagnóstico (não é despesa)
    quilometragem: int | None
    sistema: str | None
    oficina: str | None
    posto: str | None
    combustivel: str | None
    quantidade: Decimal | None   # litros (m³ no GNV, kWh na eletricidade)
    categoria: str | None
    descricao_gasto: str | None
    projeto_id: int | None
    projeto_nome: str | None
    item_descricao: str | None
    situacao: str | None         # situação atual do diagnóstico
    gravidade: str | None


class TotalDoMesResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ano: int
    mes: int
    total: Decimal
    quantidade: int


class PaginaHistorico(BaseModel):
    itens: list[EventoResposta]
    total: int
    pagina: int
    por_pagina: int
    periodo: str                 # 12_meses | ano | tudo
    ano: int | None
    inicio: date | None
    fim: date | None             # inclusive
    meses: list[TotalDoMesResposta]
    anos_disponiveis: list[int]
