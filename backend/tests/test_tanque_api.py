"""Tamanho do tanque, nível do marcador, marcação do tanque e "dois dos três"
(litros, preço, valor total), de ponta a ponta (API + PostgreSQL de teste).

O veículo de teste (Civic, flex) é cadastrado hoje com 85.000 km e tanque de
56 L. Registros de dias anteriores usam quilometragem abaixo de 85.000.
"""

from datetime import timedelta
from decimal import Decimal

import pytest

from tests.auth_utils import executar_sql
from tests.test_abastecimentos_api import abastecer, caminho, dados, resumo
from tests.test_manutencoes_api import civic, hoje, km_do_veiculo  # noqa: F401  (fixtures)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    dados_edicao,
    dados_veiculo,
    pasta_fotos,
    paula,
    rafael,
)


def marcar(cliente, veiculo_id: int, data, km: int, nivel: int, status: int = 201) -> dict:
    resposta = cliente.post(caminho(veiculo_id, "/tanque/marcacoes"),
                            json={"data": str(data), "quilometragem": km, "nivel": nivel})
    assert resposta.status_code == status, resposta.text
    return resposta.json()


def painel(cliente, veiculo_id: int) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/painel")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ============================================================ tamanho do tanque

def test_cadastro_exige_o_tamanho_do_tanque(paula):
    resposta = paula.post("/api/veiculos", json=dados_veiculo(capacidade_tanque=None))
    assert resposta.status_code == 422
    assert "tamanho do tanque" in resposta.json()["campos"]["capacidade_tanque"]
    criado = criar_veiculo(paula, capacidade_tanque="47.5")
    assert (criado["capacidade_tanque"], criado["tanque_pendente"]) == ("47.5", False)


@pytest.mark.parametrize("valor, trecho", [("0", "maior que zero"), ("47.55", "uma casa"),
                                           ("2000.1", "alto demais")])
def test_tamanho_do_tanque_invalido(paula, valor, trecho):
    resposta = paula.post("/api/veiculos", json=dados_veiculo(capacidade_tanque=valor))
    assert resposta.status_code == 422 and trecho in resposta.json()["campos"]["capacidade_tanque"]


def test_tamanho_do_tanque_como_numero_com_ponto_flutuante_e_recusado(paula):
    assert paula.post("/api/veiculos", json=dados_veiculo(capacidade_tanque=47.5)).status_code == 422


def test_eletrico_nao_tem_tanque(paula):
    criado = criar_veiculo(paula, tipo_combustivel="eletrico", capacidade_tanque="50.0")
    assert (criado["capacidade_tanque"], criado["tanque_pendente"]) == (None, False)
    marcar(paula, criado["id"], "2026-01-01", 85000, 4, status=409)


def test_veiculo_antigo_sem_tamanho_pede_para_atualizar(paula, civic, banco):
    v = civic["id"]
    executar_sql(banco, f"UPDATE veiculo SET capacidade_tanque = NULL WHERE id = {v}")
    assert paula.get(f"/api/veiculos/{v}").json()["tanque_pendente"] is True
    assert resumo(paula, v)["tanque_pendente"] is True
    assert painel(paula, v)["tanque"] == {"tamanho_pendente": True, "marcacao_do_mes_pendente": False}
    # Sem o tamanho, não dá para marcar o nível...
    erro = paula.post(caminho(v, "/tanque/marcacoes"), json={"data": "2026-01-01", "quilometragem": 80000,
                                                             "nivel": 4})
    assert erro.status_code == 409 and "tamanho do tanque" in erro.json()["mensagem"]
    # ...e a edição do veículo exige informar.
    assert paula.put(f"/api/veiculos/{v}", json=dados_edicao(capacidade_tanque=None)).status_code == 422
    editado = paula.put(f"/api/veiculos/{v}", json=dados_edicao(capacidade_tanque="55"))
    assert editado.status_code == 200 and editado.json()["capacidade_tanque"] == "55.0"
    assert painel(paula, v)["tanque"]["tamanho_pendente"] is False


# ================================================= litros, preço e valor total

def test_valor_total_e_preco_calculam_os_litros(paula, civic, hoje):
    criado = abastecer(paula, civic["id"], hoje, 85100, litros=None, preco="6.250", valor_total="250.00")
    assert (criado["litros"], criado["valor_litro"], criado["valor_total"]) == ("40.000", "6.250", "250.00")
    # 100,00 ÷ 5,79 = 17,2711... -> 17,271 L; o total gravado é o da bomba.
    outro = abastecer(paula, civic["id"], hoje, 85200, litros=None, preco="5.790", valor_total="100.00",
                      tanque_cheio=False)
    assert (outro["litros"], outro["valor_total"]) == ("17.271", "100.00")


def test_valor_total_e_litros_calculam_o_preco(paula, civic, hoje):
    criado = abastecer(paula, civic["id"], hoje, 85100, litros="38.5", preco=None, valor_total="165.17")
    assert (criado["litros"], criado["valor_litro"], criado["valor_total"]) == ("38.500", "4.290", "165.17")


def test_so_um_dos_tres_nao_basta(paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"),
                          json=dados(hoje, 85100, litros=None, preco=None, valor_total="100.00"))
    assert resposta.status_code == 422 and "valor_litro" in resposta.json()["campos"]
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85100, litros=None))
    assert resposta.status_code == 422 and "litros" in resposta.json()["campos"]


def test_total_com_float_e_recusado(paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"),
                          json=dados(hoje, 85100, litros=None, valor_total=250.0))
    assert resposta.status_code == 422


# ============================================================ limite do tanque

def test_litros_acima_do_tanque_sao_recusados(paula, civic, hoje):
    # Tanque de 56 L: até 61,6 L (10% de folga, contando o bocal).
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85100, litros="62"))
    assert resposta.status_code == 422
    assert "não cabem no tanque de 56 L" in resposta.json()["campos"]["litros"]
    abastecer(paula, civic["id"], hoje, 85100, litros="61.6")


def test_com_o_nivel_so_cabe_o_espaco_livre_com_folga_de_um_oitavo(paula, civic, hoje):
    # Marcador em 3/4 num tanque de 56 L: livre 14 L, folga 7 L -> até 21 L.
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"),
                          json=dados(hoje, 85100, litros=None, valor_total="150.00", preco="6.000",
                                     nivel_antes=6))
    assert resposta.status_code == 422
    assert "Com o marcador em 3/4, cabem cerca de 14 L" in resposta.json()["campos"]["litros"]
    criado = abastecer(paula, civic["id"], hoje, 85100, litros="21", nivel_antes=6)
    assert criado["nivel_antes"] == 6


@pytest.mark.parametrize("nivel", [-1, 9])
def test_nivel_fora_da_escala(paula, civic, hoje, nivel):
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85100, nivel_antes=nivel))
    assert resposta.status_code == 422 and "nivel_antes" in resposta.json()["campos"]


def test_nivel_nao_vale_para_recarga_eletrica(paula):
    hibrido = criar_veiculo(paula, tipo_combustivel="hibrido", placa="HIB1A23")
    resposta = paula.post(caminho(hibrido["id"], "/abastecimentos"),
                          json=dados("2026-01-01", 80000, combustivel="eletrica", tipo="ac", nivel_antes=4))
    assert resposta.status_code == 422 and "nivel_antes" in resposta.json()["campos"]


# =========================================================== marcação do tanque

def test_marcacao_e_tanque_cheio_dao_consumo_estimado_com_faixa(paula, civic, hoje):
    v = civic["id"]
    inicio = hoje - timedelta(days=20)
    # Marcador em 3/4 (faltam 14 L de 56); 280 km depois, enche com 42 L: 280 / (42 − 14) = 10.
    m = marcar(paula, v, inicio, 84000, 6)
    assert (m["nivel"], m["consumo"]["tipo"]) == (6, "primeiro_nivel")
    a = abastecer(paula, v, inicio + timedelta(days=5), 84280, litros="42")
    assert a["consumo"]["km_por_litro"] == "10.0" and a["consumo"]["estimado"] is True
    # margem ± 3,5 L (meio oitavo de 56): 280 / 31,5 = 8,9 e 280 / 24,5 = 11,4
    assert (a["consumo"]["km_por_litro_minimo"], a["consumo"]["km_por_litro_maximo"]) == ("8.9", "11.4")
    media = resumo(paula, v)["medias"][0]
    assert (media["km_por_litro"], media["estimada"], media["margem"]) == ("10.0", True, "3.500")
    consumo = painel(paula, v)["consumo"]
    assert (consumo["valor"], consumo["estimado"], consumo["minimo"], consumo["maximo"]) == (
        "10.0", True, "8.9", "11.4")


def test_marcacao_vira_leitura_e_apagar_retira(paula, civic, hoje):
    v = civic["id"]
    m = marcar(paula, v, hoje, 85500, 4)
    assert km_do_veiculo(paula, v) == 85500
    leituras = paula.get(f"/api/veiculos/{v}/leituras").json()["itens"]
    assert leituras[0]["origem"] == "medicao_tanque" and leituras[0]["editavel"] is False
    assert paula.delete(caminho(v, f"/tanque/marcacoes/{m['id']}")).status_code == 204
    assert km_do_veiculo(paula, v) == 85000


def test_marcacao_precisa_combinar_com_o_hodometro(paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"], "/tanque/marcacoes"),
                          json={"data": str(hoje - timedelta(days=3)), "quilometragem": 86000, "nivel": 4})
    assert resposta.status_code == 422 and "não combina" in resposta.json()["campos"]["quilometragem"]


@pytest.mark.parametrize("campos, campo", [
    ({"quilometragem": None, "nivel": 4}, "quilometragem"),
    ({"quilometragem": 85100, "nivel": None}, "nivel"),
    ({"quilometragem": 85100, "nivel": 9}, "nivel"),
])
def test_marcacao_validacoes(paula, civic, hoje, campos, campo):
    resposta = paula.post(caminho(civic["id"], "/tanque/marcacoes"), json={"data": str(hoje), **campos})
    assert resposta.status_code == 422 and campo in resposta.json()["campos"]


def test_marcacao_no_futuro_e_recusada(paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"], "/tanque/marcacoes"),
                          json={"data": str(hoje + timedelta(days=1)), "quilometragem": 85100, "nivel": 4})
    assert resposta.status_code == 422


def test_editar_marcacao_recalcula(paula, civic, hoje):
    v = civic["id"]
    inicio = hoje - timedelta(days=20)
    m = marcar(paula, v, inicio, 84000, 6)
    abastecer(paula, v, inicio + timedelta(days=5), 84280, litros="42")
    editada = paula.put(caminho(v, f"/tanque/marcacoes/{m['id']}"),
                        json={"data": str(inicio), "quilometragem": 84000, "nivel": 4})
    assert editada.status_code == 200, editada.text
    # Agora faltavam 28 L: 280 / (42 − 28) = 20.
    assert resumo(paula, v)["medias"][0]["km_por_litro"] == "20.0"
    lista = paula.get(caminho(v, "/tanque/marcacoes")).json()
    assert lista["total"] == 1 and lista["itens"][0]["nivel"] == 4


def test_marcacao_do_mes_pendente_some_depois_de_marcar(paula, civic, hoje):
    v = civic["id"]
    assert resumo(paula, v)["marcacao_do_mes_pendente"] is True
    assert painel(paula, v)["tanque"]["marcacao_do_mes_pendente"] is True
    marcar(paula, v, hoje, 85000, 4)
    assert resumo(paula, v)["marcacao_do_mes_pendente"] is False
    assert painel(paula, v)["tanque"]["marcacao_do_mes_pendente"] is False


def test_consumo_por_mes(paula, civic, hoje):
    v = civic["id"]
    primeiro = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)  # início do mês passado
    # Carro flex: um tanque cheio antes diz qual combustível estava no tanque.
    abastecer(paula, v, primeiro - timedelta(days=1), 83990, litros="30")
    marcar(paula, v, primeiro, 84000, 8)                                   # cheio pelo marcador
    marcar(paula, v, hoje.replace(day=1), 84500, 4)                        # faltam 28 L
    meses = resumo(paula, v)["meses"]
    assert len(meses) == 1
    m = meses[0]
    assert (m["ano"], m["mes"], m["distancia"], m["quantidade"]) == (primeiro.year, primeiro.month, 500, "28.000")
    assert (m["km_por_litro"], m["estimada"]) == ("17.9", True)


# =================================================================== permissões

def test_marcacao_de_outra_pessoa_da_404(paula, rafael, civic, hoje):
    v = civic["id"]
    m = marcar(paula, v, hoje, 85100, 4)
    assert rafael.get(caminho(v, "/tanque/marcacoes")).status_code == 404
    assert rafael.post(caminho(v, "/tanque/marcacoes"),
                       json={"data": str(hoje), "quilometragem": 85200, "nivel": 4}).status_code == 404
    assert rafael.delete(caminho(v, f"/tanque/marcacoes/{m['id']}")).status_code == 404
    # Marcação de outro veículo da mesma pessoa, pelo endereço deste: 404.
    outro = criar_veiculo(paula, placa="XYZ9A87")
    assert paula.get(caminho(outro["id"], f"/tanque/marcacoes/{m['id']}")).status_code == 404
    assert paula.put(caminho(outro["id"], f"/tanque/marcacoes/{m['id']}"),
                     json={"data": str(hoje), "quilometragem": 85100, "nivel": 2}).status_code == 404


def test_admin_ve_e_veiculo_inativo_e_so_leitura(paula, admin, civic, hoje):
    v = civic["id"]
    marcar(paula, v, hoje, 85100, 4)
    assert admin.get(caminho(v, "/tanque/marcacoes")).json()["total"] == 1
    assert paula.post(f"/api/veiculos/{v}/inativar").status_code == 200
    resposta = paula.post(caminho(v, "/tanque/marcacoes"),
                          json={"data": str(hoje), "quilometragem": 85200, "nivel": 4})
    assert resposta.status_code == 409
    assert resumo(paula, v)["marcacao_do_mes_pendente"] is False


def test_quantidade_decimal_nao_vira_float(paula, civic, hoje):
    criado = abastecer(paula, civic["id"], hoje, 85100, litros=None, preco="5.999", valor_total="99.99")
    assert Decimal(criado["litros"]) == Decimal("16.668")  # 99,99 ÷ 5,999 = 16,6677...
