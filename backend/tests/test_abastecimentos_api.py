"""Abastecimentos, consumo e "Etanol ou gasolina?", de ponta a ponta (API + PostgreSQL de teste).

O veículo de teste é cadastrado hoje com 85.000 km; os abastecimentos de hoje
têm quilometragem crescente (no mesmo dia, a ordem é a da quilometragem).
"""

from datetime import timedelta

import pytest

from tests.auth_utils import valor_sql
from tests.test_manutencoes_api import civic, hoje, km_do_veiculo  # noqa: F401  (fixtures)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    pasta_fotos,
    paula,
    rafael,
)


def dados(data, km: int, litros: str = "40.000", preco: str = "6.250", **alteracoes) -> dict:
    return {"combustivel": "gasolina", "tipo": "comum", "data": str(data), "quilometragem": km,
            "litros": litros,
            "valor_litro": preco, "valor_total": None, "tanque_cheio": True, "posto": "Shell",
            **alteracoes}


def caminho(veiculo_id: int, resto: str = "") -> str:
    return f"/api/veiculos/{veiculo_id}{resto}"


def abastecer(cliente, veiculo_id: int, data, km: int, **alteracoes) -> dict:
    resposta = cliente.post(caminho(veiculo_id, "/abastecimentos"), json=dados(data, km, **alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def lista(cliente, veiculo_id: int) -> list[dict]:
    resposta = cliente.get(caminho(veiculo_id, "/abastecimentos"))
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["itens"]


def resumo(cliente, veiculo_id: int, **params) -> dict:
    resposta = cliente.get(caminho(veiculo_id, "/combustivel/resumo"), params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


# ================================================================ cadastro

def test_registrar_com_total_calculado_meio_para_cima(paula, civic, hoje):
    criado = abastecer(paula, civic["id"], hoje, 85100, litros="38.5", preco="4.29", combustivel="etanol")
    assert (criado["litros"], criado["valor_litro"], criado["valor_total"]) == ("38.500", "4.290", "165.17")
    assert criado["consumo"] == {
        "tipo": "primeiro_cheio", "km_por_litro": None, "estimado": False, "km_por_litro_minimo": None,
        "km_por_litro_maximo": None,
        "motivo": "Primeiro tanque cheio: o consumo aparece no próximo tanque cheio ou nível do marcador."}
    assert criado["nivel_antes"] is None
    assert km_do_veiculo(paula, civic["id"]) == 85100  # vira leitura do hodômetro
    assert paula.get(caminho(civic["id"], f"/abastecimentos/{criado['id']}")).json() == criado


def test_valor_do_cupom_ate_50_reais_do_calculado_e_gravado(banco, paula, civic, hoje):
    # Pedido da Paula (0009): até R$ 50,00 de diferença. Calculado: R$ 165,17.
    perto = abastecer(paula, civic["id"], hoje, 85100, litros="38.5", preco="4.29", valor_total="165.20")
    assert perto["valor_total"] == "165.20"
    no_limite = abastecer(paula, civic["id"], hoje, 85200, litros="38.5", preco="4.29", valor_total="215.17")
    assert no_limite["valor_total"] == "215.17"
    longe = paula.post(caminho(civic["id"], "/abastecimentos"),
                       json=dados(hoje, 85300, litros="38.5", preco="4.29", valor_total="215.18"))
    assert longe.status_code == 422
    assert "difere mais de R$ 50,00 do calculado (R$ 165.17)" in longe.json()["campos"]["valor_total"]
    assert valor_sql(banco, "SELECT count(*) FROM abastecimento") == 2


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"combustivel": "diesel"}, "combustivel", "usa gasolina ou etanol"),
    ({"tipo": None}, "tipo", "Escolha o tipo de gasolina"),
    ({"tipo": "s10"}, "tipo", "Tipo inválido para gasolina"),
    ({"tipo": "aditivado"}, "tipo", "Tipo inválido para gasolina"),  # é o nome do tipo do etanol
    ({"litros": "0"}, "litros", "maior que zero"),
    ({"litros": "10.1234"}, "litros", "3 casas"),
    ({"litros": None}, "litros", "Informe os litros"),
    ({"valor_litro": None}, "valor_litro", "Informe o preço"),
    ({"quilometragem": None}, "quilometragem", "Informe a quilometragem"),
    ({"valor_total": "250.001"}, "valor_total", "duas casas"),
    ({"posto": "x" * 81}, "posto", "máximo 80"),
])
def test_validacao(banco, paula, civic, hoje, alteracao, campo, trecho):
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85100, **alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM abastecimento") == 0


def test_numero_com_ponto_flutuante_e_data_futura_sao_recusados(banco, paula, civic, hoje):
    com_float = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85100, litros=40.5))
    assert com_float.status_code == 422
    futuro = paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje + timedelta(days=1), 85100))
    assert "futuro" in futuro.json()["campos"]["data"]
    assert valor_sql(banco, "SELECT count(*) FROM abastecimento") == 0


def test_quilometragem_que_contradiz_o_hodometro_e_recusada(paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"], "/abastecimentos"),
                          json=dados(hoje - timedelta(days=3), 90000))
    assert resposta.status_code == 422
    assert "não combina com o histórico" in resposta.json()["campos"]["quilometragem"]


def test_veiculo_eletrico_so_registra_recarga(paula, hoje):
    eletrico = criar_veiculo(paula, placa="ELE-2026", tipo_combustivel="eletrico")
    gasolina = paula.post(caminho(eletrico["id"], "/abastecimentos"), json=dados(hoje, 85100))
    assert gasolina.status_code == 422 and "usa eletricidade" in gasolina.json()["campos"]["combustivel"]
    assert resumo(paula, eletrico["id"])["combustiveis"] == ["eletrica"]


# ================================================================ consumo

def test_ciclo_do_exemplo_pela_api(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85000 + 1, litros="40")          # cheio inicial
    abastecer(paula, civic["id"], hoje, 85101, litros="10", tanque_cheio=False)
    abastecer(paula, civic["id"], hoje, 85301, litros="20")              # 300 / 30 = 10 km/L
    itens = lista(paula, civic["id"])
    assert [(a["quilometragem"], a["consumo"]["tipo"], a["consumo"]["km_por_litro"]) for a in itens] == [
        (85301, "consumo", "10.0"), (85101, "parcial", None), (85001, "primeiro_cheio", None)]
    [media] = resumo(paula, civic["id"])["medias"]
    assert (media["combustivel"], media["km_por_litro"], media["distancia"], media["quantidade"],
            media["ciclos"]) == ("gasolina", "10.0", 300, "30.000", 1)


def test_lancamento_historico_e_edicao_recalculam_os_ciclos(paula, civic, hoje):
    antigo = abastecer(paula, civic["id"], hoje - timedelta(days=10), 84000, litros="40")
    atual = abastecer(paula, civic["id"], hoje, 84600, litros="50")        # 600 / 50 = 12
    assert lista(paula, civic["id"])[0]["consumo"]["km_por_litro"] == "12.0"
    # Um parcial esquecido, lançado depois, entra no ciclo: 600 / 60 = 10.
    parcial = abastecer(paula, civic["id"], hoje - timedelta(days=5), 84300, litros="10", tanque_cheio=False)
    assert lista(paula, civic["id"])[0]["consumo"]["km_por_litro"] == "10.0"
    # Corrigir a quantidade do parcial recalcula de novo: 600 / 75 = 8.
    editado = paula.put(caminho(civic["id"], f"/abastecimentos/{parcial['id']}"),
                        json=dados(hoje - timedelta(days=5), 84300, litros="25", tanque_cheio=False))
    assert editado.status_code == 200, editado.text
    assert lista(paula, civic["id"])[0]["consumo"]["km_por_litro"] == "8.0"
    # Apagar o cheio inicial: o atual vira o primeiro cheio (sem consumo).
    assert paula.delete(caminho(civic["id"], f"/abastecimentos/{antigo['id']}")).status_code == 204
    assert paula.get(caminho(civic["id"], f"/abastecimentos/{atual['id']}")).json()["consumo"]["tipo"] == "primeiro_cheio"
    assert resumo(paula, civic["id"])["medias"] == []


def test_dados_insuficientes_nao_viram_zero(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85100)
    r = resumo(paula, civic["id"])
    assert r["medias"] == []
    assert r["comparacao"]["recomendacao"] is None
    assert "falta o consumo de gasolina e de etanol" in r["comparacao"]["motivo"]


# ======================================================= etanol ou gasolina

def ciclos_do_pdf(paula, veiculo_id: int, hoje) -> None:
    """Gasolina 11,3 km/L e etanol 7,9 km/L; últimos preços R$ 6,25 e R$ 4,29 (como no PDF)."""
    abastecer(paula, veiculo_id, hoje, 85000 + 1, litros="40", preco="6.250")
    abastecer(paula, veiculo_id, hoje, 85340, litros="30", preco="6.250")                 # 339 / 30 = 11,3
    abastecer(paula, veiculo_id, hoje, 85500, litros="30", preco="4.290", combustivel="etanol")  # mistura
    abastecer(paula, veiculo_id, hoje, 85737, litros="30", preco="4.290", combustivel="etanol")  # 237 / 30 = 7,9


def test_comparacao_com_o_consumo_do_carro_e_o_ultimo_preco(paula, civic, hoje):
    ciclos_do_pdf(paula, civic["id"], hoje)
    r = resumo(paula, civic["id"])
    assert [(m["combustivel"], m["km_por_litro"]) for m in r["medias"]] == [("gasolina", "11.3"), ("etanol", "7.9")]
    c = r["comparacao"]
    # 7,9 / 11,3 = 69,9% -> 70%; 4,29 / 6,25 = 68,6% -> 69%: etanol compensa.
    assert (c["recomendacao"], c["limite_percentual"], c["relacao_percentual"], c["preco_gasolina"],
            c["preco_etanol"], c["precos_simulados"]) == ("etanol", 70, 69, "6.250", "4.290", False)
    tipos = [a["consumo"]["tipo"] for a in lista(paula, civic["id"])]
    assert tipos == ["consumo", "ciclo_invalido", "consumo", "primeiro_cheio"]


def test_simulacao_com_os_precos_de_hoje_nao_grava_nada(banco, paula, civic, hoje):
    ciclos_do_pdf(paula, civic["id"], hoje)
    r = resumo(paula, civic["id"], preco_gasolina="6.000", preco_etanol="4.500")  # 75% > 70%
    assert (r["comparacao"]["recomendacao"], r["comparacao"]["relacao_percentual"],
            r["comparacao"]["precos_simulados"]) == ("gasolina", 75, True)
    assert valor_sql(banco, "SELECT count(*) FROM abastecimento") == 4
    so_um = paula.get(caminho(civic["id"], "/combustivel/resumo"), params={"preco_gasolina": "6.000"})
    assert so_um.status_code == 422


def test_veiculo_so_a_gasolina_nao_tem_comparacao(paula, hoje):
    carro = criar_veiculo(paula, placa="GAS-2026", tipo_combustivel="gasolina")
    abastecer(paula, carro["id"], hoje, 85100)
    r = resumo(paula, carro["id"])
    assert (r["combustiveis"], r["comparacao"]) == (["gasolina"], None)
    etanol = paula.post(caminho(carro["id"], "/abastecimentos"), json=dados(hoje, 85200, combustivel="etanol"))
    assert etanol.status_code == 422 and "usa gasolina" in etanol.json()["campos"]["combustivel"]


def test_postos_recentes_sem_repetir(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85100, posto="Shell")
    abastecer(paula, civic["id"], hoje, 85200, posto="  Ipiranga  ")
    abastecer(paula, civic["id"], hoje, 85300, posto="Shell")
    abastecer(paula, civic["id"], hoje, 85400, posto=None)
    assert sorted(resumo(paula, civic["id"])["postos_recentes"]) == ["Ipiranga", "Shell"]


# ======================================================= finanças e permissões

def test_abastecimento_entra_nas_financas_como_combustivel(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85100, litros="38.5", preco="4.29", combustivel="etanol",
              posto="Ipiranga")
    r = paula.get(caminho(civic["id"], "/financas/resumo"), params={"ano": hoje.year, "mes": hoje.month}).json()
    assert (r["total"], [c["categoria"] for c in r["categorias"]]) == ("165.17", ["combustivel"])
    [lanc] = paula.get(caminho(civic["id"], "/financas/lancamentos"),
                       params={"ano": hoje.year, "mes": hoje.month}).json()["itens"]
    assert (lanc["tipo"], lanc["descricao"]) == ("abastecimento", "Abastecimento, Ipiranga")


def test_outro_usuario_nao_ve_nem_altera(banco, paula, rafael, civic, hoje):
    a = abastecer(paula, civic["id"], hoje, 85100)
    url = caminho(civic["id"], f"/abastecimentos/{a['id']}")
    for resposta in (
        rafael.get(url), rafael.put(url, json=dados(hoje, 85100)), rafael.delete(url),
        rafael.get(caminho(civic["id"], "/abastecimentos")),
        rafael.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85200)),
        rafael.get(caminho(civic["id"], "/combustivel/resumo")),
    ):
        assert resposta.status_code == 404, resposta.request.url
    carro = criar_veiculo(rafael)
    assert rafael.get(caminho(carro["id"], f"/abastecimentos/{a['id']}")).status_code == 404
    assert valor_sql(banco, "SELECT count(*) FROM abastecimento") == 1


def test_abastecimento_de_outro_veiculo_do_mesmo_dono(paula, civic, hoje):
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    a = abastecer(paula, civic["id"], hoje, 85100)
    assert paula.get(caminho(moto["id"], f"/abastecimentos/{a['id']}")).status_code == 404
    assert paula.delete(caminho(moto["id"], f"/abastecimentos/{a['id']}")).status_code == 404
    assert lista(paula, moto["id"]) == []


def test_admin_ve_e_veiculo_inativo_e_so_leitura(admin, paula, civic, hoje):
    a = abastecer(paula, civic["id"], hoje, 85100)
    assert admin.get(caminho(civic["id"], f"/abastecimentos/{a['id']}")).status_code == 200
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    url = caminho(civic["id"], f"/abastecimentos/{a['id']}")
    assert paula.get(url).status_code == 200
    for resposta in (paula.post(caminho(civic["id"], "/abastecimentos"), json=dados(hoje, 85200)),
                     paula.put(url, json=dados(hoje, 85100)), paula.delete(url)):
        assert resposta.status_code == 409 and "inativo" in resposta.json()["mensagem"]


def test_apagar_retira_a_leitura_do_hodometro(banco, paula, civic, hoje):
    a = abastecer(paula, civic["id"], hoje, 85500)
    assert km_do_veiculo(paula, civic["id"]) == 85500
    assert paula.delete(caminho(civic["id"], f"/abastecimentos/{a['id']}")).status_code == 204
    assert km_do_veiculo(paula, civic["id"]) == 85000
    assert valor_sql(banco, "SELECT count(*) FROM leitura_km WHERE origem = 'abastecimento'") == 0


# ================================================== tipo do combustível (0009)

def test_tipo_e_gravado_e_nao_muda_o_consumo(paula, civic, hoje):
    abastecer(paula, civic["id"], hoje, 85001, litros="40", tipo="comum")
    fim = abastecer(paula, civic["id"], hoje, 85301, litros="30", tipo="premium_aditivada")
    assert fim["tipo"] == "premium_aditivada"
    # Comum e premium aditivada são o mesmo combustível: o ciclo vale (300 / 30 = 10).
    assert fim["consumo"]["km_por_litro"] == "10.0"


@pytest.mark.parametrize("combustivel, tipos", [
    ("gasolina", ["comum", "comum_aditivada", "premium", "premium_aditivada"]),
    ("etanol", ["comum", "aditivado", "premium", "premium_aditivado"]),
])
def test_todos_os_tipos_da_tabela_sao_aceitos(paula, civic, hoje, combustivel, tipos):
    for i, tipo in enumerate(tipos):
        a = abastecer(paula, civic["id"], hoje, 85100 + i * 100, combustivel=combustivel, tipo=tipo)
        assert a["tipo"] == tipo


def test_veiculo_a_diesel_so_aceita_os_tipos_do_diesel(paula, hoje):
    caminhao = criar_veiculo(paula, placa="DSL-2026", tipo_combustivel="diesel")
    assert resumo(paula, caminhao["id"])["combustiveis"] == ["diesel"]
    for i, tipo in enumerate(["s10", "s10_aditivado", "s500", "s500_aditivado"]):
        a = abastecer(paula, caminhao["id"], hoje, 85100 + i * 100, combustivel="diesel", tipo=tipo)
        assert a["tipo"] == tipo
    gasolina = paula.post(caminho(caminhao["id"], "/abastecimentos"), json=dados(hoje, 86000))
    assert gasolina.status_code == 422 and "usa diesel" in gasolina.json()["campos"]["combustivel"]
    comum = paula.post(caminho(caminhao["id"], "/abastecimentos"),
                       json=dados(hoje, 86000, combustivel="diesel", tipo="comum"))
    assert comum.status_code == 422 and "Tipo inválido para diesel" in comum.json()["campos"]["tipo"]


def test_recarga_eletrica_em_kwh_com_consumo_em_km_por_kwh(paula, hoje):
    eletrico = criar_veiculo(paula, placa="ELE-2026", tipo_combustivel="eletrico")
    abastecer(paula, eletrico["id"], hoje, 85001, combustivel="eletrica", tipo="ac", litros="40", preco="0.900")
    fim = abastecer(paula, eletrico["id"], hoje, 85241, combustivel="eletrica", tipo="dc", litros="40",
                    preco="2.500")                                      # 240 km / 40 kWh = 6
    assert (fim["tipo"], fim["valor_total"], fim["consumo"]["km_por_litro"]) == ("dc", "100.00", "6.0")
    [media] = resumo(paula, eletrico["id"])["medias"]
    assert (media["combustivel"], media["km_por_litro"]) == ("eletrica", "6.0")
    sem_tipo = paula.post(caminho(eletrico["id"], "/abastecimentos"),
                          json=dados(hoje, 85300, combustivel="eletrica", tipo=None))
    assert "Escolha o tipo de eletricidade" in sem_tipo.json()["campos"]["tipo"]


def test_hibrido_aceita_gasolina_e_recarga(paula, hoje):
    hibrido = criar_veiculo(paula, placa="HIB-2026", tipo_combustivel="hibrido")
    assert resumo(paula, hibrido["id"])["combustiveis"] == ["gasolina", "eletrica"]
    abastecer(paula, hibrido["id"], hoje, 85100, combustivel="gasolina", tipo="comum")
    recarga = abastecer(paula, hibrido["id"], hoje, 85200, combustivel="eletrica", tipo="ac", litros="10",
                        preco="0.900")
    # Gasolina e recarga entre dois "cheios" é mistura: esse ciclo fica sem consumo.
    assert recarga["consumo"]["tipo"] == "ciclo_invalido"


def test_gnv_nao_tem_tipo(paula, hoje):
    carro = criar_veiculo(paula, placa="GNV-2026", tipo_combustivel="gnv")
    com_tipo = paula.post(caminho(carro["id"], "/abastecimentos"),
                          json=dados(hoje, 85100, combustivel="gnv", tipo="comum"))
    assert com_tipo.status_code == 422 and "GNV não tem tipo" in com_tipo.json()["campos"]["tipo"]
    sem_tipo = abastecer(paula, carro["id"], hoje, 85100, combustivel="gnv", tipo=None)
    assert sem_tipo["tipo"] is None


def test_abastecimento_antigo_sem_tipo_continua_editavel_sem_inventar(banco, paula, civic, hoje):
    from tests.auth_utils import executar_sql
    executar_sql(banco, "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
                        "valor_litro, valor_total) VALUES (:v, :d, 85100, 'gasolina', 40, 6.25, 250.00)",
                 v=civic["id"], d=hoje)
    antigo = lista(paula, civic["id"])[0]
    assert antigo["tipo"] is None  # não informado
    editado = paula.put(caminho(civic["id"], f"/abastecimentos/{antigo['id']}"),
                        json=dados(hoje, 85100, tipo=None, posto="Shell"))
    assert editado.status_code == 200, editado.text
    assert (editado.json()["tipo"], editado.json()["posto"]) == (None, "Shell")
    escolhido = paula.put(caminho(civic["id"], f"/abastecimentos/{antigo['id']}"),
                          json=dados(hoje, 85100, tipo="premium"))
    assert escolhido.json()["tipo"] == "premium"
