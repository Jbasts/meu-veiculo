"""Peças e mão de obra da manutenção, de ponta a ponta (API + PostgreSQL de teste)."""

from datetime import date, timedelta

import pytest

from tests.auth_utils import valor_sql
from tests.test_manutencoes_api import civic, criar_manutencao, dados_manutencao, hoje  # noqa: F401
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    pasta_fotos,
    paula,
    rafael,
)


def peca(nome: str, valor: str) -> dict:
    return {"tipo": "peca", "nome": nome, "valor": valor}


def mao_de_obra(nome: str, valor: str) -> dict:
    return {"tipo": "mao_de_obra", "nome": nome, "valor": valor}


ITENS_DO_EXEMPLO = [
    peca("Filtro de óleo", "70.00"),
    peca("Filtro de ar", "45.00"),
    mao_de_obra("Troca do filtro de óleo", "20.00"),
    mao_de_obra("Troca do filtro de ar", "30.00"),
]


def com_itens(hoje: date, itens: list[dict], **alteracoes) -> dict:
    return dados_manutencao(hoje, valor=None, itens=itens, **alteracoes)


def caminho(veiculo_id: int, manutencao_id: int | None = None) -> str:
    base = f"/api/veiculos/{veiculo_id}/manutencoes"
    return base if manutencao_id is None else f"{base}/{manutencao_id}"


def editar(cliente, veiculo_id: int, manutencao_id: int, dados: dict) -> dict:
    resposta = cliente.put(caminho(veiculo_id, manutencao_id), json=dados)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def itens_resumidos(detalhe: dict) -> list[tuple]:
    return [(i["tipo"], i["nome"], i["valor"]) for i in detalhe["itens"]]


def itens_no_banco(banco) -> int:
    return valor_sql(banco, "SELECT count(*) FROM manutencao_item")


# =========================================================== criação e totais

def test_varias_pecas_e_maos_de_obra_com_subtotais_e_total(banco, paula, civic, hoje):
    criada = paula.post(caminho(civic["id"]), json=com_itens(hoje, ITENS_DO_EXEMPLO))
    assert criada.status_code == 201, criada.text
    detalhe = criada.json()
    assert (detalhe["total_pecas"], detalhe["total_mao_de_obra"], detalhe["valor"]) == (
        "115.00", "50.00", "165.00")
    # Na ordem em que foram informados.
    assert itens_resumidos(detalhe) == [
        ("peca", "Filtro de óleo", "70.00"), ("peca", "Filtro de ar", "45.00"),
        ("mao_de_obra", "Troca do filtro de óleo", "20.00"),
        ("mao_de_obra", "Troca do filtro de ar", "30.00"),
    ]
    # O total gravado é o que as despesas e o histórico usam.
    assert str(valor_sql(banco, "SELECT valor FROM manutencao")) == "165.00"
    lista = paula.get(caminho(civic["id"])).json()["itens"]
    assert lista[0]["valor"] == "165.00"
    assert paula.get(caminho(civic["id"], detalhe["id"])).json() == detalhe


def test_centavos_somados_com_exatidao(paula, civic, hoje):
    detalhe = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=[
        peca("Arruela", "0.10"), peca("Anel", "0.20"), mao_de_obra("Aperto", "0.05"),
        peca("Junta", "33.33"),
    ])
    # Com float, 0,10 + 0,20 daria 0,30000000000000004.
    assert (detalhe["total_pecas"], detalhe["total_mao_de_obra"], detalhe["valor"]) == (
        "33.63", "0.05", "33.68")


def test_so_pecas_tem_mao_de_obra_zero_e_nao_desconhecida(paula, civic, hoje):
    detalhe = criar_manutencao(paula, civic["id"], hoje, valor=None,
                               itens=[peca("Palheta", "59.90")])
    assert (detalhe["total_pecas"], detalhe["total_mao_de_obra"], detalhe["valor"]) == (
        "59.90", "0.00", "59.90")


def test_sem_itens_o_valor_manual_vale_e_nao_ha_subtotais(banco, paula, civic, hoje):
    detalhe = criar_manutencao(paula, civic["id"], hoje, valor="50.00", descricao="Lavagem do motor")
    assert detalhe["valor"] == "50.00" and detalhe["itens"] == []
    # Desconhecido não é zero: sem detalhamento, os subtotais não existem.
    assert detalhe["total_pecas"] is None and detalhe["total_mao_de_obra"] is None
    assert itens_no_banco(banco) == 0


def test_tela_nao_consegue_informar_um_total_diferente_quando_ha_itens(banco, paula, civic, hoje):
    for total in ("999.00", "165.00", "0.00"):  # nem diferente, nem igual: o total não vem da tela
        resposta = paula.post(caminho(civic["id"]),
                              json=dados_manutencao(hoje, valor=total, itens=ITENS_DO_EXEMPLO))
        assert resposta.status_code == 422, resposta.text
        assert "calculado automaticamente" in resposta.json()["campos"]["valor"]
    assert valor_sql(banco, "SELECT count(*) FROM manutencao") == 0
    assert itens_no_banco(banco) == 0

    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    resposta = paula.put(caminho(civic["id"], feita["id"]),
                         json=dados_manutencao(hoje, valor="1.00", itens=ITENS_DO_EXEMPLO))
    assert resposta.status_code == 422
    assert str(valor_sql(banco, "SELECT valor FROM manutencao")) == "165.00"


@pytest.mark.parametrize("item, campo, trecho", [
    ({"tipo": "acessorio", "nome": "Tapete", "valor": "10.00"}, "itens.0.tipo", "Tipo de item"),
    (peca("   ", "10.00"), "itens.0.nome", "Peça: informe o nome"),
    (mao_de_obra("", "10.00"), "itens.0.nome", "Mão de obra: informe o nome"),
    ({"tipo": "peca", "nome": "Filtro"}, "itens.0.valor", 'Peça "Filtro": informe o valor'),
    (peca("Filtro", "-1.00"), "itens.0.valor", "não pode ser negativo"),
    (peca("Filtro", "10.999"), "itens.0.valor", "duas casas decimais"),
    ({"tipo": "peca", "nome": "Filtro", "valor": 10.5}, "itens.0.valor", "Valor inválido"),
    ({**peca("Filtro", "1.00"), "id": 7}, "itens.0.id", "Campo não permitido"),
])
def test_validacao_de_cada_item(banco, paula, civic, hoje, item, campo, trecho):
    resposta = paula.post(caminho(civic["id"]), json=com_itens(hoje, [item]))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM manutencao") == 0


def test_limite_de_itens_por_manutencao(banco, paula, civic, hoje):
    muitos = [peca(f"Peça {n}", "1.00") for n in range(51)]
    resposta = paula.post(caminho(civic["id"]), json=com_itens(hoje, muitos))
    assert resposta.status_code == 422
    assert "No máximo 50 itens" in resposta.json()["campos"]["itens"]
    assert itens_no_banco(banco) == 0


# ====================================================================== edição

def test_editar_troca_a_lista_inteira_e_recalcula(banco, paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    novos = [peca("Filtro de óleo", "72.50"), mao_de_obra("Troca do filtro de óleo", "20.00"),
             peca("Óleo 5W30 (4 L)", "180.00")]
    detalhe = editar(paula, civic["id"], feita["id"], com_itens(hoje, novos))
    assert itens_resumidos(detalhe) == [(i["tipo"], i["nome"], i["valor"]) for i in novos]
    assert (detalhe["total_pecas"], detalhe["total_mao_de_obra"], detalhe["valor"]) == (
        "252.50", "20.00", "272.50")
    assert itens_no_banco(banco) == 3


def test_remover_um_item(banco, paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    sem_filtro_de_ar = [i for i in ITENS_DO_EXEMPLO if "ar" not in i["nome"].split()]
    detalhe = editar(paula, civic["id"], feita["id"], com_itens(hoje, sem_filtro_de_ar))
    assert [i["nome"] for i in detalhe["itens"]] == ["Filtro de óleo", "Troca do filtro de óleo"]
    assert (detalhe["total_pecas"], detalhe["total_mao_de_obra"], detalhe["valor"]) == (
        "70.00", "20.00", "90.00")
    assert itens_no_banco(banco) == 2


def test_remover_todos_os_itens_volta_ao_valor_manual(banco, paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    detalhe = editar(paula, civic["id"], feita["id"], dados_manutencao(hoje, valor="100.00", itens=[]))
    assert detalhe["valor"] == "100.00" and detalhe["itens"] == []
    assert detalhe["total_pecas"] is None and detalhe["total_mao_de_obra"] is None
    assert itens_no_banco(banco) == 0


def test_detalhar_uma_manutencao_antiga_que_so_tinha_o_total(paula, civic, hoje):
    antiga = criar_manutencao(paula, civic["id"], hoje, valor="350.00")
    detalhe = editar(paula, civic["id"], antiga["id"], com_itens(hoje, [peca("Pastilhas", "210.00"),
                                                                        mao_de_obra("Troca", "90.00")]))
    assert detalhe["valor"] == "300.00"  # o total passa a ser a soma do que foi detalhado


def test_editar_so_os_itens_nao_recria_a_leitura_do_hodometro_a_cada_item(banco, paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, quilometragem=85200,
                             itens=ITENS_DO_EXEMPLO)
    editar(paula, civic["id"], feita["id"],
           com_itens(hoje, ITENS_DO_EXEMPLO + [peca("Anel", "3.00")], quilometragem=85200))
    # Uma única leitura da manutenção, com a quilometragem dela.
    assert valor_sql(banco, "SELECT count(*) FROM leitura_km WHERE origem = 'manutencao'") == 1
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["quilometragem"] == 85200


# ================================================================== agendadas

def test_agendada_com_itens_e_ao_concluir_os_valores_continuam(paula, civic, hoje):
    dia = str(hoje + timedelta(days=10))
    agendada = criar_manutencao(paula, civic["id"], hoje, status="agendada", data=dia,
                                quilometragem=None, valor=None, itens=ITENS_DO_EXEMPLO)
    assert agendada["status"] == "agendada"
    assert (agendada["total_pecas"], agendada["total_mao_de_obra"], agendada["valor"]) == (
        "115.00", "50.00", "165.00")

    concluida = editar(paula, civic["id"], agendada["id"],
                       com_itens(hoje, ITENS_DO_EXEMPLO, status="realizada", data=str(hoje)))
    assert concluida["status"] == "realizada"
    assert itens_resumidos(concluida) == itens_resumidos(agendada)
    assert concluida["valor"] == "165.00"


# ============================================================ acesso e exclusão

def test_outro_usuario_nao_ve_nem_altera_os_itens(banco, paula, rafael, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    for resposta in (
        rafael.get(caminho(civic["id"], feita["id"])),
        rafael.put(caminho(civic["id"], feita["id"]), json=com_itens(hoje, [peca("Nada", "0.01")])),
        rafael.delete(caminho(civic["id"], feita["id"])),
    ):
        assert resposta.status_code == 404
        assert "itens" not in resposta.json()
    assert itens_no_banco(banco) == 4
    assert str(valor_sql(banco, "SELECT valor FROM manutencao")) == "165.00"


def test_itens_nao_passam_de_um_veiculo_para_outro_do_mesmo_dono(banco, paula, admin, civic, hoje):
    argo = criar_veiculo(paula, placa="BRA2E19", quilometragem=40000)
    do_argo = criar_manutencao(paula, argo["id"], hoje, quilometragem=40000, valor=None,
                               itens=[peca("Correia", "150.00")])
    for cliente in (paula, admin):
        resposta = cliente.put(caminho(civic["id"], do_argo["id"]),
                               json=com_itens(hoje, ITENS_DO_EXEMPLO))
        assert resposta.status_code == 404
        assert cliente.get(caminho(civic["id"], do_argo["id"])).status_code == 404
    assert itens_resumidos(paula.get(caminho(argo["id"], do_argo["id"])).json()) == [
        ("peca", "Correia", "150.00")]


def test_admin_ve_e_edita_os_itens_de_outro_usuario(paula, admin, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    assert admin.get(caminho(civic["id"], feita["id"])).json()["valor"] == "165.00"
    detalhe = editar(admin, civic["id"], feita["id"], com_itens(hoje, [peca("Filtro", "10.00")]))
    assert detalhe["valor"] == "10.00"


def test_apagar_a_manutencao_apaga_os_itens(banco, paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    outra = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=[peca("Lâmpada", "12.00")])
    assert paula.delete(caminho(civic["id"], feita["id"])).status_code == 204
    assert valor_sql(banco, "SELECT count(*) FROM manutencao_item WHERE manutencao_id = :m",
                     m=feita["id"]) == 0
    assert itens_resumidos(paula.get(caminho(civic["id"], outra["id"])).json()) == [
        ("peca", "Lâmpada", "12.00")]


def test_veiculo_inativo_mostra_os_itens_mas_nao_aceita_alteracao(paula, civic, hoje):
    feita = criar_manutencao(paula, civic["id"], hoje, valor=None, itens=ITENS_DO_EXEMPLO)
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    assert paula.get(caminho(civic["id"], feita["id"])).json()["total_pecas"] == "115.00"
    resposta = paula.put(caminho(civic["id"], feita["id"]), json=com_itens(hoje, []))
    assert resposta.status_code == 409 and "inativo" in resposta.json()["mensagem"]
