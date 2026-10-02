"""Acesso à tabela medicao_tanque (marcações do tanque sem abastecer)."""

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.entities.medicao_tanque import MedicaoTanque


class MedicaoTanqueRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, medicao_id: int) -> MedicaoTanque | None:
        return self._sessao.get(MedicaoTanque, medicao_id)

    def todas(self, veiculo_id: int) -> list[MedicaoTanque]:
        """Todas as marcações do veículo, da mais antiga para a mais recente."""
        return list(self._sessao.scalars(
            select(MedicaoTanque).where(MedicaoTanque.veiculo_id == veiculo_id)
            .order_by(MedicaoTanque.data, MedicaoTanque.quilometragem, MedicaoTanque.id)
        ))

    def existe_desde(self, veiculo_id: int, desde: date) -> bool:
        return bool(self._sessao.scalar(
            select(func.count()).select_from(MedicaoTanque)
            .where(MedicaoTanque.veiculo_id == veiculo_id, MedicaoTanque.data >= desde)
        ))

    def criar(self, veiculo_id: int, dados: dict) -> MedicaoTanque:
        medicao = MedicaoTanque(veiculo_id=veiculo_id, **dados)
        self._sessao.add(medicao)
        self._sessao.flush()
        return medicao

    def atualizar(self, medicao: MedicaoTanque, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(medicao, campo, valor)
        self._sessao.flush()

    def apagar(self, medicao: MedicaoTanque) -> None:
        """A leitura do hodômetro dela sai junto (trigger da migration 0012)."""
        self._sessao.delete(medicao)
        self._sessao.flush()
