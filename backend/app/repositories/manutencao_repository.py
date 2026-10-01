"""Acesso às tabelas plano_manutencao e manutencao e à situação calculada pelo banco.

A classificação (atrasada, próxima, em dia, sem base) não é feita em Python:
vem da view vw_situacao_manutencao e da função classificar_prazo, para a
regra existir num lugar só.
"""

from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from app.entities.manutencao import (
    STATUS_AGENDADA,
    STATUS_REALIZADA,
    TIPO_AGENDADA,
    TIPO_LEMBRETE,
    TIPO_PLANO,
    Manutencao,
    ManutencaoItem,
    Pendencia,
    PlanoManutencao,
    SituacaoPlano,
)

SQL_SITUACAO_DOS_PLANOS = text("""
    SELECT plano_id, situacao, referencia_data, referencia_km, proxima_data, proxima_km,
           km_restantes, dias_restantes
      FROM vw_situacao_manutencao
     WHERE veiculo_id = :veiculo_id
""")

# Planos ativos, cada um com a manutenção agendada mais próxima (se houver).
SQL_PENDENCIAS_DE_PLANOS = text("""
    SELECT s.plano_id, s.situacao, s.nome, s.sistema, s.proxima_data, s.proxima_km,
           s.dias_restantes, s.km_restantes, s.intervalo_km, s.intervalo_meses,
           a.id AS agendada_id, a.data AS agendada_data
      FROM vw_situacao_manutencao s
      LEFT JOIN LATERAL (
            SELECT m.id, m.data FROM manutencao m
             WHERE m.plano_id = s.plano_id AND m.status = 'agendada'
             ORDER BY m.data, m.id LIMIT 1
      ) a ON TRUE
     WHERE s.veiculo_id = :veiculo_id
""")

# Agendadas que não pertencem a um plano ativo (as de plano ativo aparecem
# junto do plano, para a mesma obrigação não gerar dois alertas).
SQL_AGENDADAS_SEM_PLANO_ATIVO = text("""
    SELECT m.id, m.descricao, m.sistema, m.data, m.quilometragem,
           m.data - CURRENT_DATE AS dias_restantes,
           m.quilometragem - v.quilometragem AS km_restantes,
           classificar_prazo(m.data, m.quilometragem, v.quilometragem, CURRENT_DATE, FALSE) AS situacao
      FROM manutencao m
      JOIN veiculo v ON v.id = m.veiculo_id
      LEFT JOIN plano_manutencao p ON p.id = m.plano_id
     WHERE m.veiculo_id = :veiculo_id AND m.status = 'agendada'
       AND (m.plano_id IS NULL OR NOT p.ativo)
""")

# Lembrete manual ("próxima em...") de manutenção avulsa realizada.
SQL_LEMBRETES = text("""
    SELECT m.id, m.descricao, m.sistema, m.proxima_data, m.proxima_km,
           m.proxima_data - CURRENT_DATE AS dias_restantes,
           m.proxima_km - v.quilometragem AS km_restantes,
           classificar_prazo(m.proxima_data, m.proxima_km, v.quilometragem, CURRENT_DATE) AS situacao
      FROM manutencao m
      JOIN veiculo v ON v.id = m.veiculo_id
     WHERE m.veiculo_id = :veiculo_id AND m.status = 'realizada' AND m.plano_id IS NULL
       AND (m.proxima_data IS NOT NULL OR m.proxima_km IS NOT NULL)
""")


class PlanoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, plano_id: int) -> PlanoManutencao | None:
        return self._sessao.get(PlanoManutencao, plano_id)

    def listar(self, veiculo_id: int) -> list[PlanoManutencao]:
        """Ativos primeiro; depois por nome (o id desempata)."""
        return list(self._sessao.scalars(
            select(PlanoManutencao).where(PlanoManutencao.veiculo_id == veiculo_id)
            .order_by(PlanoManutencao.ativo.desc(), func.lower(PlanoManutencao.nome),
                      PlanoManutencao.id)
        ))

    def situacoes(self, veiculo_id: int) -> dict[int, SituacaoPlano]:
        """plano_id -> situação calculada pelo banco (só planos ativos)."""
        linhas = self._sessao.execute(SQL_SITUACAO_DOS_PLANOS, {"veiculo_id": veiculo_id}).mappings()
        return {linha["plano_id"]: SituacaoPlano(**linha) for linha in linhas}

    def criar(self, veiculo_id: int, dados: dict) -> PlanoManutencao:
        plano = PlanoManutencao(veiculo_id=veiculo_id, ativo=True, **dados)
        self._sessao.add(plano)
        self._sessao.flush()
        return plano

    def atualizar(self, plano: PlanoManutencao, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(plano, campo, valor)
        self._sessao.flush()

    def apagar(self, plano: PlanoManutencao) -> None:
        """As manutenções do plano ficam como avulsas (ON DELETE SET NULL no banco)."""
        self._sessao.delete(plano)
        self._sessao.flush()
        self._sessao.expire_all()


class ManutencaoRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def buscar(self, manutencao_id: int) -> Manutencao | None:
        return self._sessao.get(Manutencao, manutencao_id)

    def _filtro(self, veiculo_id: int, status: str | None):
        condicoes = [Manutencao.veiculo_id == veiculo_id]
        if status is not None:
            condicoes.append(Manutencao.status == status)
        return condicoes

    def contar(self, veiculo_id: int, status: str | None) -> int:
        return self._sessao.scalar(
            select(func.count()).select_from(Manutencao).where(*self._filtro(veiculo_id, status))
        ) or 0

    def listar(self, veiculo_id: int, status: str | None, limite: int,
               deslocamento: int) -> list[Manutencao]:
        """Agendadas: da mais próxima para a mais distante. Demais: da mais recente
        para a mais antiga. O id desempata (ordem estável entre páginas)."""
        if status == STATUS_AGENDADA:
            ordem = (Manutencao.data.asc(), Manutencao.id.asc())
        else:
            ordem = (Manutencao.data.desc(), Manutencao.id.desc())
        return list(self._sessao.scalars(
            select(Manutencao).where(*self._filtro(veiculo_id, status))
            .order_by(*ordem).limit(limite).offset(deslocamento)
        ))

    def agendada_do_plano(self, plano_id: int, ignorar_id: int | None = None) -> Manutencao | None:
        condicoes = [Manutencao.plano_id == plano_id, Manutencao.status == STATUS_AGENDADA]
        if ignorar_id is not None:
            condicoes.append(Manutencao.id != ignorar_id)
        return self._sessao.scalars(select(Manutencao).where(*condicoes).limit(1)).first()

    def criar(self, veiculo_id: int, dados: dict) -> Manutencao:
        manutencao = Manutencao(veiculo_id=veiculo_id, **dados)
        self._sessao.add(manutencao)
        self._sessao.flush()
        return manutencao

    def atualizar(self, manutencao: Manutencao, dados: dict) -> None:
        for campo, valor in dados.items():
            setattr(manutencao, campo, valor)
        self._sessao.flush()

    def apagar(self, manutencao: Manutencao) -> None:
        """Os itens saem junto (ON DELETE CASCADE no banco)."""
        self._sessao.delete(manutencao)
        self._sessao.flush()

    def com_garantia(self, veiculo_id: int, sistema: str) -> list[Manutencao]:
        """Manutenções realizadas do sistema que têm algum limite de garantia informado."""
        return list(self._sessao.scalars(
            select(Manutencao).where(
                Manutencao.veiculo_id == veiculo_id, Manutencao.sistema == sistema,
                Manutencao.status == STATUS_REALIZADA,
                (Manutencao.garantia_ate.is_not(None)) | (Manutencao.garantia_km.is_not(None)),
            ).order_by(Manutencao.data.desc(), Manutencao.id.desc())
        ))

    def itens(self, manutencao_id: int) -> list[ManutencaoItem]:
        """Peças e mão de obra, na ordem em que foram informadas."""
        return list(self._sessao.scalars(
            select(ManutencaoItem).where(ManutencaoItem.manutencao_id == manutencao_id)
            .order_by(ManutencaoItem.id)
        ))

    def substituir_itens(self, manutencao_id: int, itens: list[dict]) -> None:
        """Troca a lista inteira de itens da manutenção. O total (manutencao.valor)
        precisa ser gravado na mesma transação: o banco confere no fim dela."""
        self._sessao.execute(
            delete(ManutencaoItem).where(ManutencaoItem.manutencao_id == manutencao_id))
        self._sessao.add_all(ManutencaoItem(manutencao_id=manutencao_id, **item) for item in itens)
        self._sessao.flush()

    def pendencias(self, veiculo_id: int) -> list[Pendencia]:
        """Planos ativos, agendadas sem plano ativo e lembretes, já classificados."""
        parametros = {"veiculo_id": veiculo_id}
        itens: list[Pendencia] = []
        for l in self._sessao.execute(SQL_PENDENCIAS_DE_PLANOS, parametros).mappings():
            itens.append(Pendencia(
                tipo=TIPO_PLANO, situacao=l["situacao"], titulo=l["nome"], sistema=l["sistema"],
                plano_id=l["plano_id"], manutencao_id=None, proxima_data=l["proxima_data"],
                proxima_km=l["proxima_km"], dias_restantes=l["dias_restantes"],
                km_restantes=l["km_restantes"], intervalo_km=l["intervalo_km"],
                intervalo_meses=l["intervalo_meses"], agendada_id=l["agendada_id"],
                agendada_data=l["agendada_data"],
            ))
        for l in self._sessao.execute(SQL_AGENDADAS_SEM_PLANO_ATIVO, parametros).mappings():
            itens.append(Pendencia(
                tipo=TIPO_AGENDADA, situacao=l["situacao"], titulo=l["descricao"],
                sistema=l["sistema"], plano_id=None, manutencao_id=l["id"],
                proxima_data=l["data"], proxima_km=l["quilometragem"],
                dias_restantes=l["dias_restantes"], km_restantes=l["km_restantes"],
            ))
        for l in self._sessao.execute(SQL_LEMBRETES, parametros).mappings():
            itens.append(Pendencia(
                tipo=TIPO_LEMBRETE, situacao=l["situacao"], titulo=l["descricao"],
                sistema=l["sistema"], plano_id=None, manutencao_id=l["id"],
                proxima_data=l["proxima_data"], proxima_km=l["proxima_km"],
                dias_restantes=l["dias_restantes"], km_restantes=l["km_restantes"],
            ))
        return itens
