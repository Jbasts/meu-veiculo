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
import ssl
import uuid
from dataclasses import dataclass
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
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


def enviar_sem_interromper(enviador: EnviadorEmail, mensagem: MensagemEmail) -> None:
    """Usado depois que a resposta já foi enviada: uma falha no e-mail é
    registrada no log (só o tipo do erro, sem destinatário nem conteúdo)."""
    try:
        enviador.enviar(mensagem)
    except Exception as erro:  # noqa: BLE001 - qualquer falha de envio só é registrada
        log.error("Falha ao enviar e-mail (%s)", type(erro).__name__)
