"""Acesso à tabela veiculo_foto (metadados; os arquivos ficam em arquivo_foto_repository)."""

from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.entities.veiculo_foto import VeiculoFoto


class FotoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, foto_id: int) -> VeiculoFoto | None:
        return self._sessao.get(VeiculoFoto, foto_id)

    def contar(self, veiculo_id: int) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(VeiculoFoto)
            .where(VeiculoFoto.veiculo_id == veiculo_id)
        ) or 0

    def listar(self, veiculo_id: int, limite: int, deslocamento: int) -> list[VeiculoFoto]:
        """Da foto mais recente para a mais antiga; o id desempata (ordem estável)."""
        return list(self._sessao.scalars(
            select(VeiculoFoto).where(VeiculoFoto.veiculo_id == veiculo_id)
            .order_by(VeiculoFoto.data_foto.desc(), VeiculoFoto.id.desc())
            .limit(limite).offset(deslocamento)
        ))

    def capas(self, veiculo_ids: list[int]) -> dict[int, int]:
        """veiculo_id -> id da foto de capa, só para os veículos que têm capa."""
        if not veiculo_ids:
            return {}
        linhas = self._sessao.execute(
            select(VeiculoFoto.veiculo_id, VeiculoFoto.id)
            .where(VeiculoFoto.veiculo_id.in_(veiculo_ids), VeiculoFoto.principal)
        )
        return {veiculo_id: foto_id for veiculo_id, foto_id in linhas}

    def criar(self, veiculo_id: int, arquivo: str, tipo_mime: str, tamanho_bytes: int,
              legenda: str | None, data_foto: date) -> VeiculoFoto:
        foto = VeiculoFoto(veiculo_id=veiculo_id, arquivo=arquivo, tipo_mime=tipo_mime,
                           tamanho_bytes=tamanho_bytes, legenda=legenda, data_foto=data_foto,
                           principal=False)
        self._sessao.add(foto)
        self._sessao.flush()
        return foto

    def atualizar(self, foto: VeiculoFoto, legenda: str | None, data_foto: date) -> None:
        foto.legenda = legenda
        foto.data_foto = data_foto
        self._sessao.flush()

    def definir_capa(self, veiculo_id: int, foto_id: int | None) -> None:
        """Tira a capa atual e, se foto_id for informado, marca a nova.

        Chame com a linha do veículo bloqueada (VeiculoRepository.bloquear):
        assim duas trocas simultâneas não se atropelam. O índice único
        veiculo_foto_uma_capa garante no banco que nunca há duas capas.
        """
        self._sessao.execute(
            update(VeiculoFoto)
            .where(VeiculoFoto.veiculo_id == veiculo_id, VeiculoFoto.principal)
            .values(principal=False).execution_options(synchronize_session="fetch")
        )
        if foto_id is not None:
            self._sessao.execute(
                update(VeiculoFoto)
                .where(VeiculoFoto.id == foto_id, VeiculoFoto.veiculo_id == veiculo_id)
                .values(principal=True).execution_options(synchronize_session="fetch")
            )

    def apagar(self, foto: VeiculoFoto) -> None:
        self._sessao.delete(foto)
        self._sessao.flush()

    def arquivos_registrados(self) -> set[str]:
        return set(self._sessao.scalars(select(VeiculoFoto.arquivo)))
