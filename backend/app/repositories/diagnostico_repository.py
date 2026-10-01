"""Acesso às tabelas diagnostico e diagnostico_nota.

A coerência entre o diagnóstico e a manutenção ligada (resolvido só com
realizada, aberto só com agendada) é garantida por trigger (migration 0006);
aqui só ficam as consultas.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.entities.diagnostico import (
    FILTRO_ABERTOS,
    FILTRO_RESOLVIDOS,
    STATUS_EM_ABERTO,
    STATUS_ENCERRADOS,
    Diagnostico,
    DiagnosticoNota,
)
from app.entities.manutencao import Manutencao

# Mais grave primeiro.
ORDEM_DA_GRAVIDADE = case({"critica": 0, "alta": 1, "media": 2, "baixa": 3},
                          value=Diagnostico.gravidade, else_=4)


@dataclass(frozen=True)
class ManutencaoLigada:
    id: int
    descricao: str
    status: str
    data: date
    valor: Decimal


class DiagnosticoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, diagnostico_id: int) -> Diagnostico | None:
        return self._sessao.get(Diagnostico, diagnostico_id)

    @staticmethod
    def _filtro(veiculo_id: int, filtro: str | None) -> list:
        condicoes = [Diagnostico.veiculo_id == veiculo_id]
        if filtro == FILTRO_ABERTOS:
            condicoes.append(Diagnostico.status.in_(STATUS_EM_ABERTO))
        elif filtro == FILTRO_RESOLVIDOS:
            condicoes.append(Diagnostico.status.in_(STATUS_ENCERRADOS))
        return condicoes

    def contar(self, veiculo_id: int, filtro: str | None) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(Diagnostico).where(*self._filtro(veiculo_id, filtro))
        ) or 0

    def listar(self, veiculo_id: int, filtro: str | None, limite: int,
               deslocamento: int) -> list[Diagnostico]:
        """Abertos: mais graves primeiro, depois os mais antigos. Resolvidos: do
        mais recente para o mais antigo. Todos: os em aberto antes, depois pela
        data. O id desempata (ordem estável entre páginas)."""
        if filtro == FILTRO_ABERTOS:
            ordem = (ORDEM_DA_GRAVIDADE, Diagnostico.data_identificacao.asc(), Diagnostico.id.asc())
        elif filtro == FILTRO_RESOLVIDOS:
            ordem = (Diagnostico.data_resolucao.desc(), Diagnostico.id.desc())
        else:
            ordem = (Diagnostico.status.in_(STATUS_EM_ABERTO).desc(),
                     Diagnostico.data_identificacao.desc(), Diagnostico.id.desc())
        return list(self._sessao.scalars(
            select(Diagnostico).where(*self._filtro(veiculo_id, filtro))
            .order_by(*ordem).limit(limite).offset(deslocamento)
        ))

    def contar_notas(self, diagnostico_ids: list[int]) -> dict[int, int]:
        if not diagnostico_ids:
            return {}
        linhas = self._sessao.execute(
            select(DiagnosticoNota.diagnostico_id, func.count())
            .where(DiagnosticoNota.diagnostico_id.in_(diagnostico_ids))
            .group_by(DiagnosticoNota.diagnostico_id)
        )
        return {diagnostico_id: total for diagnostico_id, total in linhas}

    def manutencoes_ligadas(self, manutencao_ids: list[int]) -> dict[int, ManutencaoLigada]:
        if not manutencao_ids:
            return {}
        linhas = self._sessao.execute(
            select(Manutencao.id, Manutencao.descricao, Manutencao.status, Manutencao.data,
                   Manutencao.valor)
            .where(Manutencao.id.in_(manutencao_ids))
        )
        return {linha.id: ManutencaoLigada(*linha) for linha in linhas}

    def ligados_a_manutencao(self, manutencao_id: int) -> list[Diagnostico]:
        return list(self._sessao.scalars(
            select(Diagnostico).where(Diagnostico.manutencao_id == manutencao_id)
            .order_by(Diagnostico.id)
        ))

    def criar(self, veiculo_id: int, dados: dict) -> Diagnostico:
        diagnostico = Diagnostico(veiculo_id=veiculo_id, **dados)
        self._sessao.add(diagnostico)
        self._sessao.flush()
        return diagnostico

    def atualizar(self, diagnostico: Diagnostico, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(diagnostico, campo, valor)
        self._sessao.flush()

    def recarregar(self, diagnostico: Diagnostico) -> None:
        """Relê do banco (um trigger pode ter mudado a situação)."""
        self._sessao.refresh(diagnostico)

    def apagar(self, diagnostico: Diagnostico) -> None:
        """As anotações e as fotos saem junto (ON DELETE CASCADE no banco)."""
        self._sessao.delete(diagnostico)
        self._sessao.flush()

    # ------------------------------------------------------------------ notas
    def notas(self, diagnostico_id: int) -> list[DiagnosticoNota]:
        """Da mais recente para a mais antiga."""
        return list(self._sessao.scalars(
            select(DiagnosticoNota).where(DiagnosticoNota.diagnostico_id == diagnostico_id)
            .order_by(DiagnosticoNota.data.desc(), DiagnosticoNota.id.desc())
        ))

    def buscar_nota(self, nota_id: int) -> DiagnosticoNota | None:
        return self._sessao.get(DiagnosticoNota, nota_id)

    def criar_nota(self, diagnostico_id: int, data: date, texto: str) -> DiagnosticoNota:
        nota = DiagnosticoNota(diagnostico_id=diagnostico_id, data=data, texto=texto)
        self._sessao.add(nota)
        self._sessao.flush()
        return nota

    def apagar_nota(self, nota: DiagnosticoNota) -> None:
        self._sessao.delete(nota)
        self._sessao.flush()
