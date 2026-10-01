"""Acesso às tabelas projeto e projeto_item, e às fotos de antes/depois dos projetos."""

from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.entities.projeto import (
    ANTES,
    CANCELADO,
    CONCLUIDO,
    DEPOIS,
    EM_ANDAMENTO,
    PLANEJADO,
    Projeto,
    ProjetoItem,
)
from app.entities.veiculo_foto import VeiculoFoto

FILTRO_TODOS = "todos"

# Em andamento primeiro, depois planejados, concluídos e cancelados.
ORDEM_DO_STATUS = case({EM_ANDAMENTO: 0, PLANEJADO: 1, CONCLUIDO: 2, CANCELADO: 3},
                       value=Projeto.status, else_=4)


class ProjetoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    # ------------------------------------------------------------------ projetos
    def buscar(self, projeto_id: int) -> Projeto | None:
        return self._sessao.get(Projeto, projeto_id)

    @staticmethod
    def _filtro(veiculo_id: int, filtro: str) -> list:
        condicoes = [Projeto.veiculo_id == veiculo_id]
        if filtro != FILTRO_TODOS:
            condicoes.append(Projeto.status == filtro)
        return condicoes

    def contar(self, veiculo_id: int, filtro: str) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(Projeto).where(*self._filtro(veiculo_id, filtro))) or 0

    def contar_por_status(self, veiculo_id: int) -> dict[str, int]:
        linhas = self._sessao.execute(
            select(Projeto.status, func.count()).where(Projeto.veiculo_id == veiculo_id)
            .group_by(Projeto.status))
        return {status: total for status, total in linhas}

    def listar(self, veiculo_id: int, filtro: str, limite: int, deslocamento: int) -> list[Projeto]:
        """Em andamento, planejados, concluídos (mais recente primeiro) e cancelados; o id desempata."""
        return list(self._sessao.scalars(
            select(Projeto).where(*self._filtro(veiculo_id, filtro))
            .order_by(ORDEM_DO_STATUS, Projeto.data_conclusao.desc().nulls_last(),
                      Projeto.data_prevista.asc().nulls_last(), Projeto.id.desc())
            .limit(limite).offset(deslocamento)
        ))

    def totais(self, projeto_ids: list[int]) -> dict[int, tuple[Decimal, int]]:
        """projeto_id -> (soma dos itens, quantidade de itens), somados em numeric pelo banco."""
        if not projeto_ids:
            return {}
        linhas = self._sessao.execute(
            select(ProjetoItem.projeto_id, func.sum(ProjetoItem.valor), func.count())
            .where(ProjetoItem.projeto_id.in_(projeto_ids)).group_by(ProjetoItem.projeto_id))
        return {pid: (total, n) for pid, total, n in linhas}

    def fotos_de_antes_e_depois(self, projeto_ids: list[int]) -> dict[int, dict[str, list[int]]]:
        """projeto_id -> {"antes": [ids], "depois": [ids]}, cada lista da foto mais antiga para a
        mais nova (a primeira é a que aparece no cartão)."""
        if not projeto_ids:
            return {}
        linhas = self._sessao.execute(
            select(VeiculoFoto.projeto_id, VeiculoFoto.momento, VeiculoFoto.id)
            .where(VeiculoFoto.projeto_id.in_(projeto_ids), VeiculoFoto.momento.in_((ANTES, DEPOIS)))
            .order_by(VeiculoFoto.data_foto, VeiculoFoto.id))
        resultado: dict[int, dict[str, list[int]]] = {}
        for pid, momento, foto_id in linhas:
            resultado.setdefault(pid, {ANTES: [], DEPOIS: []})[momento].append(foto_id)
        return resultado

    def contar_fotos(self, projeto_id: int) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(VeiculoFoto).where(VeiculoFoto.projeto_id == projeto_id)) or 0

    def arquivos_das_fotos(self, projeto_id: int) -> list[str]:
        return list(self._sessao.scalars(
            select(VeiculoFoto.arquivo).where(VeiculoFoto.projeto_id == projeto_id)))

    def criar(self, veiculo_id: int, dados: dict) -> Projeto:
        projeto = Projeto(veiculo_id=veiculo_id, **dados)
        self._sessao.add(projeto)
        self._sessao.flush()
        return projeto

    def atualizar(self, projeto: Projeto, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(projeto, campo, valor)
        self._sessao.flush()

    def apagar(self, projeto: Projeto) -> None:
        """Os itens e as fotos saem junto (ON DELETE CASCADE no banco)."""
        self._sessao.delete(projeto)
        self._sessao.flush()

    # --------------------------------------------------------------------- itens
    def itens(self, projeto_id: int) -> list[ProjetoItem]:
        """Do mais antigo para o mais novo, como no PDF."""
        return list(self._sessao.scalars(
            select(ProjetoItem).where(ProjetoItem.projeto_id == projeto_id)
            .order_by(ProjetoItem.data, ProjetoItem.id)))

    def buscar_item(self, item_id: int) -> ProjetoItem | None:
        return self._sessao.get(ProjetoItem, item_id)

    def criar_item(self, projeto_id: int, dados: dict) -> ProjetoItem:
        item = ProjetoItem(projeto_id=projeto_id, **dados)
        self._sessao.add(item)
        self._sessao.flush()
        return item

    def atualizar_item(self, item: ProjetoItem, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(item, campo, valor)
        self._sessao.flush()

    def apagar_item(self, item: ProjetoItem) -> None:
        self._sessao.delete(item)
        self._sessao.flush()
