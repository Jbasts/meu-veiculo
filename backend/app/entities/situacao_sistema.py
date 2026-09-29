"""Situação do sistema (API, banco e migrations).

Não é uma tabela: é um objeto calculado a cada verificação. Por isso é uma
dataclass simples, e não uma entity mapeada pelo SQLAlchemy.
"""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

SituacaoBanco = Literal["vazio", "sem_controle", "controlado"]


@dataclass(frozen=True)
class EstadoMigracoes:
    situacao: SituacaoBanco
    versao_atual: str | None
    versao_mais_recente: str
    pendentes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RelogioBanco:
    """Data de hoje e fuso, como o PostgreSQL os enxerga nesta conexão."""

    data_hoje: date
    fuso_horario: str


@dataclass(frozen=True)
class SituacaoSistema:
    banco_disponivel: bool
    fuso_horario: str
    mensagem: str
    tudo_certo: bool
    data_hoje: date | None = None
    migracoes: EstadoMigracoes | None = field(default=None)
