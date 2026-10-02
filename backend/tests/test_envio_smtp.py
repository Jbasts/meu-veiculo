"""Envio real por SMTP e o comando "gerenciar.py testar-email".

Um servidor SMTP falso (neste arquivo, em 127.0.0.1) faz o papel do Gmail:
confere usuário e senha, recebe a mensagem e pode recusar o remetente. Nada
sai do computador. Não usa o banco.
"""

import base64
import email
import smtplib
import socket
import socketserver
import ssl
import threading
from email import policy

import pytest
from pydantic import SecretStr

import gerenciar
from app.config import obter_configuracoes
from app.services.email_service import (
    EnviadorSmtp,
    MensagemEmail,
    conferir_configuracao_smtp,
    explicar_falha_de_envio,
)

USUARIO = "meuveiculo.teste@gmail.com"
SENHA = "abcdefghijklmnop"


class ServidorSmtpFalso(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self) -> None:
        super().__init__(("127.0.0.1", 0), _AtendimentoSmtp)
        self.recebidas: list[bytes] = []
        self.logins: list[tuple[str, str]] = []
        self.remetentes_aceitos = {USUARIO}

    @property
    def porta(self) -> int:
        return self.server_address[1]


class _AtendimentoSmtp(socketserver.StreamRequestHandler):
    server: ServidorSmtpFalso

    def _responder(self, linha: str) -> None:
        self.wfile.write(linha.encode() + b"\r\n")

    def handle(self) -> None:
        self._responder("220 smtp falso")
        while linha := self.rfile.readline():
            comando = linha.decode().rstrip("\r\n")
            verbo = comando.split(" ", 1)[0].upper()
            if verbo in ("EHLO", "HELO"):
                self._responder("250-smtp falso")
                self._responder("250 AUTH PLAIN")
            elif verbo == "AUTH":
                _, usuario, senha = base64.b64decode(comando.split()[2]).decode().split("\0")
                self.server.logins.append((usuario, senha))
                ok = (usuario, senha) == (USUARIO, SENHA)
                self._responder("235 ok" if ok else "535 5.7.8 Username and Password not accepted")
            elif verbo == "MAIL":
                endereco = comando.split(":", 1)[1].strip().strip("<>").split(">")[0]
                aceito = endereco in self.server.remetentes_aceitos
                self._responder("250 ok" if aceito else "553 5.7.1 sender not allowed")
            elif verbo == "RCPT":
                self._responder("250 ok")
            elif verbo == "DATA":
                self._responder("354 pode mandar")
                partes = []
                while (dado := self.rfile.readline()) not in (b".\r\n", b""):
                    partes.append(dado)
                self.server.recebidas.append(b"".join(partes))
                self._responder("250 recebida")
            elif verbo == "QUIT":
                self._responder("221 tchau")
                return
            else:
                self._responder("250 ok")


@pytest.fixture
def servidor():
    srv = ServidorSmtpFalso()
    thread = threading.Thread(target=srv.serve_forever, daemon=True)
    thread.start()
    yield srv
    srv.shutdown()
    srv.server_close()


def cfg_smtp(porta: int, **mudancas):
    dados = {
        "email_modo": "smtp",
        "smtp_host": "127.0.0.1",
        "smtp_porta": porta,
        "smtp_seguranca": "nenhuma",
        "smtp_usuario": USUARIO,
        "smtp_senha": SENHA,
        "email_remetente": f"Meu Veículo <{USUARIO}>",
        "url_frontend": "https://192.168.0.10:4173/",
    }
    dados.update(mudancas)
    # model_copy não converte: a senha precisa virar SecretStr aqui.
    dados["smtp_senha"] = SecretStr(dados["smtp_senha"])
    return obter_configuracoes().model_copy(update=dados)


def rodar_comando(monkeypatch, cfg, *args: str) -> None:
    monkeypatch.setattr(gerenciar, "obter_configuracoes", lambda: cfg)
    gerenciar.main(["testar-email", *args])


def test_enviador_smtp_faz_login_e_entrega_a_mensagem(servidor):
    cfg = cfg_smtp(servidor.porta)
    EnviadorSmtp(cfg).enviar(MensagemEmail("ana@email.com", "Meu Veículo: teste", "Olá, Ana.\nLink: https://x/y"))

    assert servidor.logins == [(USUARIO, SENHA)]
    lida = email.message_from_bytes(servidor.recebidas[0], policy=policy.default)
    assert lida["To"] == "ana@email.com"
    assert lida["Subject"] == "Meu Veículo: teste"
    assert USUARIO in lida["From"]
    assert "Link: https://x/y" in lida.get_content()


def test_comando_envia_e_mostra_a_configuracao_sem_a_senha(servidor, monkeypatch, capsys):
    rodar_comando(monkeypatch, cfg_smtp(servidor.porta), "  Paula@Email.com ")

    saida = capsys.readouterr()
    assert "Enviado para paula@email.com" in saida.out
    assert "senha: preenchida" in saida.out
    assert "https://192.168.0.10:4173" in saida.out
    assert SENHA not in saida.out + saida.err
    lida = email.message_from_bytes(servidor.recebidas[0], policy=policy.default)
    assert lida["To"] == "paula@email.com"
    assert "https://192.168.0.10:4173" in lida.get_content()


def test_senha_recusada_explica_a_senha_de_app_sem_mostrar_a_senha(servidor, monkeypatch, capsys):
    with pytest.raises(SystemExit) as saida_do_comando:
        rodar_comando(monkeypatch, cfg_smtp(servidor.porta, smtp_senha="senha normal errada"),
                      "paula@email.com")

    assert saida_do_comando.value.code == 1
    saida = capsys.readouterr()
    assert "senha de app" in saida.err
    assert "senha normal errada" not in saida.out + saida.err
    assert servidor.recebidas == []


def test_servidor_desligado_vira_orientacao(monkeypatch, capsys):
    with socket.socket() as livre:  # porta que ninguém está ouvindo
        livre.bind(("127.0.0.1", 0))
        porta = livre.getsockname()[1]
    with pytest.raises(SystemExit):
        rodar_comando(monkeypatch, cfg_smtp(porta), "paula@email.com")
    assert "Confira SMTP_HOST e SMTP_PORTA" in capsys.readouterr().err


def test_configuracao_incoerente_para_antes_de_conectar(servidor, monkeypatch, capsys):
    cfg = cfg_smtp(servidor.porta, email_remetente="Meu Veículo <nao-responda@meuveiculo.local>")
    with pytest.raises(SystemExit):
        rodar_comando(monkeypatch, cfg, "paula@email.com")

    assert "EMAIL_REMETENTE" in capsys.readouterr().err
    assert servidor.logins == [] and servidor.recebidas == []


def test_modo_arquivo_grava_eml_e_avisa_que_nada_saiu(tmp_path, monkeypatch, capsys):
    cfg = obter_configuracoes().model_copy(update={"email_modo": "arquivo", "email_pasta": tmp_path})
    rodar_comando(monkeypatch, cfg, "paula@email.com")

    assert "Modo arquivo: nada saiu do computador" in capsys.readouterr().out
    assert len(list(tmp_path.glob("*.eml"))) == 1


def test_destino_invalido(monkeypatch):
    with pytest.raises(SystemExit) as saida:
        rodar_comando(monkeypatch, obter_configuracoes(), "paula@")
    assert "não é um e-mail válido" in str(saida.value.code)


def test_conferir_configuracao_smtp():
    assert conferir_configuracao_smtp(obter_configuracoes().model_copy(update={"email_modo": "arquivo"})) == []
    assert conferir_configuracao_smtp(cfg_smtp(587, smtp_seguranca="starttls")) == []
    assert conferir_configuracao_smtp(cfg_smtp(465, smtp_seguranca="ssl")) == []

    def um(**mudancas) -> str:
        problemas = conferir_configuracao_smtp(cfg_smtp(587, **{"smtp_seguranca": "starttls", **mudancas}))
        assert len(problemas) == 1, problemas
        return problemas[0]

    assert "SMTP_HOST" in um(smtp_host=" ")
    assert "SMTP_SENHA está vazia" in um(smtp_senha="")
    assert "465 usa SMTP_SEGURANCA=ssl" in um(smtp_porta=465)
    assert "587 usa SMTP_SEGURANCA=starttls" in um(smtp_seguranca="ssl")
    assert "mesmo endereço" in um(email_remetente="outro@gmail.com")
    # Maiúsculas e nome de exibição não importam.
    assert conferir_configuracao_smtp(
        cfg_smtp(587, smtp_seguranca="starttls", email_remetente=f"Carro <{USUARIO.upper()}>")) == []


@pytest.mark.parametrize("erro, trecho", [
    (smtplib.SMTPAuthenticationError(535, b"nao aceito"), "senha de app"),
    (smtplib.SMTPSenderRefused(553, b"x", "a@b.c"), "EMAIL_REMETENTE"),
    (smtplib.SMTPRecipientsRefused({"a@b.c": (550, b"x")}), "destinatário"),
    (smtplib.SMTPNotSupportedError("x"), "SMTP_SEGURANCA"),
    (ssl.SSLError("wrong version number"), "587 com starttls"),
    (smtplib.SMTPServerDisconnected("x"), "587 com starttls"),
    (socket.gaierror(11001, "getaddrinfo failed"), "smtp.gmail.com"),
    (TimeoutError("x"), "não respondeu a tempo"),
    (ConnectionRefusedError("x"), "SMTP_PORTA"),
    (smtplib.SMTPDataError(554, b"x"), "SMTPDataError"),
    (ValueError("dado@pessoal.com"), "ValueError"),
])
def test_explicar_falha_de_envio(erro, trecho):
    texto = explicar_falha_de_envio(erro)
    assert trecho in texto
    # Não repete a mensagem do servidor nem endereços.
    assert "@" not in texto.replace("SMTP_USUARIO", "")
