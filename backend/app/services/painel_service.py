"""Indicadores da tela inicial (PDF, página 2), todos com registros reais.

Gastos do mês (mês atual em America/Sao_Paulo)
- Mesmas despesas efetivadas das Finanças (vw_despesa), em três grupos fixos,
  como no PDF (decisão da Paula, 01/10/2026): Manutenção, Combustível e
  Outros (gastos avulsos pagos + itens de projeto). As categorias completas
  continuam na aba Finanças.

Consumo médio
- Distância total / quantidade total dos ciclos válidos entre tanques cheios,
  níveis do marcador e marcações do tanque (services/consumo.py), do
  combustível do último abastecimento; se esse
  combustível ainda não tem média, o de ciclo válido mais recente. A resposta
  traz o período (do início do primeiro ciclo ao fim do último) e quantos
  ciclos entraram. Sem ciclo válido: dados insuficientes, com o motivo.
  Quando alguma ponta vem do marcador, o valor é estimado e vem com a faixa
  possível (mínimo e máximo).

Tanque (para "Precisa de atenção")
- Falta o tamanho do tanque no cadastro; falta marcar o km e o nível neste mês.

Custo por km
- O mesmo de "Meu veículo" (services/custo_service.py), com o período.

Contas em atraso
- Gastos pendentes vencidos (e os que vencem hoje), para "Precisa de atenção".
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable

from app.entities.usuario import Usuario
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.entities.veiculo import Veiculo
from app.services.abastecimento_service import calcular_do_veiculo
from app.services.consumo import Media, medias
from app.services.custo_service import (
    COMBUSTIVEL,
    MANUTENCAO,
    OUTROS,
    ZERO,
    CustoPorKm,
    CustoService,
    Parcela,
    somar_por_grupo,
)
from app.services.gasto_service import intervalo_do_mes, percentual
from app.services.tanque import tanque_pendente

GRUPOS_DO_MES = (MANUTENCAO, COMBUSTIVEL, OUTROS)


def grupo_do_mes(categoria: str) -> str:
    return categoria if categoria in (MANUTENCAO, COMBUSTIVEL) else OUTROS


@dataclass(frozen=True)
class GastosDoMes:
    ano: int
    mes: int
    total: Decimal
    quantidade: int
    parcelas: list[Parcela]    # só os grupos com valor, na ordem do PDF


@dataclass(frozen=True)
class ConsumoMedio:
    disponivel: bool
    motivo: str | None
    combustivel: str | None
    valor: Decimal | None      # km por litro (m³ no GNV, kWh na eletricidade), 1 casa
    ciclos: int
    distancia: int | None
    quantidade: Decimal | None
    inicio: date | None
    fim: date | None
    estimado: bool = False                 # alguma ponta veio do marcador
    minimo: Decimal | None = None          # faixa possível com a margem do marcador
    maximo: Decimal | None = None


@dataclass(frozen=True)
class AvisosDoTanque:
    tamanho_pendente: bool         # tem tanque, mas falta o tamanho no cadastro
    marcacao_do_mes_pendente: bool


@dataclass(frozen=True)
class ContasEmAtraso:
    vencidas: int
    total_vencidas: Decimal
    vencem_hoje: int


@dataclass(frozen=True)
class PainelInicio:
    gastos_do_mes: GastosDoMes
    consumo: ConsumoMedio
    custo_por_km: CustoPorKm
    contas: ContasEmAtraso
    tanque: AvisosDoTanque


def consumo_medio(veiculo: Veiculo, abastecimentos, medicoes) -> ConsumoMedio:
    """Recebe os abastecimentos do veículo na ordem (data, quilometragem, id) e as marcações."""
    if not abastecimentos and not medicoes:
        return ConsumoMedio(False, "Nenhum abastecimento registrado ainda.", None, None, 0,
                            None, None, None, None)
    ciclos = calcular_do_veiculo(veiculo, abastecimentos, medicoes).ciclos
    por_combustivel = medias(ciclos)
    if not por_combustivel:
        return ConsumoMedio(
            False, "Registre dois abastecimentos de tanque cheio do mesmo combustível, ou marque o km "
            "e o nível do tanque (no início do mês e ao abastecer), para calcular o consumo médio.",
            None, None, 0, None, None, None, None)
    escolhido: Media | None = (por_combustivel.get(abastecimentos[-1].combustivel)
                               if abastecimentos else None)
    if escolhido is None:
        mais_recente = max((c for c in ciclos if c.valido and c.combustivel in por_combustivel),
                           key=lambda c: c.ordem)
        escolhido = por_combustivel[mais_recente.combustivel]
    faixa = escolhido.minimo_e_maximo
    return ConsumoMedio(
        True, None, escolhido.combustivel, escolhido.km_por_litro, escolhido.ciclos,
        escolhido.distancia, escolhido.quantidade.quantize(Decimal("0.001")),
        escolhido.inicio, escolhido.fim, escolhido.estimada,
        faixa[0] if faixa else None, faixa[1] if faixa else None,
    )


class PainelService:
    def __init__(self, veiculos, financas, gastos, abastecimentos, medicoes, custo: CustoService, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._financas = financas
        self._gastos = gastos
        self._abastecimentos = abastecimentos
        self._medicoes = medicoes
        self._custo = custo
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def inicio(self, usuario: Usuario, veiculo_id: int) -> PainelInicio:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        hoje = self._hoje()
        inicio, fim = intervalo_do_mes(hoje.year, hoje.month)
        linhas = self._financas.totais_por_categoria(veiculo.id, inicio, fim)
        somas = somar_por_grupo(linhas, grupo_do_mes)
        total = sum(somas.values(), ZERO)
        vencidas, total_vencidas, vencem_hoje = self._gastos.contas_em_atraso(veiculo.id, hoje)
        return PainelInicio(
            gastos_do_mes=GastosDoMes(
                ano=hoje.year, mes=hoje.month, total=total, quantidade=sum(q for _, _, q in linhas),
                parcelas=[Parcela(g, somas[g], percentual(somas[g], total))
                          for g in GRUPOS_DO_MES if somas.get(g, ZERO) > 0],
            ),
            consumo=consumo_medio(veiculo, self._abastecimentos.todos(veiculo.id),
                                  self._medicoes.todas(veiculo.id)),
            custo_por_km=self._custo.calcular_por_km(veiculo),
            contas=ContasEmAtraso(vencidas, total_vencidas, vencem_hoje),
            tanque=AvisosDoTanque(
                tamanho_pendente=veiculo.ativo and tanque_pendente(veiculo),
                marcacao_do_mes_pendente=(veiculo.ativo and veiculo.capacidade_tanque is not None
                                          and not self._medicoes.existe_desde(veiculo.id, inicio))),
        )
