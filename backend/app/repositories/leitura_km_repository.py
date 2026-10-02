"""Acesso à tabela leitura_km (histórico de leituras do hodômetro)."""

from datetime import date

from sqlalchemy import Date, and_, cast, func, or_, select
from sqlalchemy.orm import Session

from app.entities.leitura_km import LeituraKm


class LeituraKmRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, leitura_id: int) -> LeituraKm | None:
        return self._sessao.get(LeituraKm, leitura_id)

    def contar(self, veiculo_id: int) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(LeituraKm).where(LeituraKm.veiculo_id == veiculo_id)
        ) or 0

    def listar(self, veiculo_id: int, limite: int, deslocamento: int) -> list[LeituraKm]:
        """Da leitura mais recente para a mais antiga; o id desempata (ordem estável)."""
        return list(self._sessao.scalars(
            select(LeituraKm).where(LeituraKm.veiculo_id == veiculo_id)
            .order_by(LeituraKm.data_leitura.desc().nulls_last(), LeituraKm.id.desc())
            .limit(limite).offset(deslocamento)
        ))

    def contar_validas(self, veiculo_id: int) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(LeituraKm)
            .where(LeituraKm.veiculo_id == veiculo_id, LeituraKm.anulada_em.is_(None))
        ) or 0

    def buscar_igual(self, veiculo_id: int, quilometragem: int, data_leitura: date,
                     origem: str) -> LeituraKm | None:
        return self._sessao.scalars(
            select(LeituraKm).where(
                LeituraKm.veiculo_id == veiculo_id, LeituraKm.anulada_em.is_(None),
                LeituraKm.quilometragem == quilometragem,
                LeituraKm.data_leitura == data_leitura, LeituraKm.origem == origem,
            ).limit(1)
        ).first()

    def conflitos(self, veiculo_id: int, quilometragem: int, data_leitura: date | None,
                  digitada_em: date | None = None, ignorar_id: int | None = None,
                  ignorar_origem: tuple[str, int] | None = None) -> list[LeituraKm]:
        """Leituras válidas que contradizem (quilometragem, data_leitura).

        O hodômetro só anda para a frente: uma leitura de um dia anterior não
        pode ser maior, e uma de um dia posterior não pode ser menor. No mesmo
        dia, qualquer ordem é aceita.

        Leitura sem data (herdada): só se sabe que foi feita até o dia em que
        foi gravada (criado_em). Ela só entra na comparação com datas a partir
        desse dia. Para conferir uma leitura sem data, passe data_leitura=None
        e digitada_em com o dia em que ela foi gravada.

        ignorar_origem=("manutencao", 12): não compara com a leitura gerada
        pelo próprio registro que está sendo editado.
        """
        gravada_em = cast(LeituraKm.criado_em, Date)
        if data_leitura is not None:
            contradiz = or_(
                and_(LeituraKm.data_leitura < data_leitura, LeituraKm.quilometragem > quilometragem),
                and_(LeituraKm.data_leitura > data_leitura, LeituraKm.quilometragem < quilometragem),
                and_(LeituraKm.data_leitura.is_(None), gravada_em <= data_leitura,
                     LeituraKm.quilometragem > quilometragem),
            )
        else:
            contradiz = and_(LeituraKm.data_leitura >= digitada_em,
                             LeituraKm.quilometragem < quilometragem)
        condicoes = [LeituraKm.veiculo_id == veiculo_id, LeituraKm.anulada_em.is_(None), contradiz]
        if ignorar_id is not None:
            condicoes.append(LeituraKm.id != ignorar_id)
        if ignorar_origem is not None:
            origem, origem_id = ignorar_origem
            condicoes.append(or_(LeituraKm.origem != origem, LeituraKm.origem_id.is_(None),
                                 LeituraKm.origem_id != origem_id))
        return list(self._sessao.scalars(
            select(LeituraKm).where(*condicoes)
            .order_by(LeituraKm.data_leitura.desc().nulls_last(), LeituraKm.id.desc()).limit(3)
        ))

    def primeira_e_ultima_com_data(self, veiculo_id: int) -> tuple[LeituraKm, LeituraKm] | None:
        """A leitura válida mais antiga e a mais recente que têm data (para o
        custo por km). Leituras sem data (herdadas) não entram: não dá para
        saber a que período pertencem."""
        base = select(LeituraKm).where(LeituraKm.veiculo_id == veiculo_id,
                                       LeituraKm.anulada_em.is_(None),
                                       LeituraKm.data_leitura.is_not(None))
        primeira = self._sessao.scalars(base.order_by(
            LeituraKm.data_leitura, LeituraKm.quilometragem, LeituraKm.id).limit(1)).first()
        if primeira is None:
            return None
        ultima = self._sessao.scalars(base.order_by(
            LeituraKm.data_leitura.desc(), LeituraKm.quilometragem.desc(),
            LeituraKm.id.desc()).limit(1)).first()
        return primeira, ultima

    def criar(self, veiculo_id: int, quilometragem: int, data_leitura: date | None,
              origem: str, corrige_id: int | None = None) -> LeituraKm:
        leitura = LeituraKm(veiculo_id=veiculo_id, quilometragem=quilometragem,
                            data_leitura=data_leitura, origem=origem, corrige_id=corrige_id)
        self._sessao.add(leitura)
        self._sessao.flush()
        return leitura

    def anular(self, leitura: LeituraKm, motivo: str | None) -> None:
        leitura.anulada_em = func.now()
        leitura.motivo_anulacao = motivo
        self._sessao.flush()
        self._sessao.refresh(leitura)
