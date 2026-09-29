// Formato da resposta de GET /api/saude (igual ao backend/app/schemas/saude_schema.py).

export interface Saude {
  api: "ok";
  banco: "ok" | "indisponivel";
  situacao_banco: "vazio" | "sem_controle" | "controlado" | null;
  versao_migracao: string | null;
  versao_mais_recente: string | null;
  migracoes_pendentes: string[];
  fuso_horario: string;
  /** Data pura "AAAA-MM-DD" (sem hora e sem fuso). */
  data_hoje: string | null;
  mensagem: string;
}

export type ResultadoSaude =
  | { tipo: "resposta"; saude: Saude }
  | { tipo: "api_fora"; detalhe: string };
