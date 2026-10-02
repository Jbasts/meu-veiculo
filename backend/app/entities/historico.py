"""Linhas do histórico do veículo (tela Histórico).

Os lançamentos financeiros vêm da view vw_historico (SQL original, com o gasto
pago posicionado pela data do pagamento desde a migration 0007): manutenção
realizada, abastecimento, gasto pago e item de projeto, cada valor uma vez.

Os diagnósticos entram na lista como eventos SEM valor (valor None), na data
em que o problema foi identificado. Eles não entram em nenhum total: o custo
de um problema é o da manutenção que o resolveu, que já está na lista.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

TIPO_DIAGNOSTICO = "diagnostico"
# Tipos financeiros (os mesmos da vw_historico) + o diagnóstico.
TIPOS_DO_HISTORICO = ("manutencao", "abastecimento", "gasto", "projeto", TIPO_DIAGNOSTICO)


@dataclass(frozen=True)
class EventoHistorico:
    tipo: str                    # manutencao | abastecimento | gasto | projeto | diagnostico
    origem_id: int               # id na tabela de origem (item de projeto: id do item)
    data: date
    descricao: str               # texto da vw_historico (no diagnóstico, o título)
    valor: Decimal | None        # None no diagnóstico: não é despesa
    quilometragem: int | None
    # Detalhes para a tela montar o texto e o link (cada tipo usa os seus).
    sistema: str | None          # manutenção e diagnóstico
    oficina: str | None          # manutenção
    posto: str | None            # abastecimento
    combustivel: str | None      # abastecimento
    quantidade: Decimal | None   # abastecimento (litros, m³ ou kWh)
    categoria: str | None        # gasto
    descricao_gasto: str | None  # gasto (pode estar vazia)
    projeto_id: int | None       # item de projeto: o projeto a abrir
    projeto_nome: str | None
    item_descricao: str | None
    situacao: str | None         # diagnóstico: aberto | em_observacao | resolvido | descartado
    gravidade: str | None        # diagnóstico


@dataclass(frozen=True)
class TotalDoMes:
    """Soma dos lançamentos financeiros de um mês (diagnósticos não entram)."""

    ano: int
    mes: int
    total: Decimal
    quantidade: int
