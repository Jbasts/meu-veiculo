"""Configurações do backend, lidas do arquivo backend/.env.

Nada aqui é enviado ao frontend. Senhas ficam só no .env (que não vai para o Git).
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PASTA_BACKEND = Path(__file__).resolve().parent.parent
PASTA_PROJETO = PASTA_BACKEND.parent

# Todas as regras de calendário (hoje, mês, vencimentos) usam este fuso.
FUSO_HORARIO = "America/Sao_Paulo"


class Configuracoes(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PASTA_BACKEND / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        # Linha vazia no .env (ex.: "EMAIL_PASTA=") usa o valor padrão.
        env_ignore_empty=True,
    )

    db_host: str = "localhost"
    db_porta: int = 5432
    db_usuario: str = "meu_veiculo_app"
    db_senha: SecretStr = Field(default=SecretStr(""))
    db_nome: str = "meu_veiculo"
    db_nome_teste: str = "meu_veiculo_teste"

    # Usuário administrador do PostgreSQL, usado só pelo comando "criar-bancos".
    # A senha dele NÃO fica no .env: o comando pergunta na hora.
    pg_admin_usuario: str = "postgres"

    # Pasta dos programas do PostgreSQL (pg_dump). Vazio = procurar sozinho.
    pg_bin: str = ""

    # Pasta onde os backups automáticos são gravados.
    pasta_backups: Path = PASTA_BACKEND / "backups"

    # Endereço do frontend, usado nos links enviados por e-mail.
    url_frontend: str = "http://localhost:5173"

    # Sessão (cookie). COOKIE_SEGURO=true exige HTTPS; em http://localhost fica false.
    cookie_seguro: bool = False
    sessao_dias: int = Field(default=30, ge=1, le=365)

    # Validade do link de recuperação de senha.
    recuperacao_minutos: int = Field(default=60, ge=5, le=24 * 60)

    # E-mail. "arquivo" grava cada mensagem em EMAIL_PASTA (desenvolvimento);
    # "smtp" envia de verdade pelo servidor configurado abaixo.
    email_modo: Literal["arquivo", "smtp"] = "arquivo"
    email_pasta: Path = PASTA_BACKEND / "emails_dev"
    email_remetente: str = "Meu Veículo <nao-responda@meuveiculo.local>"
    smtp_host: str = ""
    smtp_porta: int = 587
    smtp_usuario: str = ""
    smtp_senha: SecretStr = Field(default=SecretStr(""))
    smtp_seguranca: Literal["starttls", "ssl", "nenhuma"] = "starttls"


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
