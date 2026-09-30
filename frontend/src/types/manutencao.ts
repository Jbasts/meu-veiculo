// Formatos de backend/app/schemas/manutencao_schema.py.

import { formatarDataIso } from "../utils/datas";
import { formatarInteiro } from "../utils/formatos";

export const SISTEMAS = [
  { valor: "motor", rotulo: "Motor" },
  { valor: "transmissao", rotulo: "Transmissão" },
  { valor: "suspensao", rotulo: "Suspensão" },
  { valor: "freios", rotulo: "Freios" },
  { valor: "direcao", rotulo: "Direção" },
  { valor: "pneus", rotulo: "Pneus" },
  { valor: "eletrica", rotulo: "Elétrica" },
  { valor: "arrefecimento", rotulo: "Arrefecimento" },
  { valor: "ar_condicionado", rotulo: "Ar-condicionado" },
  { valor: "carroceria", rotulo: "Carroceria" },
  { valor: "interior", rotulo: "Interior" },
  { valor: "outros", rotulo: "Outros" },
];

export function rotuloSistema(valor: string): string {
  return SISTEMAS.find((s) => s.valor === valor)?.rotulo ?? valor;
}

export type Situacao = "atrasada" | "proxima" | "em_dia" | "sem_base";
export type StatusManutencao = "realizada" | "agendada";

interface Prazo {
  proxima_data: string | null;
  proxima_km: number | null;
  dias_restantes: number | null;
  km_restantes: number | null;
}

export interface Plano extends Prazo {
  id: number;
  veiculo_id: number;
  nome: string;
  sistema: string;
  intervalo_km: number | null;
  intervalo_meses: number | null;
  data_base: string | null;
  km_base: number | null;
  ativo: boolean;
  criado_em: string;
  /** null quando o plano está inativo. */
  situacao: Situacao | null;
  referencia_data: string | null;
  referencia_km: number | null;
}

export interface DadosPlano {
  nome: string;
  sistema: string;
  intervalo_km: number | null;
  intervalo_meses: number | null;
  data_base: string | null;
  km_base: number | null;
}

export type TipoItem = "peca" | "mao_de_obra";

/** Uma peça ou um serviço de mão de obra. Valor em texto ("70.00"). */
export interface ItemManutencao {
  tipo: TipoItem;
  nome: string;
  valor: string;
}

export interface DadosManutencao {
  descricao: string;
  sistema: string;
  status: StatusManutencao;
  data: string;
  quilometragem: number | null;
  oficina: string | null;
  plano_id: number | null;
  garantia_ate: string | null;
  /** Limite do hodômetro (ex.: 95000), não distância de cobertura. */
  garantia_km: number | null;
  proxima_data: string | null;
  proxima_km: number | null;
  observacao: string | null;
  /** Só sem itens. Com itens, o backend calcula o total (valor deve ir null). */
  valor: string | null;
  /** A lista inteira: na edição, substitui os itens que a manutenção tinha. */
  itens: ItemManutencao[];
}

export interface Manutencao extends Omit<DadosManutencao, "valor" | "itens"> {
  id: number;
  veiculo_id: number;
  valor: string;
  criado_em: string;
}

export type SituacaoGarantia = "vigente" | "vencida" | "sem_informacao" | "nao_se_aplica";

export interface ManutencaoDetalhe extends Manutencao {
  plano_nome: string | null;
  garantia_situacao: SituacaoGarantia;
  garantia_explicacao: string;
  total_fotos: number;
  itens: (ItemManutencao & { id: number })[];
  /** null quando não há itens: só o total, sem detalhamento (não é zero). */
  total_pecas: string | null;
  total_mao_de_obra: string | null;
}

export interface Pendencia extends Prazo {
  tipo: "plano" | "agendada" | "lembrete";
  situacao: Situacao;
  titulo: string;
  sistema: string;
  plano_id: number | null;
  manutencao_id: number | null;
  intervalo_km: number | null;
  intervalo_meses: number | null;
  /** Plano que já tem manutenção agendada: ela aparece junto, não como outro alerta. */
  agendada_id: number | null;
  agendada_data: string | null;
}

export interface Pendentes {
  km_atual: number;
  itens: Pendencia[];
}

export const ROTULO_SITUACAO: Record<Situacao, string> = {
  atrasada: "Atrasada",
  proxima: "Próxima",
  em_dia: "Em dia",
  sem_base: "Dados insuficientes",
};

/** "A cada 10.000 km ou 12 meses" */
export function textoIntervalo(item: { intervalo_km: number | null; intervalo_meses: number | null }): string {
  const partes: string[] = [];
  if (item.intervalo_km !== null) partes.push(`${formatarInteiro(item.intervalo_km)} km`);
  if (item.intervalo_meses !== null) {
    partes.push(item.intervalo_meses === 1 ? "1 mês" : `${item.intervalo_meses} meses`);
  }
  return `A cada ${partes.join(" ou ")}`;
}

/** "aos 86.000 km ou em 15/10/2026" */
export function textoPrevisao(item: Pick<Prazo, "proxima_data" | "proxima_km">): string {
  const partes: string[] = [];
  if (item.proxima_km !== null) partes.push(`aos ${formatarInteiro(item.proxima_km)} km`);
  if (item.proxima_data !== null) partes.push(`em ${formatarDataIso(item.proxima_data)}`);
  return partes.join(" ou ");
}

function plural(valor: number, um: string, varios: string): string {
  return `${formatarInteiro(valor)} ${valor === 1 ? um : varios}`;
}

/**
 * O número em destaque de um prazo, como no PDF ("23 dias / de atraso",
 * "1.000 km / restantes"). Sem base, não há número: é "dados insuficientes".
 */
export function resumoDoPrazo(item: Prazo & { situacao: Situacao | null }): { valor: string; rotulo: string } {
  const { dias_restantes: dias, km_restantes: km } = item;
  if (item.situacao === "sem_base" || (dias === null && km === null)) {
    return { valor: "Sem base", rotulo: "informe a última vez" };
  }
  if (item.situacao === "atrasada") {
    if (dias !== null && dias <= 0) {
      return dias === 0 ? { valor: "Hoje", rotulo: "vence hoje" }
        : { valor: plural(-dias, "dia", "dias"), rotulo: "de atraso" };
    }
    if (km !== null && km <= 0) {
      return km === 0 ? { valor: "0 km", rotulo: "atingiu o limite" }
        : { valor: `${formatarInteiro(-km)} km`, rotulo: "além do limite" };
    }
  }
  // Mostra o limite que está mais perto, na proporção das faixas (1.000 km ~ 30 dias).
  const kmMaisPerto = km !== null && (dias === null || km / 1000 <= dias / 30);
  if (kmMaisPerto) return { valor: `${formatarInteiro(km)} km`, rotulo: "restantes" };
  if (dias === 0) return { valor: "Hoje", rotulo: "é o dia marcado" };
  return { valor: plural(dias ?? 0, "dia", "dias"), rotulo: (dias ?? 0) === 1 ? "restante" : "restantes" };
}

/** Quanto do intervalo já foi consumido (0 a 1), para a barra do PDF. Só para planos. */
export function progressoDoPlano(item: Pendencia | Plano): number | null {
  const fracoes: number[] = [];
  if (item.intervalo_km !== null && item.km_restantes !== null) {
    fracoes.push(1 - item.km_restantes / item.intervalo_km);
  }
  if (item.intervalo_meses !== null && item.dias_restantes !== null) {
    fracoes.push(1 - item.dias_restantes / (item.intervalo_meses * 30.44));
  }
  if (fracoes.length === 0) return null;
  return Math.min(1, Math.max(0, Math.max(...fracoes)));
}
