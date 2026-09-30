"""Regras de calendário: "hoje" é sempre o dia em America/Sao_Paulo.

Os campos DATE (data da leitura, data da compra, data da foto) são dias do
calendário, sem hora. Eles nunca são convertidos de fuso: o que o usuário
digitou é o que fica gravado.
"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from app.config import FUSO_HORARIO


def hoje() -> date:
    return datetime.now(ZoneInfo(FUSO_HORARIO)).date()


def data_br(dia: date) -> str:
    """22/09/2026 (para mensagens)."""
    return dia.strftime("%d/%m/%Y")


def numero_br(valor: int) -> str:
    """85000 -> "85.000" (para mensagens)."""
    return f"{valor:,}".replace(",", ".")
