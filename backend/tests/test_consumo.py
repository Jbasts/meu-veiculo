"""Regra do consumo entre tanques cheios (sem banco: só o cálculo)."""

from dataclasses import dataclass
from decimal import Decimal

from app.services.abastecimento_service import calcular_total
from app.services.consumo import (
    CICLO_INVALIDO,
    CONSUMO,
    FORA_DO_CALCULO,
    PARCIAL,
    PRIMEIRO_CHEIO,
    calcular,
    medias,
)


@dataclass
class A:
    id: int
    quilometragem: int
    litros: Decimal
    tanque_cheio: bool = True
    combustivel: str = "gasolina"


def L(texto: str) -> Decimal:
    return Decimal(texto)


def test_exemplo_do_pedido_dois_cheios_com_parcial_no_meio():
    # cheio aos 10.000; parcial de 10 L aos 10.100; cheio de 20 L aos 10.300 -> 300 / 30 = 10 km/L
    lista = [A(1, 10000, L("40")), A(2, 10100, L("10"), tanque_cheio=False), A(3, 10300, L("20"))]
    situacoes, ciclos = calcular(lista)
    assert [situacoes[i].tipo for i in (1, 2, 3)] == [PRIMEIRO_CHEIO, PARCIAL, CONSUMO]
    assert situacoes[3].km_por_litro == Decimal("10.0")
    assert (ciclos[0].distancia, ciclos[0].quantidade) == (300, Decimal(30))  # sem os 40 L do cheio inicial


def test_primeiro_cheio_sozinho_nao_tem_consumo():
    situacoes, ciclos = calcular([A(1, 10000, L("40"))])
    assert situacoes[1].tipo == PRIMEIRO_CHEIO and situacoes[1].km_por_litro is None
    assert ciclos == [] and medias(ciclos) == {}


def test_parcial_antes_do_primeiro_cheio_fica_fora():
    situacoes, _ = calcular([A(1, 9900, L("10"), tanque_cheio=False), A(2, 10000, L("40"))])
    assert (situacoes[1].tipo, situacoes[2].tipo) == (FORA_DO_CALCULO, PRIMEIRO_CHEIO)


def test_media_de_varios_ciclos_e_distancia_total_sobre_quantidade_total():
    # ciclo 1: 100 km / 10 L = 10; ciclo 2: 300 km / 20 L = 15.
    # Média simples daria 12,5; a correta é 400 / 30 = 13,3.
    lista = [A(1, 1000, L("30")), A(2, 1100, L("10")), A(3, 1400, L("20"))]
    _, ciclos = calcular(lista)
    media = medias(ciclos)["gasolina"]
    assert (media.distancia, media.quantidade, media.ciclos, media.km_por_litro) == (400, Decimal(30), 2, Decimal("13.3"))


def test_mistura_de_combustiveis_invalida_o_ciclo_e_fica_fora_da_media():
    lista = [A(1, 1000, L("40")), A(2, 1100, L("10"), tanque_cheio=False, combustivel="etanol"),
             A(3, 1400, L("20")), A(4, 1700, L("30"))]
    situacoes, ciclos = calcular(lista)
    assert situacoes[3].tipo == CICLO_INVALIDO and "Mistura" in situacoes[3].motivo
    # O ciclo seguinte (3 -> 4, só gasolina) volta a valer.
    assert situacoes[4].tipo == CONSUMO and situacoes[4].km_por_litro == Decimal("10.0")
    assert medias(ciclos)["gasolina"].ciclos == 1


def test_troca_de_combustivel_entre_cheios_tambem_e_mistura():
    lista = [A(1, 1000, L("40")), A(2, 1300, L("30"), combustivel="etanol"),
             A(3, 1510, L("30"), combustivel="etanol")]
    situacoes, ciclos = calcular(lista)
    assert situacoes[2].tipo == CICLO_INVALIDO       # tanque tinha gasolina
    assert situacoes[3].km_por_litro == Decimal("7.0")  # 210 / 30, só etanol
    assert set(medias(ciclos)) == {"etanol"}


def test_quilometragem_que_nao_aumentou_invalida_o_ciclo():
    situacoes, ciclos = calcular([A(1, 1000, L("40")), A(2, 1000, L("5"))])
    assert situacoes[2].tipo == CICLO_INVALIDO and "não aumentou" in situacoes[2].motivo
    assert medias(ciclos) == {}


def test_total_arredonda_meio_para_cima():
    assert calcular_total(Decimal("38.500"), Decimal("4.290")) == Decimal("165.17")  # 165,165
    assert calcular_total(Decimal("40.000"), Decimal("6.250")) == Decimal("250.00")
    assert calcular_total(Decimal("0.001"), Decimal("4.999")) == Decimal("0.00")
