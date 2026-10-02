"""Histórico integrado do veículo, de ponta a ponta (API + PostgreSQL de teste)."""

from datetime import timedelta

import pytest

from tests.auth_utils import novo_aparelho, valor_sql
from tests.test_abastecimentos_api import abastecer
from tests.test_diagnosticos_api import criar_diagnostico
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


def historico(cliente, veiculo_id: int, **params) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/historico", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def tipos(pagina: dict) -> list[str]:
    return [e["tipo"] for e in pagina["itens"]]


@pytest.fixture
def registros(banco, paula, civic, hoje):
    """Um de cada: manutenção, abastecimento, gasto pago, item de projeto e diagnóstico,
    além do que NÃO entra (agendada e pendente)."""
    v = civic["id"]
    ontem = hoje - timedelta(days=1)
    criar_manutencao(paula, v, ontem, valor="350.00", quilometragem=84900, oficina="Oficina do Zé")
    abastecer(paula, v, hoje, 85100, litros="40.000", preco="6.250", posto="Shell")
    criar_gasto(paula, v, str(hoje), categoria="estacionamento", valor="30.00")
    item_de_projeto(banco, v, str(ontem), "450.00", "cancelado")
    criar_diagnostico(paula, v, hoje, titulo="Barulho na suspensão", sistema="suspensao",
                      gravidade="media", data_identificacao=str(hoje))
    criar_manutencao(paula, v, hoje, status="agendada", quilometragem=None,
                     data=str(hoje + timedelta(days=10)), valor="999.00")
    criar_gasto(paula, v, str(hoje), categoria="multa", valor="88.00", pago=False,
                data_pagamento=None, data_vencimento=str(hoje + timedelta(days=5)))
    return v


# ================================================================ conteúdo

def test_veiculo_sem_registros(paula, civic, hoje):
    pagina = historico(paula, civic["id"])
    assert (pagina["itens"], pagina["total"], pagina["meses"], pagina["anos_disponiveis"]) == ([], 0, [], [])
    assert pagina["periodo"] == "12_meses"
    assert pagina["fim"] >= str(hoje)


def test_lista_lancamentos_efetivados_e_diagnosticos_sem_valor(paula, registros, hoje):
    pagina = historico(paula, registros)
    ontem = str(hoje - timedelta(days=1))
    # Mais recente primeiro; no mesmo dia, pelo tipo (ordem estável). Agendada e pendente ficam fora.
    assert [(e["data"], e["tipo"]) for e in pagina["itens"]] == [
        (str(hoje), "abastecimento"), (str(hoje), "diagnostico"), (str(hoje), "gasto"),
        (ontem, "manutencao"), (ontem, "projeto")]
    por_tipo = {e["tipo"]: e for e in pagina["itens"]}
    assert por_tipo["diagnostico"]["valor"] is None
    assert (por_tipo["diagnostico"]["descricao"], por_tipo["diagnostico"]["situacao"],
            por_tipo["diagnostico"]["gravidade"]) == ("Barulho na suspensão", "aberto", "media")
    assert (por_tipo["abastecimento"]["posto"], por_tipo["abastecimento"]["quantidade"],
            por_tipo["abastecimento"]["combustivel"], por_tipo["abastecimento"]["valor"]) == (
        "Shell", "40.000", "gasolina", "250.00")
    assert (por_tipo["manutencao"]["quilometragem"], por_tipo["manutencao"]["oficina"]) == (84900, "Oficina do Zé")
    assert (por_tipo["gasto"]["categoria"], por_tipo["gasto"]["valor"]) == ("estacionamento", "30.00")
    projeto = por_tipo["projeto"]
    assert (projeto["projeto_nome"], projeto["item_descricao"], projeto["valor"]) == (
        "Rodas", "Jogo de rodas", "450.00")
    assert projeto["projeto_id"] is not None


def test_total_do_mes_nao_inclui_diagnostico_e_bate_com_as_despesas(banco, paula, registros, hoje):
    pagina = historico(paula, registros, periodo="tudo")
    soma = sum(float(m["total"]) for m in pagina["meses"])
    # Mesma soma da vw_despesa (as duas views contam cada valor uma vez).
    assert valor_sql(banco, "SELECT SUM(valor) FROM vw_despesa WHERE veiculo_id = :v",
                     v=registros) == pytest.approx(soma)
    assert valor_sql(banco, "SELECT SUM(valor) FROM vw_historico WHERE veiculo_id = :v",
                     v=registros) == pytest.approx(soma)
    assert sum(m["quantidade"] for m in pagina["meses"]) == 4   # 5 eventos, 1 diagnóstico
    assert soma == pytest.approx(350 + 250 + 30 + 450)


def test_mes_total_e_do_mes_inteiro_mesmo_com_paginacao(paula, civic, hoje):
    v = civic["id"]
    for i in range(4):
        criar_gasto(paula, v, str(hoje), categoria="lavagem", valor=f"{10 + i}.00")
    pagina = historico(paula, v, por_pagina=2)
    assert len(pagina["itens"]) == 2 and pagina["total"] == 4
    assert pagina["meses"] == [{"ano": hoje.year, "mes": hoje.month, "total": "46.00", "quantidade": 4}]


def test_paginacao_estavel_sem_repetir_nem_omitir(paula, civic, hoje):
    v = civic["id"]
    for i in range(7):
        criar_gasto(paula, v, str(hoje - timedelta(days=i % 3)), categoria="pedagio", valor="5.00")
    vistos = []
    for numero in range(1, 5):
        vistos += [(e["tipo"], e["origem_id"]) for e in historico(paula, v, por_pagina=2, pagina=numero)["itens"]]
    assert len(vistos) == len(set(vistos)) == 7


# ================================================================ filtros

@pytest.mark.parametrize("tipo, esperado", [
    ("manutencao", ["manutencao"]), ("abastecimento", ["abastecimento"]), ("gasto", ["gasto"]),
    ("projeto", ["projeto"]), ("diagnostico", ["diagnostico"]),
])
def test_filtro_por_tipo(paula, registros, tipo, esperado):
    pagina = historico(paula, registros, tipo=tipo)
    assert tipos(pagina) == esperado
    if tipo == "diagnostico":
        assert pagina["meses"] == []          # diagnóstico não tem soma
    else:
        assert len(pagina["meses"]) == 1


def test_filtro_tudo_e_o_mesmo_que_sem_tipo(paula, registros):
    assert historico(paula, registros, tipo="tudo")["itens"] == historico(paula, registros)["itens"]


def test_ultimos_12_meses_ano_e_tudo(paula, civic, hoje):
    v = civic["id"]
    inicio_12 = (hoje.replace(day=1) - timedelta(days=330)).replace(day=1)
    antigo = hoje.replace(year=hoje.year - 2, day=1)
    criar_gasto(paula, v, str(hoje), categoria="lavagem", valor="10.00")
    criar_gasto(paula, v, str(antigo), categoria="lavagem", valor="20.00")
    doze = historico(paula, v)
    assert doze["total"] == 1
    assert doze["inicio"] <= str(inicio_12) and doze["inicio"].endswith("-01")
    assert historico(paula, v, periodo="tudo")["total"] == 2
    do_ano = historico(paula, v, periodo="ano", ano=antigo.year)
    assert (do_ano["total"], do_ano["ano"], do_ano["inicio"], do_ano["fim"]) == (
        1, antigo.year, f"{antigo.year}-01-01", f"{antigo.year}-12-31")
    assert doze["anos_disponiveis"] == [hoje.year, antigo.year]


def test_doze_meses_cobre_o_mes_atual_e_os_11_anteriores_inteiros(paula, civic, hoje):
    pagina = historico(paula, civic["id"])
    meses = (hoje.year * 12 + hoje.month) - (int(pagina["inicio"][:4]) * 12 + int(pagina["inicio"][5:7]))
    assert meses == 11
    assert pagina["inicio"].endswith("-01")


def test_gasto_pago_aparece_no_mes_do_pagamento(paula, civic, hoje):
    v = civic["id"]
    mes_passado = hoje.replace(day=1) - timedelta(days=1)
    gasto = criar_gasto(paula, v, str(mes_passado), categoria="seguro", valor="2400.00",
                        data_pagamento=str(hoje))
    item = historico(paula, v)["itens"][0]
    assert (item["origem_id"], item["data"]) == (gasto["id"], str(hoje))


@pytest.mark.parametrize("params, campo", [
    ({"tipo": "foto"}, "tipo"), ({"periodo": "semana"}, "periodo"), ({"periodo": "ano"}, "ano"),
])
def test_filtros_invalidos(paula, civic, params, campo):
    resposta = paula.get(f"/api/veiculos/{civic['id']}/historico", params=params)
    assert resposta.status_code == 422
    assert campo in resposta.json()["campos"]


# ================================================================ permissões

def test_outro_usuario_nao_ve_o_historico(rafael, registros):
    resposta = rafael.get(f"/api/veiculos/{registros}/historico")
    assert resposta.status_code == 404


def test_historico_e_por_veiculo_mesmo_do_mesmo_dono(paula, registros):
    outro = criar_veiculo(paula, placa="BRA2E19")
    assert historico(paula, outro["id"])["itens"] == []


def test_admin_ve_o_historico_de_outro_usuario(admin, registros):
    assert historico(admin, registros)["total"] == 5


def test_historico_exige_login(banco, civic):
    assert novo_aparelho().get(f"/api/veiculos/{civic['id']}/historico").status_code == 401


def test_veiculo_inativo_mantem_o_historico(paula, registros):
    assert paula.post(f"/api/veiculos/{registros}/inativar").status_code == 200
    assert historico(paula, registros)["total"] == 5
