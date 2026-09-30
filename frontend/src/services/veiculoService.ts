// Chamadas à API de veículos e quilometragem (/api/veiculos/...).

import type { DadosNovoVeiculo, DadosVeiculo, LeituraKm, Pagina, Veiculo } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

export function listarVeiculos(): Promise<Veiculo[]> {
  return chamarApi<Veiculo[]>("GET", "/veiculos");
}

export function obterVeiculo(id: number): Promise<Veiculo> {
  return chamarApi<Veiculo>("GET", `/veiculos/${id}`);
}

export function cadastrarVeiculo(dados: DadosNovoVeiculo): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", "/veiculos", dados);
}

export function editarVeiculo(id: number, dados: DadosVeiculo): Promise<Veiculo> {
  return chamarApi<Veiculo>("PUT", `/veiculos/${id}`, dados);
}

export function selecionarVeiculo(id: number): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${id}/selecionar`);
}

export function inativarVeiculo(id: number): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${id}/inativar`);
}

export function reativarVeiculo(id: number): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${id}/reativar`);
}

export function listarLeituras(veiculoId: number, pagina = 1, porPagina = 20): Promise<Pagina<LeituraKm>> {
  return chamarApi<Pagina<LeituraKm>>(
    "GET", `/veiculos/${veiculoId}/leituras?pagina=${pagina}&por_pagina=${porPagina}`);
}

/** Nova leitura do hodômetro. Devolve o veículo com a quilometragem recalculada. */
export function registrarLeitura(veiculoId: number, quilometragem: number,
  dataLeitura: string | null): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${veiculoId}/leituras`, {
    quilometragem,
    data_leitura: dataLeitura,
  });
}

export function corrigirLeitura(veiculoId: number, leituraId: number, quilometragem: number,
  motivo: string | null): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${veiculoId}/leituras/${leituraId}/corrigir`, {
    quilometragem,
    motivo,
  });
}

export function anularLeitura(veiculoId: number, leituraId: number,
  motivo: string | null): Promise<Veiculo> {
  return chamarApi<Veiculo>("POST", `/veiculos/${veiculoId}/leituras/${leituraId}/anular`, { motivo });
}
