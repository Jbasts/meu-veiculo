"""Acesso à tabela abastecimento."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.entities.abastecimento import Abastecimento


class AbastecimentoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, abastecimento_id: int) -> Abastecimento | None:
        return self._sessao.get(Abastecimento, abastecimento_id)

    def todos(self, veiculo_id: int) -> list[Abastecimento]:
        """Todos os abastecimentos do veículo na ordem do consumo: (data, quilometragem, id)."""
        return list(self._sessao.scalars(
            select(Abastecimento).where(Abastecimento.veiculo_id == veiculo_id)
            .order_by(Abastecimento.data, Abastecimento.quilometragem, Abastecimento.id)
        ))

    def postos_recentes(self, veiculo_id: int, limite: int = 5) -> list[str]:
        """Nomes de posto usados por último (sem repetir), para os atalhos do formulário."""
        ultimo = func.max(Abastecimento.data).label("ultimo")
        return list(self._sessao.scalars(
            select(Abastecimento.posto)
            .where(Abastecimento.veiculo_id == veiculo_id, Abastecimento.posto.is_not(None))
            .group_by(Abastecimento.posto)
            .order_by(ultimo.desc(), Abastecimento.posto).limit(limite)
        ))

    def criar(self, veiculo_id: int, dados: dict) -> Abastecimento:
        abastecimento = Abastecimento(veiculo_id=veiculo_id, **dados)
        self._sessao.add(abastecimento)
        self._sessao.flush()
        return abastecimento

    def atualizar(self, abastecimento: Abastecimento, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(abastecimento, campo, valor)
        self._sessao.flush()

    def apagar(self, abastecimento: Abastecimento) -> None:
        """A leitura do hodômetro dele sai junto (trigger da migration 0003)."""
        self._sessao.delete(abastecimento)
        self._sessao.flush()
