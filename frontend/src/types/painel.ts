import type { NivelTanque } from "./abastecimento";
// Formatos de backend/app/schemas/painel_schema.py (tela inicial e custo do veículo).
// Dinheiro vem como texto ("0.76"). Indicador sem dados vem com disponivel=false e o motivo.

export type GrupoDeCusto =
  | "aquisicao" | "combustivel" | "manutencao" | "projeto" | "seguro" | "documentacao"
  | "seguro_documentacao" | "outros";

const ROTULO_DO_GRUPO: Record<GrupoDeCusto, string> = {
  aquisicao: "Aquisição",
  combustivel: "Combustível",
  manutencao: "Manutenções",
  projeto: "Projetos",
  seguro: "Seguro",
  documentacao: "Documentação",
  seguro_documentacao: "Seguro e documentação",
  outros: "Outros",
};

/** "Manutenções" no custo total; "Manutenção" no mês e no custo por km (como no PDF). */
export function rotuloDoGrupo(grupo: GrupoDeCusto, singular = false): string {
  if (singular && grupo === "manutencao") return "Manutenção";
  return ROTULO_DO_GRUPO[grupo] ?? grupo;
}

export interface Parcela {
  grupo: GrupoDeCusto;
  total: string;
  /** Do total, inteiro meio para cima. */
  percentual: number;
}

export interface CustoTotal {
  total: string;
  /** null = valor da compra não informado. */
  valor_aquisicao: string | null;
  despesas: string;
  quantidade: number;
  parcelas: Parcela[];
}

export interface ParcelaPorKm {
  grupo: GrupoDeCusto;
  total: string;
  por_km: string;
}

export interface CustoPorKm {
  disponivel: boolean;
  motivo: string | null;
  base: "compra" | "primeira_leitura" | null;
  aviso_base: string | null;
  inicio: string | null;
  fim: string | null;
  km_inicio: number | null;
  km_fim: number | null;
  distancia: number | null;
  despesas: string | null;
  valor: string | null;
  parcelas: ParcelaPorKm[];
}

export interface CustoVeiculo {
  custo_total: CustoTotal;
  custo_por_km: CustoPorKm;
}

export interface GastosDoMes {
  ano: number;
  mes: number;
  total: string;
  quantidade: number;
  parcelas: Parcela[];
}

export interface ConsumoMedio {
  disponivel: boolean;
  motivo: string | null;
  combustivel: string | null;
  /** Com 1 casa ("11.3"). */
  valor: string | null;
  ciclos: number;
  distancia: number | null;
  quantidade: string | null;
  inicio: string | null;
  fim: string | null;
  /** Alguma ponta veio do marcador do tanque: valor estimado, com a faixa possível. */
  estimado: boolean;
  minimo: string | null;
  maximo: string | null;
}

export interface AvisosDoTanque {
  /** Tem tanque, mas falta o tamanho no cadastro. */
  tamanho_pendente: boolean;
  /** Falta marcar o km e o nível do tanque neste mês. */
  marcacao_do_mes_pendente: boolean;
}

export interface ContasEmAtraso {
  vencidas: number;
  total_vencidas: string;
  vencem_hoje: number;
}

export interface ProximoGasto {
  id: number;
  categoria: string;
  descricao: string | null;
  valor: string;
  data_vencimento: string;
  /** Dias até a data prevista (0 = hoje). */
  dias: number;
}

/** Gastos lançados para pagar depois (pendentes que vencem hoje ou depois). */
export interface GastosFuturos {
  quantidade: number;
  total: string;
  /** Os três mais próximos. */
  proximos: ProximoGasto[];
}

export interface PainelInicio {
  gastos_do_mes: GastosDoMes;
  consumo: ConsumoMedio;
  custo_por_km: CustoPorKm;
  contas: ContasEmAtraso;
  tanque: AvisosDoTanque;
  gastos_futuros: GastosFuturos;
  nivel_tanque: NivelTanque;
}
