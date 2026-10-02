// Chamadas à API dos indicadores e do histórico (/api/veiculos/{id}/painel, /custo e /historico).
// Os valores são calculados no backend; a tela só formata.

import type { FiltroHistorico, PaginaHistorico, PeriodoHistorico } from "../types/historico";
import type { CustoVeiculo, PainelInicio } from "../types/painel";
import { chamarApi } from "./apiCliente";

export function obterPainel(veiculoId: number): Promise<PainelInicio> {
  return chamarApi<PainelInicio>("GET", `/veiculos/${veiculoId}/painel`);
}

export function obterCusto(veiculoId: number): Promise<CustoVeiculo> {
  return chamarApi<CustoVeiculo>("GET", `/veiculos/${veiculoId}/custo`);
}

export function listarHistorico(veiculoId: number, filtro: FiltroHistorico, periodo: PeriodoHistorico,
  ano: number | null, pagina = 1, porPagina = 50): Promise<PaginaHistorico> {
  const parametros = new URLSearchParams({ periodo, pagina: String(pagina), por_pagina: String(porPagina) });
  if (filtro !== "tudo") parametros.set("tipo", filtro);
  if (periodo === "ano" && ano !== null) parametros.set("ano", String(ano));
  return chamarApi<PaginaHistorico>("GET", `/veiculos/${veiculoId}/historico?${parametros}`);
}
