"""Nível do tanque: o último que se sabe e uma estimativa de agora (pedido da Paula, 02/10/2026).

De onde vem o nível
- O registro mais recente do tanque de combustível líquido (gasolina, etanol
  ou diesel), na ordem do consumo (data, quilometragem; a marcação vem antes
  do abastecimento do mesmo dia e km):
  - marcação do tanque ("Atualizar km" ou "Marcar km e nível"): o nível marcado;
  - abastecimento de tanque cheio: cheio;
  - abastecimento parcial com o nível antes: nível antes + litros abastecidos,
    em oitavos do tanque (meio para cima), sem passar de cheio;
  - abastecimento parcial sem o nível antes: não dá para saber (o indicador
    diz isso; não inventa um nível).
- GNV e recarga elétrica são outros reservatórios e não mexem nesse nível.

Estimativa de agora
- Se a quilometragem atual passou da do registro, estima o nível de agora:
  litros gastos = km rodados ÷ consumo médio (km/L) do combustível no tanque.
  Só com o tamanho do tanque e um consumo médio conhecido; senão mostra só o
  último nível, com a data e os km rodados desde então.
- É sempre apresentado como estimativa ("≈"), nunca como medição.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.entities.veiculo import Veiculo
from app.services.calendario import data_br
from app.services.consumo import LIQUIDOS, OITAVOS, Media
from app.services.tanque import tem_tanque

MARCACAO = "marcacao"
ABASTECIMENTO = "abastecimento"


@dataclass(frozen=True)
class NivelDoTanque:
    disponivel: bool
    motivo: str | None              # por que não há nível (quando disponivel=False)
    nivel: int | None               # oitavos (0 = vazio, 8 = cheio), do último registro
    data: date | None
    quilometragem: int | None
    origem: str | None              # marcacao | abastecimento
    km_desde: int | None            # km rodados desde o registro (0 = nada)
    nivel_estimado: int | None      # oitavos, estimativa de agora (só quando km_desde > 0)
    km_por_litro: Decimal | None    # consumo médio usado na estimativa


def _indisponivel(motivo: str) -> NivelDoTanque:
    return NivelDoTanque(False, motivo, None, None, None, None, None, None, None)


def _em_oitavos(litros: Decimal, capacidade: Decimal) -> int:
    return int((litros * OITAVOS / capacidade).to_integral_value(ROUND_HALF_UP))


def nivel_do_tanque(veiculo: Veiculo, abastecimentos: list, medicoes: list,
                    medias: dict[str, Media]) -> NivelDoTanque:
    """abastecimentos e medicoes do veículo (em qualquer ordem); medias: consumo por combustível."""
    if not tem_tanque(veiculo.tipo_combustivel):
        return _indisponivel("Veículo elétrico não tem tanque de combustível.")
    liquidos = [a for a in abastecimentos if a.combustivel in LIQUIDOS]
    eventos = [((a.data, a.quilometragem, 1, a.id), ABASTECIMENTO, a) for a in liquidos]
    eventos += [((m.data, m.quilometragem, 0, m.id), MARCACAO, m) for m in medicoes]
    if not eventos:
        return _indisponivel("Ainda não há nível registrado. Ao atualizar o km, informe o nível "
                             "do combustível.")
    _, origem, ultimo = max(eventos, key=lambda e: e[0])
    capacidade = veiculo.capacidade_tanque

    if origem == MARCACAO:
        nivel = ultimo.nivel
    elif ultimo.tanque_cheio:
        nivel = OITAVOS
    elif ultimo.nivel_antes is not None and capacidade:
        nivel = min(OITAVOS, ultimo.nivel_antes + _em_oitavos(ultimo.litros, capacidade))
    else:
        return _indisponivel(
            f"O último abastecimento ({data_br(ultimo.data)}) não encheu o tanque e foi sem o nível "
            "do marcador, então não dá para saber o nível. Atualize o km informando o nível.")

    km_desde = max(0, veiculo.quilometragem - ultimo.quilometragem)
    estimado = km_por_litro = None
    if km_desde > 0 and capacidade:
        # Combustível no tanque: o do último abastecimento de combustível líquido.
        combustivel = (max(liquidos, key=lambda a: (a.data, a.quilometragem, a.id)).combustivel
                       if liquidos else None)
        media = medias.get(combustivel) if combustivel else None
        if media is None and len(medias) == 1:
            media = next(iter(medias.values()))
        if media is not None and media.km_por_litro > 0:
            km_por_litro = media.km_por_litro
            gastos = Decimal(km_desde) / km_por_litro
            restante = capacidade * nivel / OITAVOS - gastos
            estimado = max(0, min(OITAVOS, _em_oitavos(restante, capacidade)))
    return NivelDoTanque(True, None, nivel, ultimo.data, ultimo.quilometragem, origem,
                         km_desde, estimado, km_por_litro)
