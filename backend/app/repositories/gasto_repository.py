"""Acesso à tabela gasto e às despesas do período (view vw_despesa, migration 0007).

Período: mês, ano ou total. inicio/fim vazios = sem limite (todo o histórico).

O que conta como despesa efetivada (manutenção realizada, abastecimento,
gasto pago, item de projeto) é decidido pela view, num lugar só; aqui ficam
as consultas e as somas, feitas em numeric pelo PostgreSQL (sem float).
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.entities.gasto import Despesa, Gasto

SQL_TOTAIS_POR_CATEGORIA = text("""
    SELECT categoria, SUM(valor) AS total, COUNT(*) AS quantidade
      FROM vw_despesa
     WHERE veiculo_id = :veiculo_id AND (CAST(:inicio AS date) IS NULL OR data >= :inicio) AND (CAST(:fim AS date) IS NULL OR data < :fim)
     GROUP BY categoria
     ORDER BY SUM(valor) DESC, categoria
""")

SQL_LANCAMENTOS = text("""
    SELECT tipo, origem_id, data, categoria, descricao, valor, projeto_id
      FROM vw_despesa
     WHERE veiculo_id = :veiculo_id AND (CAST(:inicio AS date) IS NULL OR data >= :inicio) AND (CAST(:fim AS date) IS NULL OR data < :fim)
     ORDER BY data DESC, tipo, origem_id DESC
     LIMIT :limite OFFSET :deslocamento
""")

# Previsto para o período (não entra no total): manutenções agendadas e
# gastos pendentes que vencem no período.
SQL_PREVISTO = text("""
    SELECT
      (SELECT COALESCE(SUM(valor), 0)::numeric(12, 2) FROM manutencao
        WHERE veiculo_id = :veiculo_id AND status = 'agendada'
          AND (CAST(:inicio AS date) IS NULL OR data >= :inicio) AND (CAST(:fim AS date) IS NULL OR data < :fim)) AS manutencoes,
      (SELECT COUNT(*) FROM manutencao
        WHERE veiculo_id = :veiculo_id AND status = 'agendada'
          AND (CAST(:inicio AS date) IS NULL OR data >= :inicio) AND (CAST(:fim AS date) IS NULL OR data < :fim)) AS quantidade_manutencoes,
      (SELECT COALESCE(SUM(valor), 0)::numeric(12, 2) FROM gasto
        WHERE veiculo_id = :veiculo_id AND NOT pago
          AND (CAST(:inicio AS date) IS NULL OR data_vencimento >= :inicio) AND (CAST(:fim AS date) IS NULL OR data_vencimento < :fim)) AS gastos,
      (SELECT COUNT(*) FROM gasto
        WHERE veiculo_id = :veiculo_id AND NOT pago
          AND (CAST(:inicio AS date) IS NULL OR data_vencimento >= :inicio) AND (CAST(:fim AS date) IS NULL OR data_vencimento < :fim)) AS quantidade_gastos
""")


class GastoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, gasto_id: int) -> Gasto | None:
        return self._sessao.get(Gasto, gasto_id)

    def criar(self, veiculo_id: int, dados: dict) -> Gasto:
        gasto = Gasto(veiculo_id=veiculo_id, **dados)
        self._sessao.add(gasto)
        self._sessao.flush()
        return gasto

    def atualizar(self, gasto: Gasto, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(gasto, campo, valor)
        self._sessao.flush()

    def apagar(self, gasto: Gasto) -> None:
        self._sessao.delete(gasto)
        self._sessao.flush()

    def contar_pendentes(self, veiculo_id: int) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(Gasto)
            .where(Gasto.veiculo_id == veiculo_id, Gasto.pago.is_(False))
        ) or 0

    def contas_em_atraso(self, veiculo_id: int, hoje: date) -> tuple[int, Decimal, int]:
        """(vencidas, total das vencidas, que vencem hoje), só dos gastos pendentes."""
        vencida = Gasto.data_vencimento < hoje
        linha = self._sessao.execute(
            select(func.count().filter(vencida),
                   func.coalesce(func.sum(Gasto.valor).filter(vencida), 0),
                   func.count().filter(Gasto.data_vencimento == hoje))
            .where(Gasto.veiculo_id == veiculo_id, Gasto.pago.is_(False))
        ).one()
        return linha[0], Decimal(linha[1]).quantize(Decimal("0.01")), linha[2]

    def futuros(self, veiculo_id: int, hoje: date, limite: int) -> tuple[int, Decimal, list[Gasto]]:
        """Gastos futuros (pendentes que vencem hoje ou depois): (quantidade, total, os mais próximos)."""
        condicoes = (Gasto.veiculo_id == veiculo_id, Gasto.pago.is_(False), Gasto.data_vencimento >= hoje)
        quantidade, total = self._sessao.execute(
            select(func.count(), func.coalesce(func.sum(Gasto.valor), 0)).where(*condicoes)).one()
        proximos = list(self._sessao.scalars(
            select(Gasto).where(*condicoes).order_by(Gasto.data_vencimento, Gasto.id).limit(limite)))
        return quantidade, Decimal(total).quantize(Decimal("0.01")), proximos

    def pendentes(self, veiculo_id: int, limite: int, deslocamento: int) -> list[Gasto]:
        """Do vencimento mais antigo para o mais distante (vencidos primeiro)."""
        return list(self._sessao.scalars(
            select(Gasto).where(Gasto.veiculo_id == veiculo_id, Gasto.pago.is_(False))
            .order_by(Gasto.data_vencimento, Gasto.id).limit(limite).offset(deslocamento)
        ))


class FinancasRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def totais_por_categoria(self, veiculo_id: int, inicio: date | None,
                             fim: date | None) -> list[tuple[str, Decimal, int]]:
        """[(categoria, total, quantidade)], do maior total para o menor. fim é exclusivo."""
        linhas = self._sessao.execute(
            SQL_TOTAIS_POR_CATEGORIA, {"veiculo_id": veiculo_id, "inicio": inicio, "fim": fim})
        return [(l.categoria, l.total, l.quantidade) for l in linhas]

    def lancamentos(self, veiculo_id: int, inicio: date | None, fim: date | None, limite: int,
                    deslocamento: int) -> list[Despesa]:
        """Do mais recente para o mais antigo; tipo e id desempatam (ordem estável)."""
        linhas = self._sessao.execute(SQL_LANCAMENTOS, {
            "veiculo_id": veiculo_id, "inicio": inicio, "fim": fim, "limite": limite,
            "deslocamento": deslocamento}).mappings()
        return [Despesa(**linha) for linha in linhas]

    def previsto(self, veiculo_id: int, inicio: date | None, fim: date | None) -> dict:
        return dict(self._sessao.execute(
            SQL_PREVISTO, {"veiculo_id": veiculo_id, "inicio": inicio, "fim": fim}).mappings().one())
