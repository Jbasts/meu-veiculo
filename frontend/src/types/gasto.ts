// Formatos de backend/app/schemas/gasto_schema.py.

export type CategoriaGasto =
  | "ipva" | "licenciamento" | "seguro" | "multa" | "estacionamento" | "pedagio"
  | "lavagem" | "acessorios" | "outros";

/** Categorias do formulário "Novo gasto", na ordem do PDF. */
export const CATEGORIAS_GASTO: { valor: CategoriaGasto; rotulo: string }[] = [
  { valor: "ipva", rotulo: "IPVA" },
  { valor: "licenciamento", rotulo: "Licenciamento" },
  { valor: "seguro", rotulo: "Seguro" },
  { valor: "multa", rotulo: "Multa" },
  { valor: "estacionamento", rotulo: "Estacionamento" },
  { valor: "pedagio", rotulo: "Pedágio" },
  { valor: "lavagem", rotulo: "Lavagem" },
  { valor: "acessorios", rotulo: "Acessórios" },
  { valor: "outros", rotulo: "Outros" },
];

/** Categorias que vêm de outras tabelas no resumo do mês. */
const OUTRAS_CATEGORIAS: Record<string, string> = {
  manutencao: "Manutenção",
  combustivel: "Combustível",
  projeto: "Projetos",
};

export function rotuloCategoria(valor: string): string {
  return OUTRAS_CATEGORIAS[valor] ?? CATEGORIAS_GASTO.find((c) => c.valor === valor)?.rotulo ?? valor;
}

export interface DadosGasto {
  categoria: CategoriaGasto;
  /** Texto ("2400.00"). */
  valor: string | null;
  descricao: string | null;
  data: string;
  pago: boolean;
  /** Obrigatório quando pendente. */
  data_vencimento: string | null;
  /** Obrigatório quando pago (gasto antigo pode não ter). */
  data_pagamento: string | null;
}

export interface Gasto extends Omit<DadosGasto, "valor"> {
  id: number;
  veiculo_id: number;
  valor: string;
  criado_em: string;
}

export type SituacaoPendente = "vencido" | "vence_hoje" | "a_vencer";

export interface Pendente extends Gasto {
  situacao: SituacaoPendente;
  /** Dias até o vencimento (negativo = dias de atraso). */
  dias: number;
}

export interface TotalCategoria {
  categoria: string;
  total: string;
  quantidade: number;
  /** Do total do mês, inteiro arredondado meio para cima. */
  percentual: number;
}

export interface ResumoMes {
  periodo: "mes" | "ano" | "total";
  /** null no total. */
  ano: number | null;
  /** null no ano e no total. */
  mes: number | null;
  /** Só despesas efetivadas. */
  total: string;
  quantidade: number;
  categorias: TotalCategoria[];
  /** Previsto (não entra no total). */
  previsto_manutencoes: string;
  quantidade_manutencoes_previstas: number;
  previsto_gastos: string;
  quantidade_gastos_previstos: number;
}

export type TipoLancamento = "manutencao" | "abastecimento" | "gasto" | "projeto";

export interface Lancamento {
  tipo: TipoLancamento;
  origem_id: number;
  data: string;
  categoria: string;
  descricao: string | null;
  valor: string;
  /** Só nos itens de projeto: o projeto a abrir. */
  projeto_id: number | null;
}
