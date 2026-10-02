"""Acesso às tabelas veiculo_foto (metadados) e foto_conteudo (a imagem)."""

from datetime import date

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.entities.veiculo_foto import FotoConteudo, VeiculoFoto

VINCULO_MANUTENCAO = "manutencao"
VINCULO_DIAGNOSTICO = "diagnostico"
VINCULO_PROJETO = "projeto"
VINCULO_NENHUM = "nenhum"


class FotoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, foto_id: int) -> VeiculoFoto | None:
        return self._sessao.get(VeiculoFoto, foto_id)

    @staticmethod
    def _filtro(veiculo_id: int, vinculo: str | None, manutencao_id: int | None,
                diagnostico_id: int | None = None, projeto_id: int | None = None,
                momento: str | None = None) -> list:
        """vinculo: None (todas), "manutencao", "diagnostico", "projeto" ou "nenhum";
        manutencao_id / diagnostico_id / projeto_id: só as daquele registro;
        momento: só as de antes ou de depois."""
        condicoes = [VeiculoFoto.veiculo_id == veiculo_id]
        if projeto_id is not None:
            condicoes.append(VeiculoFoto.projeto_id == projeto_id)
        if momento is not None:
            condicoes.append(VeiculoFoto.momento == momento)
        if manutencao_id is not None:
            condicoes.append(VeiculoFoto.manutencao_id == manutencao_id)
        if diagnostico_id is not None:
            condicoes.append(VeiculoFoto.diagnostico_id == diagnostico_id)
        if vinculo == VINCULO_MANUTENCAO:
            condicoes.append(VeiculoFoto.manutencao_id.is_not(None))
        elif vinculo == VINCULO_DIAGNOSTICO:
            condicoes.append(VeiculoFoto.diagnostico_id.is_not(None))
        elif vinculo == VINCULO_PROJETO:
            condicoes.append(VeiculoFoto.projeto_id.is_not(None))
        elif vinculo == VINCULO_NENHUM:
            condicoes += [VeiculoFoto.manutencao_id.is_(None), VeiculoFoto.diagnostico_id.is_(None),
                          VeiculoFoto.projeto_id.is_(None)]
        return condicoes

    def contar(self, veiculo_id: int, vinculo: str | None = None,
               manutencao_id: int | None = None, diagnostico_id: int | None = None,
               projeto_id: int | None = None, momento: str | None = None) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(VeiculoFoto)
            .where(*self._filtro(veiculo_id, vinculo, manutencao_id, diagnostico_id, projeto_id,
                                 momento))
        ) or 0

    def listar(self, veiculo_id: int, limite: int, deslocamento: int, vinculo: str | None = None,
               manutencao_id: int | None = None, diagnostico_id: int | None = None,
               projeto_id: int | None = None, momento: str | None = None) -> list[VeiculoFoto]:
        """Da foto mais recente para a mais antiga; o id desempata (ordem estável)."""
        return list(self._sessao.scalars(
            select(VeiculoFoto).where(*self._filtro(veiculo_id, vinculo, manutencao_id,
                                                    diagnostico_id, projeto_id, momento))
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
              legenda: str | None, data_foto: date,
              manutencao_id: int | None = None, diagnostico_id: int | None = None,
              projeto_id: int | None = None, momento: str | None = None) -> VeiculoFoto:
        foto = VeiculoFoto(veiculo_id=veiculo_id, arquivo=arquivo, tipo_mime=tipo_mime,
                           tamanho_bytes=tamanho_bytes, legenda=legenda, data_foto=data_foto,
                           principal=False, manutencao_id=manutencao_id,
                           diagnostico_id=diagnostico_id, projeto_id=projeto_id, momento=momento)
        self._sessao.add(foto)
        self._sessao.flush()
        return foto

    def atualizar(self, foto: VeiculoFoto, legenda: str | None, data_foto: date,
                  manutencao_id: int | None, diagnostico_id: int | None = None,
                  projeto_id: int | None = None, momento: str | None = None) -> None:
        foto.legenda = legenda
        foto.data_foto = data_foto
        foto.manutencao_id = manutencao_id
        foto.diagnostico_id = diagnostico_id
        foto.projeto_id = projeto_id
        foto.momento = momento
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

    # ----------------------------------------------------------- conteúdo
    def salvar_conteudo(self, foto_id: int, dados: bytes) -> None:
        self._sessao.add(FotoConteudo(foto_id=foto_id, dados=dados))
        self._sessao.flush()

    def conteudo(self, foto_id: int) -> bytes | None:
        """Os bytes da imagem, ou None se a foto não tem conteúdo (arquivo perdido antes da 0013)."""
        return self._sessao.scalar(select(FotoConteudo.dados).where(FotoConteudo.foto_id == foto_id))

    def sem_conteudo(self) -> list[VeiculoFoto]:
        """Fotos de todos os veículos que ainda não têm a imagem no banco."""
        return list(self._sessao.scalars(
            select(VeiculoFoto)
            .where(~select(FotoConteudo.foto_id).where(FotoConteudo.foto_id == VeiculoFoto.id).exists())
            .order_by(VeiculoFoto.id)
        ))

    def arquivos_registrados(self) -> set[str]:
        return set(self._sessao.scalars(select(VeiculoFoto.arquivo)))
