"""Área de administração, de ponta a ponta (API + PostgreSQL de teste).

Dois usuários padrão (Paula e Rafael) e uma administradora (Admin).
"""

import threading
from datetime import timedelta

import pytest

from app.dependencias import obter_enviador_email
from app.main import app
from tests.auth_utils import (
    SENHA_NOVA,
    CaixaDeEntrada,
    cadastrar,
    entrar,
    executar_sql,
    novo_aparelho,
    redefinir,
    valor_sql,
)
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    banco,
    criar_veiculo,
    pasta_fotos,
    paula,
    rafael,
)


@pytest.fixture
def caixa(banco) -> CaixaDeEntrada:
    caixa = CaixaDeEntrada()
    app.dependency_overrides[obter_enviador_email] = lambda: caixa
    return caixa


def id_de(banco, email: str) -> int:
    return valor_sql(banco, "SELECT id FROM usuario WHERE email = :e", e=email)


def usuarios(cliente, **params) -> dict:
    resposta = cliente.get("/api/admin/usuarios", params=params)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def alterar(cliente, usuario_id: int, perfil: str = "padrao", ativo: bool = True):
    return cliente.put(f"/api/admin/usuarios/{usuario_id}", json={"perfil": perfil, "ativo": ativo})


def convidar(cliente, nome: str = "Carla Mendes", email: str = "carla@email.com"):
    return cliente.post("/api/admin/usuarios", json={"nome": nome, "email": email})


ENDERECOS_ADMIN = [
    ("get", "/api/admin/resumo", None), ("get", "/api/admin/usuarios", None),
    ("get", "/api/admin/usuarios/1", None), ("get", "/api/admin/veiculos", None),
    ("put", "/api/admin/usuarios/1", {"perfil": "admin", "ativo": True}),
    ("post", "/api/admin/usuarios/1/enviar-link", None),
    ("post", "/api/admin/usuarios", {"nome": "X", "email": "x@email.com"}),
]


# ================================================================ quem pode

def test_lista_acima_cobre_todos_os_endpoints_admin():
    """Endpoint admin novo precisa entrar em ENDERECOS_ADMIN (e no teste de 403)."""
    no_app = {(metodo, caminho.replace("{usuario_id}", "1"))
              for caminho, operacoes in app.openapi()["paths"].items()
              if caminho.startswith("/api/admin/") for metodo in operacoes}
    assert no_app == {(m, e) for m, e, _ in ENDERECOS_ADMIN}


@pytest.mark.parametrize("metodo, endereco, corpo", ENDERECOS_ADMIN)
def test_usuario_padrao_recebe_403_em_toda_a_area_admin(paula, metodo, endereco, corpo):
    resposta = getattr(paula, metodo)(endereco, **({"json": corpo} if corpo else {}))
    assert resposta.status_code == 403
    assert resposta.json()["mensagem"] == "Área restrita a administradores."


@pytest.mark.parametrize("metodo, endereco, corpo", ENDERECOS_ADMIN)
def test_sem_login_recebe_401(banco, metodo, endereco, corpo):
    resposta = getattr(novo_aparelho(), metodo)(endereco, **({"json": corpo} if corpo else {}))
    assert resposta.status_code == 401


def test_padrao_nao_vira_admin_pela_api(banco, paula):
    eu = paula.get("/api/auth/eu").json()
    assert alterar(paula, eu["id"], perfil="admin").status_code == 403
    assert valor_sql(banco, "SELECT perfil FROM usuario WHERE id = :i", i=eu["id"]) == "padrao"


# ================================================================ listagem

def test_lista_de_usuarios_com_contagens_e_sem_senha(banco, admin, paula, rafael):
    criar_veiculo(paula)
    pagina = usuarios(admin)
    assert [u["nome"] for u in pagina["itens"]] == ["Admin", "Paula", "Rafael"]   # por nome
    assert pagina["total"] == 3 and pagina["por_perfil"] == {"admin": 1, "padrao": 2}
    paula_linha = pagina["itens"][1]
    assert (paula_linha["email"], paula_linha["perfil"], paula_linha["ativo"],
            paula_linha["veiculos"], paula_linha["veiculos_ativos"]) == (
        "paula@email.com", "padrao", True, 1, 1)
    assert paula_linha["ultimo_acesso"] is not None
    texto = admin.get("/api/admin/usuarios").text
    assert "senha" not in texto and "argon2" not in texto and "token" not in texto


@pytest.mark.parametrize("busca, nomes", [
    ("PAULA", ["Paula"]), ("rafael@", ["Rafael"]), ("  email.com ", ["Admin", "Paula", "Rafael"]),
    ("%", []), ("_", []), ("ninguém", []),
])
def test_busca_por_nome_ou_email(admin, paula, rafael, busca, nomes):
    assert [u["nome"] for u in usuarios(admin, busca=busca)["itens"]] == nomes


def test_filtro_por_perfil_e_contagens_da_busca(admin, paula, rafael):
    so_padrao = usuarios(admin, perfil="padrao")
    assert [u["nome"] for u in so_padrao["itens"]] == ["Paula", "Rafael"]
    assert so_padrao["total"] == 2
    assert usuarios(admin, busca="paula")["por_perfil"] == {"admin": 0, "padrao": 1}
    assert admin.get("/api/admin/usuarios", params={"perfil": "dono"}).status_code == 422


def test_paginacao_dos_usuarios_estavel(banco, admin):
    for i in range(6):
        assert cadastrar(novo_aparelho(), email=f"mesmo{i}@email.com", nome="Mesmo Nome").status_code == 201
    vistos = []
    for pagina in range(1, 5):
        vistos += [u["id"] for u in usuarios(admin, por_pagina=2, pagina=pagina)["itens"]]
    assert len(vistos) == len(set(vistos)) == 7


def test_resumo_para_o_menu_mais(admin, paula, rafael):
    criar_veiculo(paula)
    criar_veiculo(paula, placa="QWE4567")
    criar_veiculo(rafael, placa="BRA2E19")
    assert admin.get("/api/admin/resumo").json() == {"usuarios": 3, "veiculos": 3}


def test_todos_os_veiculos_com_dono_e_busca(banco, admin, paula, rafael):
    civic = criar_veiculo(paula)
    argo = criar_veiculo(rafael, marca="Fiat", modelo="Argo", ano=2021, placa="BRA2E19")
    assert paula.post(f"/api/veiculos/{civic['id']}/inativar").status_code == 200
    resposta = admin.get("/api/admin/veiculos").json()
    assert [(v["modelo"], v["dono_nome"], v["ativo"]) for v in resposta["itens"]] == [
        ("Civic", "Paula", False), ("Argo", "Rafael", True)]
    for busca, esperado in (("abc-1234", ["Civic"]), ("bra 2e19", ["Argo"]), ("rafael", ["Argo"]),
                            ("fiat", ["Argo"]), ("gol", [])):
        achados = admin.get("/api/admin/veiculos", params={"busca": busca}).json()["itens"]
        assert [v["modelo"] for v in achados] == esperado, busca
    # O admin abre o veículo de outra pessoa (só leitura e alteração pelas rotas normais).
    assert admin.get(f"/api/veiculos/{argo['id']}").status_code == 200


def test_detalhe_do_usuario_com_veiculos(banco, admin, paula):
    criar_veiculo(paula)
    detalhe = admin.get(f"/api/admin/usuarios/{id_de(banco, 'paula@email.com')}").json()
    assert detalhe["usuario"]["nome"] == "Paula"
    assert [v["placa"] for v in detalhe["veiculos"]] == ["ABC1234"]
    assert admin.get("/api/admin/usuarios/999999").status_code == 404


# ================================================================ alterar

def test_promover_e_rebaixar(banco, admin, rafael):
    rafael_id = id_de(banco, "rafael@email.com")
    detalhe = alterar(admin, rafael_id, perfil="admin").json()
    assert detalhe["usuario"]["perfil"] == "admin"
    # Rafael passa a ver a área admin na próxima requisição, sem entrar de novo.
    assert rafael.get("/api/admin/resumo").status_code == 200
    assert alterar(admin, rafael_id, perfil="padrao").json()["usuario"]["perfil"] == "padrao"
    assert rafael.get("/api/admin/resumo").status_code == 403


def test_desativar_encerra_as_sessoes_na_hora_e_reativar_libera(banco, admin, rafael):
    rafael_id = id_de(banco, "rafael@email.com")
    assert rafael.get("/api/auth/eu").status_code == 200
    detalhe = alterar(admin, rafael_id, ativo=False).json()
    assert detalhe["usuario"]["ativo"] is False
    assert rafael.get("/api/auth/eu").status_code == 401
    assert valor_sql(banco, "SELECT COUNT(*) FROM sessao WHERE usuario_id = :i AND revogada_em IS NULL",
                     i=rafael_id) == 0
    assert valor_sql(banco, "SELECT motivo_revogacao FROM sessao WHERE usuario_id = :i",
                     i=rafael_id) == "conta_desativada"
    assert entrar(novo_aparelho(), "rafael@email.com").status_code == 403
    alterar(admin, rafael_id, ativo=True)
    assert entrar(novo_aparelho(), "rafael@email.com").status_code == 200


def test_admin_nao_altera_a_propria_conta(banco, admin):
    eu = id_de(banco, "admin@email.com")
    for perfil, ativo in (("padrao", True), ("admin", False)):
        resposta = alterar(admin, eu, perfil=perfil, ativo=ativo)
        assert resposta.status_code == 409
        assert "própria conta" in resposta.json()["mensagem"]
    assert valor_sql(banco, "SELECT perfil || ativo::text FROM usuario WHERE id = :i", i=eu) == "admintrue"


def test_dois_admins_rebaixando_um_ao_outro_ao_mesmo_tempo_deixa_um_admin(banco, admin, rafael):
    rafael_id, admin_id = id_de(banco, "rafael@email.com"), id_de(banco, "admin@email.com")
    executar_sql(banco, "UPDATE usuario SET perfil = 'admin' WHERE id = :i", i=rafael_id)
    largada = threading.Barrier(2)
    respostas = {}

    def rebaixar(nome, cliente, alvo):
        largada.wait()
        respostas[nome] = alterar(cliente, alvo, perfil="padrao")

    linhas = [threading.Thread(target=rebaixar, args=("admin", admin, rafael_id)),
              threading.Thread(target=rebaixar, args=("rafael", rafael, admin_id))]
    for t in linhas:
        t.start()
    for t in linhas:
        t.join()
    codigos = sorted(r.status_code for r in respostas.values())
    assert valor_sql(banco, "SELECT COUNT(*) FROM usuario WHERE perfil = 'admin' AND ativo") >= 1
    # Um rebaixamento passa; o outro é recusado (último admin) ou barrado por já não ser admin.
    assert codigos[0] == 200 and codigos[1] in (403, 409)


def test_ultimo_admin_protegido_pelo_banco_e_explicado(banco, admin, rafael):
    """Rafael vira admin e desativa a Admin pela API. Ele passa a ser o último admin
    ativo: não pode se rebaixar pela API (própria conta) e o banco recusa mesmo por fora
    (como no pgAdmin)."""
    rafael_id = id_de(banco, "rafael@email.com")
    executar_sql(banco, "UPDATE usuario SET perfil = 'admin' WHERE id = :i", i=rafael_id)
    assert alterar(rafael, id_de(banco, "admin@email.com"), perfil="admin", ativo=False).status_code == 200
    with pytest.raises(Exception, match="último administrador"):
        executar_sql(banco, "UPDATE usuario SET perfil = 'padrao' WHERE id = :i", i=rafael_id)


@pytest.mark.parametrize("corpo, campo", [
    ({"perfil": "dono", "ativo": True}, "perfil"),
    ({"perfil": "admin"}, "ativo"),
    ({"perfil": "admin", "ativo": True, "senha": "123"}, "senha"),
])
def test_validacao_da_alteracao(banco, admin, rafael, corpo, campo):
    resposta = admin.put(f"/api/admin/usuarios/{id_de(banco, 'rafael@email.com')}", json=corpo)
    assert resposta.status_code == 422
    assert campo in (resposta.json().get("campos") or {})


def test_alterar_usuario_inexistente(admin):
    assert alterar(admin, 999999).status_code == 404


# ================================================================ links

def test_enviar_link_de_nova_senha_sem_revelar_senha(banco, admin, rafael, caixa):
    rafael_id = id_de(banco, "rafael@email.com")
    resposta = admin.post(f"/api/admin/usuarios/{rafael_id}/enviar-link")
    assert resposta.status_code == 200
    assert resposta.json()["tipo"] == "recuperacao"
    assert "token" not in resposta.text
    mensagem = caixa.mensagens[-1]
    assert mensagem.para == "rafael@email.com"
    assert "Um administrador do Meu Veículo enviou este link" in mensagem.texto
    # A senha antiga continua valendo até o link ser usado.
    assert entrar(novo_aparelho(), "rafael@email.com").status_code == 200
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200
    assert entrar(novo_aparelho(), "rafael@email.com", SENHA_NOVA).status_code == 200
    assert rafael.get("/api/auth/eu").status_code == 401        # sessões antigas encerradas


def test_conta_desativada_nao_recebe_link(banco, admin, rafael, caixa):
    rafael_id = id_de(banco, "rafael@email.com")
    alterar(admin, rafael_id, ativo=False)
    resposta = admin.post(f"/api/admin/usuarios/{rafael_id}/enviar-link")
    assert resposta.status_code == 409 and caixa.mensagens == []


def test_desativar_cancela_link_pendente(banco, admin, rafael, caixa):
    rafael_id = id_de(banco, "rafael@email.com")
    admin.post(f"/api/admin/usuarios/{rafael_id}/enviar-link")
    token = caixa.ultimo_token()
    alterar(admin, rafael_id, ativo=False)
    alterar(admin, rafael_id, ativo=True)
    assert redefinir(novo_aparelho(), token).status_code == 422


# ================================================================ convite ("+")

def test_convidar_cria_conta_padrao_e_envia_convite_de_7_dias(banco, admin, caixa):
    resposta = convidar(admin, email="  Carla@Email.com ")
    assert resposta.status_code == 201, resposta.text
    usuario = resposta.json()["detalhe"]["usuario"]
    assert (usuario["nome"], usuario["email"], usuario["perfil"], usuario["ativo"],
            usuario["ultimo_acesso"]) == ("Carla Mendes", "carla@email.com", "padrao", True, None)
    assert "token" not in resposta.text
    mensagem = caixa.mensagens[-1]
    assert (mensagem.para, mensagem.assunto) == ("carla@email.com", "Meu Veículo: sua conta foi criada")
    assert "Admin criou uma conta para você" in mensagem.texto and "7 dias" in mensagem.texto
    validade = valor_sql(banco, "SELECT expira_em - criado_em FROM recuperacao_senha "
                                "WHERE finalidade = 'convite'")
    assert timedelta(days=6, hours=23) < validade <= timedelta(days=7, minutes=1)
    # Ninguém sabe a senha: só o convite dá acesso.
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200
    assert entrar(novo_aparelho(), "carla@email.com", SENHA_NOVA).status_code == 200


def test_convite_reenviado_para_quem_nunca_entrou(banco, admin, caixa):
    carla_id = convidar(admin).json()["detalhe"]["usuario"]["id"]
    primeiro = caixa.ultimo_token()
    resposta = admin.post(f"/api/admin/usuarios/{carla_id}/enviar-link")
    assert resposta.json()["tipo"] == "convite"
    assert redefinir(novo_aparelho(), primeiro).status_code == 422     # o anterior foi cancelado
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200


@pytest.mark.parametrize("corpo, status, campo", [
    ({"nome": "Paula 2", "email": "PAULA@email.com"}, 409, "email"),
    ({"nome": "  ", "email": "x@email.com"}, 422, "nome"),
    ({"nome": "X", "email": "sem-arroba"}, 422, "email"),
    ({"nome": "X", "email": "x@email.com", "perfil": "admin"}, 422, "perfil"),
])
def test_validacao_do_convite(banco, admin, paula, caixa, corpo, status, campo):
    resposta = admin.post("/api/admin/usuarios", json=corpo)
    assert resposta.status_code == status
    assert campo in (resposta.json().get("campos") or {})
    assert caixa.mensagens == []
