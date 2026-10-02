// Formato de backend/app/schemas/historico_schema.py (tela Histórico).

export type TipoEvento = "manutencao" | "abastecimento" | "gasto" | "projeto" | "diagnostico";
export type FiltroHistorico = "tudo" | TipoEvento;
export type PeriodoHistorico = "12_meses" | "ano" | "tudo";

/** Filtros da tela, na ordem do PDF (Tudo, Manutenção, Combustível, Gastos...). */
export const FILTROS_HISTORICO: { valor: FiltroHistorico; rotulo: string }[] = [
  { valor: "tudo", rotulo: "Tudo" },
  { valor: "manutencao", rotulo: "Manutenção" },
  { valor: "abastecimento", rotulo: "Combustível" },
  { valor: "gasto", rotulo: "Gastos" },
  { valor: "projeto", rotulo: "Projetos" },
  { valor: "diagnostico", rotulo: "Diagnósticos" },
];

export interface EventoHistorico {
  tipo: TipoEvento;
  origem_id: number;
  data: string;
  descricao: string;
  /** null no diagnóstico: não é despesa e não entra nos totais. */
  valor: string | null;
  quilometragem: number | null;
  sistema: string | null;
  oficina: string | null;
  posto: string | null;
  combustivel: string | null;
  quantidade: string | null;
  categoria: string | null;
  descricao_gasto: string | null;
  projeto_id: number | null;
  projeto_nome: string | null;
  item_descricao: string | null;
  situacao: "aberto" | "em_observacao" | "resolvido" | "descartado" | null;
  gravidade: string | null;
}

export interface TotalDoMes {
  ano: number;
  mes: number;
  total: string;
  quantidade: number;
}

export interface PaginaHistorico {
  itens: EventoHistorico[];
  total: number;
  pagina: number;
  por_pagina: number;
  periodo: PeriodoHistorico;
  ano: number | null;
  inicio: string | null;
  /** Inclusive. */
  fim: string | null;
  meses: TotalDoMes[];
  anos_disponiveis: number[];
}
