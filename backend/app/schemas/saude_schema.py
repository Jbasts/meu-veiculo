"""Formato JSON da resposta de GET /api/saude."""

from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.config import FUSO_HORARIO


class SaudeResposta(BaseModel):
    api: Literal["ok"] = "ok"
    banco: Literal["ok", "indisponivel"]
    situacao_banco: Literal["vazio", "sem_controle", "controlado"] | None = None
    versao_migracao: str | None = None
    versao_mais_recente: str | None = None
    migracoes_pendentes: list[str] = []
    fuso_horario: str = FUSO_HORARIO
    # Data pura "AAAA-MM-DD", sem hora e sem fuso.
    data_hoje: date | None = None
    mensagem: str
