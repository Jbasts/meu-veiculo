// Chamadas à API de abastecimentos e combustível (/api/veiculos/{id}/abastecimentos e /combustivel).

import type { Abastecimento, DadosAbastecimento, ResumoCombustivel } from "../types/abastecimento";
import type { Pagina } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

/** Sem preços: compara com o último preço pago. Com os dois: simula (nada é gravado). */
export function obterResumoCombustivel(veiculoId: number,
  simulacao?: { gasolina: string; etanol: string }): Promise<ResumoCombustivel> {
  const filtro = simulacao ? `?preco_gasolina=${simulacao.gasolina}&preco_etanol=${simulacao.etanol}` : "";
  return chamarApi<ResumoCombustivel>("GET", `/veiculos/${veiculoId}/combustivel/resumo${filtro}`);
}

export function listarAbastecimentos(veiculoId: number, pagina = 1,
  porPagina = 30): Promise<Pagina<Abastecimento>> {
  return chamarApi<Pagina<Abastecimento>>("GET",
    `/veiculos/${veiculoId}/abastecimentos?pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterAbastecimento(veiculoId: number, id: number): Promise<Abastecimento> {
  return chamarApi<Abastecimento>("GET", `/veiculos/${veiculoId}/abastecimentos/${id}`);
}

export function criarAbastecimento(veiculoId: number, dados: DadosAbastecimento): Promise<Abastecimento> {
  return chamarApi<Abastecimento>("POST", `/veiculos/${veiculoId}/abastecimentos`, dados);
}

export function editarAbastecimento(veiculoId: number, id: number,
  dados: DadosAbastecimento): Promise<Abastecimento> {
  return chamarApi<Abastecimento>("PUT", `/veiculos/${veiculoId}/abastecimentos/${id}`, dados);
}

export async function apagarAbastecimento(veiculoId: number, id: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/abastecimentos/${id}`);
}
