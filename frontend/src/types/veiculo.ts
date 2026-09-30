// Formatos de backend/app/schemas/veiculo_schema.py.
//
// Datas são texto "AAAA-MM-DD". Dinheiro é texto "65000.00" (nunca número
// com ponto flutuante, para não perder centavos).

export type Combustivel = "flex" | "gasolina" | "etanol" | "diesel" | "gnv" | "hibrido" | "eletrico";

export const COMBUSTIVEIS: { valor: Combustivel; rotulo: string }[] = [
  { valor: "flex", rotulo: "Flex" },
  { valor: "gasolina", rotulo: "Gasolina" },
  { valor: "etanol", rotulo: "Etanol" },
  { valor: "diesel", rotulo: "Diesel" },
  { valor: "gnv", rotulo: "GNV" },
  { valor: "hibrido", rotulo: "Híbrido" },
  { valor: "eletrico", rotulo: "Elétrico" },
];

export function rotuloCombustivel(valor: string): string {
  return COMBUSTIVEIS.find((c) => c.valor === valor)?.rotulo ?? valor;
}

export interface Veiculo {
  id: number;
  usuario_id: number;
  marca: string;
  modelo: string;
  versao: string | null;
  ano: number;
  placa: string;
  cor: string | null;
  tipo_combustivel: Combustivel;
  quilometragem: number;
  /** Dia da leitura que define a quilometragem atual; null = data desconhecida. */
  data_leitura_km: string | null;
  km_aquisicao: number | null;
  data_aquisicao: string | null;
  valor_aquisicao: string | null;
  ativo: boolean;
  criado_em: string;
  em_uso: boolean;
  foto_capa_id: number | null;
}

/** Dados do formulário de edição (a quilometragem só entra no cadastro). */
export interface DadosVeiculo {
  marca: string;
  modelo: string;
  versao: string | null;
  ano: number;
  placa: string;
  cor: string | null;
  tipo_combustivel: Combustivel;
  data_aquisicao: string | null;
  valor_aquisicao: string | null;
  km_aquisicao: number | null;
}

export interface DadosNovoVeiculo extends DadosVeiculo {
  quilometragem: number;
}

export type OrigemLeitura = "cadastro" | "manual" | "abastecimento" | "manutencao" | "diagnostico" | "legado";

export interface LeituraKm {
  id: number;
  veiculo_id: number;
  quilometragem: number;
  data_leitura: string | null;
  origem: OrigemLeitura;
  origem_id: number | null;
  corrige_id: number | null;
  valida: boolean;
  editavel: boolean;
  anulada_em: string | null;
  motivo_anulacao: string | null;
  criado_em: string;
}

export interface Foto {
  id: number;
  veiculo_id: number;
  tipo_mime: string;
  tamanho_bytes: number;
  legenda: string | null;
  data_foto: string;
  principal: boolean;
  projeto_id: number | null;
  momento: "antes" | "depois" | null;
  diagnostico_id: number | null;
  manutencao_id: number | null;
  criado_em: string;
}

export interface Pagina<T> {
  itens: T[];
  total: number;
  pagina: number;
  por_pagina: number;
}
