"""Planos, manutenções e pendências de ponta a ponta (API + PostgreSQL de teste)."""

from datetime import date, timedelta

import pytest

from tests.auth_utils import executar_sql, valor_sql
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    enviar_foto,
    imagens_no_banco,
    pasta_fotos,
    paula,
    rafael,
)


@pytest.fixture
def hoje(banco) -> date:
    return valor_sql(banco, "SELECT current_date")


@pytest.fixture
def civic(paula) -> dict:
    return criar_veiculo(paula)  # 85.000 km


def um_ano_antes(dia: date) -> date:
    try:
        return dia.replace(year=dia.year - 1)
    except ValueError:  # 29 de fevereiro
        return dia.replace(year=dia.year - 1, day=28)


def dados_plano(**alteracoes) -> dict:
    return {"nome": "Troca de óleo", "sistema": "motor", "intervalo_km": 10000,
            "intervalo_meses": None, "data_base": None, "km_base": 80000, **alteracoes}


def dados_manutencao(hoje: date, **alteracoes) -> dict:
    return {"descricao": "Troca de óleo", "sistema": "motor", "status": "realizada",
            "data": str(hoje), "quilometragem": 85000, "valor": "350.00", "oficina": None,
            "plano_id": None, "garantia_ate": None, "garantia_km": None, "proxima_data": None,
            "proxima_km": None, "observacao": None, **alteracoes}


def criar_plano(cliente, veiculo_id: int, **alteracoes) -> dict:
    resposta = cliente.post(f"/api/veiculos/{veiculo_id}/planos", json=dados_plano(**alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def criar_manutencao(cliente, veiculo_id: int, hoje: date, **alteracoes) -> dict:
    resposta = cliente.post(f"/api/veiculos/{veiculo_id}/manutencoes",
                            json=dados_manutencao(hoje, **alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def pendentes(cliente, veiculo_id: int) -> list[dict]:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/manutencoes/pendentes")
    assert resposta.status_code == 200, resposta.text
    return resposta.json()["itens"]


def plano(cliente, veiculo_id: int, plano_id: int) -> dict:
    return cliente.get(f"/api/veiculos/{veiculo_id}/planos/{plano_id}").json()


def km_do_veiculo(cliente, veiculo_id: int) -> int:
    return cliente.get(f"/api/veiculos/{veiculo_id}").json()["quilometragem"]


# ======================================================================= planos

def test_plano_sem_manutencao_anterior_conta_a_partir_da_base(paula, civic, hoje):
    base = um_ano_antes(hoje) + timedelta(days=100)
    criado = criar_plano(paula, civic["id"], nome=" Revisão  geral ", sistema="outros",
                         intervalo_km=10000, intervalo_meses=12, km_base=80000, data_base=str(base))
    assert criado["nome"] == "Revisão geral" and criado["ativo"] is True
    assert (criado["referencia_km"], criado["proxima_km"], criado["km_restantes"]) == (80000, 90000, 5000)
    assert criado["referencia_data"] == str(base)
    assert criado["dias_restantes"] == 100 and criado["situacao"] == "em_dia"
    # O prazo é o mesmo em qualquer consulta: vem da base gravada, não de "hoje".
    assert plano(paula, civic["id"], criado["id"])["proxima_data"] == criado["proxima_data"]


@pytest.mark.parametrize("km_base, situacao, km_restantes", [
    (75000, "atrasada", 0),      # próxima aos 85.000: atingiu
    (74000, "atrasada", -1000),
    (75001, "proxima", 1),
    (76000, "proxima", 1000),    # limite da faixa
    (76001, "em_dia", 1001),
])
def test_faixas_por_quilometragem(paula, civic, km_base, situacao, km_restantes):
    criado = criar_plano(paula, civic["id"], km_base=km_base)
    assert (criado["situacao"], criado["km_restantes"]) == (situacao, km_restantes)


@pytest.mark.parametrize("dias, situacao", [
    (-23, "atrasada"), (0, "atrasada"), (1, "proxima"), (30, "proxima"), (31, "em_dia"),
])
def test_faixas_por_tempo(paula, civic, hoje, dias, situacao):
    base = um_ano_antes(hoje + timedelta(days=dias))
    criado = criar_plano(paula, civic["id"], intervalo_km=None, km_base=None, intervalo_meses=12,
                         data_base=str(base))
    assert (criado["dias_restantes"], criado["situacao"]) == (dias, situacao)
    assert criado["proxima_km"] is None and criado["km_restantes"] is None


def test_com_km_e_tempo_vale_o_limite_atingido_primeiro(paula, civic, hoje):
    longe = str(um_ano_antes(hoje + timedelta(days=200)))
    vencida = str(um_ano_antes(hoje - timedelta(days=5)))
    por_km = criar_plano(paula, civic["id"], nome="A", intervalo_meses=12, data_base=longe,
                         km_base=75000)  # km atingido, data longe
    por_data = criar_plano(paula, civic["id"], nome="B", intervalo_meses=12, data_base=vencida,
                           km_base=84000)  # data vencida, km longe
    perto_km = criar_plano(paula, civic["id"], nome="C", intervalo_meses=12, data_base=longe,
                           km_base=75500)  # faltam 500 km, 200 dias
    assert [p["situacao"] for p in (por_km, por_data, perto_km)] == ["atrasada", "atrasada", "proxima"]


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"nome": " "}, "nome", "Informe o nome"),
    ({"sistema": "asas"}, "sistema", "Escolha o sistema"),
    ({"intervalo_km": None, "km_base": None}, "intervalo_km", "em quilômetros, em meses ou os dois"),
    ({"intervalo_km": 0}, "intervalo_km", "entre 1 e"),
    ({"intervalo_meses": 601, "data_base": "2026-01-01"}, "intervalo_meses", "entre 1 e 600"),
    ({"km_base": None}, "km_base", "Informe a quilometragem da última vez"),
    ({"km_base": 90000}, "km_base", "não pode ser maior que a atual (85.000 km)"),
    ({"intervalo_meses": 12}, "data_base", "Informe a data da última vez"),
    ({"intervalo_meses": 12, "data_base": "2999-01-01"}, "data_base", "não pode ser no futuro"),
    ({"veiculo_id": 1}, "veiculo_id", "Campo não permitido"),
    ({"ativo": False}, "ativo", "Campo não permitido"),
])
def test_validacao_do_plano(banco, paula, civic, alteracao, campo, trecho):
    resposta = paula.post(f"/api/veiculos/{civic['id']}/planos", json=dados_plano(**alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM plano_manutencao") == 0


def test_base_de_intervalo_nao_usado_nao_e_guardada(paula, civic):
    criado = criar_plano(paula, civic["id"], intervalo_km=None, intervalo_meses=6,
                         data_base="2026-01-10", km_base=80000)
    assert (criado["km_base"], criado["data_base"]) == (None, "2026-01-10")


def test_plano_antigo_sem_base_aparece_como_dados_insuficientes(banco, paula, civic):
    criado = criar_plano(paula, civic["id"])
    executar_sql(banco, "UPDATE plano_manutencao SET km_base = NULL")  # como um plano antigo
    atual = plano(paula, civic["id"], criado["id"])
    assert atual["situacao"] == "sem_base"
    assert (atual["proxima_km"], atual["km_restantes"]) == (None, None)  # desconhecido, não zero
    [item] = pendentes(paula, civic["id"])
    assert (item["tipo"], item["situacao"], item["proxima_km"]) == ("plano", "sem_base", None)
    # Informar a base resolve.
    resposta = paula.put(f"/api/veiculos/{civic['id']}/planos/{criado['id']}",
                         json=dados_plano(km_base=84000))
    assert resposta.json()["situacao"] == "em_dia"


def test_editar_desativar_reativar_e_apagar_plano(banco, paula, civic, hoje):
    criado = criar_plano(paula, civic["id"])
    base = f"/api/veiculos/{civic['id']}/planos/{criado['id']}"
    manutencao = criar_manutencao(paula, civic["id"], hoje, plano_id=criado["id"])

    editado = paula.put(base, json=dados_plano(nome="Óleo e filtro", intervalo_km=5000)).json()
    assert editado["nome"] == "Óleo e filtro" and editado["proxima_km"] == 90000  # 85.000 + 5.000

    inativo = paula.post(f"{base}/desativar").json()
    assert inativo["ativo"] is False and inativo["situacao"] is None
    assert pendentes(paula, civic["id"]) == []
    assert paula.post(f"{base}/ativar").json()["situacao"] == "em_dia"

    assert paula.delete(base).status_code == 204
    assert paula.get(base).status_code == 404
    # A manutenção do plano apagado continua no histórico, como avulsa.
    ficou = paula.get(f"/api/veiculos/{civic['id']}/manutencoes/{manutencao['id']}").json()
    assert ficou["plano_id"] is None and ficou["plano_nome"] is None
    assert ficou["descricao"] == "Troca de óleo"


def test_lista_de_planos_ativos_primeiro(paula, civic):
    criar_plano(paula, civic["id"], nome="Velas")
    inativo = criar_plano(paula, civic["id"], nome="Alinhamento")
    paula.post(f"/api/veiculos/{civic['id']}/planos/{inativo['id']}/desativar")
    criar_plano(paula, civic["id"], nome="correia dentada")
    lista = paula.get(f"/api/veiculos/{civic['id']}/planos").json()
    assert [(p["nome"], p["ativo"]) for p in lista] == [
        ("correia dentada", True), ("Velas", True), ("Alinhamento", False)]


# ================================================================== manutenções

def test_manutencao_realizada_com_dinheiro_exato_e_detalhe(banco, paula, civic, hoje):
    criada = criar_manutencao(paula, civic["id"], hoje, descricao="  Troca das bieletas ",
                              sistema="suspensao", valor="280.10", oficina="Oficina do Zé",
                              observacao="  Peças originais.\nRevisar em 6 meses.  ")
    assert criada["descricao"] == "Troca das bieletas" and criada["valor"] == "280.10"
    assert criada["observacao"] == "Peças originais.\nRevisar em 6 meses."
    assert criada["status"] == "realizada" and criada["plano_nome"] is None
    assert criada["garantia_situacao"] == "sem_informacao" and criada["total_fotos"] == 0
    assert str(valor_sql(banco, "SELECT valor FROM manutencao")) == "280.10"
    sem_valor = criar_manutencao(paula, civic["id"], hoje, valor=None)
    assert sem_valor["valor"] == "0.00"


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"descricao": ""}, "descricao", "Informe a descrição"),
    ({"sistema": "asas"}, "sistema", "Escolha o sistema"),
    ({"status": "talvez"}, "status", "realizada ou está agendada"),
    ({"data": "2999-01-01"}, "data", "não pode ter data no futuro"),
    ({"quilometragem": -1}, "quilometragem", "não pode ser negativa"),
    ({"valor": "-1.00"}, "valor", "não pode ser negativo"),
    ({"valor": "10.999"}, "valor", "duas casas decimais"),
    ({"valor": 10.5}, "valor", "Valor inválido"),
    ({"plano_id": 99999}, "plano_id", "Plano não encontrado neste veículo"),
    ({"garantia_ate": "2000-01-01"}, "garantia_ate", "não pode terminar antes"),
    ({"garantia_km": 10000}, "garantia_km", "LIMITE da garantia"),
    ({"proxima_data": "2000-01-01"}, "proxima_data", "depois da data da manutenção"),
    ({"proxima_km": 85000}, "proxima_km", "maior que a da manutenção"),
    ({"status": "agendada", "garantia_km": 99000}, "garantia_km", "só é informada em manutenção realizada"),
    ({"status": "agendada", "proxima_km": 99000}, "proxima_km", "só vale para manutenção realizada"),
    ({"veiculo_id": 1}, "veiculo_id", "Campo não permitido"),
])
def test_validacao_da_manutencao(banco, paula, civic, hoje, alteracao, campo, trecho):
    resposta = paula.post(f"/api/veiculos/{civic['id']}/manutencoes",
                          json=dados_manutencao(hoje, **alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM manutencao") == 0


def test_agendada_nao_aumenta_a_quilometragem_e_realizada_aumenta(paula, civic, hoje):
    futura = str(hoje + timedelta(days=10))
    criar_manutencao(paula, civic["id"], hoje, status="agendada", data=futura, quilometragem=90000)
    assert km_do_veiculo(paula, civic["id"]) == 85000
    criar_manutencao(paula, civic["id"], hoje, quilometragem=85600)
    veiculo = paula.get(f"/api/veiculos/{civic['id']}").json()
    assert (veiculo["quilometragem"], veiculo["data_leitura_km"]) == (85600, str(hoje))


def test_manutencao_antiga_nao_reduz_a_quilometragem(paula, civic, hoje):
    criar_manutencao(paula, civic["id"], hoje, data=str(hoje - timedelta(days=300)),
                     quilometragem=70000)
    assert km_do_veiculo(paula, civic["id"]) == 85000


def test_concluir_mudando_so_o_status_atualiza_km_e_plano(paula, civic, hoje):
    """Transição isolada agendada -> realizada: o corpo muda apenas o status."""
    revisao = criar_plano(paula, civic["id"], nome="Revisão", km_base=76000)  # próxima aos 86.000
    dados = dados_manutencao(hoje, status="agendada", plano_id=revisao["id"], quilometragem=85900)
    agendada = paula.post(f"/api/veiculos/{civic['id']}/manutencoes", json=dados).json()
    assert km_do_veiculo(paula, civic["id"]) == 85000
    assert plano(paula, civic["id"], revisao["id"])["referencia_km"] == 76000

    caminho = f"/api/veiculos/{civic['id']}/manutencoes/{agendada['id']}"
    resposta = paula.put(caminho, json={**dados, "status": "realizada"})
    assert resposta.status_code == 200, resposta.text
    assert km_do_veiculo(paula, civic["id"]) == 85900
    atual = plano(paula, civic["id"], revisao["id"])
    assert (atual["referencia_km"], atual["proxima_km"], atual["situacao"]) == (85900, 95900, "em_dia")

    # Reclassificar de volta para agendada desfaz os dois efeitos.
    assert paula.put(caminho, json=dados).status_code == 200
    assert km_do_veiculo(paula, civic["id"]) == 85000
    assert plano(paula, civic["id"], revisao["id"])["referencia_km"] == 76000


def test_editar_quilometragem_errada_da_manutencao_recalcula(paula, civic, hoje):
    criada = criar_manutencao(paula, civic["id"], hoje, quilometragem=856000)  # zero a mais
    assert km_do_veiculo(paula, civic["id"]) == 856000
    caminho = f"/api/veiculos/{civic['id']}/manutencoes/{criada['id']}"
    assert paula.put(caminho, json=dados_manutencao(hoje, quilometragem=85600)).status_code == 200
    assert km_do_veiculo(paula, civic["id"]) == 85600
    assert paula.delete(caminho).status_code == 204
    assert km_do_veiculo(paula, civic["id"]) == 85000
    assert paula.get(caminho).status_code == 404


def test_quilometragem_que_contradiz_o_hodometro_e_recusada(banco, paula, civic, hoje):
    executar_sql(banco, "UPDATE leitura_km SET data_leitura = :d", d=hoje - timedelta(days=5))
    resposta = paula.post(f"/api/veiculos/{civic['id']}/manutencoes",
                          json=dados_manutencao(hoje, quilometragem=84000))
    assert resposta.status_code == 422
    assert "não combina com o histórico" in resposta.json()["campos"]["quilometragem"]
    # A mesma quilometragem numa data anterior é coerente e entra como histórico.
    antiga = dados_manutencao(hoje, quilometragem=84000, data=str(hoje - timedelta(days=30)))
    assert paula.post(f"/api/veiculos/{civic['id']}/manutencoes", json=antiga).status_code == 201


def test_manutencao_de_plano_por_km_exige_quilometragem(paula, civic, hoje):
    por_km = criar_plano(paula, civic["id"])
    resposta = paula.post(f"/api/veiculos/{civic['id']}/manutencoes",
                          json=dados_manutencao(hoje, plano_id=por_km["id"], quilometragem=None))
    assert resposta.status_code == 422
    assert "o plano conta o prazo em quilômetros" in resposta.json()["campos"]["quilometragem"]


def test_realizar_manutencao_do_plano_renova_o_prazo(paula, civic, hoje):
    atrasado = criar_plano(paula, civic["id"], km_base=70000, intervalo_meses=12,
                           data_base=str(um_ano_antes(hoje - timedelta(days=23))))
    assert plano(paula, civic["id"], atrasado["id"])["dias_restantes"] == -23
    criada = criar_manutencao(paula, civic["id"], hoje, plano_id=atrasado["id"], quilometragem=85200)
    assert criada["plano_nome"] == "Troca de óleo"
    atual = plano(paula, civic["id"], atrasado["id"])
    assert (atual["situacao"], atual["proxima_km"], atual["referencia_data"]) == (
        "em_dia", 95200, str(hoje))


def test_listagens_por_status_com_ordem_estavel(paula, civic, hoje):
    for dias in (40, 10, 10, 25):
        criar_manutencao(paula, civic["id"], hoje, data=str(hoje - timedelta(days=dias)),
                         quilometragem=None)
    for dias in (20, 5):
        criar_manutencao(paula, civic["id"], hoje, status="agendada",
                         data=str(hoje + timedelta(days=dias)), quilometragem=None)
    base = f"/api/veiculos/{civic['id']}/manutencoes"
    realizadas = [paula.get(base, params={"status": "realizada", "pagina": p, "por_pagina": 3}).json()
                  for p in (1, 2)]
    assert realizadas[0]["total"] == 4
    itens = realizadas[0]["itens"] + realizadas[1]["itens"]
    assert [i["data"] for i in itens] == [str(hoje - timedelta(days=d)) for d in (10, 10, 25, 40)]
    assert itens[0]["id"] > itens[1]["id"] and len({i["id"] for i in itens}) == 4
    agendadas = paula.get(base, params={"status": "agendada"}).json()
    assert [i["data"] for i in agendadas["itens"]] == [str(hoje + timedelta(days=d)) for d in (5, 20)]
    assert paula.get(base).json()["total"] == 6
    assert paula.get(base, params={"status": "outra"}).status_code == 422


# ==================================================================== pendentes

def test_plano_com_manutencao_agendada_gera_um_unico_alerta(paula, civic, hoje):
    revisao = criar_plano(paula, civic["id"], nome="Revisão", km_base=76000)
    marcada = str(hoje + timedelta(days=7))
    agendada = criar_manutencao(paula, civic["id"], hoje, status="agendada", plano_id=revisao["id"],
                                data=marcada, quilometragem=None)
    [item] = pendentes(paula, civic["id"])  # um item, não dois
    assert (item["tipo"], item["plano_id"], item["situacao"]) == ("plano", revisao["id"], "proxima")
    assert (item["agendada_id"], item["agendada_data"]) == (agendada["id"], marcada)

    # Cada plano aceita uma agendada só.
    repetida = paula.post(f"/api/veiculos/{civic['id']}/manutencoes",
                          json=dados_manutencao(hoje, status="agendada", plano_id=revisao["id"],
                                                data=marcada, quilometragem=None))
    assert repetida.status_code == 409
    assert "já tem uma manutenção agendada" in repetida.json()["mensagem"]


def test_agendada_avulsa_atrasa_so_no_dia_seguinte(banco, paula, civic, hoje):
    criada = criar_manutencao(paula, civic["id"], hoje, status="agendada", descricao="Alinhamento",
                              sistema="direcao", quilometragem=None, valor="120.00")
    [item] = pendentes(paula, civic["id"])
    assert (item["tipo"], item["manutencao_id"], item["titulo"]) == ("agendada", criada["id"], "Alinhamento")
    assert (item["situacao"], item["dias_restantes"]) == ("proxima", 0)  # marcada para hoje
    executar_sql(banco, "UPDATE manutencao SET data = current_date - 1")
    assert pendentes(paula, civic["id"])[0]["situacao"] == "atrasada"
    executar_sql(banco, "UPDATE manutencao SET data = current_date + 31")
    assert pendentes(paula, civic["id"])[0]["situacao"] == "em_dia"
    # Concluída, deixa de ser pendência.
    paula.put(f"/api/veiculos/{civic['id']}/manutencoes/{criada['id']}",
              json=dados_manutencao(hoje, descricao="Alinhamento", sistema="direcao",
                                    quilometragem=None))
    assert pendentes(paula, civic["id"]) == []


def test_agendada_de_plano_inativo_continua_aparecendo(paula, civic, hoje):
    revisao = criar_plano(paula, civic["id"])
    criar_manutencao(paula, civic["id"], hoje, status="agendada", plano_id=revisao["id"],
                     data=str(hoje + timedelta(days=3)), quilometragem=None)
    paula.post(f"/api/veiculos/{civic['id']}/planos/{revisao['id']}/desativar")
    [item] = pendentes(paula, civic["id"])
    assert item["tipo"] == "agendada"


def test_lembrete_so_em_manutencao_avulsa_e_sem_duplicar_o_plano(paula, civic, hoje):
    pneus = criar_manutencao(paula, civic["id"], hoje, descricao="Troca de pneus", sistema="pneus",
                             proxima_km=85800, proxima_data=str(hoje + timedelta(days=200)))
    [item] = pendentes(paula, civic["id"])
    assert (item["tipo"], item["manutencao_id"]) == ("lembrete", pneus["id"])
    assert (item["situacao"], item["km_restantes"], item["dias_restantes"]) == ("proxima", 800, 200)

    oleo = criar_plano(paula, civic["id"])
    recusada = paula.post(f"/api/veiculos/{civic['id']}/manutencoes",
                          json=dados_manutencao(hoje, plano_id=oleo["id"], proxima_km=95000))
    assert recusada.status_code == 422
    assert "a próxima é calculada pelo plano" in recusada.json()["campos"]["proxima_km"]
    # Tirar o lembrete pela edição remove a pendência.
    paula.put(f"/api/veiculos/{civic['id']}/manutencoes/{pneus['id']}",
              json=dados_manutencao(hoje, descricao="Troca de pneus", sistema="pneus"))
    assert [i["tipo"] for i in pendentes(paula, civic["id"])] == ["plano"]


def test_pendentes_das_mais_urgentes_para_as_menos(banco, paula, civic, hoje):
    criar_plano(paula, civic["id"], nome="Em dia", km_base=84000)
    criar_plano(paula, civic["id"], nome="Atrasado", km_base=70000)
    criar_plano(paula, civic["id"], nome="Proximo", km_base=75500)
    sem_base = criar_plano(paula, civic["id"], nome="Sem base")
    executar_sql(banco, "UPDATE plano_manutencao SET km_base = NULL WHERE id = :p", p=sem_base["id"])
    criar_manutencao(paula, civic["id"], hoje, status="agendada", descricao="Agendada",
                     data=str(hoje + timedelta(days=2)), quilometragem=None)
    resposta = paula.get(f"/api/veiculos/{civic['id']}/manutencoes/pendentes").json()
    assert resposta["km_atual"] == 85000
    assert [(i["titulo"], i["situacao"]) for i in resposta["itens"]] == [
        ("Atrasado", "atrasada"), ("Agendada", "proxima"), ("Proximo", "proxima"),
        ("Sem base", "sem_base"), ("Em dia", "em_dia")]


def test_veiculo_sem_nada_tem_pendentes_vazio(paula, civic):
    assert pendentes(paula, civic["id"]) == []


# ===================================================================== garantia

def test_garantia_vale_ate_o_limite_atingido_primeiro(banco, paula, civic, hoje):
    em_um_ano = str(hoje + timedelta(days=365))
    criada = criar_manutencao(paula, civic["id"], hoje, garantia_ate=em_um_ano, garantia_km=95000)
    caminho = f"/api/veiculos/{civic['id']}/manutencoes/{criada['id']}"
    assert criada["garantia_situacao"] == "vigente"
    assert "o que vier primeiro" in criada["garantia_explicacao"]
    assert "95.000 km" in criada["garantia_explicacao"]

    # O hodômetro passa do limite antes da data: acabou.
    paula.post(f"/api/veiculos/{civic['id']}/leituras", json={"quilometragem": 95001})
    detalhe = paula.get(caminho).json()
    assert detalhe["garantia_situacao"] == "vencida" and "95.000 km" in detalhe["garantia_explicacao"]

    # Só por data: vale até o último dia, inclusive.
    so_data = criar_manutencao(paula, civic["id"], hoje, quilometragem=None, garantia_ate=str(hoje))
    assert so_data["garantia_situacao"] == "vigente"
    executar_sql(banco, "UPDATE manutencao SET garantia_ate = current_date - 1, data = current_date - 9 "
                        "WHERE id = :m", m=so_data["id"])
    vencida = paula.get(f"/api/veiculos/{civic['id']}/manutencoes/{so_data['id']}").json()
    assert vencida["garantia_situacao"] == "vencida"


def test_falta_de_informacao_nao_e_garantia_confirmada(paula, civic, hoje):
    sem = criar_manutencao(paula, civic["id"], hoje)
    assert (sem["garantia_situacao"], sem["garantia_explicacao"]) == (
        "sem_informacao", "Sem informação de garantia.")
    agendada = criar_manutencao(paula, civic["id"], hoje, status="agendada", quilometragem=None)
    assert agendada["garantia_situacao"] == "nao_se_aplica"


# =================================================================== permissões

def test_outro_usuario_nao_acessa_planos_nem_manutencoes(banco, paula, rafael, civic, hoje):
    oleo = criar_plano(paula, civic["id"])
    feita = criar_manutencao(paula, civic["id"], hoje)
    base = f"/api/veiculos/{civic['id']}"
    for resposta in (
        rafael.get(f"{base}/planos"),
        rafael.get(f"{base}/planos/{oleo['id']}"),
        rafael.post(f"{base}/planos", json=dados_plano()),
        rafael.put(f"{base}/planos/{oleo['id']}", json=dados_plano(nome="Meu")),
        rafael.post(f"{base}/planos/{oleo['id']}/desativar"),
        rafael.delete(f"{base}/planos/{oleo['id']}"),
        rafael.get(f"{base}/manutencoes"),
        rafael.get(f"{base}/manutencoes/pendentes"),
        rafael.get(f"{base}/manutencoes/{feita['id']}"),
        rafael.post(f"{base}/manutencoes", json=dados_manutencao(hoje)),
        rafael.put(f"{base}/manutencoes/{feita['id']}", json=dados_manutencao(hoje, valor="1.00")),
        rafael.delete(f"{base}/manutencoes/{feita['id']}"),
    ):
        assert resposta.status_code == 404, resposta.request.url
        assert resposta.json()["mensagem"] == "Veículo não encontrado."
    assert valor_sql(banco, "SELECT count(*) FROM manutencao") == 1
    assert valor_sql(banco, "SELECT nome FROM plano_manutencao") == "Troca de óleo"


def test_nao_vincula_registros_de_veiculos_diferentes_do_mesmo_dono(banco, paula, admin, civic, hoje):
    argo = criar_veiculo(paula, placa="BRA2E19", quilometragem=40000)
    plano_do_argo = criar_plano(paula, argo["id"], km_base=35000)
    manutencao_do_argo = criar_manutencao(paula, argo["id"], hoje, quilometragem=40000)

    for cliente in (paula, admin):  # o admin também respeita a regra
        # Manutenção do Civic num plano do Argo.
        resposta = cliente.post(f"/api/veiculos/{civic['id']}/manutencoes",
                                json=dados_manutencao(hoje, plano_id=plano_do_argo["id"]))
        assert resposta.status_code == 422
        assert resposta.json()["campos"] == {"plano_id": "Plano não encontrado neste veículo."}
        # Plano e manutenção do Argo acessados pelo endereço do Civic.
        base = f"/api/veiculos/{civic['id']}"
        for outra in (
            cliente.get(f"{base}/planos/{plano_do_argo['id']}"),
            cliente.put(f"{base}/planos/{plano_do_argo['id']}", json=dados_plano()),
            cliente.delete(f"{base}/planos/{plano_do_argo['id']}"),
            cliente.get(f"{base}/manutencoes/{manutencao_do_argo['id']}"),
            cliente.put(f"{base}/manutencoes/{manutencao_do_argo['id']}", json=dados_manutencao(hoje)),
            cliente.delete(f"{base}/manutencoes/{manutencao_do_argo['id']}"),
        ):
            assert outra.status_code == 404
    assert valor_sql(banco, "SELECT count(*) FROM manutencao") == 1
    assert valor_sql(banco, "SELECT count(*) FROM plano_manutencao") == 1


def test_admin_gerencia_manutencoes_de_outro_usuario(paula, admin, civic, hoje):
    oleo = criar_plano(admin, civic["id"])
    feita = criar_manutencao(admin, civic["id"], hoje, plano_id=oleo["id"], quilometragem=85300)
    assert paula.get(f"/api/veiculos/{civic['id']}/manutencoes/{feita['id']}").json()["plano_nome"] == "Troca de óleo"
    assert km_do_veiculo(paula, civic["id"]) == 85300


def test_veiculo_inativo_mostra_o_historico_mas_nao_aceita_alteracoes(paula, civic, hoje):
    oleo = criar_plano(paula, civic["id"])
    feita = criar_manutencao(paula, civic["id"], hoje)
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    base = f"/api/veiculos/{civic['id']}"
    assert paula.get(f"{base}/manutencoes").json()["total"] == 1
    assert len(paula.get(f"{base}/planos").json()) == 1
    for resposta in (
        paula.post(f"{base}/manutencoes", json=dados_manutencao(hoje)),
        paula.put(f"{base}/manutencoes/{feita['id']}", json=dados_manutencao(hoje)),
        paula.delete(f"{base}/manutencoes/{feita['id']}"),
        paula.post(f"{base}/planos", json=dados_plano()),
        paula.delete(f"{base}/planos/{oleo['id']}"),
    ):
        assert resposta.status_code == 409 and "inativo" in resposta.json()["mensagem"]


# ================================================= fotos ligadas a manutenção

def test_foto_ligada_a_manutencao_do_mesmo_veiculo(banco, paula, civic, hoje, pasta_fotos):
    feita = criar_manutencao(paula, civic["id"], hoje)
    avulsa = enviar_foto(paula, civic["id"]).json()
    nota = enviar_foto(paula, civic["id"], legenda="Nota fiscal", manutencao_id=feita["id"]).json()
    assert nota["manutencao_id"] == feita["id"] and avulsa["manutencao_id"] is None

    base = f"/api/veiculos/{civic['id']}"
    detalhe = paula.get(f"{base}/manutencoes/{feita['id']}").json()
    assert detalhe["total_fotos"] == 1

    def ids(**filtro) -> list[int]:
        return [f["id"] for f in paula.get(f"{base}/fotos", params=filtro).json()["itens"]]

    assert ids() == [nota["id"], avulsa["id"]]
    assert ids(vinculo="manutencao") == [nota["id"]]
    assert ids(vinculo="nenhum") == [avulsa["id"]]
    assert ids(manutencao_id=feita["id"]) == [nota["id"]]
    assert paula.get(f"{base}/fotos", params={"vinculo": "outro"}).status_code == 422

    # Ligar e desligar pela edição da foto.
    ligada = paula.put(f"{base}/fotos/{avulsa['id']}", json={
        "legenda": None, "data_foto": str(hoje), "manutencao_id": feita["id"]}).json()
    assert ligada["manutencao_id"] == feita["id"]
    solta = paula.put(f"{base}/fotos/{avulsa['id']}", json={
        "legenda": None, "data_foto": str(hoje), "manutencao_id": None}).json()
    assert solta["manutencao_id"] is None


def test_foto_nao_pode_ser_ligada_a_manutencao_de_outro_veiculo(banco, paula, rafael, admin, civic,
                                                               hoje, pasta_fotos):
    argo = criar_veiculo(paula, placa="BRA2E19", quilometragem=40000)
    do_argo = criar_manutencao(paula, argo["id"], hoje, quilometragem=40000)
    do_rafael = criar_manutencao(rafael, criar_veiculo(rafael, placa="QWE4567")["id"], hoje)
    foto = enviar_foto(paula, civic["id"]).json()

    for cliente in (paula, admin):
        for manutencao in (do_argo, do_rafael):
            envio = enviar_foto(cliente, civic["id"], manutencao_id=manutencao["id"])
            assert envio.status_code == 422
            assert envio.json()["campos"] == {"manutencao_id": "Manutenção não encontrada neste veículo."}
            edicao = cliente.put(f"/api/veiculos/{civic['id']}/fotos/{foto['id']}", json={
                "legenda": None, "data_foto": str(hoje), "manutencao_id": manutencao["id"]})
            assert edicao.status_code == 422
    # Nenhum arquivo ficou sobrando das tentativas recusadas.
    assert imagens_no_banco(banco) == 1
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto WHERE manutencao_id IS NOT NULL") == 0


def test_apagar_manutencao_apaga_as_fotos_dela_e_as_imagens(banco, paula, civic, hoje, pasta_fotos):
    feita = criar_manutencao(paula, civic["id"], hoje)
    outra = enviar_foto(paula, civic["id"]).json()
    enviar_foto(paula, civic["id"], manutencao_id=feita["id"])
    enviar_foto(paula, civic["id"], manutencao_id=feita["id"])
    assert imagens_no_banco(banco) == 3

    assert paula.delete(f"/api/veiculos/{civic['id']}/manutencoes/{feita['id']}").status_code == 204
    assert [f["id"] for f in paula.get(f"/api/veiculos/{civic['id']}/fotos").json()["itens"]] == [outra["id"]]
    assert imagens_no_banco(banco) == 1  # as duas imagens saíram junto com as linhas
