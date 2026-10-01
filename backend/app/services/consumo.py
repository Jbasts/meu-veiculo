"""Cálculo do consumo entre abastecimentos de tanque cheio (sem banco, só a regra).

Ciclo: do tanque cheio inicial até o próximo tanque cheio.
    distância  = km do cheio final − km do cheio inicial
    quantidade = soma do que foi abastecido DEPOIS do cheio inicial, até o
                 cheio final inclusive (parciais do meio + cheio final). A
                 quantidade do cheio inicial não entra: ela encheu o tanque
                 antes de começar a contar.
    consumo    = distância / quantidade

Exemplo do pedido: cheio aos 10.000 km; parcial de 10 L aos 10.100 km; cheio
de 20 L aos 10.300 km → 300 / (10 + 20) = 10 km/L.

Ciclo inválido (não entra nas médias, e a tela diz o motivo):
    - mistura de combustíveis (o cheio inicial ou algum abastecimento do
      ciclo é de outro combustível);
    - a quilometragem não aumentou.
O primeiro tanque cheio sozinho não dá consumo. Parciais antes do primeiro
cheio também não entram.

Média de vários ciclos: distância total / quantidade total (dos ciclos
válidos do mesmo combustível), nunca a média simples dos km/L.

A ordem é (data, quilometragem, id): no mesmo dia, a quilometragem decide.
Como tudo é recalculado a cada consulta, incluir ou editar um abastecimento
antigo recalcula os ciclos afetados automaticamente.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Protocol

CONSUMO = "consumo"                  # cheio que fecha um ciclo válido
PARCIAL = "parcial"                  # parcial dentro de um ciclo
PRIMEIRO_CHEIO = "primeiro_cheio"    # cheio que só abre o primeiro ciclo
FORA_DO_CALCULO = "fora_do_calculo"  # parcial antes do primeiro cheio
CICLO_INVALIDO = "ciclo_invalido"    # cheio que fecha um ciclo inválido

UM_DECIMO = Decimal("0.1")


class AbastecimentoLike(Protocol):
    id: int
    quilometragem: int
    combustivel: str
    litros: Decimal
    tanque_cheio: bool


@dataclass(frozen=True)
class Situacao:
    """Como um abastecimento aparece no cálculo de consumo."""

    tipo: str
    km_por_litro: Decimal | None = None   # só em CONSUMO, com 1 casa (meio para cima)
    motivo: str | None = None


@dataclass(frozen=True)
class Ciclo:
    inicio_id: int
    fim_id: int
    combustivel: str | None   # None quando misturou combustíveis
    distancia: int
    quantidade: Decimal
    valido: bool


@dataclass(frozen=True)
class Media:
    combustivel: str
    distancia: int
    quantidade: Decimal
    ciclos: int

    @property
    def exata(self) -> Decimal:
        return Decimal(self.distancia) / self.quantidade

    @property
    def km_por_litro(self) -> Decimal:
        return arredondar(self.exata)


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(UM_DECIMO, rounding=ROUND_HALF_UP)


def calcular(abastecimentos: list[AbastecimentoLike]) -> tuple[dict[int, Situacao], list[Ciclo]]:
    """Recebe os abastecimentos de UM veículo, já na ordem (data, quilometragem, id)."""
    situacoes: dict[int, Situacao] = {}
    ciclos: list[Ciclo] = []
    inicio: AbastecimentoLike | None = None
    no_ciclo: list[AbastecimentoLike] = []

    for a in abastecimentos:
        if inicio is None:
            if a.tanque_cheio:
                inicio = a
                situacoes[a.id] = Situacao(PRIMEIRO_CHEIO, motivo=(
                    "Primeiro tanque cheio: o consumo aparece no próximo tanque cheio."))
            else:
                situacoes[a.id] = Situacao(FORA_DO_CALCULO, motivo=(
                    "Tanque parcial antes do primeiro tanque cheio: não entra no cálculo."))
            continue

        no_ciclo.append(a)
        if not a.tanque_cheio:
            situacoes[a.id] = Situacao(PARCIAL)
            continue

        distancia = a.quilometragem - inicio.quilometragem
        quantidade = sum((x.litros for x in no_ciclo), Decimal(0))
        combustiveis = {inicio.combustivel} | {x.combustivel for x in no_ciclo}
        if len(combustiveis) > 1:
            situacoes[a.id] = Situacao(CICLO_INVALIDO, motivo=(
                "Mistura de combustíveis desde o último tanque cheio: este tanque não entra na média."))
            valido = False
        elif distancia <= 0 or quantidade <= 0:
            situacoes[a.id] = Situacao(CICLO_INVALIDO, motivo=(
                "A quilometragem não aumentou desde o último tanque cheio."))
            valido = False
        else:
            situacoes[a.id] = Situacao(CONSUMO, km_por_litro=arredondar(Decimal(distancia) / quantidade))
            valido = True
        ciclos.append(Ciclo(inicio.id, a.id, a.combustivel if len(combustiveis) == 1 else None,
                            distancia, quantidade, valido))
        inicio = a
        no_ciclo = []

    return situacoes, ciclos


def medias(ciclos: list[Ciclo]) -> dict[str, Media]:
    """Por combustível: distância total / quantidade total dos ciclos válidos."""
    somas: dict[str, tuple[int, Decimal, int]] = {}
    for c in ciclos:
        if not c.valido or c.combustivel is None:
            continue
        distancia, quantidade, n = somas.get(c.combustivel, (0, Decimal(0), 0))
        somas[c.combustivel] = (distancia + c.distancia, quantidade + c.quantidade, n + 1)
    return {comb: Media(comb, d, q, n) for comb, (d, q, n) in somas.items()}
