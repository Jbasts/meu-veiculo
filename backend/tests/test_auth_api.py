"""Cadastro, login, sessão e troca de senha, de ponta a ponta (PostgreSQL de teste)."""

import pytest

from app.main import app
from tests.auth_utils import (
    SENHA_BOA,
    SENHA_NOVA,
    CaixaDeEntrada,
    cadastrar,
    entrar,
    executar_sql,
    ligar_app_ao_banco,
    novo_aparelho,
    valor_sql,
)


@pytest.fixture
def banco(banco_migrado):
    ligar_app_ao_banco(banco_migrado, CaixaDeEntrada())
    yield banco_migrado
    app.dependency_overrides.clear()


@pytest.fixture
def aparelho(banco):
    return novo_aparelho()


# ------------------------------------------------------------------ cadastro

def test_cadastro_cria_conta_padrao_e_ja_entra(banco, aparelho):
    resposta = cadastrar(aparelho, email="  Paula@Email.COM ")
    assert resposta.status_code == 201
    corpo = resposta.json()
    assert corpo == {"id": corpo["id"], "nome": "Paula", "email": "paula@email.com",
                     "perfil": "padrao", "ativo": True}
    assert "senha" not in resposta.text and "hash" not in resposta.text
    cookie = resposta.headers["set-cookie"]
    assert "mv_sessao=" in cookie and "HttpOnly" in cookie
    assert "Path=/api" in cookie and "samesite=lax" in cookie.lower()
    assert aparelho.get("/api/auth/eu").json()["email"] == "paula@email.com"


def test_senha_guardada_so_como_hash_argon2id(banco, aparelho):
    cadastrar(aparelho)
    guardado = valor_sql(banco, "SELECT senha_hash FROM usuario")
    assert guardado.startswith("$argon2id$")
    assert SENHA_BOA not in guardado


def test_email_equivalente_com_maiusculas_e_espacos_e_recusado(banco, aparelho):
    assert cadastrar(aparelho, email="paula@email.com").status_code == 201
    resposta = cadastrar(novo_aparelho(), email="  PAULA@email.com ")
    assert resposta.status_code == 409
    assert resposta.json()["campos"] == {"email": resposta.json()["mensagem"]}
    assert valor_sql(banco, "SELECT count(*) FROM usuario") == 1


def test_cadastro_nao_aceita_escolher_admin(banco, aparelho):
    resposta = cadastrar(aparelho, perfil="admin")
    assert resposta.status_code == 422
    assert resposta.json()["campos"] == {"perfil": "Campo não permitido."}
    assert valor_sql(banco, "SELECT count(*) FROM usuario") == 0
    # Sem o campo, a conta nasce padrão.
    cadastrar(aparelho)
    assert valor_sql(banco, "SELECT perfil FROM usuario") == "padrao"


@pytest.mark.parametrize(
    ("dados", "campo", "trecho"),
    [
        ({"senha": "curta", "confirmacao_senha": "curta"}, "senha", "pelo menos 8"),
        ({"confirmacao_senha": "outra coisa qualquer"}, "confirmacao_senha", "não é igual"),
        ({"senha": "12345678", "confirmacao_senha": "12345678"}, "senha", "fácil de adivinhar"),
        ({"senha": "paula@email.com", "confirmacao_senha": "paula@email.com"}, "senha",
         "fácil de adivinhar"),
        ({"email": "paula.email.com"}, "email", "E-mail inválido"),
        ({"nome": "   "}, "nome", "Informe seu nome"),
    ],
)
def test_validacoes_do_cadastro_em_portugues(banco, aparelho, dados, campo, trecho):
    corpo = {"nome": "Paula", "email": "paula@email.com", "senha": SENHA_BOA,
             "confirmacao_senha": SENHA_BOA, **dados}
    resposta = aparelho.post("/api/auth/cadastro", json=corpo)
    assert resposta.status_code == 422
    assert trecho in resposta.json()["campos"][campo]
    assert valor_sql(banco, "SELECT count(*) FROM usuario") == 0


def test_campo_faltando_tem_mensagem_em_portugues(banco, aparelho):
    resposta = aparelho.post("/api/auth/cadastro", json={"nome": "Paula"})
    assert resposta.status_code == 422
    assert resposta.json()["campos"]["email"] == "Campo obrigatório."


# --------------------------------------------------------------------- login

def test_login_com_email_em_outra_grafia(banco, aparelho):
    cadastrar(aparelho)
    outro = novo_aparelho()
    resposta = entrar(outro, email=" PAULA@EMAIL.com")
    assert resposta.status_code == 200
    assert outro.get("/api/auth/eu").status_code == 200
    assert valor_sql(banco, "SELECT ultimo_acesso IS NOT NULL FROM usuario")


def test_senha_errada_e_email_inexistente_tem_a_mesma_resposta(banco, aparelho):
    cadastrar(aparelho)
    errada = entrar(novo_aparelho(), senha="senha errada mesmo")
    inexistente = entrar(novo_aparelho(), email="ninguem@email.com")
    assert errada.status_code == inexistente.status_code == 401
    assert errada.json() == inexistente.json() == {"mensagem": "E-mail ou senha incorretos.",
                                                   "campos": None}


def test_muitas_tentativas_bloqueiam_mesmo_com_a_senha_certa(banco, aparelho):
    cadastrar(aparelho)
    for _ in range(5):
        assert entrar(novo_aparelho(), senha="senha errada mesmo").status_code == 401
    resposta = entrar(novo_aparelho())
    assert resposta.status_code == 429
    assert "Aguarde 15 minutos" in resposta.json()["mensagem"]


def test_bloqueio_por_email_nao_afeta_outra_conta(banco, aparelho):
    cadastrar(aparelho)
    cadastrar(novo_aparelho(), email="rafael@email.com", nome="Rafael")
    for _ in range(5):
        entrar(novo_aparelho(), senha="senha errada mesmo")
    assert entrar(novo_aparelho(), email="rafael@email.com").status_code == 200


def test_conta_desativada_nao_entra_e_perde_a_sessao_antiga(banco, aparelho):
    cadastrar(aparelho)
    assert aparelho.get("/api/auth/eu").status_code == 200
    executar_sql(banco, "UPDATE usuario SET ativo = FALSE")
    # Sessão emitida antes da desativação deixa de valer.
    resposta = aparelho.get("/api/auth/eu")
    assert resposta.status_code == 401
    assert "desativada" in resposta.json()["mensagem"]
    # Com a senha certa, a resposta explica que a conta está desativada.
    login = entrar(novo_aparelho())
    assert login.status_code == 403
    assert "desativada" in login.json()["mensagem"]
    # Reativar não ressuscita a sessão antiga (foi encerrada).
    executar_sql(banco, "UPDATE usuario SET ativo = TRUE")
    assert aparelho.get("/api/auth/eu").status_code == 401


# -------------------------------------------------------------------- sessão

def test_sem_sessao_ou_com_token_inventado_da_401(banco):
    anonimo = novo_aparelho()
    assert anonimo.get("/api/auth/eu").status_code == 401
    anonimo.cookies.set("mv_sessao", "token-inventado", path="/api")
    assert anonimo.get("/api/auth/eu").status_code == 401


def test_sair_encerra_a_sessao_mesmo_que_o_token_seja_reenviado(banco, aparelho):
    cadastrar(aparelho)
    token = aparelho.cookies.get("mv_sessao")
    resposta = aparelho.post("/api/auth/sair")
    assert resposta.status_code == 204
    assert 'mv_sessao=""' in resposta.headers["set-cookie"]
    copia = novo_aparelho()
    copia.cookies.set("mv_sessao", token, path="/api")
    assert copia.get("/api/auth/eu").status_code == 401


def test_sessao_expirada_da_401(banco, aparelho):
    cadastrar(aparelho)
    executar_sql(banco, "UPDATE sessao SET criada_em = now() - interval '31 days', "
                        "expira_em = now() - interval '1 day'")
    assert aparelho.get("/api/auth/eu").status_code == 401


def test_banco_guarda_so_o_hash_do_token_da_sessao(banco, aparelho):
    cadastrar(aparelho)
    token = aparelho.cookies.get("mv_sessao")
    guardado = valor_sql(banco, "SELECT token_hash FROM sessao")
    assert token not in guardado and len(guardado) == 64


def test_gravacao_sem_cabecalho_do_app_e_recusada(banco):
    sem_cabecalho = novo_aparelho()
    sem_cabecalho.headers.pop("X-MV-Requisicao")
    resposta = cadastrar(sem_cabecalho)
    assert resposta.status_code == 403
    assert valor_sql(banco, "SELECT count(*) FROM usuario") == 0
    # Leitura não precisa do cabeçalho.
    assert sem_cabecalho.get("/api/saude").status_code == 200


# ------------------------------------------------------------- troca de senha

def trocar_senha(cliente, atual=SENHA_BOA, nova=SENHA_NOVA, confirmacao=None):
    return cliente.post("/api/auth/alterar-senha", json={
        "senha_atual": atual, "nova_senha": nova, "confirmacao_senha": confirmacao or nova,
    })


def test_trocar_senha_exige_a_senha_atual(banco, aparelho):
    cadastrar(aparelho)
    resposta = trocar_senha(aparelho, atual="não é esta")
    assert resposta.status_code == 422
    assert "senha_atual" in resposta.json()["campos"]


def test_trocar_senha_encerra_os_outros_aparelhos(banco, aparelho):
    cadastrar(aparelho)
    celular = novo_aparelho()
    entrar(celular)
    assert trocar_senha(aparelho).status_code == 200
    assert aparelho.get("/api/auth/eu").status_code == 200  # este continua
    assert celular.get("/api/auth/eu").status_code == 401   # o outro saiu
    assert entrar(novo_aparelho()).status_code == 401
    assert entrar(novo_aparelho(), senha=SENHA_NOVA).status_code == 200


def test_trocar_senha_exige_login(banco):
    assert trocar_senha(novo_aparelho()).status_code == 401


def test_nova_senha_igual_a_atual_e_recusada(banco, aparelho):
    cadastrar(aparelho)
    resposta = trocar_senha(aparelho, nova=SENHA_BOA)
    assert resposta.status_code == 422
    assert "diferente da atual" in resposta.json()["mensagem"]


# ------------------------------------------------------- HTTPS (etapa 11)

def test_cookie_seguro_com_https(banco):
    """COOKIE_SEGURO=true (README 18.8): o cookie só trafega em HTTPS e a sessão
    continua funcionando por https; os links dos e-mails usam URL_FRONTEND."""
    from fastapi.testclient import TestClient

    from app.config import obter_configuracoes
    from app.dependencias import obter_enviador_email
    from tests.auth_utils import CABECALHOS_APP, pedir_recuperacao

    cfg = obter_configuracoes().model_copy(update={
        "cookie_seguro": True, "url_frontend": "https://192.168.0.10:4173"})
    app.dependency_overrides[obter_configuracoes] = lambda: cfg
    caixa = CaixaDeEntrada()
    app.dependency_overrides[obter_enviador_email] = lambda: caixa
    celular = TestClient(app, headers=CABECALHOS_APP, base_url="https://testserver")

    resposta = cadastrar(celular)
    assert resposta.status_code == 201
    cookie = resposta.headers["set-cookie"].lower()
    assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    assert celular.get("/api/auth/eu").status_code == 200
    assert "secure" in celular.post("/api/auth/sair").headers["set-cookie"].lower()

    assert pedir_recuperacao(celular).status_code in (200, 202)
    assert "https://192.168.0.10:4173/redefinir-senha#token=" in caixa.mensagens[-1].texto


def test_sem_cookie_seguro_o_padrao_continua_em_http(banco, aparelho):
    resposta = cadastrar(aparelho)
    assert "secure" not in resposta.headers["set-cookie"].lower()
