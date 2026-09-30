"""Quilometragem de ponta a ponta: leituras, histórico, coerência e correção."""

from datetime import date, timedelta

import pytest

from tests.auth_utils import executar_sql, valor_sql
from tests.veiculo_utils import admin, banco, criar_veiculo, pasta_fotos, paula, rafael  # noqa: F401


@pytest.fixture
def hoje(banco) -> date:
    return valor_sql(banco, "SELECT current_date")


@pytest.fixture
def civic(paula) -> dict:
    return criar_veiculo(paula)


def leituras(cliente, veiculo_id: int, **parametros) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/leituras", params=parametros)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def registrar(cliente, veiculo_id: int, km, data=None):
    corpo = {"quilometragem": km}
    if data is not None:
        corpo["data_leitura"] = str(data)
    return cliente.post(f"/api/veiculos/{veiculo_id}/leituras", json=corpo)


# ------------------------------------------------------------------- registrar

def test_cadastro_cria_a_primeira_leitura_com_a_data_de_hoje(paula, civic, hoje):
    historico = leituras(paula, civic["id"])
    assert historico["total"] == 1
    primeira = historico["itens"][0]
    assert (primeira["origem"], primeira["quilometragem"], primeira["data_leitura"]) == (
        "cadastro", 85000, str(hoje))
    assert primeira["valida"] is True and primeira["editavel"] is True


def test_atualizar_km_guarda_a_data_da_leitura(paula, civic, hoje):
    resposta = registrar(paula, civic["id"], 85450)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["quilometragem"] == 85450 and corpo["data_leitura_km"] == str(hoje)


def test_data_da_leitura_e_diferente_da_data_em_que_foi_digitada(banco, paula, hoje):
    """Leitura feita há 3 dias e digitada hoje: a tela mostra a data da leitura."""
    veiculo = criar_veiculo(paula)
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = :d", d=hoje - timedelta(days=30))
    tres_dias = hoje - timedelta(days=3)
    corpo = registrar(paula, veiculo["id"], 85300, tres_dias).json()
    assert corpo["quilometragem"] == 85300 and corpo["data_leitura_km"] == str(tres_dias)
    item = leituras(paula, veiculo["id"])["itens"][0]
    assert item["data_leitura"] == str(tres_dias)
    assert item["criado_em"][:10] == str(hoje)


def test_leitura_historica_nao_reduz_a_quilometragem_atual(banco, paula, hoje):
    veiculo = criar_veiculo(paula)
    antiga = hoje - timedelta(days=200)
    resposta = registrar(paula, veiculo["id"], 70000, antiga)
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo["quilometragem"] == 85000 and corpo["data_leitura_km"] == str(hoje)
    assert [i["quilometragem"] for i in leituras(paula, veiculo["id"])["itens"]] == [85000, 70000]


@pytest.mark.parametrize("corpo, campo, trecho", [
    ({"quilometragem": -5}, "quilometragem", "não pode ser negativa"),
    ({"quilometragem": 99_999_999}, "quilometragem", "alta demais"),
    ({"quilometragem": "muito"}, "quilometragem", "Informe um número inteiro"),
    ({}, "quilometragem", "Campo obrigatório"),
    ({"quilometragem": 86000, "data_leitura": "2999-01-01"}, "data_leitura", "não pode ser no futuro"),
    ({"quilometragem": 86000, "veiculo_id": 1}, "veiculo_id", "Campo não permitido"),
])
def test_validacao_da_leitura(paula, civic, corpo, campo, trecho):
    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras", json=corpo)
    assert resposta.status_code == 422
    assert trecho in resposta.json()["campos"][campo]
    assert leituras(paula, civic["id"])["total"] == 1


def test_leitura_que_contradiz_o_historico_e_recusada(banco, paula, hoje):
    veiculo = criar_veiculo(paula)
    ontem = hoje - timedelta(days=1)
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = :d", d=ontem)

    # Hoje com km menor que o de ontem: o hodômetro não anda para trás.
    resposta = registrar(paula, veiculo["id"], 84000, hoje)
    assert resposta.status_code == 422
    mensagem = resposta.json()["campos"]["quilometragem"]
    assert f"em {ontem:%d/%m/%Y} o hodômetro marcava 85.000 km" in mensagem

    # Anteontem com km maior que o de ontem: também contradiz.
    resposta = registrar(paula, veiculo["id"], 86000, hoje - timedelta(days=2))
    assert resposta.status_code == 422

    # No mesmo dia, qualquer ordem vale; e a sequência coerente é aceita.
    assert registrar(paula, veiculo["id"], 84900, ontem).status_code == 201
    assert registrar(paula, veiculo["id"], 85200, hoje).status_code == 201
    assert valor_sql(banco, "SELECT quilometragem FROM veiculo") == 85200


def test_envio_repetido_nao_duplica_a_leitura(paula, civic):
    assert registrar(paula, civic["id"], 85450).status_code == 201
    assert registrar(paula, civic["id"], 85450).status_code == 201
    assert leituras(paula, civic["id"])["total"] == 2  # cadastro + uma manual


# ---------------------------------------------------------------- permissões

def test_outro_usuario_nao_ve_nem_registra_leituras(paula, rafael, civic):
    caminho = f"/api/veiculos/{civic['id']}/leituras"
    leitura_id = leituras(paula, civic["id"])["itens"][0]["id"]
    for resposta in (
        rafael.get(caminho),
        rafael.post(caminho, json={"quilometragem": 90000}),
        rafael.post(f"{caminho}/{leitura_id}/corrigir", json={"quilometragem": 1}),
        rafael.post(f"{caminho}/{leitura_id}/anular", json={}),
    ):
        assert resposta.status_code == 404
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["quilometragem"] == 85000


def test_leitura_de_outro_veiculo_nao_e_aceita_nem_do_mesmo_dono(paula, civic):
    """O id da leitura precisa ser do veículo do endereço, mesmo com o mesmo dono."""
    argo = criar_veiculo(paula, placa="BRA2E19", quilometragem=40000)
    leitura_do_argo = leituras(paula, argo["id"])["itens"][0]["id"]
    caminho = f"/api/veiculos/{civic['id']}/leituras/{leitura_do_argo}"
    assert paula.post(f"{caminho}/corrigir", json={"quilometragem": 50000}).status_code == 404
    assert paula.post(f"{caminho}/anular", json={}).status_code == 404
    assert paula.get(f"/api/veiculos/{argo['id']}").json()["quilometragem"] == 40000


def test_admin_tambem_respeita_o_veiculo_da_leitura(paula, admin, civic):
    argo = criar_veiculo(paula, placa="BRA2E19", quilometragem=40000)
    leitura_do_argo = leituras(admin, argo["id"])["itens"][0]["id"]
    resposta = admin.post(f"/api/veiculos/{civic['id']}/leituras/{leitura_do_argo}/corrigir",
                          json={"quilometragem": 50000})
    assert resposta.status_code == 404
    # No veículo certo, o admin consegue.
    resposta = admin.post(f"/api/veiculos/{argo['id']}/leituras/{leitura_do_argo}/corrigir",
                          json={"quilometragem": 41000})
    assert resposta.status_code == 200 and resposta.json()["quilometragem"] == 41000


# ------------------------------------------------------------------ correção

def test_corrigir_leitura_errada_preserva_o_historico_e_recalcula(banco, paula, civic, hoje):
    registrar(paula, civic["id"], 854500)  # um zero a mais
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["quilometragem"] == 854500
    errada = leituras(paula, civic["id"])["itens"][0]

    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras/{errada['id']}/corrigir",
                          json={"quilometragem": 85450, "motivo": "  Digitei um zero a mais  "})
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert corpo["quilometragem"] == 85450 and corpo["data_leitura_km"] == str(hoje)

    historico = leituras(paula, civic["id"])
    assert historico["total"] == 3
    por_km = {i["quilometragem"]: i for i in historico["itens"]}
    anulada, nova = por_km[854500], por_km[85450]
    assert anulada["valida"] is False and anulada["editavel"] is False
    assert anulada["motivo_anulacao"] == "Digitei um zero a mais" and anulada["anulada_em"]
    assert nova["valida"] is True and nova["corrige_id"] == anulada["id"]
    assert nova["data_leitura"] == anulada["data_leitura"] and nova["origem"] == "manual"


def test_corrigir_a_leitura_do_cadastro_para_menos_reduz_o_km_atual(paula, civic):
    """A redução só acontece por correção explícita, nunca por registro histórico."""
    cadastro = leituras(paula, civic["id"])["itens"][0]
    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras/{cadastro['id']}/corrigir",
                          json={"quilometragem": 58000})
    assert resposta.status_code == 200
    assert resposta.json()["quilometragem"] == 58000


def test_correcao_abaixo_do_km_da_compra_e_desfeita_por_inteiro(banco, paula, civic):
    cadastro = leituras(paula, civic["id"])["itens"][0]
    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras/{cadastro['id']}/corrigir",
                          json={"quilometragem": 8500})  # km da compra: 22.000
    assert resposta.status_code == 422
    assert "menor que a da compra (22.000 km)" in resposta.json()["campos"]["quilometragem"]
    # Rollback: nem leitura nova, nem leitura anulada, nem km alterado.
    assert valor_sql(banco, "SELECT count(*) FROM leitura_km") == 1
    assert valor_sql(banco, "SELECT count(*) FROM leitura_km WHERE anulada_em IS NOT NULL") == 0
    assert valor_sql(banco, "SELECT quilometragem FROM veiculo") == 85000


def test_correcao_tambem_precisa_combinar_com_o_historico(banco, paula, hoje):
    veiculo = criar_veiculo(paula)
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = :d", d=hoje - timedelta(days=10))
    registrar(paula, veiculo["id"], 86000, hoje)
    cadastro = [i for i in leituras(paula, veiculo["id"])["itens"] if i["origem"] == "cadastro"][0]
    resposta = paula.post(f"/api/veiculos/{veiculo['id']}/leituras/{cadastro['id']}/corrigir",
                          json={"quilometragem": 90000})
    assert resposta.status_code == 422
    assert "não combina com o histórico" in resposta.json()["mensagem"]
    igual = paula.post(f"/api/veiculos/{veiculo['id']}/leituras/{cadastro['id']}/corrigir",
                       json={"quilometragem": 85000})
    assert igual.status_code == 422 and "igual" in igual.json()["mensagem"]


def test_anular_leitura_recalcula_e_nao_deixa_o_veiculo_sem_leitura(paula, civic):
    registrar(paula, civic["id"], 99000)
    itens = leituras(paula, civic["id"])["itens"]
    errada = [i for i in itens if i["quilometragem"] == 99000][0]
    cadastro = [i for i in itens if i["origem"] == "cadastro"][0]

    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras/{errada['id']}/anular", json={})
    assert resposta.status_code == 200
    assert resposta.json()["quilometragem"] == 85000

    # Anular de novo, ou anular a única leitura válida, é recusado.
    repetida = paula.post(f"/api/veiculos/{civic['id']}/leituras/{errada['id']}/anular", json={})
    assert repetida.status_code == 409 and "já foi anulada" in repetida.json()["mensagem"]
    unica = paula.post(f"/api/veiculos/{civic['id']}/leituras/{cadastro['id']}/anular", json={})
    assert unica.status_code == 409 and "única leitura válida" in unica.json()["mensagem"]
    assert leituras(paula, civic["id"])["total"] == 2  # a anulada continua no histórico


def test_leitura_vinda_de_abastecimento_e_corrigida_no_registro_de_origem(banco, paula, civic):
    executar_sql(banco,
                 "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
                 "valor_litro, valor_total) VALUES (:v, current_date, 85450, 'gasolina', 40, 6.25, 250)",
                 v=civic["id"])
    do_abastecimento = [i for i in leituras(paula, civic["id"])["itens"]
                        if i["origem"] == "abastecimento"][0]
    assert do_abastecimento["editavel"] is False and do_abastecimento["origem_id"] is not None
    resposta = paula.post(
        f"/api/veiculos/{civic['id']}/leituras/{do_abastecimento['id']}/corrigir",
        json={"quilometragem": 85400})
    assert resposta.status_code == 409
    assert "registro de abastecimento" in resposta.json()["mensagem"]


def test_leitura_herdada_sem_data_aparece_como_desconhecida_e_pode_ser_corrigida(banco, paula,
                                                                                  civic, hoje):
    executar_sql(banco, "UPDATE leitura_km SET origem = 'legado', data_leitura = NULL")
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["data_leitura_km"] is None
    herdada = leituras(paula, civic["id"])["itens"][0]
    assert herdada["data_leitura"] is None and herdada["editavel"] is True
    # Uma leitura de hoje menor que a herdada contradiz o histórico.
    assert registrar(paula, civic["id"], 80000, hoje).status_code == 422
    resposta = paula.post(f"/api/veiculos/{civic['id']}/leituras/{herdada['id']}/corrigir",
                          json={"quilometragem": 84000})
    assert resposta.status_code == 200
    assert resposta.json()["quilometragem"] == 84000 and resposta.json()["data_leitura_km"] is None
    # Com uma leitura nova, a tela volta a ter uma data confiável.
    assert registrar(paula, civic["id"], 84500, hoje).json()["data_leitura_km"] == str(hoje)


# ----------------------------------------------------------------- paginação

def test_historico_paginado_com_ordem_estavel(banco, paula, civic, hoje):
    for km in range(85001, 85008):
        assert registrar(paula, civic["id"], km).status_code == 201
    primeira = leituras(paula, civic["id"], pagina=1, por_pagina=3)
    segunda = leituras(paula, civic["id"], pagina=2, por_pagina=3)
    terceira = leituras(paula, civic["id"], pagina=3, por_pagina=3)
    assert (primeira["total"], primeira["pagina"], primeira["por_pagina"]) == (8, 1, 3)
    ids = [i["id"] for pagina in (primeira, segunda, terceira) for i in pagina["itens"]]
    assert len(ids) == 8 and len(set(ids)) == 8  # nada repetido nem omitido entre páginas
    assert ids == sorted(ids, reverse=True)  # mesma data: o id desempata
    assert paula.get(f"/api/veiculos/{civic['id']}/leituras",
                     params={"por_pagina": 500}).status_code == 422
