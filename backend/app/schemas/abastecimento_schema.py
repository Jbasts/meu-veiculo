"""Formatos JSON dos abastecimentos e do resumo de combustível.

Números com casas decimais viajam como TEXTO ("38.500", "4.290", "165.17"):
nunca número com ponto flutuante. O total é calculado pelo backend; o valor
do cupom é opcional e só é aceito perto do calculado (até R$ 50,00).
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.veiculo_schema import Dinheiro

Decimal3 = Dinheiro  # mesmo cuidado: texto, nunca float


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AbastecimentoEntrada(_Entrada):
    combustivel: str = Field(max_length=20)
    tipo: str | None = Field(default=None, max_length=30)  # um dos tipos do combustível (GNV: vazio)
    data: date
    quilometragem: int | None = None
    litros: Decimal3 | None = None       # litros; m³ no GNV; kWh na eletricidade
    valor_litro: Decimal3 | None = None
    valor_total: Dinheiro | None = None  # só quando o cupom difere do calculado
    tanque_cheio: bool
    posto: str | None = Field(default=None, max_length=300)


class SituacaoResposta(BaseModel):
    """Como o abastecimento entra no cálculo do consumo."""

    tipo: str            # consumo | parcial | primeiro_cheio | fora_do_calculo | ciclo_invalido
    km_por_litro: Decimal | None
    motivo: str | None


class AbastecimentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    data: date
    quilometragem: int
    combustivel: str
    tipo: str | None   # um dos tipos do combustível | null (antigo, não informado; ou GNV)
    litros: Decimal
    valor_litro: Decimal
    valor_total: Decimal
    tanque_cheio: bool
    posto: str | None
    criado_em: datetime


class AbastecimentoDetalheResposta(AbastecimentoResposta):
    consumo: SituacaoResposta


class PaginaAbastecimentos(BaseModel):
    itens: list[AbastecimentoDetalheResposta]
    total: int
    pagina: int
    por_pagina: int


class MediaResposta(BaseModel):
    combustivel: str
    km_por_litro: Decimal   # distância total / quantidade total dos ciclos válidos, 1 casa
    distancia: int
    quantidade: Decimal
    ciclos: int


class ComparacaoResposta(BaseModel):
    recomendacao: str | None        # etanol | gasolina | tanto_faz | null (sem dados)
    motivo: str | None
    limite_percentual: int | None   # até quanto do preço da gasolina o etanol compensa
    relacao_percentual: int | None  # preço do etanol / preço da gasolina
    preco_gasolina: Decimal | None
    preco_etanol: Decimal | None
    precos_simulados: bool


class ResumoCombustivelResposta(BaseModel):
    combustiveis: list[str]         # os que o veículo aceita
    medias: list[MediaResposta]     # só combustíveis com pelo menos um ciclo válido
    comparacao: ComparacaoResposta | None   # só para veículo flex
    postos_recentes: list[str]
    ultima_quilometragem: int
