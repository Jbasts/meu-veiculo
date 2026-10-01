// Chamadas à API de fotos (/api/veiculos/{id}/fotos/...).

import type { Foto, Pagina } from "../types/veiculo";
import { chamarApi } from "./apiCliente";

export const TAMANHO_MAXIMO_FOTO = 10_485_760; // 10 MB, o mesmo limite do backend

/**
 * Endereço da imagem. Não é um arquivo público: o backend confere a sessão
 * (cookie) e o dono do veículo a cada pedido.
 */
export function urlDaFoto(veiculoId: number, fotoId: number): string {
  return `/api/veiculos/${veiculoId}/fotos/${fotoId}/arquivo`;
}

/** Filtro da galeria: só as ligadas a manutenção, a diagnóstico ou sem vínculo. */
export type VinculoFoto = "manutencao" | "diagnostico" | "nenhum";

export function listarFotos(veiculoId: number, pagina = 1, porPagina = 30, filtro: {
  vinculo?: VinculoFoto;
  manutencaoId?: number;
  diagnosticoId?: number;
} = {}): Promise<Pagina<Foto>> {
  let extra = "";
  if (filtro.vinculo) extra += `&vinculo=${filtro.vinculo}`;
  if (filtro.manutencaoId) extra += `&manutencao_id=${filtro.manutencaoId}`;
  if (filtro.diagnosticoId) extra += `&diagnostico_id=${filtro.diagnosticoId}`;
  return chamarApi<Pagina<Foto>>(
    "GET", `/veiculos/${veiculoId}/fotos?pagina=${pagina}&por_pagina=${porPagina}${extra}`);
}

export function obterFoto(veiculoId: number, fotoId: number): Promise<Foto> {
  return chamarApi<Foto>("GET", `/veiculos/${veiculoId}/fotos/${fotoId}`);
}

export function enviarFoto(veiculoId: number, dados: {
  arquivo: File;
  legenda: string;
  dataFoto: string;
  principal: boolean;
  /** Manutenção OU diagnóstico do mesmo veículo aos quais a foto fica ligada (opcional). */
  manutencaoId?: number | null;
  diagnosticoId?: number | null;
}): Promise<Foto> {
  const formulario = new FormData();
  formulario.append("arquivo", dados.arquivo);
  if (dados.legenda.trim()) formulario.append("legenda", dados.legenda.trim());
  if (dados.dataFoto) formulario.append("data_foto", dados.dataFoto);
  formulario.append("principal", dados.principal ? "true" : "false");
  if (dados.manutencaoId) formulario.append("manutencao_id", String(dados.manutencaoId));
  if (dados.diagnosticoId) formulario.append("diagnostico_id", String(dados.diagnosticoId));
  return chamarApi<Foto>("POST", `/veiculos/${veiculoId}/fotos`, formulario);
}

/** Atualiza legenda, data e vínculo. Os dois ids null = foto sem vínculo. */
export function editarFoto(veiculoId: number, fotoId: number, legenda: string,
  dataFoto: string, manutencaoId: number | null, diagnosticoId: number | null = null): Promise<Foto> {
  return chamarApi<Foto>("PUT", `/veiculos/${veiculoId}/fotos/${fotoId}`, {
    legenda: legenda.trim() || null,
    data_foto: dataFoto,
    manutencao_id: manutencaoId,
    diagnostico_id: diagnosticoId,
  });
}

export function usarComoCapa(veiculoId: number, fotoId: number): Promise<Foto> {
  return chamarApi<Foto>("POST", `/veiculos/${veiculoId}/fotos/${fotoId}/capa`);
}

export async function removerCapa(veiculoId: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/capa`);
}

export async function apagarFoto(veiculoId: number, fotoId: number): Promise<void> {
  await chamarApi<null>("DELETE", `/veiculos/${veiculoId}/fotos/${fotoId}`);
}

/** Confere o arquivo escolhido antes de enviar (o backend confere de novo, pelo conteúdo). */
export function erroDoArquivo(arquivo: File | null): string | null {
  if (!arquivo) return "Escolha uma foto.";
  if (arquivo.size === 0) return "O arquivo está vazio.";
  if (arquivo.size > TAMANHO_MAXIMO_FOTO) return "Foto grande demais. O limite é 10 MB.";
  return null;
}
