// Chamadas à API de projetos (/api/veiculos/{id}/projetos).

import type { DadosProjeto, FiltroProjeto, PaginaProjetos, ProjetoDetalhe, StatusProjeto } from "../types/projeto";
import { chamarApi } from "./apiCliente";

function base(veiculoId: number, id?: number): string {
  return `/veiculos/${veiculoId}/projetos${id === undefined ? "" : `/${id}`}`;
}

export function listarProjetos(veiculoId: number, filtro: FiltroProjeto = "todos", pagina = 1,
  porPagina = 20): Promise<PaginaProjetos> {
  return chamarApi<PaginaProjetos>("GET", `${base(veiculoId)}?filtro=${filtro}&pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterProjeto(veiculoId: number, id: number): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("GET", base(veiculoId, id));
}

export function criarProjeto(veiculoId: number, dados: DadosProjeto & { status: StatusProjeto }): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("POST", base(veiculoId), dados);
}

export function editarProjeto(veiculoId: number, id: number, dados: DadosProjeto): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("PUT", base(veiculoId, id), dados);
}

export async function apagarProjeto(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", base(veiculoId, id));
}

export type AcaoProjeto = "iniciar" | "cancelar" | "reabrir";

export function mudarSituacao(veiculoId: number, id: number, acao: AcaoProjeto): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("POST", `${base(veiculoId, id)}/${acao}`);
}

export function concluirProjeto(veiculoId: number, id: number, dataConclusao: string): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("POST", `${base(veiculoId, id)}/concluir`, { data_conclusao: dataConclusao });
}

export interface DadosItem {
  descricao: string;
  data: string;
  valor: string;
}

export function adicionarItem(veiculoId: number, id: number, dados: DadosItem): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("POST", `${base(veiculoId, id)}/itens`, dados);
}

export function editarItem(veiculoId: number, id: number, itemId: number, dados: DadosItem): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("PUT", `${base(veiculoId, id)}/itens/${itemId}`, dados);
}

export function apagarItem(veiculoId: number, id: number, itemId: number): Promise<ProjetoDetalhe> {
  return chamarApi<ProjetoDetalhe>("DELETE", `${base(veiculoId, id)}/itens/${itemId}`);
}
