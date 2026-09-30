"""Acesso à tabela veiculo_foto (metadados; os arquivos ficam em arquivo_foto_repository)."""

from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.entities.veiculo_foto import VeiculoFoto

VINCULO_MANUTENCAO = "manutencao"
VINCULO_NENHUM = "nenhum"


class FotoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, foto_id: int) -> VeiculoFoto | None:
        return self._sessao.get(VeiculoFoto, foto_id)

    @staticmethod
    def _filtro(veiculo_id: int, vinculo: str | None, manutencao_id: int | None) -> list:
        """vinculo: None (todas), "manutencao" ou "nenhum"; manutencao_id: só as daquela manutenção."""
        condicoes = [VeiculoFoto.veiculo_id == veiculo_id]
        if manutencao_id is not None:
            condicoes.append(VeiculoFoto.manutencao_id == manutencao_id)
        if vinculo == VINCULO_MANUTENCAO:
            condicoes.append(VeiculoFoto.manutencao_id.is_not(None))
        elif vinculo == VINCULO_NENHUM:
            condicoes += [VeiculoFoto.manutencao_id.is_(None), VeiculoFoto.diagnostico_id.is_(None),
                          VeiculoFoto.projeto_id.is_(None)]
        return condicoes

    def contar(self, veiculo_id: int, vinculo: str | None = None,
               manutencao_id: int | None = None) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(VeiculoFoto)
            .where(*self._filtro(veiculo_id, vinculo, manutencao_id))
        ) or 0

    def listar(self, veiculo_id: int, limite: int, deslocamento: int, vinculo: str | None = None,
               manutencao_id: int | None = None) -> list[VeiculoFoto]:
        """Da foto mais recente para a mais antiga; o id desempata (ordem estável)."""
        return list(self._sessao.scalars(
            select(VeiculoFoto).where(*self._filtro(veiculo_id, vinculo, manutencao_id))
            .order_by(VeiculoFoto.data_foto.desc(), VeiculoFoto.id.desc())
            .limit(limite).offset(deslocamento)
        ))

    def arquivos_da_manutencao(self, manutencao_id: int) -> list[str]:
        """Caminhos dos arquivos das fotos ligadas a uma manutenção."""
        return list(self._sessao.scalars(
            select(VeiculoFoto.arquivo).where(VeiculoFoto.manutencao_id == manutencao_id)
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
              legenda: str | None, data_foto: date,
              manutencao_id: int | None = None) -> VeiculoFoto:
        foto = VeiculoFoto(veiculo_id=veiculo_id, arquivo=arquivo, tipo_mime=tipo_mime,
                           tamanho_bytes=tamanho_bytes, legenda=legenda, data_foto=data_foto,
                           principal=False, manutencao_id=manutencao_id)
        self._sessao.add(foto)
        self._sessao.flush()
        return foto

    def atualizar(self, foto: VeiculoFoto, legenda: str | None, data_foto: date,
                  manutencao_id: int | None) -> None:
        foto.legenda = legenda
        foto.data_foto = data_foto
        foto.manutencao_id = manutencao_id
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
