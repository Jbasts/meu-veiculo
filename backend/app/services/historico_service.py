"""Histórico integrado do veículo (PDF, página 17).

O que aparece
- Lançamentos financeiros efetivados, da view vw_historico (manutenção
  realizada, abastecimento, gasto pago pela data do pagamento, item de
  projeto), com o valor.
- Diagnósticos, na data em que o problema foi identificado, SEM valor: não
  entram em nenhum total. O custo de um problema é o da manutenção que o
  resolveu, que já aparece como lançamento (sem contar duas vezes).
- Manutenções agendadas e gastos pendentes não aparecem: ainda não
  aconteceram (ficam em Manutenção e em Finanças → A vencer).

Filtros
- Tipo: tudo, manutencao, abastecimento, gasto, projeto ou diagnostico.
- Período: últimos 12 meses (o mês atual e os 11 anteriores, inteiros, em
  America/Sao_Paulo), um ano, ou tudo.

Totais por mês: somados pelo PostgreSQL a partir da vw_historico, para o mês
inteiro (não só a página carregada), respeitando o filtro de tipo.
Paginação com ordem estável: data, tipo e id.
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable

from app.entities.historico import TIPOS_DO_HISTORICO, EventoHistorico, TotalDoMes
from app.entities.usuario import Usuario
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.erros import DadosInvalidos
from app.services.gasto_service import ANO_MAXIMO, ANO_MINIMO, intervalo_do_mes
from app.services.paginacao import limite_e_deslocamento

PERIODO_12_MESES = "12_meses"
PERIODO_ANO = "ano"
PERIODO_TUDO = "tudo"
PERIODOS = (PERIODO_12_MESES, PERIODO_ANO, PERIODO_TUDO)
TIPO_TUDO = "tudo"


@dataclass(frozen=True)
class PaginaHistorico:
    itens: list[EventoHistorico]
    total: int
    pagina: int
    por_pagina: int
    periodo: str
    ano: int | None
    inicio: date | None        # primeiro dia do período (None em "tudo")
    fim: date | None           # último dia do período, inclusive (None em "tudo")
    meses: list[TotalDoMes]    # soma de cada mês do período (diagnósticos fora)
    anos_disponiveis: list[int]


def doze_meses(hoje: date) -> tuple[date, date]:
    """(primeiro dia de 11 meses atrás, primeiro dia do mês que vem)."""
    indice = hoje.year * 12 + hoje.month - 1 - 11
    inicio = date(indice // 12, indice % 12 + 1, 1)
    _, fim = intervalo_do_mes(hoje.year, hoje.month)
    return inicio, fim


class HistoricoService:
    def __init__(self, veiculos, historico, *, hoje: Callable[[], date] = calendario.hoje):
        self._historico = historico
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _intervalo(self, periodo: str, ano: int | None) -> tuple[date | None, date | None]:
        if periodo == PERIODO_TUDO:
            return None, None
        if periodo == PERIODO_ANO:
            if ano is None or not ANO_MINIMO <= ano <= ANO_MAXIMO:
                raise DadosInvalidos("Escolha o ano.", campo="ano")
            return date(ano, 1, 1), date(ano + 1, 1, 1)
        return doze_meses(self._hoje())

    def listar(self, usuario: Usuario, veiculo_id: int, tipo: str | None = None,
               periodo: str = PERIODO_12_MESES, ano: int | None = None, pagina: int = 1,
               por_pagina: int = 50) -> PaginaHistorico:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if tipo == TIPO_TUDO:
            tipo = None
        if tipo is not None and tipo not in TIPOS_DO_HISTORICO:
            raise DadosInvalidos("Tipo de registro inválido.", campo="tipo")
        if periodo not in PERIODOS:
            raise DadosInvalidos("Período inválido.", campo="periodo")
        if periodo != PERIODO_ANO:
            ano = None
        inicio, fim = self._intervalo(periodo, ano)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return PaginaHistorico(
            itens=self._historico.eventos(veiculo.id, tipo, inicio, fim, limite, deslocamento),
            total=self._historico.contar(veiculo.id, tipo, inicio, fim),
            pagina=pagina, por_pagina=por_pagina, periodo=periodo, ano=ano,
            inicio=inicio, fim=date.fromordinal(fim.toordinal() - 1) if fim else None,
            meses=self._historico.totais_por_mes(veiculo.id, tipo, inicio, fim),
            anos_disponiveis=self._historico.anos(veiculo.id),
        )
