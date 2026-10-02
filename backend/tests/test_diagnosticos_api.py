"""Diagnósticos (problemas), anotações e resolução, de ponta a ponta (API + PostgreSQL de teste)."""

import threading
from datetime import date, timedelta

import pytest

from app.repositories.diagnostico_repository import DiagnosticoRepository
from tests.auth_utils import entrar, novo_aparelho, valor_sql
from tests.test_manutencoes_api import (  # noqa: F401  (fixtures)
    civic,
    criar_manutencao,
    dados_manutencao,
    hoje,
    km_do_veiculo,
)
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


def dados_diagnostico(hoje: date, **alteracoes) -> dict:
    return {"titulo": "Barulho na suspensão dianteira", "descricao": "Ao passar em lombadas.",
            "sistema": "suspensao", "gravidade": "media",
            "data_identificacao": str(hoje - timedelta(days=10)), "quilometragem": None,
            **alteracoes}


def caminho(veiculo_id: int, diagnostico_id: int | None = None, acao: str = "") -> str:
    base = f"/api/veiculos/{veiculo_id}/diagnosticos"
    if diagnostico_id is not None:
        base += f"/{diagnostico_id}"
    return base + (f"/{acao}" if acao else "")


def criar_diagnostico(cliente, veiculo_id: int, hoje: date, **alteracoes) -> dict:
    resposta = cliente.post(caminho(veiculo_id), json=dados_diagnostico(hoje, **alteracoes))
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def lista(cliente, veiculo_id: int, filtro: str = "abertos") -> dict:
    resposta = cliente.get(caminho(veiculo_id), params={"filtro": filtro})
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def textos_das_notas(detalhe: dict) -> list[str]:
    return [nota["texto"] for nota in detalhe["notas"]]


def contar(banco, tabela: str) -> int:
    return valor_sql(banco, f"SELECT count(*) FROM {tabela}")


# =========================================================== cadastro e listagem

def test_banco_vazio_lista_sem_diagnosticos(paula, civic):
    for filtro in ("abertos", "resolvidos", "todos"):
        assert lista(paula, civic["id"], filtro) == {"itens": [], "total": 0, "pagina": 1,
                                                     "por_pagina": 30}


def test_registrar_problema_e_ver_o_detalhe(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje, titulo="  Barulho   na suspensão ")
    assert criado["titulo"] == "Barulho na suspensão"
    assert (criado["status"], criado["gravidade"], criado["sistema"]) == (
        "aberto", "media", "suspensao")
    assert (criado["notas"], criado["manutencao"], criado["garantias"], criado["total_fotos"]) == (
        [], None, [], 0)
    assert paula.get(caminho(civic["id"], criado["id"])).json() == criado


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"titulo": "   "}, "titulo", "Conte em poucas palavras"),
    ({"titulo": "x" * 151}, "titulo", "máximo 150"),
    ({"gravidade": "urgente"}, "gravidade", "Escolha a gravidade"),
    ({"sistema": "radio"}, "sistema", "Escolha o sistema"),
    ({"quilometragem": -5}, "quilometragem", ""),
])
def test_validacao_do_diagnostico(banco, paula, civic, hoje, alteracao, campo, trecho):
    resposta = paula.post(caminho(civic["id"]), json=dados_diagnostico(hoje, **alteracao))
    assert resposta.status_code == 422, resposta.text
    corpo = resposta.json()
    assert campo in corpo["campos"] and trecho in corpo["campos"][campo]
    assert contar(banco, "diagnostico") == 0


def test_data_no_futuro_e_recusada(banco, paula, civic, hoje):
    resposta = paula.post(caminho(civic["id"]),
                          json=dados_diagnostico(hoje, data_identificacao=str(hoje + timedelta(1))))
    assert resposta.status_code == 422
    assert "futuro" in resposta.json()["campos"]["data_identificacao"]


def test_quilometragem_do_problema_vira_leitura_e_nao_pode_contradizer(banco, paula, civic, hoje):
    criar_diagnostico(paula, civic["id"], hoje, quilometragem=85600,
                      data_identificacao=str(hoje))
    assert km_do_veiculo(paula, civic["id"]) == 85600
    ontem_menor = paula.post(caminho(civic["id"]), json=dados_diagnostico(
        hoje, quilometragem=90000, data_identificacao=str(hoje - timedelta(days=5))))
    assert ontem_menor.status_code == 422
    assert "não combina com o histórico" in ontem_menor.json()["campos"]["quilometragem"]


def test_abertos_por_gravidade_resolvidos_pelo_mais_recente(paula, civic, hoje):
    dia = lambda n: str(hoje - timedelta(days=n))  # noqa: E731
    leve = criar_diagnostico(paula, civic["id"], hoje, titulo="Leve", gravidade="baixa",
                             data_identificacao=dia(30))
    grave_novo = criar_diagnostico(paula, civic["id"], hoje, titulo="Grave novo",
                                   gravidade="critica", data_identificacao=dia(2))
    grave_antigo = criar_diagnostico(paula, civic["id"], hoje, titulo="Grave antigo",
                                     gravidade="critica", data_identificacao=dia(20))
    fim1 = criar_diagnostico(paula, civic["id"], hoje, titulo="Descartado antes")
    fim2 = criar_diagnostico(paula, civic["id"], hoje, titulo="Descartado depois")
    paula.post(caminho(civic["id"], fim1["id"], "descartar"), json={"data": dia(5)})
    paula.post(caminho(civic["id"], fim2["id"], "descartar"), json={"data": dia(1)})

    abertos = lista(paula, civic["id"])
    assert [d["id"] for d in abertos["itens"]] == [grave_antigo["id"], grave_novo["id"], leve["id"]]
    resolvidos = lista(paula, civic["id"], "resolvidos")
    assert [d["id"] for d in resolvidos["itens"]] == [fim2["id"], fim1["id"]]
    todos = lista(paula, civic["id"], "todos")
    assert todos["total"] == 5
    assert {d["id"] for d in todos["itens"][:3]} == {leve["id"], grave_novo["id"],
                                                     grave_antigo["id"]}
    assert paula.get(caminho(civic["id"]), params={"filtro": "xyz"}).status_code == 422


def test_editar_o_registro_sem_mudar_a_situacao(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    editado = paula.put(caminho(civic["id"], criado["id"]), json=dados_diagnostico(
        hoje, titulo="Estalo na suspensão", gravidade="alta"))
    assert editado.status_code == 200, editado.text
    assert (editado.json()["titulo"], editado.json()["gravidade"], editado.json()["status"]) == (
        "Estalo na suspensão", "alta", "aberto")
    # status e manutencao_id não vêm do formulário
    com_status = paula.put(caminho(civic["id"], criado["id"]),
                           json={**dados_diagnostico(hoje), "status": "resolvido"})
    assert com_status.status_code == 422


# ================================================================ anotações

def test_anotacoes_da_mais_recente_para_a_mais_antiga(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    url = caminho(civic["id"], criado["id"], "notas")
    paula.post(url, json={"texto": "Piorou com chuva.", "data": str(hoje - timedelta(days=3))})
    detalhe = paula.post(url, json={"texto": "Mecânico pediu para observar."})
    assert detalhe.status_code == 201, detalhe.text
    assert textos_das_notas(detalhe.json()) == ["Mecânico pediu para observar.",
                                                "Piorou com chuva."]
    assert detalhe.json()["notas"][0]["data"] == str(hoje)
    assert lista(paula, civic["id"])["itens"][0]["total_notas"] == 2

    vazia = paula.post(url, json={"texto": "   "})
    assert vazia.status_code == 422 and "Escreva a anotação" in vazia.json()["campos"]["texto"]

    nota = detalhe.json()["notas"][1]["id"]
    depois = paula.delete(f"{url}/{nota}")
    assert textos_das_notas(depois.json()) == ["Mecânico pediu para observar."]
    assert paula.delete(f"{url}/{nota}").status_code == 404


def test_anotacao_de_outro_diagnostico_nao_e_apagada_por_este(paula, civic, hoje):
    um = criar_diagnostico(paula, civic["id"], hoje)
    outro = criar_diagnostico(paula, civic["id"], hoje)
    nota = paula.post(caminho(civic["id"], um["id"], "notas"),
                      json={"texto": "x"}).json()["notas"][0]["id"]
    resposta = paula.delete(caminho(civic["id"], outro["id"], f"notas/{nota}"))
    assert resposta.status_code == 404
    assert len(paula.get(caminho(civic["id"], um["id"])).json()["notas"]) == 1


# ============================================================ situações simples

def test_observar_descartar_e_reabrir(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    url = caminho(civic["id"], criado["id"])
    observado = paula.post(f"{url}/acompanhamento", json={"status": "em_observacao"}).json()
    assert observado["status"] == "em_observacao"
    assert lista(paula, civic["id"])["total"] == 1  # em observação continua em "Abertos"
    assert paula.post(f"{url}/acompanhamento", json={"status": "resolvido"}).status_code == 422

    descartado = paula.post(f"{url}/descartar", json={"motivo": "Era a tampa do porta-malas."})
    assert descartado.status_code == 200, descartado.text
    corpo = descartado.json()
    assert (corpo["status"], corpo["solucao"], corpo["data_resolucao"]) == (
        "descartado", "Era a tampa do porta-malas.", str(hoje))
    assert textos_das_notas(corpo) == ["Descartado. Motivo: Era a tampa do porta-malas."]
    assert paula.post(f"{url}/descartar", json={}).status_code == 409
    assert paula.post(f"{url}/acompanhamento",
                      json={"status": "aberto"}).status_code == 409

    reaberto = paula.post(f"{url}/reabrir").json()
    assert (reaberto["status"], reaberto["solucao"], reaberto["data_resolucao"]) == (
        "aberto", None, None)
    assert textos_das_notas(reaberto)[0] == "Reaberto."
    assert paula.post(f"{url}/reabrir").status_code == 409


def test_descarte_nao_pode_ser_antes_do_problema(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    resposta = paula.post(caminho(civic["id"], criado["id"], "descartar"),
                          json={"data": str(hoje - timedelta(days=30))})
    assert resposta.status_code == 422 and "identificado" in resposta.json()["campos"]["data"]


def test_apagar_diagnostico_apaga_anotacoes(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    paula.post(caminho(civic["id"], criado["id"], "notas"), json={"texto": "x"})
    assert paula.delete(caminho(civic["id"], criado["id"])).status_code == 204
    assert paula.get(caminho(civic["id"], criado["id"])).status_code == 404
    assert (contar(banco, "diagnostico"), contar(banco, "diagnostico_nota")) == (0, 0)


# ======================================================= resolver com manutenção nova

def test_resolver_com_manutencao_realizada_nova(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    resposta = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(
        hoje, descricao="Troca das buchas", sistema="suspensao", valor=None, itens=[
            {"tipo": "peca", "nome": "Bucha da bandeja", "valor": "120.00"},
            {"tipo": "mao_de_obra", "nome": "Troca das buchas", "valor": "80.00"}]))
    assert resposta.status_code == 201, resposta.text
    diagnostico, manutencao = resposta.json()["diagnostico"], resposta.json()["manutencao"]
    assert (diagnostico["status"], diagnostico["data_resolucao"]) == ("resolvido", str(hoje))
    assert diagnostico["manutencao"] == {"id": manutencao["id"], "descricao": "Troca das buchas",
                                         "status": "realizada", "data": str(hoje),
                                         "valor": "200.00"}
    assert textos_das_notas(diagnostico) == ['Resolvido com a manutenção "Troca das buchas".']
    assert manutencao["valor"] == "200.00"  # total calculado pelo backend
    assert [d["id"] for d in manutencao["diagnosticos"]] == [criado["id"]]
    assert lista(paula, civic["id"])["total"] == 0
    assert lista(paula, civic["id"], "resolvidos")["itens"][0]["manutencao"]["id"] == \
        manutencao["id"]


def test_manutencao_anterior_ao_problema_nao_resolve_e_nada_e_gravado(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    resposta = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(
        hoje, data=str(hoje - timedelta(days=20)), quilometragem=None))
    assert resposta.status_code == 422
    assert "não pode ser anterior" in resposta.json()["campos"]["data"]
    assert contar(banco, "manutencao") == 0
    assert paula.get(caminho(civic["id"], criado["id"])).json()["status"] == "aberto"


def test_manutencao_invalida_nao_resolve(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    resposta = paula.post(caminho(civic["id"], criado["id"], "resolver"),
                          json=dados_manutencao(hoje, descricao="  "))
    assert resposta.status_code == 422
    assert (contar(banco, "manutencao"), contar(banco, "diagnostico_nota")) == (0, 0)


def test_falha_no_meio_desfaz_a_manutencao_e_a_resolucao(banco, paula, civic, hoje, monkeypatch):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    km_antes = km_do_veiculo(paula, civic["id"])

    def falhar(self, *args, **kwargs):
        raise RuntimeError("falha forçada ao anotar")

    monkeypatch.setattr(DiagnosticoRepository, "criar_nota", falhar)
    with pytest.raises(RuntimeError, match="falha forçada"):
        paula.post(caminho(civic["id"], criado["id"], "resolver"),
                   json=dados_manutencao(hoje, quilometragem=86000))
    monkeypatch.undo()

    assert (contar(banco, "manutencao"), contar(banco, "leitura_km WHERE origem = 'manutencao'")) \
        == (0, 0)
    assert km_do_veiculo(paula, civic["id"]) == km_antes
    detalhe = paula.get(caminho(civic["id"], criado["id"])).json()
    assert (detalhe["status"], detalhe["manutencao_id"], detalhe["notas"]) == ("aberto", None, [])


def test_envio_repetido_nao_cria_duas_manutencoes(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    url = caminho(civic["id"], criado["id"], "resolver")
    assert paula.post(url, json=dados_manutencao(hoje)).status_code == 201
    segundo = paula.post(url, json=dados_manutencao(hoje))
    assert segundo.status_code == 409 and "já foi resolvido" in segundo.json()["mensagem"]
    assert contar(banco, "manutencao") == 1


def test_envios_simultaneos_resolvem_uma_vez_so(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    url = caminho(civic["id"], criado["id"], "resolver")
    aparelhos = []
    for _ in range(3):
        aparelho = novo_aparelho()
        assert entrar(aparelho).status_code == 200
        aparelhos.append(aparelho)
    largada = threading.Barrier(len(aparelhos))
    codigos: list[int] = []

    def enviar(aparelho):
        largada.wait(timeout=10)
        codigos.append(aparelho.post(url, json=dados_manutencao(hoje)).status_code)

    tarefas = [threading.Thread(target=enviar, args=(a,)) for a in aparelhos]
    for tarefa in tarefas:
        tarefa.start()
    for tarefa in tarefas:
        tarefa.join(timeout=30)

    assert sorted(codigos) == [201, 409, 409]
    assert contar(banco, "manutencao") == 1
    assert contar(banco, "diagnostico_nota") == 1


# ============================================================ manutenção agendada

def test_agendada_fica_prevista_e_resolve_ao_concluir(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    daqui_a_5 = str(hoje + timedelta(days=5))
    resposta = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(
        hoje, descricao="Troca das buchas", status="agendada", data=daqui_a_5,
        quilometragem=None, valor="200.00"))
    assert resposta.status_code == 201, resposta.text
    diagnostico, agendada = resposta.json()["diagnostico"], resposta.json()["manutencao"]
    assert (diagnostico["status"], diagnostico["manutencao"]["status"]) == ("aberto", "agendada")
    assert "será resolvido quando ela for marcada como realizada" in diagnostico["notas"][0]["texto"]
    assert lista(paula, civic["id"])["total"] == 1

    # Não dá para resolver de novo enquanto a prevista existe.
    outra = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(hoje))
    assert outra.status_code == 409 and "já tem uma manutenção agendada" in outra.json()["mensagem"]

    concluida = paula.put(f"/api/veiculos/{civic['id']}/manutencoes/{agendada['id']}",
                          json=dados_manutencao(hoje, descricao="Troca das buchas",
                                                valor="200.00"))
    assert concluida.status_code == 200, concluida.text
    assert concluida.json()["diagnosticos"][0]["status"] == "resolvido"
    depois = paula.get(caminho(civic["id"], criado["id"])).json()
    assert (depois["status"], depois["data_resolucao"]) == ("resolvido", str(hoje))
    assert textos_das_notas(depois)[0] == 'Resolvido com a manutenção "Troca das buchas".'


def test_concluir_antes_da_data_do_problema_e_recusado(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    agendada = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(
        hoje, status="agendada", data=str(hoje + timedelta(days=5)),
        quilometragem=None)).json()["manutencao"]
    resposta = paula.put(f"/api/veiculos/{civic['id']}/manutencoes/{agendada['id']}",
                         json=dados_manutencao(hoje, data=str(hoje - timedelta(days=30)),
                                               quilometragem=None))
    assert resposta.status_code == 422 and "não pode ser anterior" in resposta.json()["campos"]["data"]
    assert paula.get(caminho(civic["id"], criado["id"])).json()["status"] == "aberto"


def test_descartar_solta_a_agendada_sem_apagar(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    agendada = paula.post(caminho(civic["id"], criado["id"], "resolver"), json=dados_manutencao(
        hoje, status="agendada", data=str(hoje + timedelta(days=5)),
        quilometragem=None)).json()["manutencao"]
    descartado = paula.post(caminho(civic["id"], criado["id"], "descartar"), json={}).json()
    assert (descartado["status"], descartado["manutencao_id"]) == ("descartado", None)
    detalhe = paula.get(f"/api/veiculos/{civic['id']}/manutencoes/{agendada['id']}").json()
    assert (detalhe["status"], detalhe["diagnosticos"]) == ("agendada", [])


# ===================================================== reabrir pela manutenção

def resolvido_por_manutencao(paula, civic, hoje) -> tuple[dict, dict]:
    criado = criar_diagnostico(paula, civic["id"], hoje)
    corpo = paula.post(caminho(civic["id"], criado["id"], "resolver"),
                       json=dados_manutencao(hoje, descricao="Troca das buchas",
                                             quilometragem=None)).json()
    return corpo["diagnostico"], corpo["manutencao"]


def test_manutencao_de_volta_para_agendada_reabre_com_aviso(paula, civic, hoje):
    diagnostico, manutencao = resolvido_por_manutencao(paula, civic, hoje)
    resposta = paula.put(f"/api/veiculos/{civic['id']}/manutencoes/{manutencao['id']}",
                         json=dados_manutencao(hoje, descricao="Troca das buchas",
                                               status="agendada",
                                               data=str(hoje + timedelta(days=2)),
                                               quilometragem=None))
    assert resposta.status_code == 200, resposta.text
    depois = paula.get(caminho(civic["id"], diagnostico["id"])).json()
    assert (depois["status"], depois["data_resolucao"], depois["manutencao"]["status"]) == (
        "aberto", None, "agendada")
    assert textos_das_notas(depois)[0] == \
        'Reaberto: a manutenção "Troca das buchas" voltou a ficar agendada.'


def test_apagar_a_manutencao_reabre_com_aviso(paula, civic, hoje):
    diagnostico, manutencao = resolvido_por_manutencao(paula, civic, hoje)
    assert paula.delete(
        f"/api/veiculos/{civic['id']}/manutencoes/{manutencao['id']}").status_code == 204
    depois = paula.get(caminho(civic["id"], diagnostico["id"])).json()
    assert (depois["status"], depois["manutencao"]) == ("aberto", None)
    assert textos_das_notas(depois)[0] == 'Reaberto: a manutenção "Troca das buchas" foi apagada.'


def test_reabrir_o_diagnostico_mantem_a_manutencao_no_historico(banco, paula, civic, hoje):
    diagnostico, manutencao = resolvido_por_manutencao(paula, civic, hoje)
    reaberto = paula.post(caminho(civic["id"], diagnostico["id"], "reabrir")).json()
    assert (reaberto["status"], reaberto["manutencao_id"]) == ("aberto", None)
    detalhe = paula.get(f"/api/veiculos/{civic['id']}/manutencoes/{manutencao['id']}").json()
    assert (detalhe["status"], detalhe["diagnosticos"]) == ("realizada", [])


def test_nao_pode_mudar_a_data_do_problema_para_depois_da_resolucao(paula, civic, hoje):
    diagnostico, _ = resolvido_por_manutencao(paula, civic, hoje)
    resposta = paula.put(caminho(civic["id"], diagnostico["id"]), json=dados_diagnostico(
        hoje, data_identificacao=str(hoje)))
    assert resposta.status_code == 200  # no mesmo dia pode
    diagnostico, _ = resolvido_por_manutencao(paula, civic, hoje - timedelta(days=1))
    # resolvida ontem: identificar hoje ficaria depois da resolução
    ontem = paula.put(caminho(civic["id"], diagnostico["id"]),
                      json=dados_diagnostico(hoje, data_identificacao=str(hoje)))
    assert ontem.status_code == 422, ontem.text


# ================================================== manutenção já registrada

def test_usar_manutencao_realizada_ja_registrada(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    feita = criar_manutencao(paula, civic["id"], hoje, quilometragem=None)
    resposta = paula.post(caminho(civic["id"], criado["id"], "vincular"),
                          json={"manutencao_id": feita["id"]})
    assert resposta.status_code == 200, resposta.text
    assert (resposta.json()["status"], resposta.json()["manutencao"]["id"]) == (
        "resolvido", feita["id"])


def test_usar_manutencao_de_outro_veiculo_e_recusado(banco, paula, rafael, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    da_moto = criar_manutencao(paula, moto["id"], hoje, quilometragem=None)
    carro_do_rafael = criar_veiculo(rafael)
    do_rafael = criar_manutencao(rafael, carro_do_rafael["id"], hoje, quilometragem=None)
    for manutencao_id in (da_moto["id"], do_rafael["id"], 999999):
        resposta = paula.post(caminho(civic["id"], criado["id"], "vincular"),
                              json={"manutencao_id": manutencao_id})
        assert resposta.status_code == 422
        assert "não encontrada neste veículo" in resposta.json()["campos"]["manutencao_id"]
    assert paula.get(caminho(civic["id"], criado["id"])).json()["status"] == "aberto"


# ============================================================ aviso de garantia

@pytest.mark.parametrize("garantia, km_problema, avisa", [
    ({"garantia_ate": "+30"}, None, True),
    ({"garantia_ate": "-1"}, None, False),               # venceu pela data
    ({"garantia_km": 90000}, 86000, True),
    ({"garantia_km": 86000}, 87000, False),              # venceu pela km
    ({"garantia_km": 90000}, None, False),               # sem km do problema: não dá para saber
    ({"garantia_ate": "+30", "garantia_km": 86000}, 87000, False),  # km veio primeiro
])
def test_aviso_de_garantia_do_mesmo_sistema(paula, civic, hoje, garantia, km_problema, avisa):
    feito_em = hoje - timedelta(days=60)
    campos = {"garantia_ate": None, "garantia_km": None}
    for chave, valor in garantia.items():
        campos[chave] = str(hoje + timedelta(days=int(valor))) if chave == "garantia_ate" else valor
    criar_manutencao(paula, civic["id"], hoje, descricao="Amortecedores", sistema="suspensao",
                     data=str(feito_em), quilometragem=85000, **campos)
    criado = criar_diagnostico(paula, civic["id"], hoje, quilometragem=km_problema,
                               data_identificacao=str(hoje))
    garantias = criado["garantias"]
    assert (len(garantias) == 1) is avisa
    if avisa:
        assert garantias[0]["descricao"] == "Amortecedores"
        assert "Amortecedores" in garantias[0]["explicacao"]


def test_garantia_de_outro_sistema_nao_avisa(paula, civic, hoje):
    criar_manutencao(paula, civic["id"], hoje, sistema="freios", quilometragem=None,
                     data=str(hoje - timedelta(days=5)),
                     garantia_ate=str(hoje + timedelta(days=30)))
    assert criar_diagnostico(paula, civic["id"], hoje)["garantias"] == []


def test_garantia_com_data_e_km_sem_km_do_problema_pede_a_quilometragem(paula, civic, hoje):
    criar_manutencao(paula, civic["id"], hoje, sistema="suspensao", quilometragem=85000,
                     data=str(hoje - timedelta(days=60)),
                     garantia_ate=str(hoje + timedelta(days=30)), garantia_km=95000)
    [aviso] = criar_diagnostico(paula, civic["id"], hoje)["garantias"]
    assert "o que vier primeiro" in aviso["explicacao"]
    assert "Informe a quilometragem do problema" in aviso["explicacao"]


# ======================================================= permissões e isolamento

def test_outro_usuario_nao_ve_nem_altera(banco, paula, rafael, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    url = caminho(civic["id"], criado["id"])
    assert rafael.get(caminho(civic["id"])).status_code == 404
    assert rafael.get(url).status_code == 404
    assert rafael.post(caminho(civic["id"]), json=dados_diagnostico(hoje)).status_code == 404
    assert rafael.put(url, json=dados_diagnostico(hoje)).status_code == 404
    assert rafael.post(f"{url}/notas", json={"texto": "x"}).status_code == 404
    assert rafael.post(f"{url}/descartar", json={}).status_code == 404
    assert rafael.post(f"{url}/resolver", json=dados_manutencao(hoje)).status_code == 404
    assert rafael.delete(url).status_code == 404
    # Com o próprio veículo no endereço, o diagnóstico da Paula continua invisível.
    carro_do_rafael = criar_veiculo(rafael)
    assert rafael.get(caminho(carro_do_rafael["id"], criado["id"])).status_code == 404
    assert rafael.delete(caminho(carro_do_rafael["id"], criado["id"])).status_code == 404
    assert (contar(banco, "diagnostico"), contar(banco, "diagnostico_nota"),
            contar(banco, "manutencao")) == (1, 0, 0)


def test_diagnostico_de_outro_veiculo_do_mesmo_dono_nao_aparece(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    assert paula.get(caminho(moto["id"], criado["id"])).status_code == 404
    assert lista(paula, moto["id"])["total"] == 0


def test_admin_ve_e_altera(admin, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    assert admin.get(caminho(civic["id"], criado["id"])).status_code == 200
    resposta = admin.post(caminho(civic["id"], criado["id"], "notas"), json={"texto": "Visto."})
    assert resposta.status_code == 201


def test_veiculo_inativo_mostra_mas_nao_aceita_alteracoes(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    url = caminho(civic["id"], criado["id"])
    assert paula.get(url).status_code == 200
    assert lista(paula, civic["id"])["total"] == 1
    for resposta in (
        paula.post(caminho(civic["id"]), json=dados_diagnostico(hoje)),
        paula.put(url, json=dados_diagnostico(hoje)),
        paula.post(f"{url}/notas", json={"texto": "x"}),
        paula.post(f"{url}/descartar", json={}),
        paula.post(f"{url}/resolver", json=dados_manutencao(hoje)),
        paula.delete(url),
    ):
        assert resposta.status_code == 409, resposta.text
        assert "inativo" in resposta.json()["mensagem"]


def test_sem_login_nao_acessa(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    anonimo = novo_aparelho()
    assert anonimo.get(caminho(civic["id"], criado["id"])).status_code == 401


# =================================================================== fotos

def test_foto_ligada_ao_diagnostico(banco, paula, civic, hoje, pasta_fotos):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    foto = enviar_foto(paula, civic["id"], diagnostico_id=criado["id"])
    assert foto.status_code == 201, foto.text
    assert foto.json()["diagnostico_id"] == criado["id"]
    enviar_foto(paula, civic["id"])  # sem vínculo
    fotos = paula.get(f"/api/veiculos/{civic['id']}/fotos",
                      params={"vinculo": "diagnostico"}).json()
    assert [f["id"] for f in fotos["itens"]] == [foto.json()["id"]]
    so_dele = paula.get(f"/api/veiculos/{civic['id']}/fotos",
                        params={"diagnostico_id": criado["id"]}).json()
    assert so_dele["total"] == 1
    assert paula.get(caminho(civic["id"], criado["id"])).json()["total_fotos"] == 1

    # Apagar o diagnóstico apaga a foto dele (linha e arquivo); a outra fica.
    assert imagens_no_banco(banco) == 2
    assert paula.delete(caminho(civic["id"], criado["id"])).status_code == 204
    assert contar(banco, "veiculo_foto") == 1
    assert imagens_no_banco(banco) == 1


def test_foto_nao_liga_a_dois_registros_nem_a_outro_veiculo(banco, paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    feita = criar_manutencao(paula, civic["id"], hoje, quilometragem=None)
    dois = enviar_foto(paula, civic["id"], diagnostico_id=criado["id"],
                       manutencao_id=feita["id"])
    assert dois.status_code == 422 and "um só registro" in dois.json()["campos"]["diagnostico_id"]
    moto = criar_veiculo(paula, placa="XYZ-9876", marca="Honda", modelo="CG")
    outro = enviar_foto(paula, moto["id"], diagnostico_id=criado["id"])
    assert outro.status_code == 422
    assert "não encontrado neste veículo" in outro.json()["campos"]["diagnostico_id"]
    assert contar(banco, "veiculo_foto") == 0


def test_editar_foto_troca_o_vinculo(paula, civic, hoje):
    criado = criar_diagnostico(paula, civic["id"], hoje)
    foto = enviar_foto(paula, civic["id"]).json()
    url = f"/api/veiculos/{civic['id']}/fotos/{foto['id']}"
    ligada = paula.put(url, json={"legenda": "Vazamento", "diagnostico_id": criado["id"]})
    assert ligada.status_code == 200, ligada.text
    assert (ligada.json()["diagnostico_id"], ligada.json()["manutencao_id"]) == (criado["id"], None)
    solta = paula.put(url, json={"legenda": "Vazamento"})
    assert solta.json()["diagnostico_id"] is None
