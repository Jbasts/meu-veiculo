// Chamadas à API de diagnósticos (/api/veiculos/{id}/diagnosticos).

import type {
  DadosDiagnostico,
  DiagnosticoDetalhe,
  DiagnosticoResumo,
  FiltroDiagnostico,
} from "../types/diagnostico";
import type { DadosManutencao, ManutencaoDetalhe } from "../types/manutencao";
import type { Pagina } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

function base(veiculoId: number, id?: number): string {
  return `/veiculos/${veiculoId}/diagnosticos${id === undefined ? "" : `/${id}`}`;
}

export function listarDiagnosticos(veiculoId: number, filtro: FiltroDiagnostico = "abertos",
  pagina = 1, porPagina = 20): Promise<Pagina<DiagnosticoResumo>> {
  return chamarApi<Pagina<DiagnosticoResumo>>(
    "GET", `${base(veiculoId)}?filtro=${filtro}&pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterDiagnostico(veiculoId: number, id: number): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("GET", base(veiculoId, id));
}

export function criarDiagnostico(veiculoId: number, dados: DadosDiagnostico): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", base(veiculoId), dados);
}

export function editarDiagnostico(veiculoId: number, id: number,
  dados: DadosDiagnostico): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("PUT", base(veiculoId, id), dados);
}

export async function apagarDiagnostico(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", base(veiculoId, id));
}

export function definirAcompanhamento(veiculoId: number, id: number,
  status: "aberto" | "em_observacao"): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", `${base(veiculoId, id)}/acompanhamento`, { status });
}

export function descartarDiagnostico(veiculoId: number, id: number,
  motivo: string): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", `${base(veiculoId, id)}/descartar`, {
    motivo: motivo.trim() || null,
  });
}

export function reabrirDiagnostico(veiculoId: number, id: number): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", `${base(veiculoId, id)}/reabrir`);
}

/** Registra a manutenção e resolve (realizada) ou liga como prevista (agendada), de uma vez. */
export function resolverComNovaManutencao(veiculoId: number, id: number,
  dados: DadosManutencao): Promise<{ diagnostico: DiagnosticoDetalhe; manutencao: ManutencaoDetalhe }> {
  return chamarApi("POST", `${base(veiculoId, id)}/resolver`, dados);
}

/** Usa uma manutenção já registrada do mesmo veículo. */
export function resolverComManutencaoExistente(veiculoId: number, id: number,
  manutencaoId: number): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", `${base(veiculoId, id)}/vincular`, {
    manutencao_id: manutencaoId,
  });
}

export function adicionarNota(veiculoId: number, id: number, texto: string,
  data: string): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("POST", `${base(veiculoId, id)}/notas`, { texto, data });
}

export function apagarNota(veiculoId: number, id: number, notaId: number): Promise<DiagnosticoDetalhe> {
  return chamarApi<DiagnosticoDetalhe>("DELETE", `${base(veiculoId, id)}/notas/${notaId}`);
}
