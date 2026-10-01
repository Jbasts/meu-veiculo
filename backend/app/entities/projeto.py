"""Tabelas projeto e projeto_item (SQL original + migration 0011).

Projeto: uma melhoria no veículo ("Rodas de liga leve").
    status: planejado | em_andamento | concluido | cancelado.
    data_conclusao: só no concluído, e obrigatória nele (CHECK da 0011).
    orcamento: opcional; zero é tratado como "sem orçamento" para o percentual.
Item: um gasto do projeto. Entra nas despesas pela data dele, uma vez só,
    inclusive se o projeto for cancelado (a despesa aconteceu).
"""

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.entities.base import Base

PLANEJADO = "planejado"
EM_ANDAMENTO = "em_andamento"
CONCLUIDO = "concluido"
CANCELADO = "cancelado"
STATUS = (PLANEJADO, EM_ANDAMENTO, CONCLUIDO, CANCELADO)
STATUS_ABERTOS = (PLANEJADO, EM_ANDAMENTO)  # aceitam gastos novos
CATEGORIAS = ("exterior", "interior", "mecanica", "som", "outros")

ANTES = "antes"
DEPOIS = "depois"
MOMENTOS = (ANTES, DEPOIS)


class Projeto(Base):
    __tablename__ = "projeto"

    id: Mapped[int] = mapped_column(primary_key=True)
    veiculo_id: Mapped[int] = mapped_column(ForeignKey("veiculo.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(String(120))
    descricao: Mapped[str | None] = mapped_column(Text)
    categoria: Mapped[str] = mapped_column(String(20), server_default=text("'outros'"))
    orcamento: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    data_prevista: Mapped[date | None]
    status: Mapped[str] = mapped_column(String(15), server_default=text("'planejado'"))
    data_conclusao: Mapped[date | None]
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProjetoItem(Base):
    __tablename__ = "projeto_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    projeto_id: Mapped[int] = mapped_column(ForeignKey("projeto.id", ondelete="CASCADE"))
    descricao: Mapped[str] = mapped_column(String(150))
    data: Mapped[date] = mapped_column(server_default=func.current_date())
    valor: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
