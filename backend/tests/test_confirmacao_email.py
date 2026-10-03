"""Confirmação do e-mail ao criar a conta (migration 0014), de ponta a ponta."""

import pytest

from app.main import app
from tests.auth_utils import (
    SENHA_BOA,
    SENHA_NOVA,
    CaixaDeEntrada,
    confirmar,
    entrar,
    executar_sql,
    ligar_app_ao_banco,
    novo_aparelho,
    pedir_recuperacao,
    redefinir,
    so_cadastrar,
    valor_sql,
)


@pytest.fixture
def caixa():
    return CaixaDeEntrada()


@pytest.fixture
def banco(banco_migrado, caixa):
    ligar_app_ao_banco(banco_migrado, caixa)
    yield banco_migrado
    app.dependency_overrides.clear()


def reenviar(cliente, email="paula@email.com"):
    return cliente.post("/api/auth/reenviar-confirmacao", json={"email": email})


def test_cadastro_nao_entra_e_envia_o_link(banco, caixa):
    aparelho = novo_aparelho()
    resposta = so_cadastrar(aparelho, email="  Paula@Email.COM ")
    assert resposta.status_code == 201
    assert resposta.json() == {"mensagem": "Conta criada! Enviamos um link de confirmação para "
                               "paula@email.com. Abra o link para liberar a entrada (confira "
                               "também o spam)."}
    assert "set-cookie" not in resposta.headers
    assert aparelho.get("/api/auth/eu").status_code == 401
    assert valor_sql(banco, "SELECT perfil || '/' || email_confirmado || '/' || "
                            "(email_confirmado_em IS NULL) FROM usuario") == "padrao/false/true"

    assert len(caixa.mensagens) == 1
    mensagem = caixa.mensagens[0]
    assert mensagem.para == "paula@email.com"
    assert mensagem.assunto == "Meu Veículo: confirme seu e-mail"
    assert "http://localhost:5173/confirmar-email#token=" in mensagem.texto
    assert "48 horas" in mensagem.texto
    # O banco guarda só o hash do token.
    assert caixa.ultimo_token() not in valor_sql(banco, "SELECT token_hash FROM recuperacao_senha")
    assert valor_sql(banco, "SELECT finalidade FROM recuperacao_senha") == "confirmacao"


def test_sem_confirmar_nao_entra_e_a_tela_sabe_o_motivo(banco):
    so_cadastrar(novo_aparelho())
    resposta = entrar(novo_aparelho())
    assert resposta.status_code == 403
    corpo = resposta.json()
    assert corpo["codigo"] == "email_nao_confirmado"
    assert corpo["mensagem"].startswith("Confirme seu e-mail para entrar")
    assert "set-cookie" not in resposta.headers
    # Senha errada continua com a resposta de sempre (não revela que a conta espera confirmação).
    errada = entrar(novo_aparelho(), senha="outra senha qualquer")
    assert errada.status_code == 401
    assert "codigo" not in errada.json()


def test_confirmar_libera_a_entrada_uma_vez_so(banco, caixa):
    so_cadastrar(novo_aparelho())
    token = caixa.ultimo_token()
    resposta = confirmar(novo_aparelho(), token)
    assert resposta.status_code == 200
    assert resposta.json()["mensagem"] == "E-mail confirmado! Entre com seu e-mail e senha."
    assert "set-cookie" not in resposta.headers  # confirmar não abre sessão
    assert valor_sql(banco, "SELECT email_confirmado AND email_confirmado_em IS NOT NULL "
                            "FROM usuario")
    assert entrar(novo_aparelho()).status_code == 200

    de_novo = confirmar(novo_aparelho(), token)
    assert de_novo.status_code == 422
    assert "não vale mais" in de_novo.json()["mensagem"]


@pytest.mark.parametrize("token", ["", "abc", "x" * 43])
def test_token_invalido(banco, token):
    resposta = confirmar(novo_aparelho(), token)
    assert resposta.status_code == 422
    assert resposta.json()["campos"]["token"]


def test_link_vencido_nao_confirma(banco, caixa):
    so_cadastrar(novo_aparelho())
    executar_sql(banco, "UPDATE recuperacao_senha SET criado_em = now() - interval '3 days', "
                        "expira_em = now() - interval '1 minute'")
    assert confirmar(novo_aparelho(), caixa.ultimo_token()).status_code == 422
    assert entrar(novo_aparelho()).status_code == 403


def test_link_de_confirmacao_nao_troca_senha_e_link_de_senha_nao_confirma_pela_tela_errada(
        banco, caixa):
    so_cadastrar(novo_aparelho())
    confirmacao = caixa.ultimo_token()
    assert redefinir(novo_aparelho(), confirmacao).status_code == 422
    assert pedir_recuperacao(novo_aparelho()).status_code == 202
    recuperacao = caixa.ultimo_token()
    assert confirmar(novo_aparelho(), recuperacao).status_code == 422


def test_reenviar_troca_o_link(banco, caixa):
    so_cadastrar(novo_aparelho())
    primeiro = caixa.ultimo_token()
    resposta = reenviar(novo_aparelho(), " PAULA@email.com")
    assert resposta.status_code == 202
    assert "paula@email.com" in resposta.json()["mensagem"]
    assert len(caixa.mensagens) == 2
    assert confirmar(novo_aparelho(), primeiro).status_code == 422
    assert confirmar(novo_aparelho(), caixa.ultimo_token()).status_code == 200


def test_reenviar_para_email_inexistente_ou_ja_confirmado(banco, caixa):
    inexistente = reenviar(novo_aparelho(), "ninguem@email.com")
    assert inexistente.status_code == 404
    assert inexistente.json()["mensagem"] == "E-mail não existente, digite novamente."

    so_cadastrar(novo_aparelho())
    confirmar(novo_aparelho(), caixa.ultimo_token())
    ja = reenviar(novo_aparelho())
    assert ja.status_code == 409
    assert "já foi confirmado" in ja.json()["mensagem"]
    assert len(caixa.mensagens) == 1


def test_conta_desativada_nao_confirma_nem_recebe_link(banco, caixa):
    so_cadastrar(novo_aparelho())
    token = caixa.ultimo_token()
    executar_sql(banco, "UPDATE usuario SET ativo = FALSE")
    assert confirmar(novo_aparelho(), token).status_code == 422
    assert reenviar(novo_aparelho()).status_code == 403
    assert len(caixa.mensagens) == 1


def test_redefinir_a_senha_pelo_link_tambem_confirma(banco, caixa):
    """Quem abriu o link de senha que chegou no e-mail provou que o e-mail é dela."""
    so_cadastrar(novo_aparelho())
    pedir_recuperacao(novo_aparelho())
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200
    assert valor_sql(banco, "SELECT email_confirmado FROM usuario")
    assert entrar(novo_aparelho(), senha=SENHA_NOVA).status_code == 200
    assert entrar(novo_aparelho(), senha=SENHA_BOA).status_code == 401


def test_cadastro_repetido_continua_recusado_mesmo_sem_confirmar(banco):
    so_cadastrar(novo_aparelho())
    resposta = so_cadastrar(novo_aparelho())
    assert resposta.status_code == 409
    assert valor_sql(banco, "SELECT count(*) FROM usuario") == 1
