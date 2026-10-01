// Formatos de backend/app/schemas/diagnostico_schema.py.

export type StatusDiagnostico = "aberto" | "em_observacao" | "resolvido" | "descartado";
export type Gravidade = "baixa" | "media" | "alta" | "critica";
/** abertos = aberto e em observação; resolvidos = resolvido e descartado. */
export type FiltroDiagnostico = "abertos" | "resolvidos" | "todos";

export const GRAVIDADES: { valor: Gravidade; rotulo: string; orientacao: string }[] = [
  { valor: "baixa", rotulo: "Baixa", orientacao: "Pode esperar a próxima revisão." },
  { valor: "media", rotulo: "Média", orientacao: "Resolver nas próximas semanas." },
  { valor: "alta", rotulo: "Alta", orientacao: "Resolver o quanto antes." },
  { valor: "critica", rotulo: "Crítica", orientacao: "Evite usar o veículo até resolver." },
];

export function rotuloGravidade(valor: Gravidade): string {
  return GRAVIDADES.find((g) => g.valor === valor)?.rotulo ?? valor;
}

export const ROTULO_STATUS: Record<StatusDiagnostico, string> = {
  aberto: "Aberto",
  em_observacao: "Em observação",
  resolvido: "Resolvido",
  descartado: "Descartado",
};

export function emAberto(status: StatusDiagnostico): boolean {
  return status === "aberto" || status === "em_observacao";
}

export interface DadosDiagnostico {
  titulo: string;
  descricao: string | null;
  sistema: string;
  gravidade: Gravidade;
  data_identificacao: string;
  quilometragem: number | null;
}

/** Manutenção que resolveu (realizada) ou vai resolver (agendada) o problema. */
export interface ManutencaoLigada {
  id: number;
  descricao: string;
  status: "realizada" | "agendada";
  data: string;
  valor: string;
}

export interface Nota {
  id: number;
  data: string;
  texto: string;
  criado_em: string;
}

/** Manutenção do mesmo sistema que estava em garantia na data do problema. */
export interface GarantiaPossivel {
  manutencao_id: number;
  descricao: string;
  data: string;
  explicacao: string;
}

export interface Diagnostico extends DadosDiagnostico {
  id: number;
  veiculo_id: number;
  status: StatusDiagnostico;
  data_resolucao: string | null;
  /** Motivo informado ao descartar. */
  solucao: string | null;
  manutencao_id: number | null;
  criado_em: string;
}

export interface DiagnosticoResumo extends Diagnostico {
  total_notas: number;
  manutencao: ManutencaoLigada | null;
}

export interface DiagnosticoDetalhe extends Diagnostico {
  /** Da mais recente para a mais antiga. */
  notas: Nota[];
  manutencao: ManutencaoLigada | null;
  garantias: GarantiaPossivel[];
  total_fotos: number;
}

/** Diagnóstico que aparece no detalhe da manutenção. */
export interface DiagnosticoLigado {
  id: number;
  titulo: string;
  status: StatusDiagnostico;
  gravidade: Gravidade;
  data_identificacao: string;
}
