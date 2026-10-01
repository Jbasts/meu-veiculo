// Formatos de backend/app/schemas/abastecimento_schema.py.

/** "eletrica" é a recarga do veículo elétrico ou híbrido. */
export type Combustivel = "gasolina" | "etanol" | "diesel" | "gnv" | "eletrica";

export const ROTULO_COMBUSTIVEL: Record<Combustivel, string> = {
  gasolina: "Gasolina",
  etanol: "Etanol",
  diesel: "Diesel",
  gnv: "GNV",
  eletrica: "Eletricidade",
};

/** Os tipos de cada combustível (tabela da Paula). GNV não tem tipo. */
export const TIPOS_POR_COMBUSTIVEL: Record<Combustivel, { valor: string; rotulo: string }[]> = {
  gasolina: [
    { valor: "comum", rotulo: "Comum" },
    { valor: "comum_aditivada", rotulo: "Comum aditivada" },
    { valor: "premium", rotulo: "Premium" },
    { valor: "premium_aditivada", rotulo: "Premium aditivada" },
  ],
  etanol: [
    { valor: "comum", rotulo: "Comum (hidratado)" },
    { valor: "aditivado", rotulo: "Aditivado" },
    { valor: "premium", rotulo: "Premium" },
    { valor: "premium_aditivado", rotulo: "Premium aditivado" },
  ],
  diesel: [
    { valor: "s10", rotulo: "S10" },
    { valor: "s10_aditivado", rotulo: "S10 aditivado" },
    { valor: "s500", rotulo: "S500" },
    { valor: "s500_aditivado", rotulo: "S500 aditivado" },
  ],
  gnv: [],
  eletrica: [
    { valor: "ac", rotulo: "Recarga AC" },
    { valor: "dc", rotulo: "Recarga DC" },
  ],
};

export function rotuloDoTipo(combustivel: Combustivel, tipo: string | null): string | null {
  return TIPOS_POR_COMBUSTIVEL[combustivel].find((t) => t.valor === tipo)?.rotulo ?? null;
}

/** "gasolina premium aditivada", "diesel S10", "eletricidade (recarga DC)", "etanol" (sem tipo). */
export function nomeDoCombustivel(combustivel: Combustivel, tipo: string | null): string {
  if (combustivel === "gnv") return "GNV";
  const nome = ROTULO_COMBUSTIVEL[combustivel].toLowerCase();
  const rotulo = rotuloDoTipo(combustivel, tipo);
  if (!rotulo) return nome;
  if (combustivel === "eletrica") return `${nome} (recarga ${tipo!.toUpperCase()})`;
  if (combustivel === "diesel") return `${nome} ${rotulo}`;
  return `${nome} ${rotulo.toLowerCase()}`;
}

/** Litros; m³ no GNV; kWh na recarga elétrica. */
export function unidade(combustivel: string): {
  curta: string; consumo: string; preco: string; quantidade: string; cheio: string; cheioDescricao: string;
} {
  if (combustivel === "gnv") {
    return { curta: "m³", consumo: "km/m³", preco: "Preço por m³", quantidade: "Metros cúbicos (m³)",
      cheio: "Tanque cheio", cheioDescricao: "O consumo deste tanque será calculado automaticamente." };
  }
  if (combustivel === "eletrica") {
    return { curta: "kWh", consumo: "km/kWh", preco: "Preço por kWh", quantidade: "Energia (kWh)",
      cheio: "Carga completa", cheioDescricao: "Bateria a 100%: o consumo desta carga será calculado automaticamente." };
  }
  return { curta: "L", consumo: "km/L", preco: "Preço por litro", quantidade: "Litros",
    cheio: "Tanque cheio", cheioDescricao: "O consumo deste tanque será calculado automaticamente." };
}

export interface DadosAbastecimento {
  combustivel: Combustivel;
  /** Um dos tipos do combustível; null no GNV (e em abastecimento antigo, não informado). */
  tipo: string | null;
  data: string;
  quilometragem: number | null;
  /** Texto com até 3 casas ("38.500"). */
  litros: string | null;
  valor_litro: string | null;
  /** Só quando o cupom difere do calculado (até R$ 50,00). */
  valor_total: string | null;
  tanque_cheio: boolean;
  posto: string | null;
}

export type TipoSituacao = "consumo" | "parcial" | "primeiro_cheio" | "fora_do_calculo" | "ciclo_invalido";

export interface SituacaoConsumo {
  tipo: TipoSituacao;
  /** Só em "consumo", com 1 casa ("11.3"). */
  km_por_litro: string | null;
  motivo: string | null;
}

export interface Abastecimento {
  id: number;
  veiculo_id: number;
  data: string;
  quilometragem: number;
  combustivel: Combustivel;
  tipo: string | null;
  litros: string;
  valor_litro: string;
  valor_total: string;
  tanque_cheio: boolean;
  posto: string | null;
  criado_em: string;
  consumo: SituacaoConsumo;
}

export interface MediaConsumo {
  combustivel: Combustivel;
  km_por_litro: string;
  distancia: number;
  quantidade: string;
  ciclos: number;
}

export interface Comparacao {
  /** null quando faltam dados (o motivo diz o quê). */
  recomendacao: "etanol" | "gasolina" | "tanto_faz" | null;
  motivo: string | null;
  limite_percentual: number | null;
  relacao_percentual: number | null;
  preco_gasolina: string | null;
  preco_etanol: string | null;
  precos_simulados: boolean;
}

export interface ResumoCombustivel {
  combustiveis: Combustivel[];
  medias: MediaConsumo[];
  /** Só para veículo flex. */
  comparacao: Comparacao | null;
  postos_recentes: string[];
  ultima_quilometragem: number;
}
