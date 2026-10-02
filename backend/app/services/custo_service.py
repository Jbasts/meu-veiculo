"""Custo do veículo: "Quanto esse carro já me custou" e "Custo por quilômetro".

Custo total
- Valor da compra (quando informado) + todas as despesas efetivadas da view
  vw_despesa (manutenção realizada, abastecimento, gasto pago, item de projeto,
  inclusive de projeto cancelado), cada valor contado uma vez, pela tabela de
  origem. Sem o valor da compra, o total mostra só as despesas e avisa.
- Grupos como no PDF: Aquisição, Combustível, Manutenções, Projetos, Seguro,
  Documentação (IPVA + licenciamento) e Outros (os demais gastos avulsos).

Custo por km (sem o valor da compra, como no PDF)
- Numerador e denominador do MESMO período:
    início = a compra (data e km), se as duas existirem e combinarem com as
             leituras do hodômetro; senão (decisão da Paula, 01/10/2026), a
             primeira leitura de km com data, e a tela diz o porquê;
    fim    = a leitura de km com data mais recente;
    distância = km do fim − km do início;
    despesas  = vw_despesa com data entre início e fim, inclusive.
  Despesas depois da última leitura só entram quando houver uma leitura nova.
- Sem leitura com data, ou distância zero: "dados insuficientes", com o
  motivo. Nada de distância inventada a partir da quilometragem atual.
- Valor por km com Decimal, em centavos, meio para cima. Cada grupo é
  arredondado sozinho; a soma dos grupos pode diferir 1 centavo do total.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br
from app.services.gasto_service import percentual

CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")

AQUISICAO = "aquisicao"
COMBUSTIVEL = "combustivel"
MANUTENCAO = "manutencao"
PROJETO = "projeto"
SEGURO = "seguro"
DOCUMENTACAO = "documentacao"
SEGURO_E_DOCUMENTACAO = "seguro_documentacao"
OUTROS = "outros"

# Ordem em que os grupos aparecem nas telas.
GRUPOS_DO_TOTAL = (AQUISICAO, COMBUSTIVEL, MANUTENCAO, PROJETO, SEGURO, DOCUMENTACAO, OUTROS)
GRUPOS_POR_KM = (COMBUSTIVEL, MANUTENCAO, PROJETO, SEGURO_E_DOCUMENTACAO, OUTROS)

BASE_COMPRA = "compra"
BASE_PRIMEIRA_LEITURA = "primeira_leitura"


def grupo_do_total(categoria: str) -> str:
    """Categoria da vw_despesa → grupo de "Quanto esse carro já me custou"."""
    if categoria in (COMBUSTIVEL, MANUTENCAO, PROJETO, SEGURO):
        return categoria
    if categoria in ("ipva", "licenciamento"):
        return DOCUMENTACAO
    return OUTROS


def grupo_por_km(categoria: str) -> str:
    grupo = grupo_do_total(categoria)
    return SEGURO_E_DOCUMENTACAO if grupo in (SEGURO, DOCUMENTACAO) else grupo


def somar_por_grupo(linhas: list[tuple[str, Decimal, int]], agrupar) -> dict[str, Decimal]:
    somas: dict[str, Decimal] = {}
    for categoria, total, _ in linhas:
        grupo = agrupar(categoria)
        somas[grupo] = somas.get(grupo, ZERO) + total
    return somas


def por_km(valor: Decimal, distancia: int) -> Decimal:
    return (valor / Decimal(distancia)).quantize(CENTAVO, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Parcela:
    grupo: str
    total: Decimal
    percentual: int        # do total, inteiro meio para cima


@dataclass(frozen=True)
class CustoTotal:
    total: Decimal                    # compra (se informada) + despesas
    valor_aquisicao: Decimal | None   # None = valor da compra não informado
    despesas: Decimal
    quantidade: int                   # lançamentos de despesa
    parcelas: list[Parcela]           # só os grupos com valor


@dataclass(frozen=True)
class ParcelaPorKm:
    grupo: str
    total: Decimal
    por_km: Decimal


@dataclass(frozen=True)
class CustoPorKm:
    disponivel: bool
    motivo: str | None          # por que não dá para calcular (quando indisponível)
    base: str | None            # compra | primeira_leitura
    aviso_base: str | None      # por que não foi usada a compra
    inicio: date | None
    fim: date | None
    km_inicio: int | None
    km_fim: int | None
    distancia: int | None
    despesas: Decimal | None    # despesas do período
    valor: Decimal | None       # R$ por km
    parcelas: list[ParcelaPorKm]


def _indisponivel(motivo: str) -> CustoPorKm:
    return CustoPorKm(False, motivo, None, None, None, None, None, None, None, None, None, [])


class CustoService:
    def __init__(self, veiculos, financas, leituras):
        self._financas = financas
        self._leituras = leituras
        self._acesso = AcessoVeiculo(veiculos)

    # ----------------------------------------------------------- custo total
    def custo_total(self, usuario: Usuario, veiculo_id: int) -> CustoTotal:
        return self.calcular_total(self._acesso.exigir(usuario, veiculo_id))

    def calcular_total(self, veiculo: Veiculo) -> CustoTotal:
        linhas = self._financas.totais_por_categoria(veiculo.id, None, None)
        somas = somar_por_grupo(linhas, grupo_do_total)
        despesas = sum(somas.values(), ZERO)
        aquisicao = veiculo.valor_aquisicao
        if aquisicao:
            somas[AQUISICAO] = aquisicao
        total = despesas + (aquisicao or ZERO)
        return CustoTotal(
            total=total, valor_aquisicao=aquisicao, despesas=despesas,
            quantidade=sum(q for _, _, q in linhas),
            parcelas=[Parcela(g, somas[g], percentual(somas[g], total))
                      for g in GRUPOS_DO_TOTAL if somas.get(g, ZERO) > 0],
        )

    # --------------------------------------------------------- custo por km
    def custo_por_km(self, usuario: Usuario, veiculo_id: int) -> CustoPorKm:
        return self.calcular_por_km(self._acesso.exigir(usuario, veiculo_id))

    def _base(self, veiculo: Veiculo, primeira, ultima) -> tuple[str, date, int, str | None]:
        """(base, data, km, aviso): a compra, se for confiável; senão a primeira leitura."""
        data, km = veiculo.data_aquisicao, veiculo.km_aquisicao
        if data is not None and km is not None:
            incoerente = (data > ultima.data_leitura or km > ultima.quilometragem
                          or self._leituras.conflitos(veiculo.id, km, data))
            if not incoerente:
                return BASE_COMPRA, data, km, None
            aviso = ("A data e o km da compra não combinam com as leituras do hodômetro: "
                     "confira os dados da compra em Editar veículo.")
        elif data is None and km is None:
            aviso = "A compra está sem data e sem km."
        elif data is None:
            aviso = "A compra está sem data."
        else:
            aviso = "A compra está sem o km."
        return BASE_PRIMEIRA_LEITURA, primeira.data_leitura, primeira.quilometragem, aviso

    def calcular_por_km(self, veiculo: Veiculo) -> CustoPorKm:
        extremos = self._leituras.primeira_e_ultima_com_data(veiculo.id)
        if extremos is None:
            return _indisponivel(
                "Não há leitura de quilometragem com data. Registre a quilometragem atual em "
                "\"Atualizar km\" para começar a contar.")
        primeira, ultima = extremos
        base, inicio, km_inicio, aviso = self._base(veiculo, primeira, ultima)
        fim, km_fim = ultima.data_leitura, ultima.quilometragem
        distancia = km_fim - km_inicio
        if distancia <= 0:
            desde = "a compra" if base == BASE_COMPRA else f"a leitura de {data_br(inicio)}"
            return CustoPorKm(
                False, f"Ainda não há quilômetros rodados desde {desde}. Registre uma leitura "
                "nova de quilometragem para calcular o custo por km.",
                base, aviso, inicio, fim, km_inicio, km_fim, distancia, None, None, [])
        # fim é inclusivo: a consulta recebe o dia seguinte (exclusivo).
        linhas = self._financas.totais_por_categoria(veiculo.id, inicio, fim + timedelta(days=1))
        somas = somar_por_grupo(linhas, grupo_por_km)
        despesas = sum(somas.values(), ZERO)
        return CustoPorKm(
            True, None, base, aviso, inicio, fim, km_inicio, km_fim, distancia, despesas,
            por_km(despesas, distancia),
            [ParcelaPorKm(g, somas[g], por_km(somas[g], distancia))
             for g in GRUPOS_POR_KM if somas.get(g, ZERO) > 0],
        )
