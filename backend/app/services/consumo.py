"""Cálculo do consumo (sem banco, só a regra).

Ideia: o consumo é medido entre dois PONTOS em que se sabe quanto
combustível havia no tanque. Entre um ponto e o seguinte há um ciclo:
    distância  = km do ponto final − km do ponto inicial
    quantidade = o que havia no início + o que foi abastecido no meio
                 − o que havia no fim
    consumo    = distância / quantidade

Para não depender do tamanho exato do tanque, a conta usa o que FALTA para
encher ("falta"):
    quantidade = falta no fim (antes de abastecer) − falta no início
                 (depois de abastecer) + abastecimentos do meio

Pontos
- Tanque cheio: depois de abastecer falta 0; antes faltavam os litros
  abastecidos. É o ponto exato (margem zero).
- Abastecimento com o nível do marcador (só combustível líquido e com o
  tamanho do tanque no cadastro): antes faltavam capacidade × (8 − nível)/8;
  depois, isso menos os litros.
- Marcação do tanque (sem abastecer): falta capacidade × (8 − nível)/8.
O nível é lido em oitavos (1/4 = 2/8, "1,5/4" = 3/8). Cada leitura do
marcador tem margem de ± meio oitavo do tanque (capacidade / 16). A margem
cobre só a leitura: marcadores de carro não são lineares, por isso o tanque
cheio continua sendo a referência mais exata.

Exemplo do pedido (só tanques cheios): cheio aos 10.000 km; parcial de 10 L
aos 10.100 km; cheio de 20 L aos 10.300 km → 300 / (10 + 20) = 10 km/L.
Exemplo com o marcador (tanque de 50 L): marcação de 3/4 aos 10.000 km
(faltam 12,5 L); tanque cheio de 42,5 L aos 10.300 km → 300 / (42,5 − 12,5)
= 10 km/L, com margem de ± 3,125 L: entre 9,1 e 11,2 km/L.

Abastecimento parcial SEM nível: entra como "abastecido no meio".
Antes do primeiro ponto, não entra no cálculo.

Ciclo inválido (não entra nas médias, e a tela diz o motivo):
- mistura de combustíveis (o que estava no tanque, o abastecido no meio e,
  quando o fim é tanque cheio, o do fim; ou ponto de outro reservatório,
  como recarga elétrica e marcador do tanque);
- dois tanques cheios sem a quilometragem aumentar.
Ciclo "trecho curto": com marcador, a quantidade não passa da margem (ou a
quilometragem não mudou). Não mostra km/L sozinho, mas entra na média.

Média de vários ciclos: distância total / quantidade total dos ciclos
válidos do mesmo combustível, nunca a média simples dos km/L. Em ciclos
seguidos, a leitura do marcador do meio entra com + num e − no outro e se
anula: só as pontas que não se anulam somam margem. Por isso, quanto mais
longo o período, mais exato o resultado.

A ordem é (data, quilometragem, marcação antes do abastecimento, id). Tudo é
recalculado a cada consulta: incluir ou editar um registro antigo recalcula
os ciclos afetados automaticamente.
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Protocol

CONSUMO = "consumo"                  # ponto que fecha um ciclo válido com km/L
PARCIAL = "parcial"                  # abastecimento sem nível dentro de um ciclo
PRIMEIRO_CHEIO = "primeiro_cheio"    # tanque cheio que só abre o primeiro ciclo
PRIMEIRO_NIVEL = "primeiro_nivel"    # nível do marcador que só abre o primeiro ciclo
FORA_DO_CALCULO = "fora_do_calculo"  # abastecimento sem nível antes do primeiro ponto
CICLO_INVALIDO = "ciclo_invalido"    # ponto que fecha um ciclo inválido
TRECHO_CURTO = "trecho_curto"        # ciclo válido curto demais para o marcador
SEM_TANQUE = "sem_tanque"            # marcação sem o tamanho do tanque no cadastro

ABASTECIMENTO = "abastecimento"
MEDICAO = "medicao"

UM_DECIMO = Decimal("0.1")
OITAVOS = 8
LIQUIDOS = ("gasolina", "etanol", "diesel")   # o tanque do marcador


class AbastecimentoLike(Protocol):
    id: int
    quilometragem: int
    combustivel: str
    litros: Decimal
    tanque_cheio: bool


class MedicaoLike(Protocol):
    id: int
    data: date
    quilometragem: int
    nivel: int


@dataclass(frozen=True)
class Situacao:
    """Como um abastecimento (ou marcação) aparece no cálculo de consumo."""

    tipo: str
    km_por_litro: Decimal | None = None   # só em CONSUMO, com 1 casa (meio para cima)
    motivo: str | None = None
    estimado: bool = False                # usou o marcador (tem margem)
    km_por_litro_minimo: Decimal | None = None
    km_por_litro_maximo: Decimal | None = None


@dataclass(frozen=True)
class Ciclo:
    inicio_id: int
    fim_id: int
    combustivel: str | None   # None quando misturou combustíveis
    distancia: int
    quantidade: Decimal
    valido: bool
    inicio_tipo: str = ABASTECIMENTO
    fim_tipo: str = ABASTECIMENTO
    inicio_data: date | None = None
    fim_data: date | None = None
    margem_inicio: Decimal = Decimal(0)   # litros (± leitura do marcador)
    margem_fim: Decimal = Decimal(0)
    ordem: int = 0                        # posição na sequência (ciclos seguidos)


def faixa(distancia: int, quantidade: Decimal, margem: Decimal) -> tuple[Decimal, Decimal] | None:
    """Menor e maior km/L possíveis com a margem do marcador (None: margem maior que a quantidade)."""
    if margem <= 0:
        return None
    if quantidade <= margem:
        return None
    return (arredondar(Decimal(distancia) / (quantidade + margem)),
            arredondar(Decimal(distancia) / (quantidade - margem)))


@dataclass(frozen=True)
class Media:
    combustivel: str
    distancia: int
    quantidade: Decimal
    ciclos: int
    margem: Decimal = Decimal(0)   # litros que não se anularam (pontas com marcador)
    inicio: date | None = None
    fim: date | None = None

    @property
    def exata(self) -> Decimal:
        return Decimal(self.distancia) / self.quantidade

    @property
    def km_por_litro(self) -> Decimal:
        return arredondar(self.exata)

    @property
    def estimada(self) -> bool:
        return self.margem > 0

    @property
    def minimo_e_maximo(self) -> tuple[Decimal, Decimal] | None:
        return faixa(self.distancia, self.quantidade, self.margem)


@dataclass(frozen=True)
class MesDeConsumo:
    """Ciclos que COMEÇARAM no mês (com a marcação do início do mês, o mês fecha certinho)."""

    ano: int
    mes: int
    media: Media


@dataclass
class Resultado:
    situacoes: dict[int, Situacao]            # por id de abastecimento
    situacoes_medicao: dict[int, Situacao]    # por id de marcação
    ciclos: list[Ciclo] = field(default_factory=list)


def arredondar(valor: Decimal) -> Decimal:
    return valor.quantize(UM_DECIMO, rounding=ROUND_HALF_UP)


def falta_pelo_marcador(capacidade: Decimal, nivel: int) -> Decimal:
    """Litros que faltam para encher, pelo marcador em oitavos."""
    return capacidade * (OITAVOS - nivel) / OITAVOS


def margem_do_marcador(capacidade: Decimal) -> Decimal:
    """± meio oitavo do tanque por leitura."""
    return capacidade / (2 * OITAVOS)


@dataclass
class _Ponto:
    tipo: str
    id: int
    km: int
    data: date | None
    falta_depois: Decimal
    margem: Decimal
    conteudo: frozenset[str] | None   # combustíveis no tanque depois do ponto (None = desconhecido)
    cheio: bool
    reservatorio: str                 # "liquido", "gnv" ou "eletrica"


def _reservatorio(combustivel: str) -> str:
    return "liquido" if combustivel in LIQUIDOS else combustivel


def _ordenar(abastecimentos: list, medicoes: list) -> list[tuple[str, object]]:
    if not medicoes:
        return [(ABASTECIMENTO, a) for a in abastecimentos]
    eventos = [((a.data, a.quilometragem, 1, a.id), ABASTECIMENTO, a) for a in abastecimentos]
    eventos += [((m.data, m.quilometragem, 0, m.id), MEDICAO, m) for m in medicoes]
    eventos.sort(key=lambda e: e[0])
    return [(tipo, registro) for _, tipo, registro in eventos]


def calcular_tudo(abastecimentos: list[AbastecimentoLike], medicoes: Iterable[MedicaoLike] = (),
                  capacidade: Decimal | None = None, combustivel_inicial: str | None = None) -> Resultado:
    """Recebe os registros de UM veículo: abastecimentos na ordem (data,
    quilometragem, id) e as marcações do tanque (qualquer ordem).

    combustivel_inicial: o que estava no tanque antes do primeiro registro,
    quando o veículo só usa um combustível líquido (gasolina, etanol ou
    diesel). No flex é desconhecido até o primeiro abastecimento."""
    resultado = Resultado({}, {})
    ponto: _Ponto | None = None
    no_meio: list[AbastecimentoLike] = []
    # O que há no tanque agora (None = desconhecido).
    conteudo: frozenset[str] | None = frozenset({combustivel_inicial}) if combustivel_inicial else None

    for tipo, r in _ordenar(abastecimentos, list(medicoes)):
        situacoes = resultado.situacoes_medicao if tipo == MEDICAO else resultado.situacoes
        cheio = tipo == ABASTECIMENTO and r.tanque_cheio
        nivel = r.nivel if tipo == MEDICAO else getattr(r, "nivel_antes", None)
        marcador = (nivel is not None and capacidade is not None
                    and (tipo == MEDICAO or r.combustivel in LIQUIDOS))

        if not cheio and not marcador:
            if tipo == MEDICAO:
                situacoes[r.id] = Situacao(SEM_TANQUE, motivo=(
                    "Informe o tamanho do tanque no cadastro do veículo para usar esta marcação."))
                continue
            if ponto is None:
                situacoes[r.id] = Situacao(FORA_DO_CALCULO, motivo=(
                    "Abastecimento parcial antes do primeiro tanque cheio (ou nível do marcador): "
                    "não entra no cálculo."))
            else:
                no_meio.append(r)
                situacoes[r.id] = Situacao(PARCIAL)
            if conteudo is not None:
                conteudo = conteudo | {r.combustivel}
            continue

        # É um ponto: sabe-se quanto falta para encher.
        if cheio:
            falta_antes, falta_depois, margem = r.litros, Decimal(0), Decimal(0)
            reservatorio = _reservatorio(r.combustivel)
        else:
            falta_antes = falta_pelo_marcador(capacidade, nivel)
            falta_depois = falta_antes - (r.litros if tipo == ABASTECIMENTO else 0)
            margem = margem_do_marcador(capacidade)
            reservatorio = "liquido"

        if ponto is None:
            if cheio:
                situacoes[r.id] = Situacao(PRIMEIRO_CHEIO, motivo=(
                    "Primeiro tanque cheio: o consumo aparece no próximo tanque cheio ou nível do marcador."))
            else:
                situacoes[r.id] = Situacao(PRIMEIRO_NIVEL, motivo=(
                    "Primeiro registro com o nível do marcador: o consumo aparece no próximo "
                    "(tanque cheio, abastecimento com nível ou marcação do tanque)."))
        else:
            distancia = r.quilometragem - ponto.km
            quantidade = falta_antes - ponto.falta_depois + sum((x.litros for x in no_meio), Decimal(0))
            combustiveis = set(ponto.conteudo or ()) | {x.combustivel for x in no_meio}
            if cheio:
                combustiveis.add(r.combustivel)
            unico = next(iter(combustiveis)) if len(combustiveis) == 1 else None
            margem_total = ponto.margem + margem
            outro_reservatorio = ponto.reservatorio != reservatorio or (
                unico is not None and _reservatorio(unico) != reservatorio)
            valido = True
            if len(combustiveis) > 1 or outro_reservatorio:
                situacoes[r.id] = Situacao(CICLO_INVALIDO, motivo=(
                    "Mistura de combustíveis desde o último tanque cheio ou nível do marcador: "
                    "este trecho não entra na média."))
                valido = False
            elif unico is None:
                situacoes[r.id] = Situacao(CICLO_INVALIDO, motivo=(
                    "Não dá para saber qual combustível estava no tanque: este trecho não entra na média."))
                valido = False
            elif distancia <= 0 and margem_total == 0:
                situacoes[r.id] = Situacao(CICLO_INVALIDO, motivo=(
                    "A quilometragem não aumentou desde o último tanque cheio."))
                valido = False
            elif distancia <= 0 or quantidade <= margem_total:
                situacoes[r.id] = Situacao(TRECHO_CURTO, estimado=True, motivo=(
                    "Trecho curto para medir pelo marcador: o km/L dele sozinho não é confiável, "
                    "mas ele entra na média do período."))
            else:
                limites = faixa(distancia, quantidade, margem_total)
                situacoes[r.id] = Situacao(
                    CONSUMO, km_por_litro=arredondar(Decimal(distancia) / quantidade),
                    estimado=margem_total > 0,
                    km_por_litro_minimo=limites[0] if limites else None,
                    km_por_litro_maximo=limites[1] if limites else None)
            resultado.ciclos.append(Ciclo(
                ponto.id, r.id, unico if valido else None, distancia, quantidade, valido,
                inicio_tipo=ponto.tipo, fim_tipo=tipo, inicio_data=ponto.data,
                fim_data=getattr(r, "data", None), margem_inicio=ponto.margem, margem_fim=margem,
                ordem=len(resultado.ciclos)))

        if tipo == ABASTECIMENTO:
            if cheio:
                conteudo = frozenset({r.combustivel})
            elif conteudo is not None:
                conteudo = conteudo | {r.combustivel}
        ponto = _Ponto(tipo, r.id, r.quilometragem, getattr(r, "data", None), falta_depois, margem,
                       conteudo, cheio, reservatorio)
        no_meio = []

    return resultado


def calcular(abastecimentos: list[AbastecimentoLike], medicoes: Iterable[MedicaoLike] = (),
             capacidade: Decimal | None = None,
             combustivel_inicial: str | None = None) -> tuple[dict[int, Situacao], list[Ciclo]]:
    """Situação de cada abastecimento e os ciclos (sem as situações das marcações)."""
    r = calcular_tudo(abastecimentos, medicoes, capacidade, combustivel_inicial)
    return r.situacoes, r.ciclos


def _somar(ciclos: list[Ciclo]) -> Media | None:
    """Soma ciclos válidos do MESMO combustível; a margem do ponto compartilhado por
    dois ciclos seguidos se anula."""
    if not ciclos:
        return None
    distancia = sum(c.distancia for c in ciclos)
    quantidade = sum((c.quantidade for c in ciclos), Decimal(0))
    margem = sum((c.margem_inicio + c.margem_fim for c in ciclos), Decimal(0))
    for anterior, seguinte in zip(ciclos, ciclos[1:]):
        if seguinte.ordem == anterior.ordem + 1:
            margem -= anterior.margem_fim + seguinte.margem_inicio
    datas_inicio = [c.inicio_data for c in ciclos if c.inicio_data is not None]
    datas_fim = [c.fim_data for c in ciclos if c.fim_data is not None]
    return Media(ciclos[0].combustivel, distancia, quantidade, len(ciclos), margem,
                 min(datas_inicio) if datas_inicio else None, max(datas_fim) if datas_fim else None)


def _por_combustivel(ciclos: list[Ciclo]) -> dict[str, list[Ciclo]]:
    grupos: dict[str, list[Ciclo]] = {}
    for c in ciclos:
        if c.valido and c.combustivel is not None:
            grupos.setdefault(c.combustivel, []).append(c)
    return grupos


def _utilizavel(media: Media | None) -> bool:
    """Com distância e quantidade acima da margem do marcador."""
    return media is not None and media.distancia > 0 and media.quantidade > media.margem


def medias(ciclos: list[Ciclo]) -> dict[str, Media]:
    """Por combustível: distância total / quantidade total dos ciclos válidos."""
    resultado = {}
    for combustivel, grupo in _por_combustivel(ciclos).items():
        media = _somar(grupo)
        if _utilizavel(media):
            resultado[combustivel] = media
    return resultado


def por_mes(ciclos: list[Ciclo]) -> list[MesDeConsumo]:
    """Consumo de cada mês (e combustível), do mais recente para o mais antigo.
    Cada ciclo conta no mês em que começou."""
    grupos: dict[tuple[int, int, str], list[Ciclo]] = {}
    for combustivel, grupo in _por_combustivel(ciclos).items():
        for c in grupo:
            if c.inicio_data is not None:
                grupos.setdefault((c.inicio_data.year, c.inicio_data.month, combustivel), []).append(c)
    meses = []
    for (ano, mes, _), grupo in grupos.items():
        media = _somar(grupo)
        if _utilizavel(media):
            meses.append(MesDeConsumo(ano, mes, media))
    meses.sort(key=lambda m: (m.ano, m.mes, m.media.combustivel), reverse=True)
    return meses
