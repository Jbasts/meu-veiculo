"""Configurações do backend, lidas do arquivo backend/.env.

Nada aqui é enviado ao frontend. Senhas ficam só no .env (que não vai para o Git).
"""

from functools import lru_cache
from pathlib import Path

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


@lru_cache
def obter_configuracoes() -> Configuracoes:
    return Configuracoes()
