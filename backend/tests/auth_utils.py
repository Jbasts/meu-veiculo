"""Apoio aos testes de conta: cliente HTTP ligado ao banco de teste."""

from dataclasses import dataclass, field

from argon2 import PasswordHasher
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.banco.conexao import obter_engine
from app.dependencias import obter_enviador_email, obter_senha_service
from app.main import app
from app.services.email_service import MensagemEmail
from app.services.senha_service import SenhaService

CABECALHOS_APP = {"X-MV-Requisicao": "1"}
SENHA_BOA = "meu carro azul 2020"
SENHA_NOVA = "outra frase bem longa 77"

# Argon2 com parâmetros baixos só para os testes ficarem rápidos.
SENHAS_RAPIDAS = SenhaService(PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1))


@dataclass
class CaixaDeEntrada:
    """Substitui o envio de e-mail nos testes: guarda as mensagens."""

    mensagens: list[MensagemEmail] = field(default_factory=list)

    def enviar(self, mensagem: MensagemEmail) -> None:
        self.mensagens.append(mensagem)

    def ultimo_token(self, para: str | None = None) -> str:
        mensagens = [m for m in self.mensagens if para is None or m.para == para]
        return mensagens[-1].texto.split("#token=")[1].split()[0]


def ligar_app_ao_banco(engine, caixa: CaixaDeEntrada) -> None:
    app.dependency_overrides[obter_engine] = lambda: engine
    app.dependency_overrides[obter_senha_service] = lambda: SENHAS_RAPIDAS
    app.dependency_overrides[obter_enviador_email] = lambda: caixa


def novo_aparelho() -> TestClient:
    """Um "aparelho": cliente com os próprios cookies."""
    return TestClient(app, headers=CABECALHOS_APP)


def so_cadastrar(cliente: TestClient, email: str = "paula@email.com", nome: str = "Paula",
                 senha: str = SENHA_BOA, **extra):
    """Só o POST /cadastro: a conta fica esperando a confirmação do e-mail."""
    return cliente.post("/api/auth/cadastro", json={
        "nome": nome, "email": email, "senha": senha, "confirmacao_senha": senha, **extra,
    })


def confirmar(cliente: TestClient, token: str):
    return cliente.post("/api/auth/confirmar-email", json={"token": token})


def cadastrar(cliente: TestClient, email: str = "paula@email.com", nome: str = "Paula",
              senha: str = SENHA_BOA, **extra):
    """Conta pronta para os testes: cadastra, abre o link de confirmação que
    chegou na caixa de entrada e entra com o mesmo cliente (o fluxo real da
    tela). Devolve a resposta do cadastro (201 se deu certo)."""
    resposta = so_cadastrar(cliente, email=email, nome=nome, senha=senha, **extra)
    if resposta.status_code == 201:
        # A caixa de entrada que o app deste cliente está usando no teste.
        caixa = cliente.app.dependency_overrides[obter_enviador_email]()
        token = caixa.ultimo_token(para=email.strip().lower())
        assert confirmar(cliente, token).status_code == 200
        assert entrar(cliente, email=email, senha=senha).status_code == 200
    return resposta


def entrar(cliente: TestClient, email: str = "paula@email.com", senha: str = SENHA_BOA):
    return cliente.post("/api/auth/entrar", json={"email": email, "senha": senha})


def pedir_recuperacao(cliente: TestClient, email: str = "paula@email.com"):
    return cliente.post("/api/auth/recuperar-senha", json={"email": email})


def redefinir(cliente: TestClient, token: str, senha: str = SENHA_NOVA):
    return cliente.post("/api/auth/redefinir-senha", json={
        "token": token, "nova_senha": senha, "confirmacao_senha": senha,
    })


def executar_sql(engine, sql: str, **parametros) -> None:
    with engine.begin() as conexao:
        conexao.execute(text(sql), parametros)


def valor_sql(engine, sql: str, **parametros):
    with engine.connect() as conexao:
        return conexao.execute(text(sql), parametros).scalar()
