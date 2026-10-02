"""Envio de e-mail.

Dois modos (EMAIL_MODO no backend/.env):
- "arquivo" (padrão, desenvolvimento): cada mensagem vira um arquivo .eml em
  EMAIL_PASTA. Dá para abrir com Outlook/Thunderbird ou no VS Code. Não
  depende de nenhum serviço e não envia nada para fora do computador.
  Atenção: o arquivo contém o link de recuperação; não compartilhe.
- "smtp": envia de verdade por um servidor SMTP (ex.: o do seu provedor de
  e-mail ou o Mailpit para testes locais). Veja o README.
"""

import logging
import smtplib
import socket
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, parseaddr
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

from app.config import FUSO_HORARIO, Configuracoes

log = logging.getLogger("meu_veiculo")


@dataclass(frozen=True)
class MensagemEmail:
    para: str
    assunto: str
    texto: str


class EnviadorEmail(Protocol):
    def enviar(self, mensagem: MensagemEmail) -> None: ...


def montar_email(mensagem: MensagemEmail, remetente: str,
                 codificacao: str = "quoted-printable") -> EmailMessage:
    """codificacao: "quoted-printable" (padrão, a mais compatível com servidores
    SMTP) ou "8bit" (texto UTF-8 direto, legível ao abrir o arquivo .eml)."""
    email = EmailMessage()
    email["From"] = remetente
    email["To"] = mensagem.para
    email["Subject"] = mensagem.assunto
    email["Date"] = formatdate(localtime=True)
    email["Message-ID"] = make_msgid(domain="meuveiculo.local")
    email.set_content(mensagem.texto, charset="utf-8", cte=codificacao)
    return email


class EnviadorArquivo:
    def __init__(self, pasta: Path, remetente: str):
        self._pasta = pasta
        self._remetente = remetente

    def enviar(self, mensagem: MensagemEmail) -> Path:
        self._pasta.mkdir(parents=True, exist_ok=True)
        agora = datetime.now(ZoneInfo(FUSO_HORARIO)).strftime("%Y%m%d_%H%M%S")
        arquivo = self._pasta / f"{agora}_{uuid.uuid4().hex[:8]}.eml"
        # "8bit": o link aparece inteiro e sem códigos (=3D) ao abrir o arquivo.
        arquivo.write_bytes(bytes(montar_email(mensagem, self._remetente, codificacao="8bit")))
        return arquivo


class EnviadorSmtp:
    def __init__(self, cfg: Configuracoes):
        self._cfg = cfg

    def enviar(self, mensagem: MensagemEmail) -> None:
        cfg = self._cfg
        email = montar_email(mensagem, cfg.email_remetente)
        contexto = ssl.create_default_context()
        if cfg.smtp_seguranca == "ssl":
            servidor = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_porta, context=contexto, timeout=20)
        else:
            servidor = smtplib.SMTP(cfg.smtp_host, cfg.smtp_porta, timeout=20)
        with servidor:
            if cfg.smtp_seguranca == "starttls":
                servidor.starttls(context=contexto)
            if cfg.smtp_usuario:
                servidor.login(cfg.smtp_usuario, cfg.smtp_senha.get_secret_value())
            servidor.send_message(email)


def criar_enviador(cfg: Configuracoes) -> EnviadorEmail:
    if cfg.email_modo == "smtp":
        return EnviadorSmtp(cfg)
    return EnviadorArquivo(cfg.email_pasta, cfg.email_remetente)


def conferir_configuracao_smtp(cfg: Configuracoes) -> list[str]:
    """Problemas que impedem (ou atrapalham) o envio real, antes de tentar.
    Usado pelo "gerenciar.py testar-email". Nunca mostra a senha."""
    if cfg.email_modo != "smtp":
        return []
    problemas: list[str] = []
    if not cfg.smtp_host.strip():
        problemas.append("SMTP_HOST está vazio (Gmail: smtp.gmail.com).")
    if cfg.smtp_usuario and not cfg.smtp_senha.get_secret_value():
        problemas.append("SMTP_USUARIO está preenchido, mas SMTP_SENHA está vazia.")
    if cfg.smtp_seguranca == "starttls" and cfg.smtp_porta == 465:
        problemas.append("A porta 465 usa SMTP_SEGURANCA=ssl (starttls é para a porta 587).")
    if cfg.smtp_seguranca == "ssl" and cfg.smtp_porta == 587:
        problemas.append("A porta 587 usa SMTP_SEGURANCA=starttls (ssl é para a porta 465).")
    _, endereco_remetente = parseaddr(cfg.email_remetente)
    if (cfg.smtp_usuario and "@" in cfg.smtp_usuario
            and endereco_remetente.lower() != cfg.smtp_usuario.strip().lower()):
        problemas.append(
            f"EMAIL_REMETENTE ({endereco_remetente or 'vazio'}) é diferente de SMTP_USUARIO. "
            "O Gmail (e a maioria dos provedores) só envia com o endereço da própria conta: "
            "use o mesmo endereço."
        )
    return problemas


def explicar_falha_de_envio(erro: BaseException) -> str:
    """Traduz o erro do envio por SMTP numa orientação em português.
    Não repete a mensagem do servidor (pode conter o endereço ou dados da conta)."""
    if isinstance(erro, smtplib.SMTPAuthenticationError):
        return ("O servidor recusou o usuário ou a senha. No Gmail, SMTP_SENHA "
                "precisa ser uma \"senha de app\" (16 letras, digitadas sem espaços), "
                "não a senha normal da conta; a verificação em duas etapas precisa estar ligada.")
    if isinstance(erro, smtplib.SMTPSenderRefused):
        return "O servidor recusou o remetente. Use em EMAIL_REMETENTE o mesmo endereço de SMTP_USUARIO."
    if isinstance(erro, smtplib.SMTPRecipientsRefused):
        return "O servidor recusou o destinatário. Confira o endereço digitado."
    if isinstance(erro, smtplib.SMTPNotSupportedError):
        return ("O servidor não aceita esse tipo de conexão ou de login. Confira SMTP_SEGURANCA "
                "(starttls na porta 587, ssl na 465).")
    if isinstance(erro, (ssl.SSLError, smtplib.SMTPServerDisconnected)):
        return ("A conexão segura falhou. Confira o par porta/segurança: 587 com starttls "
                "ou 465 com ssl.")
    if isinstance(erro, socket.gaierror):
        return "Não encontrei o servidor SMTP_HOST. Confira o nome (ex.: smtp.gmail.com) e a internet."
    if isinstance(erro, (TimeoutError, socket.timeout)):
        return ("O servidor não respondeu a tempo. Confira SMTP_PORTA, a internet e se o "
                "antivírus ou a rede bloqueiam envio de e-mail.")
    if isinstance(erro, ConnectionRefusedError):
        return "A conexão foi recusada. Confira SMTP_HOST e SMTP_PORTA."
    if isinstance(erro, smtplib.SMTPException):
        return f"O servidor de e-mail recusou o envio ({type(erro).__name__})."
    return f"Falha inesperada ao enviar ({type(erro).__name__})."


def enviar_sem_interromper(enviador: EnviadorEmail, mensagem: MensagemEmail) -> None:
    """Usado depois que a resposta já foi enviada: uma falha no e-mail é
    registrada no log (só o tipo do erro, sem destinatário nem conteúdo)."""
    try:
        enviador.enviar(mensagem)
    except Exception as erro:  # noqa: BLE001 - qualquer falha de envio só é registrada
        log.error("Falha ao enviar e-mail (%s)", type(erro).__name__)
