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

/** Nível do marcador em oitavos do tanque, como a Paula lê: "1/4", "1,5/4"... */
export const NIVEIS: { valor: number; rotulo: string }[] = [
  { valor: 0, rotulo: "Vazio" },
  { valor: 1, rotulo: "0,5/4" },
  { valor: 2, rotulo: "1/4" },
  { valor: 3, rotulo: "1,5/4" },
  { valor: 4, rotulo: "2/4" },
  { valor: 5, rotulo: "2,5/4" },
  { valor: 6, rotulo: "3/4" },
  { valor: 7, rotulo: "3,5/4" },
  { valor: 8, rotulo: "Cheio" },
];

export function rotuloDoNivel(nivel: number): string {
  return NIVEIS.find((n) => n.valor === nivel)?.rotulo ?? String(nivel);
}

/** Os combustíveis do tanque do marcador (o GNV e a recarga têm outro reservatório). */
export function temMarcador(combustivel: Combustivel): boolean {
  return combustivel === "gasolina" || combustivel === "etanol" || combustivel === "diesel";
}

export interface DadosAbastecimento {
  combustivel: Combustivel;
  /** Um dos tipos do combustível; null no GNV (e em abastecimento antigo, não informado). */
  tipo: string | null;
  data: string;
  quilometragem: number | null;
  /** Texto com até 3 casas ("38.500"). Vazio = calculado pelo valor total ÷ preço. */
  litros: string | null;
  /** Vazio = calculado pelo valor total ÷ litros. */
  valor_litro: string | null;
  /** Cupom (até R$ 50,00 do calculado) ou, sem litros ou sem preço, o total da bomba. */
  valor_total: string | null;
  tanque_cheio: boolean;
  /** Marcador antes de abastecer, em oitavos; null = não informado. */
  nivel_antes: number | null;
  posto: string | null;
}

export type TipoSituacao = "consumo" | "parcial" | "primeiro_cheio" | "primeiro_nivel" | "fora_do_calculo"
  | "ciclo_invalido" | "trecho_curto" | "sem_tanque";

export interface SituacaoConsumo {
  tipo: TipoSituacao;
  /** Só em "consumo", com 1 casa ("11.3"). */
  km_por_litro: string | null;
  motivo: string | null;
  /** Usou o marcador do tanque: tem margem. */
  estimado: boolean;
  km_por_litro_minimo: string | null;
  km_por_litro_maximo: string | null;
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
  nivel_antes: number | null;
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
  /** Alguma ponta veio do marcador do tanque. */
  estimada: boolean;
  /** Litros de margem ("3.500"). */
  margem: string;
  km_por_litro_minimo: string | null;
  km_por_litro_maximo: string | null;
  inicio: string | null;
  fim: string | null;
}

export interface MesConsumo extends MediaConsumo {
  ano: number;
  mes: number;
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

/** Último nível conhecido do tanque e a estimativa de agora (Início e Combustível). */
export interface NivelTanque {
  disponivel: boolean;
  /** Por que não há nível (quando disponivel = false). */
  motivo: string | null;
  /** Oitavos do tanque (0 = vazio, 8 = cheio), do último registro. */
  nivel: number | null;
  data: string | null;
  quilometragem: number | null;
  origem: "marcacao" | "abastecimento" | null;
  /** Km rodados desde o registro. */
  km_desde: number | null;
  /** Oitavos, estimativa de agora pelo consumo médio (só se rodou desde o registro). */
  nivel_estimado: number | null;
  km_por_litro: string | null;
}

export interface ResumoCombustivel {
  combustiveis: Combustivel[];
  medias: MediaConsumo[];
  /** Só para veículo flex. */
  comparacao: Comparacao | null;
  postos_recentes: string[];
  ultima_quilometragem: number;
  /** Litros do tanque ("56.0"); null = não informado ou elétrico. */
  capacidade_tanque: string | null;
  tanque_pendente: boolean;
  marcacao_do_mes_pendente: boolean;
  /** Consumo por mês, do mais recente (até 12). */
  meses: MesConsumo[];
  nivel_tanque: NivelTanque;
}

export interface DadosMarcacao {
  data: string;
  quilometragem: number | null;
  /** Oitavos do tanque. */
  nivel: number | null;
}

export interface MarcacaoTanque {
  id: number;
  veiculo_id: number;
  data: string;
  quilometragem: number;
  nivel: number;
  criado_em: string;
  /** O trecho que esta marcação fecha. */
  consumo: SituacaoConsumo;
}
