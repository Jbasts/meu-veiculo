"""Custo do veículo ("Meu veículo") e indicadores da tela inicial, de ponta a ponta
(API + PostgreSQL de teste).

O Civic de teste é cadastrado hoje com 85.000 km (a leitura do cadastro é de
hoje) e foi comprado em 15/03/2022 com 22.000 km por R$ 65.000,00.
"""

from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal

import pytest

from tests.auth_utils import executar_sql
from tests.test_abastecimentos_api import abastecer
from tests.test_gastos_api import criar_gasto, item_de_projeto
from tests.test_manutencoes_api import civic, criar_manutencao, hoje  # noqa: F401  (fixtures)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    pasta_fotos,
    paula,
    rafael,
)

COMPRA = date(2022, 3, 15)


def custo(cliente, veiculo_id: int) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/custo")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def painel(cliente, veiculo_id: int) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/painel")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def por_km(valor: str, distancia: int) -> str:
    return str((Decimal(valor) / distancia).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def registrar_leitura(cliente, veiculo_id: int, km: int, data) -> None:
    resposta = cliente.post(f"/api/veiculos/{veiculo_id}/leituras",
                            json={"quilometragem": km, "data_leitura": str(data)})
    assert resposta.status_code == 201, resposta.text


def parcelas(bloco: dict, campo: str = "total") -> dict[str, str]:
    return {p["grupo"]: p[campo] for p in bloco["parcelas"]}


# ================================================================ custo total

def test_veiculo_sem_registros_custa_so_a_compra(paula, civic):
    total = custo(paula, civic["id"])["custo_total"]
    assert total == {"total": "65000.00", "valor_aquisicao": "65000.00", "despesas": "0.00",
                     "quantidade": 0,
                     "parcelas": [{"grupo": "aquisicao", "total": "65000.00", "percentual": 100}]}


def test_custo_total_soma_compra_e_despesas_sem_duplicar(banco, paula, civic, hoje):
    v = civic["id"]
    criar_manutencao(paula, v, hoje, valor="350.00")                     # realizada: conta
    criar_manutencao(paula, v, hoje, status="agendada", quilometragem=None,
                     data=str(hoje + timedelta(days=10)), valor="999.00")  # agendada: não conta
    criar_gasto(paula, v, "2023-01-10", categoria="seguro", valor="5000.00")
    criar_gasto(paula, v, "2024-02-01", categoria="ipva", valor="1200.00")
    criar_gasto(paula, v, "2024-02-02", categoria="licenciamento", valor="160.00")
    criar_gasto(paula, v, str(hoje), categoria="estacionamento", valor="30.00")
    criar_gasto(paula, v, str(hoje), categoria="multa", valor="88.00", pago=False,
                data_pagamento=None, data_vencimento=str(hoje + timedelta(days=5)))  # pendente
    abastecer(paula, v, hoje, 85100)                                      # R$ 250,00
    item_de_projeto(banco, v, str(hoje), "8300.00", "cancelado")          # cancelado: continua

    total = custo(paula, v)["custo_total"]
    assert total["despesas"] == "15290.00"     # 350 + 5000 + 1200 + 160 + 30 + 250 + 8300
    assert total["total"] == "80290.00"        # + 65.000 da compra
    assert total["quantidade"] == 7
    # Ordem do PDF; seguro separado da documentação (IPVA + licenciamento).
    assert parcelas(total) == {"aquisicao": "65000.00", "combustivel": "250.00",
                               "manutencao": "350.00", "projeto": "8300.00", "seguro": "5000.00",
                               "documentacao": "1360.00", "outros": "30.00"}
    assert [p["grupo"] for p in total["parcelas"]] == [
        "aquisicao", "combustivel", "manutencao", "projeto", "seguro", "documentacao", "outros"]
    assert parcelas(total, "percentual")["aquisicao"] == 81   # 65000 / 80290 = 81,0%


def test_compra_sem_valor_mostra_so_as_despesas(paula, hoje):
    v = criar_veiculo(paula, valor_aquisicao=None)["id"]
    criar_manutencao(paula, v, hoje, valor="350.00")
    total = custo(paula, v)["custo_total"]
    assert (total["valor_aquisicao"], total["total"], total["despesas"]) == (None, "350.00", "350.00")
    assert [p["grupo"] for p in total["parcelas"]] == ["manutencao"]


# ============================================================ custo por km

def test_custo_por_km_desde_a_compra_sem_o_valor_da_compra(banco, paula, civic, hoje):
    v = civic["id"]
    criar_manutencao(paula, v, hoje, valor="350.00")
    criar_gasto(paula, v, "2023-01-10", categoria="seguro", valor="5000.00")
    criar_gasto(paula, v, "2024-02-01", categoria="ipva", valor="1200.00")
    criar_gasto(paula, v, "2022-01-05", categoria="lavagem", valor="100.00")  # antes da compra
    item_de_projeto(banco, v, str(hoje), "8300.00", "em_andamento")

    km = custo(paula, v)["custo_por_km"]
    assert (km["disponivel"], km["base"], km["aviso_base"]) == (True, "compra", None)
    assert (km["inicio"], km["fim"]) == (str(COMPRA), str(hoje))
    assert (km["km_inicio"], km["km_fim"], km["distancia"]) == (22000, 85000, 63000)
    # Mesmo período no numerador: a lavagem de antes da compra fica de fora.
    assert km["despesas"] == "14850.00"
    assert km["valor"] == por_km("14850.00", 63000) == "0.24"
    assert parcelas(km, "por_km") == {"manutencao": "0.01", "projeto": "0.13",
                                      "seguro_documentacao": "0.10"}
    # Total geral continua com a lavagem e com a compra.
    assert custo(paula, v)["custo_total"]["despesas"] == "14950.00"


def test_sem_dados_da_compra_usa_a_primeira_leitura_e_avisa(paula, hoje):
    v = criar_veiculo(paula, data_aquisicao=None, km_aquisicao=None, valor_aquisicao=None)["id"]
    # Só a leitura do cadastro (hoje): não há distância.
    km = custo(paula, v)["custo_por_km"]
    assert km["disponivel"] is False and km["valor"] is None
    assert (km["base"], km["aviso_base"]) == ("primeira_leitura", "A compra está sem data e sem km.")
    assert "Ainda não há quilômetros rodados" in km["motivo"]

    um_ano = hoje - timedelta(days=365)
    registrar_leitura(paula, v, 80000, um_ano)
    criar_gasto(paula, v, str(um_ano - timedelta(days=1)), categoria="lavagem", valor="70.00")  # antes
    criar_manutencao(paula, v, hoje, valor="350.00")
    km = custo(paula, v)["custo_por_km"]
    assert (km["disponivel"], km["base"], km["inicio"], km["km_inicio"]) == (
        True, "primeira_leitura", str(um_ano), 80000)
    assert (km["distancia"], km["despesas"], km["valor"]) == (5000, "350.00", "0.07")


@pytest.mark.parametrize("compra, aviso", [
    ({"data_aquisicao": "2022-03-15", "km_aquisicao": None}, "A compra está sem o km."),
    ({"data_aquisicao": None, "km_aquisicao": 22000}, "A compra está sem data."),
])
def test_compra_incompleta_nao_e_usada(paula, compra, aviso):
    v = criar_veiculo(paula, **compra)["id"]
    km = custo(paula, v)["custo_por_km"]
    assert (km["base"], km["aviso_base"]) == ("primeira_leitura", aviso)


def test_compra_que_contradiz_as_leituras_nao_e_usada(banco, paula, civic):
    # Em 2021 o hodômetro já marcava 30.000 km, mas a compra (2022) diz 22.000.
    executar_sql(banco, "INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem) "
                        "VALUES (:v, 30000, '2021-06-01', 'manual')", v=civic["id"])
    km = custo(paula, civic["id"])["custo_por_km"]
    assert km["base"] == "primeira_leitura" and "não combinam" in km["aviso_base"]
    assert (km["inicio"], km["km_inicio"], km["distancia"]) == ("2021-06-01", 30000, 55000)


def test_sem_leitura_com_data_nao_calcula(banco, paula, civic):
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = NULL, origem = 'legado' "
                        "WHERE veiculo_id = :v", v=civic["id"])
    km = custo(paula, civic["id"])["custo_por_km"]
    assert km == {**km, "disponivel": False, "valor": None, "distancia": None, "parcelas": []}
    assert "Não há leitura de quilometragem com data" in km["motivo"]


def test_despesa_depois_da_ultima_leitura_fica_fora_ate_nova_leitura(banco, paula, civic, hoje):
    v = civic["id"]
    dez_dias = hoje - timedelta(days=10)
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = :d WHERE veiculo_id = :v",
                 d=dez_dias, v=v)
    criar_gasto(paula, v, str(dez_dias), categoria="lavagem", valor="63.00")   # no último dia: entra
    criar_gasto(paula, v, str(hoje), categoria="lavagem", valor="630.00")      # depois: fora
    km = custo(paula, v)["custo_por_km"]
    assert (km["fim"], km["despesas"], km["valor"]) == (str(dez_dias), "63.00", "0.00")
    registrar_leitura(paula, v, 85100, hoje)
    km = custo(paula, v)["custo_por_km"]
    assert (km["fim"], km["distancia"], km["despesas"]) == (str(hoje), 63100, "693.00")
    assert km["valor"] == por_km("693.00", 63100) == "0.01"


def test_correcao_de_leitura_recalcula_o_custo_por_km(paula, civic, hoje):
    v = civic["id"]
    criar_manutencao(paula, v, hoje, valor="630.00")
    leituras = paula.get(f"/api/veiculos/{v}/leituras").json()["itens"]
    cadastro = next(l for l in leituras if l["origem"] == "cadastro")
    # A leitura do cadastro era 85.000; a correção vira 85.630 (a manutenção ficou com 85.000).
    resposta = paula.post(f"/api/veiculos/{v}/leituras/{cadastro['id']}/corrigir",
                          json={"quilometragem": 85630, "motivo": "Digitei errado"})
    assert resposta.status_code in (200, 201), resposta.text
    km = custo(paula, v)["custo_por_km"]
    assert (km["km_fim"], km["distancia"], km["valor"]) == (85630, 63630, por_km("630.00", 63630))


# ================================================================ tela inicial

def test_painel_de_veiculo_sem_registros(paula, civic, hoje):
    dados = painel(paula, civic["id"])
    assert dados["gastos_do_mes"] == {"ano": hoje.year, "mes": hoje.month, "total": "0.00",
                                      "quantidade": 0, "parcelas": []}
    assert dados["consumo"]["disponivel"] is False
    assert dados["consumo"]["valor"] is None
    assert dados["consumo"]["motivo"] == "Nenhum abastecimento registrado ainda."
    assert dados["contas"] == {"vencidas": 0, "total_vencidas": "0.00", "vencem_hoje": 0}
    assert dados["custo_por_km"]["disponivel"] is True      # compra informada: 0,00 de 63.000 km
    assert dados["custo_por_km"]["valor"] == "0.00"


def test_painel_gastos_do_mes_em_tres_grupos(banco, paula, civic, hoje):
    v = civic["id"]
    criar_manutencao(paula, v, hoje, valor="350.00")
    abastecer(paula, v, hoje, 85100)                     # R$ 250,00
    abastecer(paula, v, hoje, 85500)                     # R$ 250,00
    criar_gasto(paula, v, str(hoje), categoria="estacionamento", valor="30.00")
    item_de_projeto(banco, v, str(hoje), "100.00", "em_andamento")
    mes_passado = hoje.replace(day=1) - timedelta(days=1)
    criar_gasto(paula, v, str(mes_passado), categoria="lavagem", valor="999.00")  # outro mês

    mes = painel(paula, v)["gastos_do_mes"]
    assert (mes["total"], mes["quantidade"]) == ("980.00", 5)
    assert mes["parcelas"] == [
        {"grupo": "manutencao", "total": "350.00", "percentual": 36},
        {"grupo": "combustivel", "total": "500.00", "percentual": 51},
        {"grupo": "outros", "total": "130.00", "percentual": 13},
    ]
    # O mesmo total da aba Finanças.
    financas = paula.get(f"/api/veiculos/{v}/financas/resumo",
                         params={"ano": hoje.year, "mes": hoje.month}).json()
    assert financas["total"] == mes["total"]


def test_painel_consumo_medio_do_combustivel_com_media(paula, civic, hoje):
    v = civic["id"]
    ontem = hoje - timedelta(days=1)
    abastecer(paula, v, ontem, 85000)                                 # primeiro cheio
    abastecer(paula, v, hoje, 85400)                                  # 400 km / 40 L = 10,0
    consumo = painel(paula, v)["consumo"]
    assert consumo == {"disponivel": True, "motivo": None, "combustivel": "gasolina", "valor": "10.0",
                       "ciclos": 1, "distancia": 400, "quantidade": "40.000",
                       "inicio": str(ontem), "fim": str(hoje), "estimado": False, "minimo": None,
                       "maximo": None}
    # Último abastecimento é de etanol, que ainda não tem média: mostra a gasolina.
    abastecer(paula, v, hoje, 85500, combustivel="etanol", preco="4.290", tanque_cheio=False)
    assert painel(paula, v)["consumo"]["combustivel"] == "gasolina"


def test_painel_consumo_com_um_cheio_so_e_dados_insuficientes(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85100)
    consumo = painel(paula, civic["id"])["consumo"]
    assert (consumo["disponivel"], consumo["valor"]) == (False, None)
    assert "dois abastecimentos de tanque cheio" in consumo["motivo"]


def test_painel_contas_vencidas_e_que_vencem_hoje(paula, civic, hoje):
    v = civic["id"]
    pendente = {"pago": False, "data_pagamento": None}
    criar_gasto(paula, v, str(hoje - timedelta(days=20)), categoria="ipva", valor="1200.00",
                data_vencimento=str(hoje - timedelta(days=3)), **pendente)
    criar_gasto(paula, v, str(hoje - timedelta(days=20)), categoria="multa", valor="88.38",
                data_vencimento=str(hoje - timedelta(days=1)), **pendente)
    criar_gasto(paula, v, str(hoje), categoria="seguro", valor="2400.00",
                data_vencimento=str(hoje), **pendente)
    criar_gasto(paula, v, str(hoje), categoria="lavagem", valor="40.00",
                data_vencimento=str(hoje + timedelta(days=5)), **pendente)
    assert painel(paula, v)["contas"] == {"vencidas": 2, "total_vencidas": "1288.38", "vencem_hoje": 1}


# ================================================================ permissões

def test_outro_usuario_nao_ve_custo_nem_painel(paula, rafael, civic):
    for resto in ("/custo", "/painel"):
        resposta = rafael.get(f"/api/veiculos/{civic['id']}{resto}")
        assert resposta.status_code == 404
        assert resposta.json()["mensagem"] == "Veículo não encontrado."


def test_admin_ve_custo_e_painel_de_outro_usuario(paula, admin, civic):
    assert admin.get(f"/api/veiculos/{civic['id']}/custo").status_code == 200
    assert admin.get(f"/api/veiculos/{civic['id']}/painel").status_code == 200


def test_custo_e_painel_exigem_login(banco, civic):
    from tests.auth_utils import novo_aparelho
    anonimo = novo_aparelho()
    assert anonimo.get(f"/api/veiculos/{civic['id']}/custo").status_code == 401
    assert anonimo.get(f"/api/veiculos/{civic['id']}/painel").status_code == 401


def test_veiculo_inativo_continua_com_custo_e_historico(paula, civic, hoje):
    criar_manutencao(paula, civic["id"], hoje, valor="350.00")
    assert paula.post(f"/api/veiculos/{civic['id']}/inativar").status_code == 200
    assert custo(paula, civic["id"])["custo_total"]["despesas"] == "350.00"
    assert painel(paula, civic["id"])["gastos_do_mes"]["total"] == "350.00"
