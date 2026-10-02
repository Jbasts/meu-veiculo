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


# ---------------------------------------------------------------- marcador do tanque (0012)

from datetime import date  # noqa: E402

from app.services.consumo import (  # noqa: E402
    PRIMEIRO_NIVEL,
    SEM_TANQUE,
    TRECHO_CURTO,
    calcular_tudo,
    por_mes,
)


@dataclass
class Ab:
    id: int
    data: date
    quilometragem: int
    litros: Decimal
    tanque_cheio: bool = True
    combustivel: str = "gasolina"
    nivel_antes: int | None = None


@dataclass
class M:
    id: int
    data: date
    quilometragem: int
    nivel: int  # oitavos


def D(dia: int, mes: int = 9) -> date:
    return date(2026, mes, dia)


def test_exemplo_da_documentacao_marcacao_e_tanque_cheio():
    # Tanque de 50 L. Marcação de 3/4 (faltam 12,5 L) aos 10.000; cheio de 42,5 L aos 10.300.
    r = calcular_tudo([Ab(1, D(5), 10300, L("42.5"))], [M(1, D(1), 10000, 6)], L("50"))
    assert r.situacoes_medicao[1].tipo == PRIMEIRO_NIVEL
    s = r.situacoes[1]
    assert (s.tipo, s.km_por_litro, s.estimado) == (CONSUMO, Decimal("10.0"), True)
    # 300 / (30 + 3,125) = 9,06 e 300 / (30 − 3,125) = 11,16
    assert (s.km_por_litro_minimo, s.km_por_litro_maximo) == (Decimal("9.1"), Decimal("11.2"))
    assert r.ciclos[0].quantidade == Decimal(30)


def test_sem_tamanho_do_tanque_o_nivel_e_ignorado_e_a_marcacao_avisa():
    lista = [Ab(1, D(1), 1000, L("40")), Ab(2, D(2), 1100, L("10"), tanque_cheio=False, nivel_antes=4),
             Ab(3, D(3), 1300, L("20"))]
    r = calcular_tudo(lista, [M(1, D(2), 1200, 4)], None)
    assert r.situacoes[2].tipo == PARCIAL and r.situacoes_medicao[1].tipo == SEM_TANQUE
    assert r.situacoes[3].km_por_litro == Decimal("10.0") and not r.situacoes[3].estimado


def test_leitura_do_meio_se_anula_na_media():
    # Tanque de 40 L (margem ± 2,5 L por leitura), 10 km/L de verdade.
    # Marcação 4/8 (faltam 20) -> 200 km -> parcial de 25 L com marcador vazio (faltam 40)
    # -> 200 km -> marcação 1/8 (faltam 35).
    lista = [Ab(1, D(10), 10200, L("25"), tanque_cheio=False, nivel_antes=0)]
    r = calcular_tudo(lista, [M(1, D(1), 10000, 4), M(2, D(20), 10400, 1)], L("40"), "gasolina")
    assert r.situacoes[1].km_por_litro == Decimal("10.0")                       # 200 / (40 − 20)
    assert r.situacoes_medicao[2].km_por_litro == Decimal("10.0")               # 200 / (35 − 15)
    assert (r.situacoes[1].km_por_litro_minimo, r.situacoes[1].km_por_litro_maximo) == (
        Decimal("8.0"), Decimal("13.3"))                                        # ± 5 L num trecho
    media = medias(r.ciclos)["gasolina"]
    # Duas pontas sobrando (± 5 L), não quatro: o nível do meio entrou com + e com −.
    assert (media.distancia, media.quantidade, media.margem) == (400, Decimal(40), Decimal(5))
    assert media.minimo_e_maximo == (Decimal("8.9"), Decimal("11.4"))           # 400/45 e 400/35


def test_trecho_curto_nao_mostra_km_por_litro_mas_entra_na_media():
    lista = [Ab(1, D(30), 10500, L("45"))]
    medicoes = [M(1, D(1), 10000, 4), M(2, D(2), 10010, 4)]  # 10 km sem mexer no marcador
    r = calcular_tudo(lista, medicoes, L("50"), "gasolina")
    assert r.situacoes_medicao[2].tipo == TRECHO_CURTO and r.situacoes_medicao[2].km_por_litro is None
    media = medias(r.ciclos)["gasolina"]
    # 500 km / (45 − 25) = 25 km/L; só a primeira marcação tem margem (o cheio é exato).
    assert (media.distancia, media.quantidade, media.margem) == (500, Decimal(20), Decimal("3.125"))


def test_marcacao_no_mesmo_dia_e_km_vem_antes_do_abastecimento():
    lista = [Ab(1, D(1), 10000, L("30"))]
    r = calcular_tudo(lista, [M(1, D(1), 10000, 2)], L("40"))
    assert r.situacoes_medicao[1].tipo == PRIMEIRO_NIVEL
    assert r.situacoes[1].tipo == TRECHO_CURTO   # 0 km: 30 L cabiam (faltavam 30)


def test_recarga_eletrica_e_marcador_do_tanque_sao_reservatorios_diferentes():
    lista = [Ab(1, D(1), 1000, L("40"), combustivel="eletrica")]
    r = calcular_tudo(lista, [M(1, D(5), 1200, 4)], L("40"))
    assert r.situacoes_medicao[1].tipo == CICLO_INVALIDO
    assert medias(r.ciclos) == {}


def test_nivel_em_recarga_eletrica_e_ignorado():
    lista = [Ab(1, D(1), 1000, L("40"), combustivel="eletrica", tanque_cheio=False, nivel_antes=2)]
    r = calcular_tudo(lista, [], L("40"))
    assert r.situacoes[1].tipo == FORA_DO_CALCULO


def test_consumo_por_mes_conta_no_mes_em_que_o_trecho_comecou():
    # Marcação no início de cada mês; tanque de 50 L.
    medicoes = [M(1, D(1, 8), 10000, 8), M(2, D(1, 9), 10600, 4), M(3, D(1, 10), 11000, 4)]
    lista = [Ab(1, D(15, 9), 10800, L("20"), tanque_cheio=False, nivel_antes=2)]
    meses = por_mes(calcular_tudo(lista, medicoes, L("50"), "gasolina").ciclos)
    assert [(m.ano, m.mes) for m in meses] == [(2026, 9), (2026, 8)]
    setembro, agosto = meses[0].media, meses[1].media
    assert (agosto.distancia, agosto.quantidade) == (600, Decimal(25))   # 0 -> faltam 25
    # Setembro: 400 km; 25 + 20 − 25 = 20 L; o nível do dia 15 se anula.
    assert (setembro.distancia, setembro.quantidade, setembro.margem) == (400, Decimal(20), Decimal("6.25"))
    assert setembro.km_por_litro == Decimal("20.0")


def test_flex_sem_abastecimento_antes_nao_sabe_o_combustivel_da_primeira_marcacao():
    r = calcular_tudo([], [M(1, D(1), 10000, 4), M(2, D(30), 10500, 2)], L("50"))
    assert r.situacoes_medicao[2].tipo == CICLO_INVALIDO
    assert "qual combustível" in r.situacoes_medicao[2].motivo
    # Com um tanque cheio antes, o tanque é conhecido (um parcial sozinho não basta).
    r = calcular_tudo([Ab(1, D(1, 8), 9800, L("10"), combustivel="etanol")],
                      [M(1, D(1), 10000, 4), M(2, D(30), 10500, 2)], L("50"))
    assert r.situacoes_medicao[2].tipo == CONSUMO and r.ciclos[-1].combustivel == "etanol"


def test_sem_marcacoes_tudo_continua_como_antes():
    lista = [A(1, 10000, L("40")), A(2, 10100, L("10"), tanque_cheio=False), A(3, 10300, L("20"))]
    situacoes, _ = calcular(lista, [], L("50"))
    assert situacoes[3].km_por_litro == Decimal("10.0") and not situacoes[3].estimado
