"""Projetos de melhoria, gastos do projeto, orçamento e fotos de antes/depois (API + PostgreSQL de teste)."""

from datetime import timedelta

import pytest

from tests.auth_utils import valor_sql
from tests.test_manutencoes_api import civic, hoje  # noqa: F401  (fixtures)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    arquivos_na_pasta,
    banco,
    criar_veiculo,
    enviar_foto,
    pasta_fotos,
    paula,
    rafael,
)


def dados_projeto(**alteracoes) -> dict:
    return {"nome": "Rodas de liga leve", "descricao": "Trocar as rodas originais por um jogo aro 17.",
            "categoria": "exterior", "orcamento": "4500.00", "data_prevista": None, **alteracoes}


def caminho(veiculo_id: int, resto: str = "") -> str:
    return f"/api/veiculos/{veiculo_id}/projetos{resto}"


def criar_projeto(cliente, veiculo_id: int, **alteracoes) -> dict:
    resposta = cliente.post(caminho(veiculo_id), json=dados_projeto(**alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def gastar(cliente, veiculo_id: int, projeto_id: int, descricao: str, valor: str, data) -> dict:
    resposta = cliente.post(caminho(veiculo_id, f"/{projeto_id}/itens"),
                            json={"descricao": descricao, "valor": valor, "data": str(data)})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# ================================================================ cadastro

def test_criar_projeto_e_ver_vazio(paula, civic):
    p = criar_projeto(paula, civic["id"], nome="  Rodas  de liga leve ")
    assert (p["nome"], p["status"], p["gasto"], p["orcamento"], p["percentual"], p["diferenca"]) == (
        "Rodas de liga leve", "planejado", "0.00", "4500.00", 0, "4500.00")
    assert (p["itens"], p["fotos_antes"], p["fotos_depois"], p["data_conclusao"]) == ([], [], [], None)
    assert paula.get(caminho(civic["id"], f"/{p['id']}")).json() == p


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"nome": "  "}, "nome", "Dê um nome"),
    ({"categoria": "rodas"}, "categoria", "Escolha a categoria"),
    ({"orcamento": "10.001"}, "orcamento", "duas casas"),
    ({"orcamento": "-1.00"}, "orcamento", "negativo"),
    ({"status": "concluido"}, "status", "planejado ou em andamento"),
])
def test_validacao_do_projeto(banco, paula, civic, alteracao, campo, trecho):
    resposta = paula.post(caminho(civic["id"]), json=dados_projeto(**alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM projeto") == 0


# ================================================================ orçamento

def test_gastos_somam_e_mostram_percentual_e_restante(paula, civic, hoje):
    p = criar_projeto(paula, civic["id"], status="em_andamento")
    gastar(paula, civic["id"], p["id"], "Jogo de rodas aro 17", "3400.00", hoje - timedelta(days=2))
    d = gastar(paula, civic["id"], p["id"], "Parafusos antifurto", "400.00", hoje)
    # 3.800 de 4.500: 84,4% -> 84%; restam 700.
    assert (d["gasto"], d["percentual"], d["diferenca"], d["quantidade_itens"]) == ("3800.00", 84, "700.00", 2)
    assert [i["descricao"] for i in d["itens"]] == ["Jogo de rodas aro 17", "Parafusos antifurto"]


@pytest.mark.parametrize("orcamento, gasto, percentual, diferenca", [
    (None, "300.00", None, None),          # sem orçamento: sem percentual e sem diferença
    ("0.00", "300.00", None, "-300.00"),   # orçamento zero: sem divisão por zero; tudo excedido
    ("500.00", "450.00", 90, "50.00"),     # R$ 50,00 abaixo
    ("500.00", "650.00", 130, "-150.00"),  # excedido
])
def test_orcamento_ausente_zero_e_excedido(paula, civic, hoje, orcamento, gasto, percentual, diferenca):
    p = criar_projeto(paula, civic["id"], orcamento=orcamento)
    d = gastar(paula, civic["id"], p["id"], "Gasto", gasto, hoje)
    assert (d["percentual"], d["diferenca"]) == (percentual, diferenca)


def test_editar_e_apagar_gasto_atualizam_os_totais_e_as_financas(paula, civic, hoje):
    p = criar_projeto(paula, civic["id"])
    item = gastar(paula, civic["id"], p["id"], "Película", "450.00", hoje)["itens"][0]
    url = caminho(civic["id"], f"/{p['id']}/itens/{item['id']}")
    editado = paula.put(url, json={"descricao": "Película G5", "valor": "500.00", "data": str(hoje)})
    assert editado.json()["gasto"] == "500.00"
    financas = paula.get(f"/api/veiculos/{civic['id']}/financas/lancamentos",
                         params={"ano": hoje.year, "mes": hoje.month}).json()["itens"]
    assert [(l["tipo"], l["valor"], l["projeto_id"], l["descricao"]) for l in financas] == [
        ("projeto", "500.00", p["id"], "Rodas de liga leve: Película G5")]
    assert paula.delete(url).json()["gasto"] == "0.00"
    assert paula.get(f"/api/veiculos/{civic['id']}/financas/resumo",
                     params={"ano": hoje.year, "mes": hoje.month}).json()["total"] == "0.00"


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"descricao": " "}, "descricao", "Informe o que foi"),
    ({"valor": "0.00"}, "valor", "maior que zero"),
    ({"valor": None}, "valor", "Informe o valor"),
])
def test_validacao_do_gasto(banco, paula, civic, hoje, alteracao, campo, trecho):
    p = criar_projeto(paula, civic["id"])
    resposta = paula.post(caminho(civic["id"], f"/{p['id']}/itens"),
                          json={"descricao": "Rodas", "valor": "10.00", "data": str(hoje), **alteracao})
    assert resposta.status_code == 422 and trecho in resposta.json()["campos"][campo]
    futuro = paula.post(caminho(civic["id"], f"/{p['id']}/itens"),
                        json={"descricao": "Rodas", "valor": "10.00", "data": str(hoje + timedelta(days=1))})
    assert "futuro" in futuro.json()["campos"]["data"]
    assert valor_sql(banco, "SELECT count(*) FROM projeto_item") == 0


# ============================================================== situações

def test_iniciar_concluir_reabrir_e_concluir_de_novo(paula, civic, hoje):
    p = criar_projeto(paula, civic["id"])
    url = caminho(civic["id"], f"/{p['id']}")
    assert paula.post(f"{url}/iniciar").json()["status"] == "em_andamento"
    assert paula.post(f"{url}/iniciar").status_code == 409
    ontem = str(hoje - timedelta(days=1))
    concluido = paula.post(f"{url}/concluir", json={"data_conclusao": ontem}).json()
    assert (concluido["status"], concluido["data_conclusao"]) == ("concluido", ontem)
    assert paula.post(f"{url}/concluir", json={}).status_code == 409
    reaberto = paula.post(f"{url}/reabrir").json()
    assert (reaberto["status"], reaberto["data_conclusao"]) == ("em_andamento", None)
    de_novo = paula.post(f"{url}/concluir", json={}).json()   # padrão: hoje
    assert (de_novo["status"], de_novo["data_conclusao"]) == ("concluido", str(hoje))
    assert paula.post(f"{url}/reabrir").status_code == 200
    futuro = paula.post(f"{url}/concluir", json={"data_conclusao": str(hoje + timedelta(days=1))})
    assert futuro.status_code == 422


def test_concluido_e_cancelado_nao_aceitam_gastos_ate_reabrir(paula, civic, hoje):
    p = criar_projeto(paula, civic["id"], status="em_andamento")
    item = gastar(paula, civic["id"], p["id"], "Rodas", "3400.00", hoje)["itens"][0]
    url = caminho(civic["id"], f"/{p['id']}")
    paula.post(f"{url}/concluir", json={})
    for resposta in (
        paula.post(f"{url}/itens", json={"descricao": "x", "valor": "1.00", "data": str(hoje)}),
        paula.put(f"{url}/itens/{item['id']}", json={"descricao": "x", "valor": "1.00", "data": str(hoje)}),
        paula.delete(f"{url}/itens/{item['id']}"),
    ):
        assert resposta.status_code == 409 and "Reabra o projeto" in resposta.json()["mensagem"]
    paula.post(f"{url}/reabrir")
    assert gastar(paula, civic["id"], p["id"], "Calibragem", "50.00", hoje)["gasto"] == "3450.00"


def test_cancelar_mantem_os_gastos_nas_despesas(paula, civic, hoje):
    p = criar_projeto(paula, civic["id"])
    gastar(paula, civic["id"], p["id"], "Sinal", "500.00", hoje)
    cancelado = paula.post(caminho(civic["id"], f"/{p['id']}/cancelar")).json()
    assert (cancelado["status"], cancelado["gasto"]) == ("cancelado", "500.00")
    total = paula.get(f"/api/veiculos/{civic['id']}/financas/resumo",
                      params={"ano": hoje.year, "mes": hoje.month}).json()["total"]
    assert total == "500.00"


def test_lista_filtra_conta_e_ordena(paula, civic, hoje):
    planejado = criar_projeto(paula, civic["id"], nome="Câmera de ré", categoria="interior")
    andamento = criar_projeto(paula, civic["id"], nome="Rodas", status="em_andamento")
    concluido = criar_projeto(paula, civic["id"], nome="Insulfilm", status="em_andamento")
    paula.post(caminho(civic["id"], f"/{concluido['id']}/concluir"), json={})
    todos = paula.get(caminho(civic["id"])).json()
    assert [p["id"] for p in todos["itens"]] == [andamento["id"], planejado["id"], concluido["id"]]
    assert todos["por_status"] == {"planejado": 1, "em_andamento": 1, "concluido": 1, "cancelado": 0}
    so = paula.get(caminho(civic["id"]), params={"filtro": "concluido"}).json()
    assert [p["nome"] for p in so["itens"]] == ["Insulfilm"] and so["total"] == 1
    assert paula.get(caminho(civic["id"]), params={"filtro": "x"}).status_code == 422


# =================================================================== fotos

def test_fotos_de_antes_e_depois_varias_e_a_primeira_no_cartao(banco, paula, civic, hoje, pasta_fotos):
    p = criar_projeto(paula, civic["id"], status="em_andamento")
    a1 = enviar_foto(paula, civic["id"], projeto_id=p["id"], momento="antes",
                     data_foto=str(hoje - timedelta(days=10))).json()
    enviar_foto(paula, civic["id"], projeto_id=p["id"], momento="antes", data_foto=str(hoje))
    # "Depois" pode ser enviada antes de concluir (decisão da Paula).
    d1 = enviar_foto(paula, civic["id"], projeto_id=p["id"], momento="depois")
    assert d1.status_code == 201, d1.text
    enviar_foto(paula, civic["id"], projeto_id=p["id"])  # do projeto, sem momento
    detalhe = paula.get(caminho(civic["id"], f"/{p['id']}")).json()
    assert (detalhe["foto_antes_id"], detalhe["foto_depois_id"], len(detalhe["fotos_antes"]),
            detalhe["total_fotos"]) == (a1["id"], d1.json()["id"], 2, 4)
    [resumo] = paula.get(caminho(civic["id"])).json()["itens"]
    assert (resumo["foto_antes_id"], resumo["foto_depois_id"]) == (a1["id"], d1.json()["id"])
    galeria = paula.get(f"/api/veiculos/{civic['id']}/fotos", params={"vinculo": "projeto"}).json()
    assert galeria["total"] == 4
    so_depois = paula.get(f"/api/veiculos/{civic['id']}/fotos",
                          params={"projeto_id": p["id"], "momento": "depois"}).json()
    assert so_depois["total"] == 1
    # Apagar o projeto apaga as fotos dele (linhas e arquivos).
    assert len(arquivos_na_pasta(pasta_fotos)) == 4
    assert paula.delete(caminho(civic["id"], f"/{p['id']}")).status_code == 204
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0
    assert arquivos_na_pasta(pasta_fotos) == []


def test_antes_e_depois_exigem_projeto_e_do_mesmo_veiculo(banco, paula, civic):
    p = criar_projeto(paula, civic["id"])
    sem_projeto = enviar_foto(paula, civic["id"], momento="antes")
    assert sem_projeto.status_code == 422 and "precisam estar ligadas a um projeto" in sem_projeto.json()["campos"]["momento"]
    invalido = enviar_foto(paula, civic["id"], projeto_id=p["id"], momento="durante")
    assert invalido.status_code == 422
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    outro = enviar_foto(paula, moto["id"], projeto_id=p["id"], momento="antes")
    assert outro.status_code == 422 and "não encontrado neste veículo" in outro.json()["campos"]["projeto_id"]
    dois = enviar_foto(paula, civic["id"], projeto_id=p["id"], diagnostico_id=1)
    assert dois.status_code == 422 and "um só registro" in dois.json()["campos"]["projeto_id"]
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0


def test_reabrir_mantem_as_fotos_de_depois(paula, civic):
    p = criar_projeto(paula, civic["id"], status="em_andamento")
    enviar_foto(paula, civic["id"], projeto_id=p["id"], momento="depois")
    paula.post(caminho(civic["id"], f"/{p['id']}/concluir"), json={})
    reaberto = paula.post(caminho(civic["id"], f"/{p['id']}/reabrir")).json()
    assert len(reaberto["fotos_depois"]) == 1


# ======================================================= permissões e isolamento

def test_outro_usuario_nao_ve_nem_altera(banco, paula, rafael, civic, hoje):
    p = criar_projeto(paula, civic["id"])
    item = gastar(paula, civic["id"], p["id"], "Rodas", "100.00", hoje)["itens"][0]
    url = caminho(civic["id"], f"/{p['id']}")
    for resposta in (
        rafael.get(caminho(civic["id"])), rafael.get(url), rafael.put(url, json=dados_projeto()),
        rafael.delete(url), rafael.post(f"{url}/concluir", json={}),
        rafael.post(f"{url}/itens", json={"descricao": "x", "valor": "1.00", "data": str(hoje)}),
        rafael.delete(f"{url}/itens/{item['id']}"),
        rafael.post(caminho(civic["id"]), json=dados_projeto()),
    ):
        assert resposta.status_code == 404, resposta.request.url
    carro = criar_veiculo(rafael)
    assert rafael.get(caminho(carro["id"], f"/{p['id']}")).status_code == 404
    foto = enviar_foto(rafael, carro["id"], projeto_id=p["id"], momento="antes")
    assert foto.status_code == 422
    assert (valor_sql(banco, "SELECT count(*) FROM projeto"),
            valor_sql(banco, "SELECT count(*) FROM projeto_item")) == (1, 1)


def test_gasto_de_outro_projeto_nao_e_alterado_por_este(paula, civic, hoje):
    um = criar_projeto(paula, civic["id"])
    outro = criar_projeto(paula, civic["id"], nome="Som")
    item = gastar(paula, civic["id"], um["id"], "Rodas", "100.00", hoje)["itens"][0]
    resposta = paula.delete(caminho(civic["id"], f"/{outro['id']}/itens/{item['id']}"))
    assert resposta.status_code == 404
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    assert paula.get(caminho(moto["id"], f"/{um['id']}")).status_code == 404


def test_admin_ve_e_veiculo_inativo_e_so_leitura(admin, paula, civic, hoje):
    p = criar_projeto(paula, civic["id"])
    assert admin.get(caminho(civic["id"], f"/{p['id']}")).status_code == 200
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    url = caminho(civic["id"], f"/{p['id']}")
    assert paula.get(url).status_code == 200
    for resposta in (paula.post(caminho(civic["id"]), json=dados_projeto()), paula.put(url, json=dados_projeto()),
                     paula.post(f"{url}/iniciar"), paula.delete(url),
                     paula.post(f"{url}/itens", json={"descricao": "x", "valor": "1.00", "data": str(hoje)})):
        assert resposta.status_code == 409 and "inativo" in resposta.json()["mensagem"]
