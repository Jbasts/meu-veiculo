"""Consultas da tela Histórico.

Lançamentos financeiros: view vw_historico (a finalidade dela não muda: só o
que foi efetivado — manutenção realizada, abastecimento, gasto pago, item de
projeto). Diagnósticos: tabela diagnostico, acrescentados aqui como eventos
sem valor. Os totais por mês somam só a vw_historico.

Período: inicio (inclusive) e fim (exclusivo); vazios = sem limite.
Ordem estável: data (mais recente primeiro), tipo e id de origem.
"""

from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.entities.historico import TIPO_DIAGNOSTICO, EventoHistorico, TotalDoMes



def filtro_periodo(coluna: str) -> str:
    return (f"(CAST(:inicio AS date) IS NULL OR {coluna} >= :inicio)"
            f" AND (CAST(:fim AS date) IS NULL OR {coluna} < :fim)")


SQL_EVENTOS = f"""
    WITH eventos AS (
        SELECT veiculo_id, data, tipo, descricao, valor, quilometragem, origem_id
          FROM vw_historico
         WHERE veiculo_id = :veiculo_id
        UNION ALL
        SELECT veiculo_id, data_identificacao, '{TIPO_DIAGNOSTICO}', titulo::text,
               NULL::numeric, quilometragem, id
          FROM diagnostico
         WHERE veiculo_id = :veiculo_id
    )
"""

SQL_FILTRO = f"""
     WHERE {filtro_periodo("e.data")}
       AND (CAST(:tipo AS text) IS NULL OR e.tipo = :tipo)
"""

SQL_LISTA = text(SQL_EVENTOS + """
    SELECT e.tipo, e.origem_id, e.data, e.descricao, e.valor, e.quilometragem,
           COALESCE(m.sistema, d.sistema) AS sistema, m.oficina,
           a.posto, a.combustivel, a.litros AS quantidade,
           g.categoria, g.descricao AS descricao_gasto,
           i.projeto_id, p.nome AS projeto_nome, i.descricao AS item_descricao,
           d.status AS situacao, d.gravidade
      FROM eventos e
      LEFT JOIN manutencao m ON e.tipo = 'manutencao' AND m.id = e.origem_id
      LEFT JOIN abastecimento a ON e.tipo = 'abastecimento' AND a.id = e.origem_id
      LEFT JOIN gasto g ON e.tipo = 'gasto' AND g.id = e.origem_id
      LEFT JOIN projeto_item i ON e.tipo = 'projeto' AND i.id = e.origem_id
      LEFT JOIN projeto p ON p.id = i.projeto_id
      LEFT JOIN diagnostico d ON e.tipo = 'diagnostico' AND d.id = e.origem_id
""" + SQL_FILTRO + """
     ORDER BY e.data DESC, e.tipo, e.origem_id DESC
     LIMIT :limite OFFSET :deslocamento
""")

SQL_CONTAR = text(SQL_EVENTOS + "SELECT COUNT(*) FROM eventos e" + SQL_FILTRO)

# Diagnósticos ficam de fora das somas (não são despesa).
SQL_MESES = text(f"""
    SELECT CAST(EXTRACT(YEAR FROM data) AS int) AS ano, CAST(EXTRACT(MONTH FROM data) AS int) AS mes,
           SUM(valor) AS total, COUNT(*) AS quantidade
      FROM vw_historico
     WHERE veiculo_id = :veiculo_id AND {filtro_periodo("data")}
       AND (CAST(:tipo AS text) IS NULL OR tipo = :tipo)
     GROUP BY 1, 2
     ORDER BY 1 DESC, 2 DESC
""")


SQL_ANOS = text(SQL_EVENTOS + """
    SELECT DISTINCT CAST(EXTRACT(YEAR FROM data) AS int) AS ano FROM eventos ORDER BY ano DESC
""")


class HistoricoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    @staticmethod
    def _parametros(veiculo_id: int, tipo: str | None, inicio: date | None,
                    fim: date | None) -> dict:
        return {"veiculo_id": veiculo_id, "tipo": tipo, "inicio": inicio, "fim": fim}

    def eventos(self, veiculo_id: int, tipo: str | None, inicio: date | None, fim: date | None,
                limite: int, deslocamento: int) -> list[EventoHistorico]:
        linhas = self._sessao.execute(SQL_LISTA, {
            **self._parametros(veiculo_id, tipo, inicio, fim), "limite": limite,
            "deslocamento": deslocamento}).mappings()
        return [EventoHistorico(**linha) for linha in linhas]

    def contar(self, veiculo_id: int, tipo: str | None, inicio: date | None,
               fim: date | None) -> int:
        return self._sessao.execute(
            SQL_CONTAR, self._parametros(veiculo_id, tipo, inicio, fim)).scalar() or 0

    def anos(self, veiculo_id: int) -> list[int]:
        """Anos com algum registro (para o seletor de período), do mais recente."""
        return list(self._sessao.execute(SQL_ANOS, {"veiculo_id": veiculo_id}).scalars())

    def totais_por_mes(self, veiculo_id: int, tipo: str | None, inicio: date | None,
                       fim: date | None) -> list[TotalDoMes]:
        """Do mês mais recente para o mais antigo. tipo 'diagnostico' não tem soma (lista vazia)."""
        if tipo == TIPO_DIAGNOSTICO:
            return []
        linhas = self._sessao.execute(
            SQL_MESES, self._parametros(veiculo_id, tipo, inicio, fim)).mappings()
        return [TotalDoMes(**linha) for linha in linhas]
