// Chamadas à API de planos e manutenções (/api/veiculos/{id}/planos e /manutencoes).

import type {
  DadosManutencao,
  DadosPlano,
  Manutencao,
  ManutencaoDetalhe,
  Pendentes,
  Plano,
  StatusManutencao,
} from "../types/manutencao";
import type { Pagina } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

export function listarPendentes(veiculoId: number): Promise<Pendentes> {
  return chamarApi<Pendentes>("GET", `/veiculos/${veiculoId}/manutencoes/pendentes`);
}

export function listarManutencoes(veiculoId: number, opcoes: {
  status?: StatusManutencao;
  pagina?: number;
  porPagina?: number;
} = {}): Promise<Pagina<Manutencao>> {
  const { status, pagina = 1, porPagina = 20 } = opcoes;
  const filtro = status ? `status=${status}&` : "";
  return chamarApi<Pagina<Manutencao>>(
    "GET", `/veiculos/${veiculoId}/manutencoes?${filtro}pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterManutencao(veiculoId: number, id: number): Promise<ManutencaoDetalhe> {
  return chamarApi<ManutencaoDetalhe>("GET", `/veiculos/${veiculoId}/manutencoes/${id}`);
}

export function criarManutencao(veiculoId: number, dados: DadosManutencao): Promise<ManutencaoDetalhe> {
  return chamarApi<ManutencaoDetalhe>("POST", `/veiculos/${veiculoId}/manutencoes`, dados);
}

export function editarManutencao(veiculoId: number, id: number,
  dados: DadosManutencao): Promise<ManutencaoDetalhe> {
  return chamarApi<ManutencaoDetalhe>("PUT", `/veiculos/${veiculoId}/manutencoes/${id}`, dados);
}

export async function apagarManutencao(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/manutencoes/${id}`);
}

export function listarPlanos(veiculoId: number): Promise<Plano[]> {
  return chamarApi<Plano[]>("GET", `/veiculos/${veiculoId}/planos`);
}

export function obterPlano(veiculoId: number, id: number): Promise<Plano> {
  return chamarApi<Plano>("GET", `/veiculos/${veiculoId}/planos/${id}`);
}

export function criarPlano(veiculoId: number, dados: DadosPlano): Promise<Plano> {
  return chamarApi<Plano>("POST", `/veiculos/${veiculoId}/planos`, dados);
}

export function editarPlano(veiculoId: number, id: number, dados: DadosPlano): Promise<Plano> {
  return chamarApi<Plano>("PUT", `/veiculos/${veiculoId}/planos/${id}`, dados);
}

export function definirPlanoAtivo(veiculoId: number, id: number, ativo: boolean): Promise<Plano> {
  return chamarApi<Plano>("POST", `/veiculos/${veiculoId}/planos/${id}/${ativo ? "ativar" : "desativar"}`);
}

export async function apagarPlano(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/planos/${id}`);
}
