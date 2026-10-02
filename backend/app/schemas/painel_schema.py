"""Formatos JSON dos indicadores: tela inicial e custo do veículo ("Meu veículo").

Dinheiro sai como texto ("0.76"), datas como "AAAA-MM-DD". Indicador que não
dá para calcular vem com disponivel=false e o motivo, nunca com zero.
"""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class ParcelaResposta(BaseModel):
    grupo: str        # aquisicao | combustivel | manutencao | projeto | seguro | documentacao | outros
    total: Decimal
    percentual: int   # do total, inteiro meio para cima


class CustoTotalResposta(BaseModel):
    total: Decimal                    # compra (se informada) + despesas registradas
    valor_aquisicao: Decimal | None   # null = valor da compra não informado
    despesas: Decimal
    quantidade: int
    parcelas: list[ParcelaResposta]


class ParcelaPorKmResposta(BaseModel):
    grupo: str        # combustivel | manutencao | projeto | seguro_documentacao | outros
    total: Decimal
    por_km: Decimal


class CustoPorKmResposta(BaseModel):
    disponivel: bool
    motivo: str | None          # por que não dá para calcular
    base: str | None            # compra | primeira_leitura
    aviso_base: str | None      # por que a compra não foi usada como início
    inicio: date | None         # período usado, nas duas pontas inclusive
    fim: date | None
    km_inicio: int | None
    km_fim: int | None
    distancia: int | None
    despesas: Decimal | None
    valor: Decimal | None       # R$ por km, sem o valor da compra
    parcelas: list[ParcelaPorKmResposta]


class CustoVeiculoResposta(BaseModel):
    custo_total: CustoTotalResposta
    custo_por_km: CustoPorKmResposta


class GastosDoMesResposta(BaseModel):
    ano: int
    mes: int
    total: Decimal
    quantidade: int
    parcelas: list[ParcelaResposta]   # manutencao | combustivel | outros


class ConsumoMedioResposta(BaseModel):
    disponivel: bool
    motivo: str | None
    combustivel: str | None
    valor: Decimal | None       # km por litro (m³ no GNV, kWh na eletricidade), 1 casa
    ciclos: int
    distancia: int | None
    quantidade: Decimal | None
    inicio: date | None
    fim: date | None
    estimado: bool              # alguma ponta veio do marcador do tanque
    minimo: Decimal | None      # faixa possível com a margem do marcador
    maximo: Decimal | None


class AvisosDoTanqueResposta(BaseModel):
    tamanho_pendente: bool          # tem tanque, mas falta o tamanho no cadastro
    marcacao_do_mes_pendente: bool  # falta marcar o km e o nível neste mês


class ContasEmAtrasoResposta(BaseModel):
    vencidas: int
    total_vencidas: Decimal
    vencem_hoje: int


class PainelInicioResposta(BaseModel):
    gastos_do_mes: GastosDoMesResposta
    consumo: ConsumoMedioResposta
    custo_por_km: CustoPorKmResposta
    contas: ContasEmAtrasoResposta
    tanque: AvisosDoTanqueResposta
