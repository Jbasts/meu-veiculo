"""Gastos e resumo financeiro do mês, de ponta a ponta (API + PostgreSQL de teste)."""

from datetime import date, timedelta

import pytest

from tests.auth_utils import executar_sql, valor_sql
from tests.test_manutencoes_api import civic, criar_manutencao, hoje  # noqa: F401  (fixtures)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    pasta_fotos,
    paula,
    rafael,
)


@pytest.fixture
def mes_passado(hoje) -> date:
    """Primeiro dia do mês passado: todas as datas dele já são passado, qualquer que seja hoje."""
    return (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)


def dia(mes: date, numero: int) -> str:
    return str(mes.replace(day=numero))


def dados_gasto(data: str, **alteracoes) -> dict:
    return {"categoria": "estacionamento", "valor": "30.00", "descricao": None, "data": data,
            "pago": True, "data_vencimento": None, "data_pagamento": data, **alteracoes}


def caminho(veiculo_id: int, resto: str = "") -> str:
    return f"/api/veiculos/{veiculo_id}{resto}"


def criar_gasto(cliente, veiculo_id: int, data: str, **alteracoes) -> dict:
    resposta = cliente.post(caminho(veiculo_id, "/gastos"), json=dados_gasto(data, **alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def resumo(cliente, veiculo_id: int, mes: date) -> dict:
    resposta = cliente.get(caminho(veiculo_id, "/financas/resumo"),
                           params={"ano": mes.year, "mes": mes.month})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def lancamentos(cliente, veiculo_id: int, mes: date, **params) -> dict:
    resposta = cliente.get(caminho(veiculo_id, "/financas/lancamentos"),
                           params={"ano": mes.year, "mes": mes.month, **params})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def abastecer(banco, veiculo_id: int, data: str, valor_total: str, km: int = 84000) -> None:
    executar_sql(banco, "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, "
                        "litros, valor_litro, valor_total, posto) VALUES (:v, :d, :km, 'gasolina', "
                        "38.5, 4.29, CAST(:t AS numeric), 'Shell')",
                 v=veiculo_id, d=data, km=km, t=valor_total)


def item_de_projeto(banco, veiculo_id: int, data: str, valor: str, status: str) -> None:
    executar_sql(banco, "WITH p AS (INSERT INTO projeto (veiculo_id, nome, status) "
                        "VALUES (:v, 'Rodas', :s) RETURNING id) "
                        "INSERT INTO projeto_item (projeto_id, descricao, data, valor) "
                        "SELECT id, 'Jogo de rodas', :d, CAST(:valor AS numeric) FROM p",
                 v=veiculo_id, s=status, d=data, valor=valor)


# ================================================================ cadastro

def test_registrar_gasto_pago_e_ver(paula, civic, mes_passado):
    criado = criar_gasto(paula, civic["id"], dia(mes_passado, 18), descricao="  Shopping  centro ")
    assert (criado["descricao"], criado["valor"], criado["pago"], criado["data_pagamento"]) == (
        "Shopping centro", "30.00", True, dia(mes_passado, 18))
    assert paula.get(caminho(civic["id"], f"/gastos/{criado['id']}")).json() == criado


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"categoria": "combustivel"}, "categoria", "Escolha a categoria"),
    ({"valor": None}, "valor", "Informe o valor"),
    ({"valor": "0.00"}, "valor", "maior que zero"),
    ({"valor": "10.005"}, "valor", "duas casas"),
    ({"data_pagamento": None}, "data_pagamento", "Informe a data do pagamento"),
    ({"pago": False}, "data_vencimento", "Informe o vencimento"),
    ({"pago": False, "data_vencimento": "2030-01-10"}, "data_pagamento", "pendente não tem data de pagamento"),
    ({"descricao": "x" * 151}, "descricao", "máximo 150"),
])
def test_validacao_do_gasto(banco, paula, civic, mes_passado, alteracao, campo, trecho):
    resposta = paula.post(caminho(civic["id"], "/gastos"),
                          json=dados_gasto(dia(mes_passado, 18), **alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM gasto") == 0


def test_datas_no_futuro_e_valor_como_numero_sao_recusados(banco, paula, civic, hoje):
    amanha = str(hoje + timedelta(days=1))
    futuro = paula.post(caminho(civic["id"], "/gastos"), json=dados_gasto(amanha))
    assert futuro.status_code == 422 and "futuro" in futuro.json()["campos"]["data"]
    pago_amanha = paula.post(caminho(civic["id"], "/gastos"),
                             json=dados_gasto(str(hoje), data_pagamento=amanha))
    assert "futuro" in pago_amanha.json()["campos"]["data_pagamento"]
    com_float = paula.post(caminho(civic["id"], "/gastos"), json=dados_gasto(str(hoje), valor=30.5))
    assert com_float.status_code == 422
    total = paula.post(caminho(civic["id"], "/gastos"), json={**dados_gasto(str(hoje)), "total": "1.00"})
    assert total.status_code == 422  # a tela não envia totais
    assert valor_sql(banco, "SELECT count(*) FROM gasto") == 0


# ================================================================ pendentes

def test_vencidos_vence_hoje_e_a_vencer(paula, civic, hoje):
    def pendente(dias: int, descricao: str) -> dict:
        return criar_gasto(paula, civic["id"], str(hoje), categoria="seguro", valor="2400.00",
                           descricao=descricao, pago=False, data_pagamento=None,
                           data_vencimento=str(hoje + timedelta(days=dias)))

    distante = pendente(47, "Renovação do seguro")
    vencido = pendente(-3, "IPVA")
    hoje_vence = pendente(0, "Licenciamento")
    criar_gasto(paula, civic["id"], str(hoje))  # pago: não aparece
    lista = paula.get(caminho(civic["id"], "/gastos/pendentes")).json()
    assert lista["total"] == 3
    assert [(p["id"], p["situacao"], p["dias"]) for p in lista["itens"]] == [
        (vencido["id"], "vencido", -3), (hoje_vence["id"], "vence_hoje", 0),
        (distante["id"], "a_vencer", 47)]


def test_marcar_como_pago_entra_no_mes_do_pagamento(paula, civic, hoje, mes_passado):
    conta = criar_gasto(paula, civic["id"], dia(mes_passado, 24), categoria="seguro", valor="2400.00",
                        pago=False, data_pagamento=None, data_vencimento=str(hoje + timedelta(days=40)))
    assert resumo(paula, civic["id"], mes_passado)["total"] == "0.00"  # pendente não conta
    assert resumo(paula, civic["id"], mes_passado)["previsto_gastos"] == "0.00"  # vence noutro mês

    pago = paula.post(caminho(civic["id"], f"/gastos/{conta['id']}/pagar"), json={})
    assert pago.status_code == 200, pago.text
    assert (pago.json()["pago"], pago.json()["data_pagamento"]) == (True, str(hoje))
    assert resumo(paula, civic["id"], mes_passado)["total"] == "0.00"  # lançado no mês passado...
    assert resumo(paula, civic["id"], hoje)["total"] == "2400.00"     # ...pago neste mês
    de_novo = paula.post(caminho(civic["id"], f"/gastos/{conta['id']}/pagar"), json={})
    assert de_novo.status_code == 409 and "já está pago" in de_novo.json()["mensagem"]
    assert paula.get(caminho(civic["id"], "/gastos/pendentes")).json()["total"] == 0


def test_pagar_com_data_no_futuro_e_recusado(paula, civic, hoje):
    conta = criar_gasto(paula, civic["id"], str(hoje), pago=False, data_pagamento=None,
                        data_vencimento=str(hoje))
    resposta = paula.post(caminho(civic["id"], f"/gastos/{conta['id']}/pagar"),
                          json={"data_pagamento": str(hoje + timedelta(days=1))})
    assert resposta.status_code == 422
    assert paula.get(caminho(civic["id"], f"/gastos/{conta['id']}")).json()["pago"] is False


# ================================================================ resumo do mês

def test_resumo_integra_as_fontes_sem_duplicar(banco, paula, civic, mes_passado):
    criar_manutencao(paula, civic["id"], mes_passado, data=dia(mes_passado, 2), valor="1800.00",
                     descricao="Troca de pneus", quilometragem=None)
    abastecer(banco, civic["id"], dia(mes_passado, 15), "165.17")
    criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    item_de_projeto(banco, civic["id"], dia(mes_passado, 10), "500.00", status="cancelado")
    # Não entram: gasto pendente e despesa de outro mês.
    criar_gasto(paula, civic["id"], dia(mes_passado, 20), valor="99.00", pago=False,
                data_pagamento=None, data_vencimento=dia(mes_passado, 28))
    criar_gasto(paula, civic["id"], str(mes_passado - timedelta(days=1)), valor="77.00")

    r = resumo(paula, civic["id"], mes_passado)
    assert (r["total"], r["quantidade"]) == ("2495.17", 4)
    assert [(c["categoria"], c["total"], c["percentual"]) for c in r["categorias"]] == [
        ("manutencao", "1800.00", 72), ("projeto", "500.00", 20),
        ("combustivel", "165.17", 7), ("estacionamento", "30.00", 1)]
    # O pendente que vence no mês aparece como previsto, fora do total.
    assert (r["previsto_gastos"], r["quantidade_gastos_previstos"]) == ("99.00", 1)
    # Nenhuma cópia em gasto foi criada para manutenção, abastecimento ou projeto.
    assert valor_sql(banco, "SELECT count(*) FROM gasto") == 3


def test_manutencao_agendada_fica_no_previsto(paula, civic, hoje):
    daqui_a_3 = hoje + timedelta(days=3)
    criar_manutencao(paula, civic["id"], hoje, status="agendada", data=str(daqui_a_3),
                     valor="350.00", quilometragem=None)
    r = resumo(paula, civic["id"], daqui_a_3)
    assert (r["total"], r["previsto_manutencoes"], r["quantidade_manutencoes_previstas"]) == (
        "0.00", "350.00", 1)


def test_mes_vazio_nao_inventa_percentuais(paula, civic, mes_passado):
    r = resumo(paula, civic["id"], mes_passado)
    assert (r["total"], r["quantidade"], r["categorias"]) == ("0.00", 0, [])


def test_percentual_arredonda_meio_para_cima(paula, civic, mes_passado):
    criar_gasto(paula, civic["id"], dia(mes_passado, 3), valor="1.00", categoria="pedagio")
    criar_gasto(paula, civic["id"], dia(mes_passado, 4), valor="7.00", categoria="lavagem")
    categorias = resumo(paula, civic["id"], mes_passado)["categorias"]
    # 12,5% -> 13 e 87,5% -> 88 (a soma pode passar de 100; é o arredondamento de cada um).
    assert [(c["categoria"], c["percentual"]) for c in categorias] == [("lavagem", 88), ("pedagio", 13)]


def test_virada_do_mes_e_edicao_mudam_o_total(paula, civic, mes_passado):
    ultimo_dia = mes_passado.replace(day=28) + timedelta(days=4)
    ultimo_dia = ultimo_dia.replace(day=1) - timedelta(days=1)
    gasto = criar_gasto(paula, civic["id"], str(ultimo_dia), valor="50.00")
    proximo = ultimo_dia + timedelta(days=1)
    assert resumo(paula, civic["id"], mes_passado)["total"] == "50.00"
    assert resumo(paula, civic["id"], proximo)["total"] == "0.00"

    # Muda o pagamento para o primeiro dia do mês seguinte: o gasto muda de mês.
    editado = paula.put(caminho(civic["id"], f"/gastos/{gasto['id']}"),
                        json=dados_gasto(str(ultimo_dia), valor="50.00", data_pagamento=str(proximo)))
    assert editado.status_code == 200, editado.text
    assert resumo(paula, civic["id"], mes_passado)["total"] == "0.00"
    assert resumo(paula, civic["id"], proximo)["total"] == "50.00"

    # Volta para pendente: sai do total.
    paula.put(caminho(civic["id"], f"/gastos/{gasto['id']}"), json=dados_gasto(
        str(ultimo_dia), valor="50.00", pago=False, data_pagamento=None,
        data_vencimento=str(proximo)))
    assert resumo(paula, civic["id"], proximo)["total"] == "0.00"

    assert paula.delete(caminho(civic["id"], f"/gastos/{gasto['id']}")).status_code == 204
    assert paula.get(caminho(civic["id"], "/gastos/pendentes")).json()["total"] == 0


def test_lancamentos_do_mes_paginados_com_a_origem(banco, paula, civic, mes_passado):
    manutencao = criar_manutencao(paula, civic["id"], mes_passado, data=dia(mes_passado, 2),
                                  valor="350.00", descricao="Troca de óleo", quilometragem=None)
    abastecer(banco, civic["id"], dia(mes_passado, 15), "165.17")
    estacionamento = criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    primeira = lancamentos(paula, civic["id"], mes_passado, por_pagina=2)
    assert primeira["total"] == 3
    assert [(l["tipo"], l["data"], l["valor"]) for l in primeira["itens"]] == [
        ("gasto", dia(mes_passado, 18), "30.00"), ("abastecimento", dia(mes_passado, 15), "165.17")]
    assert primeira["itens"][0]["origem_id"] == estacionamento["id"]
    assert primeira["itens"][0]["descricao"] is None  # a tela mostra o nome da categoria
    assert primeira["itens"][1]["descricao"] == "Abastecimento, Shell"
    segunda = lancamentos(paula, civic["id"], mes_passado, por_pagina=2, pagina=2)
    assert [(l["tipo"], l["origem_id"], l["descricao"]) for l in segunda["itens"]] == [
        ("manutencao", manutencao["id"], "Troca de óleo")]


def test_mes_e_ano_invalidos(paula, civic):
    for params in ({"ano": 2026, "mes": 13}, {"ano": 1800, "mes": 1}, {"mes": 9}):
        assert paula.get(caminho(civic["id"], "/financas/resumo"), params=params).status_code == 422


def test_gasto_pago_antigo_sem_data_do_pagamento_continua_editavel(banco, paula, civic, mes_passado):
    executar_sql(banco, "INSERT INTO gasto (veiculo_id, categoria, valor, data, pago) "
                        "VALUES (:v, 'lavagem', 40.00, :d, true)", v=civic["id"], d=dia(mes_passado, 5))
    gasto_id = valor_sql(banco, "SELECT id FROM gasto")
    assert resumo(paula, civic["id"], mes_passado)["total"] == "40.00"  # conta pela data do gasto
    editado = paula.put(caminho(civic["id"], f"/gastos/{gasto_id}"), json=dados_gasto(
        dia(mes_passado, 5), categoria="lavagem", valor="45.00", data_pagamento=None))
    assert editado.status_code == 200, editado.text
    assert editado.json()["data_pagamento"] is None  # não inventada


# ======================================================= permissões e isolamento

def test_outro_usuario_nao_ve_nem_altera(banco, paula, rafael, civic, mes_passado):
    gasto = criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    url = caminho(civic["id"], f"/gastos/{gasto['id']}")
    params = {"ano": mes_passado.year, "mes": mes_passado.month}
    for resposta in (
        rafael.get(url),
        rafael.put(url, json=dados_gasto(dia(mes_passado, 18), valor="1.00")),
        rafael.post(f"{url}/pagar", json={}),
        rafael.delete(url),
        rafael.post(caminho(civic["id"], "/gastos"), json=dados_gasto(dia(mes_passado, 18))),
        rafael.get(caminho(civic["id"], "/gastos/pendentes")),
        rafael.get(caminho(civic["id"], "/financas/resumo"), params=params),
        rafael.get(caminho(civic["id"], "/financas/lancamentos"), params=params),
    ):
        assert resposta.status_code == 404, resposta.request.url
    # Com o próprio veículo no endereço, o gasto da Paula continua invisível.
    carro = criar_veiculo(rafael)
    assert rafael.get(caminho(carro["id"], f"/gastos/{gasto['id']}")).status_code == 404
    assert valor_sql(banco, "SELECT valor::text FROM gasto") == "30.00"


def test_gasto_de_outro_veiculo_do_mesmo_dono_e_os_totais_separados(paula, civic, mes_passado):
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    gasto = criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    assert paula.get(caminho(moto["id"], f"/gastos/{gasto['id']}")).status_code == 404
    assert resumo(paula, moto["id"], mes_passado)["total"] == "0.00"


def test_admin_ve_e_altera(admin, paula, civic, mes_passado):
    gasto = criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    assert admin.get(caminho(civic["id"], f"/gastos/{gasto['id']}")).status_code == 200
    assert resumo(admin, civic["id"], mes_passado)["total"] == "30.00"


def test_veiculo_inativo_mostra_mas_nao_aceita_alteracoes(paula, civic, mes_passado):
    gasto = criar_gasto(paula, civic["id"], dia(mes_passado, 18))
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    url = caminho(civic["id"], f"/gastos/{gasto['id']}")
    assert paula.get(url).status_code == 200
    assert resumo(paula, civic["id"], mes_passado)["total"] == "30.00"
    for resposta in (
        paula.post(caminho(civic["id"], "/gastos"), json=dados_gasto(dia(mes_passado, 18))),
        paula.put(url, json=dados_gasto(dia(mes_passado, 18))),
        paula.post(f"{url}/pagar", json={}),
        paula.delete(url),
    ):
        assert resposta.status_code == 409, resposta.text
        assert "inativo" in resposta.json()["mensagem"]


# ======================================================== ano e total (pedido da Paula)

def resumo_do_periodo(cliente, veiculo_id: int, **params) -> dict:
    resposta = cliente.get(caminho(veiculo_id, "/financas/resumo"), params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def test_resumo_do_ano_e_total_desde_o_primeiro_registro(banco, paula, civic, hoje):
    este_ano = hoje.replace(month=1, day=1)
    ano_passado = este_ano.replace(year=este_ano.year - 1)
    criar_gasto(paula, civic["id"], str(este_ano), valor="100.00")                     # janeiro deste ano
    criar_gasto(paula, civic["id"], str(ano_passado.replace(month=12, day=31)), valor="40.00")
    criar_manutencao(paula, civic["id"], hoje, data=str(ano_passado.replace(month=6, day=10)),
                     valor="300.00", quilometragem=None)
    # Pendente que vence neste ano: previsto do ano e do total, fora dos totais.
    criar_gasto(paula, civic["id"], str(hoje), valor="99.00", pago=False, data_pagamento=None,
                data_vencimento=str(hoje.replace(month=12, day=31)))

    ano = resumo_do_periodo(paula, civic["id"], ano=este_ano.year)
    assert (ano["periodo"], ano["ano"], ano["mes"], ano["total"], ano["quantidade"]) == (
        "ano", este_ano.year, None, "100.00", 1)
    assert (ano["previsto_gastos"], ano["quantidade_gastos_previstos"]) == ("99.00", 1)

    anterior = resumo_do_periodo(paula, civic["id"], ano=ano_passado.year)
    assert (anterior["total"], anterior["quantidade"]) == ("340.00", 2)
    assert [(c["categoria"], c["percentual"]) for c in anterior["categorias"]] == [
        ("manutencao", 88), ("estacionamento", 12)]

    total = resumo_do_periodo(paula, civic["id"])
    assert (total["periodo"], total["ano"], total["mes"], total["total"], total["quantidade"]) == (
        "total", None, None, "440.00", 3)
    assert total["previsto_gastos"] == "99.00"
    # A soma dos anos é o total: nada some nem é contado duas vezes.
    assert resumo_do_periodo(paula, civic["id"], ano=este_ano.year, mes=1)["total"] == "100.00"


def test_lancamentos_do_ano_e_do_total(paula, civic, hoje):
    este_ano = hoje.replace(month=1, day=1)
    ano_passado = este_ano.replace(year=este_ano.year - 1)
    criar_gasto(paula, civic["id"], str(este_ano), valor="100.00")
    criar_gasto(paula, civic["id"], str(ano_passado.replace(month=3, day=5)), valor="40.00")
    do_ano = paula.get(caminho(civic["id"], "/financas/lancamentos"), params={"ano": este_ano.year}).json()
    assert [l["valor"] for l in do_ano["itens"]] == ["100.00"]
    tudo = paula.get(caminho(civic["id"], "/financas/lancamentos")).json()
    assert (tudo["total"], [l["valor"] for l in tudo["itens"]]) == (2, ["100.00", "40.00"])


def test_mes_sem_ano_e_recusado(paula, civic):
    resposta = paula.get(caminho(civic["id"], "/financas/resumo"), params={"mes": 9})
    assert resposta.status_code == 422 and "Informe o ano" in resposta.json()["campos"]["ano"]
