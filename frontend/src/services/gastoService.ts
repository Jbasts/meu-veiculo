// Chamadas à API de gastos e finanças (/api/veiculos/{id}/gastos e /financas).

import type { DadosGasto, Gasto, Lancamento, Pendente, ResumoMes } from "../types/gasto";
import type { Pagina } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

/** Período do resumo: um mês, um ano inteiro ou o total desde o primeiro registro. */
export type Periodo =
  | { tipo: "mes"; ano: number; mes: number }
  | { tipo: "ano"; ano: number }
  | { tipo: "total" };

/** "ano=2026&mes=9&", "ano=2026&" ou "" (total). */
function filtroDoPeriodo(periodo: Periodo): string {
  if (periodo.tipo === "total") return "";
  if (periodo.tipo === "ano") return `ano=${periodo.ano}&`;
  return `ano=${periodo.ano}&mes=${periodo.mes}&`;
}

export function obterResumo(veiculoId: number, periodo: Periodo): Promise<ResumoMes> {
  const filtro = filtroDoPeriodo(periodo).replace(/&$/, "");
  return chamarApi<ResumoMes>("GET", `/veiculos/${veiculoId}/financas/resumo${filtro ? `?${filtro}` : ""}`);
}

export function listarLancamentos(veiculoId: number, periodo: Periodo, pagina = 1,
  porPagina = 50): Promise<Pagina<Lancamento>> {
  return chamarApi<Pagina<Lancamento>>("GET",
    `/veiculos/${veiculoId}/financas/lancamentos?${filtroDoPeriodo(periodo)}pagina=${pagina}&por_pagina=${porPagina}`);
}

export function listarPendentes(veiculoId: number, pagina = 1, porPagina = 50): Promise<Pagina<Pendente>> {
  return chamarApi<Pagina<Pendente>>("GET",
    `/veiculos/${veiculoId}/gastos/pendentes?pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterGasto(veiculoId: number, id: number): Promise<Gasto> {
  return chamarApi<Gasto>("GET", `/veiculos/${veiculoId}/gastos/${id}`);
}

export function criarGasto(veiculoId: number, dados: DadosGasto): Promise<Gasto> {
  return chamarApi<Gasto>("POST", `/veiculos/${veiculoId}/gastos`, dados);
}

export function editarGasto(veiculoId: number, id: number, dados: DadosGasto): Promise<Gasto> {
  return chamarApi<Gasto>("PUT", `/veiculos/${veiculoId}/gastos/${id}`, dados);
}

/** Marca um gasto pendente como pago na data informada. */
export function pagarGasto(veiculoId: number, id: number, dataPagamento: string): Promise<Gasto> {
  return chamarApi<Gasto>("POST", `/veiculos/${veiculoId}/gastos/${id}/pagar`, {
    data_pagamento: dataPagamento,
  });
}

export async function apagarGasto(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/gastos/${id}`);
}
