"""Recuperação de senha: link de uso único, validade, concorrência e sigilo."""

import threading
from datetime import timedelta

import pytest

from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao
from app.main import app
from app.repositories.recuperacao_senha_repository import RecuperacaoSenhaRepository
from app.repositories.sessao_repository import SessaoRepository
from app.repositories.tentativa_acesso_repository import TentativaAcessoRepository
from app.repositories.usuario_repository import UsuarioRepository
from app.services.autenticacao_service import AutenticacaoService
from app.services.erros import DadosInvalidos
from tests.auth_utils import (
    SENHA_BOA,
    SENHA_NOVA,
    SENHAS_RAPIDAS,
    CaixaDeEntrada,
    cadastrar,
    entrar,
    executar_sql,
    ligar_app_ao_banco,
    novo_aparelho,
    pedir_recuperacao,
    redefinir,
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


@pytest.fixture
def conta(banco):
    aparelho = novo_aparelho()
    cadastrar(aparelho)
    return aparelho


def test_pedido_para_email_cadastrado_envia_link(banco, conta, caixa):
    resposta = pedir_recuperacao(novo_aparelho(), " PAULA@email.com")
    assert resposta.status_code == 202
    assert len(caixa.mensagens) == 1
    mensagem = caixa.mensagens[0]
    assert mensagem.para == "paula@email.com"
    assert "http://localhost:5173/redefinir-senha#token=" in mensagem.texto
    assert "60 minutos" in mensagem.texto
    # O banco guarda só o hash do token do link.
    assert caixa.ultimo_token() not in valor_sql(banco, "SELECT token_hash FROM recuperacao_senha")


def test_email_sem_conta_pede_para_digitar_de_novo(banco, conta, caixa):
    """Decisão da Paula (02/10/2026): substitui a resposta sempre igual."""
    existe = pedir_recuperacao(novo_aparelho(), "paula@email.com")
    assert existe.status_code == 202
    assert existe.json()["mensagem"].startswith("Enviamos um link")

    nao_existe = pedir_recuperacao(novo_aparelho(), "paula@gmial.com")
    assert nao_existe.status_code == 404
    assert nao_existe.json()["mensagem"] == "E-mail não existente, digite novamente."
    assert nao_existe.json()["campos"] == {"email": "E-mail não existente, digite novamente."}
    assert len(caixa.mensagens) == 1  # só a conta real recebeu
    assert valor_sql(banco, "SELECT count(*) FROM recuperacao_senha") == 1




def test_link_valido_troca_a_senha_e_encerra_todas_as_sessoes(banco, conta, caixa):
    celular = novo_aparelho()
    entrar(celular)
    pedir_recuperacao(novo_aparelho())
    resposta = redefinir(novo_aparelho(), caixa.ultimo_token())
    assert resposta.status_code == 200
    assert conta.get("/api/auth/eu").status_code == 401
    assert celular.get("/api/auth/eu").status_code == 401
    assert entrar(novo_aparelho(), senha=SENHA_BOA).status_code == 401
    assert entrar(novo_aparelho(), senha=SENHA_NOVA).status_code == 200


def test_link_reutilizado_e_recusado(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    token = caixa.ultimo_token()
    assert redefinir(novo_aparelho(), token).status_code == 200
    segunda = redefinir(novo_aparelho(), token, senha="mais uma frase diferente")
    assert segunda.status_code == 422
    assert "já foi usado" in segunda.json()["mensagem"]
    assert entrar(novo_aparelho(), senha=SENHA_NOVA).status_code == 200


def test_link_expirado_e_recusado(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    executar_sql(banco, "UPDATE recuperacao_senha SET criado_em = now() - interval '2 hours', "
                        "expira_em = now() - interval '1 minute'")
    resposta = redefinir(novo_aparelho(), caixa.ultimo_token())
    assert resposta.status_code == 422
    assert "expirou" in resposta.json()["mensagem"]
    assert entrar(novo_aparelho(), senha=SENHA_BOA).status_code == 200


def test_link_novo_invalida_o_anterior(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    primeiro = caixa.ultimo_token()
    pedir_recuperacao(novo_aparelho())
    assert redefinir(novo_aparelho(), primeiro).status_code == 422
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200


def test_token_inventado_e_recusado(banco, conta):
    assert redefinir(novo_aparelho(), "token-que-nao-existe").status_code == 422


def test_senha_fraca_no_link_nao_gasta_o_link(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    token = caixa.ultimo_token()
    fraca = redefinir(novo_aparelho(), token, senha="12345678")
    assert fraca.status_code == 422
    assert redefinir(novo_aparelho(), token).status_code == 200


def test_conta_desativada_nao_recebe_nem_usa_link(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    token = caixa.ultimo_token()
    executar_sql(banco, "UPDATE usuario SET ativo = FALSE")
    assert redefinir(novo_aparelho(), token).status_code == 422
    resposta = pedir_recuperacao(novo_aparelho())
    assert resposta.status_code == 403
    assert "desativada" in resposta.json()["mensagem"]
    assert len(caixa.mensagens) == 1  # nenhum e-mail novo


def test_sem_limite_de_pedidos(banco, conta, caixa):
    """Decisão da Paula (02/10/2026): sem limite na recuperação. Errar muitas
    vezes só mostra o aviso; cada pedido certo envia um link novo, e só o
    último vale."""
    for i in range(15):
        resposta = pedir_recuperacao(novo_aparelho(), f"errado{i}@email.com")
        assert resposta.status_code == 404
        assert resposta.json()["mensagem"] == "E-mail não existente, digite novamente."
    respostas = [pedir_recuperacao(novo_aparelho()) for _ in range(6)]
    assert {r.status_code for r in respostas} == {202}
    assert len(caixa.mensagens) == 6
    assert valor_sql(banco, "SELECT count(*) FROM tentativa_acesso WHERE tipo = 'recuperacao'") == 0
    assert redefinir(novo_aparelho(), caixa.mensagens[0].texto.split("#token=")[1].split()[0]).status_code == 422
    assert redefinir(novo_aparelho(), caixa.ultimo_token()).status_code == 200




# ----------------------------------------------------- transação e concorrência

def montar_service(engine):
    sessao = abrir_sessao(engine)
    service = AutenticacaoService(
        UnidadeDeTrabalho(sessao), UsuarioRepository(sessao), SessaoRepository(sessao),
        RecuperacaoSenhaRepository(sessao), TentativaAcessoRepository(sessao), SENHAS_RAPIDAS,
        validade_sessao=timedelta(days=30), validade_link=timedelta(minutes=60),
        url_frontend="http://localhost:5173",
    )
    return sessao, service


def test_link_consumido_ao_mesmo_tempo_so_funciona_uma_vez(banco, conta, caixa):
    pedir_recuperacao(novo_aparelho())
    token = caixa.ultimo_token()
    largada = threading.Barrier(2)
    resultados: list[str] = []

    def tentar(senha: str) -> None:
        sessao, service = montar_service(banco)
        try:
            largada.wait(timeout=10)
            service.redefinir_senha(token, senha, senha)
            resultados.append("ok")
        except DadosInvalidos:
            resultados.append("recusado")
        finally:
            sessao.close()

    tarefas = [threading.Thread(target=tentar, args=(s,))
               for s in ("primeira frase comprida", "segunda frase comprida")]
    for tarefa in tarefas:
        tarefa.start()
    for tarefa in tarefas:
        tarefa.join(timeout=30)

    assert sorted(resultados) == ["ok", "recusado"]
    assert valor_sql(banco, "SELECT count(*) FROM recuperacao_senha WHERE usado_em IS NOT NULL") == 1


def test_falha_na_troca_desfaz_o_consumo_do_link(banco, conta, caixa, monkeypatch):
    pedir_recuperacao(novo_aparelho())
    token = caixa.ultimo_token()
    sessao, service = montar_service(banco)

    def falhar(*_args, **_kwargs):
        raise RuntimeError("falha forçada ao gravar a senha")

    monkeypatch.setattr(UsuarioRepository, "atualizar_senha", falhar)
    with pytest.raises(RuntimeError):
        service.redefinir_senha(token, SENHA_NOVA, SENHA_NOVA)
    sessao.close()
    monkeypatch.undo()

    assert valor_sql(banco, "SELECT count(*) FROM recuperacao_senha WHERE usado_em IS NOT NULL") == 0
    assert conta.get("/api/auth/eu").status_code == 200  # sessões intactas
    assert redefinir(novo_aparelho(), token).status_code == 200
