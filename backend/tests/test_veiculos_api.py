"""Veículos de ponta a ponta (API + PostgreSQL de teste): cadastro, edição,
veículo em uso, inativação e permissões entre dois usuários e um admin."""

from decimal import Decimal

import pytest

from app.services.erros import DadosInvalidos
from app.services.veiculo_service import normalizar_placa, validar_dinheiro
from tests.auth_utils import executar_sql, novo_aparelho, valor_sql
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


# ------------------------------------------------------------------- cadastro

def test_cadastra_veiculo_com_placa_normalizada_e_dinheiro_exato(banco, paula):
    corpo = criar_veiculo(paula, placa=" abc-1234 ", marca="  Honda ", valor_aquisicao="65000.10")
    assert corpo["placa"] == "ABC1234"
    assert corpo["marca"] == "Honda"
    assert corpo["valor_aquisicao"] == "65000.10"  # texto, não número com ponto flutuante
    assert corpo["data_aquisicao"] == "2022-03-15"  # DATE sem conversão de fuso
    assert corpo["quilometragem"] == 85000
    assert corpo["data_leitura_km"] == str(valor_sql(banco, "SELECT current_date"))
    assert corpo["ativo"] is True and corpo["em_uso"] is True and corpo["foto_capa_id"] is None
    assert valor_sql(banco, "SELECT valor_aquisicao FROM veiculo") == Decimal("65000.10")


def test_dono_e_sempre_quem_esta_logado(banco, paula, rafael):
    """usuario_id, ativo e outros campos internos vindos da tela são recusados."""
    id_paula = paula.get("/api/auth/eu").json()["id"]
    for campo, valor in (("usuario_id", id_paula), ("ativo", False), ("id", 99)):
        resposta = rafael.post("/api/veiculos", json=dados_veiculo(**{campo: valor}))
        assert resposta.status_code == 422
        assert resposta.json()["campos"] == {campo: "Campo não permitido."}
    assert valor_sql(banco, "SELECT count(*) FROM veiculo") == 0
    veiculo = criar_veiculo(rafael)
    assert veiculo["usuario_id"] == rafael.get("/api/auth/eu").json()["id"]


def test_sem_login_nao_acessa_nada(banco, paula):
    veiculo = criar_veiculo(paula)
    anonimo = novo_aparelho()
    assert anonimo.get("/api/veiculos").status_code == 401
    assert anonimo.get(f"/api/veiculos/{veiculo['id']}").status_code == 401
    assert anonimo.post("/api/veiculos", json=dados_veiculo()).status_code == 401


@pytest.mark.parametrize("alteracao, campo, trecho", [
    ({"marca": "   "}, "marca", "Informe a marca"),
    ({"modelo": ""}, "modelo", "Informe o modelo"),
    ({"ano": 1800}, "ano", "Informe um ano entre 1900"),
    ({"ano": 3000}, "ano", "Informe um ano entre 1900"),
    ({"placa": ""}, "placa", "Informe a placa"),
    ({"placa": "ABC-12345"}, "placa", "Placa inválida"),
    ({"placa": "1234ABC"}, "placa", "Placa inválida"),
    ({"tipo_combustivel": "agua"}, "tipo_combustivel", "Escolha o combustível"),
    ({"quilometragem": -1}, "quilometragem", "não pode ser negativa"),
    ({"quilometragem": 10_000_000}, "quilometragem", "alta demais"),
    ({"km_aquisicao": 90000}, "km_aquisicao", "não pode ser maior que a atual (85.000 km)"),
    ({"data_aquisicao": "2999-01-01"}, "data_aquisicao", "não pode ser no futuro"),
    ({"valor_aquisicao": "-1.00"}, "valor_aquisicao", "não pode ser negativo"),
    ({"valor_aquisicao": "10.005"}, "valor_aquisicao", "duas casas decimais"),
    ({"valor_aquisicao": 65000.1}, "valor_aquisicao", "Valor inválido"),  # float recusado
    ({"ano": "dois mil"}, "ano", "Informe um número inteiro"),
    ({"data_aquisicao": "15/03/2022"}, "data_aquisicao", "Data inválida"),
])
def test_validacao_do_cadastro_com_mensagem_no_campo(banco, paula, alteracao, campo, trecho):
    resposta = paula.post("/api/veiculos", json=dados_veiculo(**alteracao))
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM veiculo") == 0


def test_placa_mercosul_e_todos_os_combustiveis_do_banco(banco, paula):
    combustiveis = ["flex", "gasolina", "etanol", "diesel", "gnv", "hibrido", "eletrico"]
    for indice, combustivel in enumerate(combustiveis):
        corpo = criar_veiculo(paula, placa=f"BRA2E{10 + indice}", tipo_combustivel=combustivel)
        assert corpo["tipo_combustivel"] == combustivel
    assert len(paula.get("/api/veiculos").json()) == 7


def test_dados_da_compra_sao_opcionais(banco, paula):
    corpo = criar_veiculo(paula, data_aquisicao=None, valor_aquisicao=None, km_aquisicao=None)
    assert (corpo["data_aquisicao"], corpo["valor_aquisicao"], corpo["km_aquisicao"]) == (
        None, None, None)


# ------------------------------------------------------ placa única por dono

def test_placa_repetida_na_mesma_conta_e_recusada(banco, paula):
    criar_veiculo(paula, placa="ABC-1234")
    resposta = paula.post("/api/veiculos", json=dados_veiculo(placa="abc 1234"))
    assert resposta.status_code == 409
    assert resposta.json()["campos"] == {"placa": "Já existe um veículo com esta placa nesta conta."}
    assert valor_sql(banco, "SELECT count(*) FROM veiculo") == 1
    # A sessão continua utilizável depois do conflito.
    assert criar_veiculo(paula, placa="BRA2E19")["placa"] == "BRA2E19"


def test_mesma_placa_em_contas_diferentes_e_aceita(banco, paula, rafael):
    criar_veiculo(paula, placa="ABC-1234")
    assert criar_veiculo(rafael, placa="ABC1234")["placa"] == "ABC1234"


def test_editar_para_placa_de_outro_veiculo_da_conta_e_recusado(banco, paula):
    criar_veiculo(paula, placa="ABC-1234")
    outro = criar_veiculo(paula, placa="BRA2E19")
    resposta = paula.put(f"/api/veiculos/{outro['id']}", json=dados_edicao(placa="ABC1234"))
    assert resposta.status_code == 409
    assert paula.get(f"/api/veiculos/{outro['id']}").json()["placa"] == "BRA2E19"


# --------------------------------------------------------------------- edição

def test_edita_dados_sem_mexer_na_quilometragem(banco, paula):
    veiculo = criar_veiculo(paula)
    resposta = paula.put(f"/api/veiculos/{veiculo['id']}", json=dados_edicao(
        cor="Prata", versao="EXL", valor_aquisicao="64000.00", tipo_combustivel="gasolina"))
    assert resposta.status_code == 200, resposta.text
    corpo = resposta.json()
    assert (corpo["cor"], corpo["versao"], corpo["valor_aquisicao"]) == ("Prata", "EXL", "64000.00")
    assert corpo["quilometragem"] == 85000 and corpo["em_uso"] is True


def test_edicao_nao_aceita_quilometragem(banco, paula):
    veiculo = criar_veiculo(paula)
    resposta = paula.put(f"/api/veiculos/{veiculo['id']}", json=dados_veiculo(quilometragem=1))
    assert resposta.status_code == 422
    assert resposta.json()["campos"] == {"quilometragem": "Campo não permitido."}


def test_placa_antiga_fora_do_formato_continua_editavel(banco, paula):
    """Um veículo antigo com placa diferente não fica travado ao editar outros campos."""
    veiculo = criar_veiculo(paula)
    executar_sql(banco, "UPDATE veiculo SET placa = 'XY123'")
    resposta = paula.put(f"/api/veiculos/{veiculo['id']}", json=dados_edicao(placa="XY123",
                                                                             cor="Azul"))
    assert resposta.status_code == 200
    assert resposta.json()["placa"] == "XY123"


# -------------------------------------------------- permissões entre usuários

def test_usuario_nao_ve_nem_altera_veiculo_de_outro(banco, paula, rafael):
    veiculo = criar_veiculo(paula)
    caminho = f"/api/veiculos/{veiculo['id']}"
    assert rafael.get("/api/veiculos").json() == []
    for resposta in (
        rafael.get(caminho),
        rafael.put(caminho, json=dados_edicao(marca="Roubado")),
        rafael.post(f"{caminho}/selecionar"),
        rafael.post(f"{caminho}/inativar"),
        rafael.post(f"{caminho}/reativar"),
    ):
        # Mesma resposta de um veículo que não existe.
        assert resposta.status_code == 404
        assert resposta.json()["mensagem"] == "Veículo não encontrado."
    assert rafael.get("/api/veiculos/999999").status_code == 404
    assert paula.get(caminho).json()["marca"] == "Honda"
    assert valor_sql(banco, "SELECT ativo FROM veiculo") is True


def test_admin_ve_e_gerencia_veiculo_de_outro_usuario(banco, paula, admin):
    veiculo = criar_veiculo(paula)
    caminho = f"/api/veiculos/{veiculo['id']}"
    corpo = admin.get(caminho).json()
    assert corpo["placa"] == "ABC1234" and corpo["em_uso"] is False
    assert admin.put(caminho, json=dados_edicao(cor="Preto")).json()["cor"] == "Preto"
    # O dono não muda quando o admin edita.
    assert valor_sql(banco, "SELECT usuario_id FROM veiculo") == veiculo["usuario_id"]
    # A lista "meus veículos" do admin continua só com os dele.
    assert admin.get("/api/veiculos").json() == []
    # "Veículo em uso" é escolha do dono.
    assert admin.post(f"{caminho}/selecionar").status_code == 409


def test_identificador_invalido_no_endereco(banco, paula):
    for caminho in ("/api/veiculos/0", "/api/veiculos/abc", "/api/veiculos/99999999999"):
        assert paula.get(caminho).status_code == 422


# ------------------------------------------------------------ veículo em uso

def test_varios_veiculos_e_selecao_do_veiculo_em_uso(banco, paula):
    civic = criar_veiculo(paula, placa="ABC-1234")
    argo = criar_veiculo(paula, placa="BRA2E19", marca="Fiat", modelo="Argo")

    def em_uso() -> list[str]:
        return [v["placa"] for v in paula.get("/api/veiculos").json() if v["em_uso"]]

    assert em_uso() == ["BRA2E19"]  # o recém-cadastrado
    assert paula.post(f"/api/veiculos/{civic['id']}/selecionar").json()["em_uso"] is True
    assert em_uso() == ["ABC1234"]
    assert paula.get(f"/api/veiculos/{argo['id']}").json()["em_uso"] is False


def test_nao_seleciona_veiculo_inativo(banco, paula):
    civic = criar_veiculo(paula)
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    resposta = paula.post(f"/api/veiculos/{civic['id']}/selecionar")
    assert resposta.status_code == 409
    assert "inativo" in resposta.json()["mensagem"]


# ----------------------------------------------------------------- inativação

def test_inativar_preserva_o_historico_e_deixa_somente_leitura(banco, paula):
    civic = criar_veiculo(paula, placa="ABC-1234")
    argo = criar_veiculo(paula, placa="BRA2E19")
    paula.post(f"/api/veiculos/{argo['id']}/leituras", json={"quilometragem": 86000, "nivel": 4})
    executar_sql(banco,
                 "INSERT INTO gasto (veiculo_id, categoria, valor) VALUES (:v, 'multa', 130.16)",
                 v=argo["id"])
    caminho = f"/api/veiculos/{argo['id']}"

    resposta = paula.post(f"{caminho}/inativar")
    assert resposta.status_code == 200
    assert resposta.json()["ativo"] is False and resposta.json()["em_uso"] is False

    # Nada foi apagado: o veículo, as leituras e os registros continuam lá.
    assert valor_sql(banco, "SELECT count(*) FROM leitura_km WHERE veiculo_id = :v", v=argo["id"]) == 2
    assert valor_sql(banco, "SELECT count(*) FROM gasto WHERE veiculo_id = :v", v=argo["id"]) == 1
    assert paula.get(caminho).json()["quilometragem"] == 86000
    assert paula.get(f"{caminho}/leituras").json()["total"] == 2

    # Aparece na lista, depois dos ativos; o veículo em uso passa a ser o outro.
    lista = paula.get("/api/veiculos").json()
    assert [(v["placa"], v["ativo"], v["em_uso"]) for v in lista] == [
        ("ABC1234", True, True), ("BRA2E19", False, False)]
    assert civic["id"] == lista[0]["id"]

    # Inativo não aceita alterações.
    for resposta in (
        paula.put(caminho, json=dados_edicao(placa="BRA2E19", cor="Azul")),
        paula.post(f"{caminho}/leituras", json={"quilometragem": 87000, "nivel": 4}),
    ):
        assert resposta.status_code == 409
        assert "inativo" in resposta.json()["mensagem"]

    # Reativar devolve tudo como estava.
    assert paula.post(f"{caminho}/reativar").json()["ativo"] is True
    assert paula.post(f"{caminho}/leituras", json={"quilometragem": 87000, "nivel": 4}).status_code == 201


def test_nao_existe_endpoint_para_apagar_veiculo(banco, paula):
    veiculo = criar_veiculo(paula)
    assert paula.delete(f"/api/veiculos/{veiculo['id']}").status_code == 405
    assert valor_sql(banco, "SELECT count(*) FROM veiculo") == 1


def test_usuario_sem_veiculo_recebe_lista_vazia(banco, paula):
    resposta = paula.get("/api/veiculos")
    assert resposta.status_code == 200 and resposta.json() == []


# ------------------------------------------------------------ regras isoladas

def test_normalizar_placa():
    assert normalizar_placa(" abc-1234 ") == "ABC1234"
    assert normalizar_placa("bra 2e19") == "BRA2E19"
    assert normalizar_placa("") == ""


def test_validar_dinheiro_nao_arredonda_em_silencio():
    assert validar_dinheiro(Decimal("65000"), "valor") == Decimal("65000.00")
    assert validar_dinheiro(Decimal("0.10"), "valor") == Decimal("0.10")
    assert validar_dinheiro(None, "valor") is None
    for ruim in ("0.001", "-0.01", "NaN", "10000000000.00"):
        with pytest.raises(DadosInvalidos):
            validar_dinheiro(Decimal(ruim), "valor")
