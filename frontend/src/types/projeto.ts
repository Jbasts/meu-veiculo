// Formatos de backend/app/schemas/projeto_schema.py.

export type StatusProjeto = "planejado" | "em_andamento" | "concluido" | "cancelado";
export type CategoriaProjeto = "exterior" | "interior" | "mecanica" | "som" | "outros";
export type FiltroProjeto = "todos" | StatusProjeto;

export const CATEGORIAS_PROJETO: { valor: CategoriaProjeto; rotulo: string }[] = [
  { valor: "exterior", rotulo: "Exterior" },
  { valor: "interior", rotulo: "Interior" },
  { valor: "mecanica", rotulo: "Mecânica" },
  { valor: "som", rotulo: "Som" },
  { valor: "outros", rotulo: "Outros" },
];

export const ROTULO_STATUS_PROJETO: Record<StatusProjeto, string> = {
  planejado: "Planejado",
  em_andamento: "Em andamento",
  concluido: "Concluído",
  cancelado: "Cancelado",
};

export function rotuloCategoriaProjeto(valor: string): string {
  return CATEGORIAS_PROJETO.find((c) => c.valor === valor)?.rotulo ?? valor;
}

export interface DadosProjeto {
  nome: string;
  descricao: string | null;
  categoria: CategoriaProjeto;
  /** Texto ("4500.00"); null = sem orçamento. */
  orcamento: string | null;
  data_prevista: string | null;
}

export interface ItemProjeto {
  id: number;
  descricao: string;
  data: string;
  valor: string;
}

export interface Projeto extends Omit<DadosProjeto, "categoria"> {
  id: number;
  veiculo_id: number;
  categoria: CategoriaProjeto;
  status: StatusProjeto;
  data_conclusao: string | null;
  criado_em: string;
  /** Soma dos itens, calculada pelo backend. */
  gasto: string;
  /** Do orçamento; null sem orçamento ou com orçamento zero. */
  percentual: number | null;
  /** Orçamento − gasto (negativo = excedido); null sem orçamento. */
  diferenca: string | null;
  quantidade_itens: number;
  /** A primeira (mais antiga) de cada momento. */
  foto_antes_id: number | null;
  foto_depois_id: number | null;
}

export interface ProjetoDetalhe extends Projeto {
  itens: ItemProjeto[];
  fotos_antes: number[];
  fotos_depois: number[];
  total_fotos: number;
}

export interface PaginaProjetos {
  itens: Projeto[];
  total: number;
  pagina: number;
  por_pagina: number;
  por_status: Record<StatusProjeto, number>;
}
