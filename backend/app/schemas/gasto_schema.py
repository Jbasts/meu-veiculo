"""Formatos JSON de gastos e do resumo financeiro do mês.

Como nos outros módulos: entradas com extra="forbid" (veiculo_id não vem da
tela), datas "AAAA-MM-DD" e dinheiro como texto ("2400.00"). Os totais só
saem do backend: nenhuma entrada aceita total.
"""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.veiculo_schema import Dinheiro


class _Entrada(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GastoEntrada(_Entrada):
    categoria: str = Field(max_length=30)
    valor: Dinheiro | None = None
    descricao: str | None = Field(default=None, max_length=500)
    data: date
    pago: bool
    data_vencimento: date | None = None   # obrigatório quando pendente
    data_pagamento: date | None = None    # obrigatório quando pago (exceto gastos antigos)


class PagamentoEntrada(_Entrada):
    data_pagamento: date | None = None    # vazio = hoje


class GastoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    veiculo_id: int
    categoria: str
    descricao: str | None
    data: date
    valor: Decimal
    pago: bool
    data_vencimento: date | None
    # null em gasto pago antigo: a data do pagamento não foi informada (conta pela data do gasto)
    data_pagamento: date | None
    criado_em: datetime


class PendenteResposta(GastoResposta):
    situacao: str   # vencido | vence_hoje | a_vencer
    dias: int       # dias até o vencimento (negativo = dias de atraso)


class PaginaPendentes(BaseModel):
    itens: list[PendenteResposta]
    total: int
    pagina: int
    por_pagina: int


class CategoriaResposta(BaseModel):
    categoria: str   # manutencao | combustivel | projeto | uma categoria de gasto
    total: Decimal
    quantidade: int
    percentual: int  # do total do mês, inteiro arredondado meio para cima


class ResumoMesResposta(BaseModel):
    periodo: str            # mes | ano | total (desde o primeiro registro)
    ano: int | None         # null no total
    mes: int | None         # null no ano e no total
    total: Decimal          # só despesas efetivadas
    quantidade: int
    categorias: list[CategoriaResposta]
    # Previsto (não entra no total): manutenções agendadas e gastos pendentes que vencem no período.
    previsto_manutencoes: Decimal
    quantidade_manutencoes_previstas: int
    previsto_gastos: Decimal
    quantidade_gastos_previstos: int


class LancamentoResposta(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    tipo: str        # manutencao | abastecimento | gasto | projeto
    origem_id: int   # id na tabela de origem (para abrir o detalhe)
    data: date
    categoria: str
    descricao: str | None
    valor: Decimal


class PaginaLancamentos(BaseModel):
    itens: list[LancamentoResposta]
    total: int
    pagina: int
    por_pagina: int
