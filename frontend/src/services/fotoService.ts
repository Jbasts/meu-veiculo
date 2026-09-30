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

export function listarFotos(veiculoId: number, pagina = 1, porPagina = 30): Promise<Pagina<Foto>> {
  return chamarApi<Pagina<Foto>>(
    "GET", `/veiculos/${veiculoId}/fotos?pagina=${pagina}&por_pagina=${porPagina}`);
}

export function obterFoto(veiculoId: number, fotoId: number): Promise<Foto> {
  return chamarApi<Foto>("GET", `/veiculos/${veiculoId}/fotos/${fotoId}`);
}

export function enviarFoto(veiculoId: number, dados: {
  arquivo: File;
  legenda: string;
  dataFoto: string;
  principal: boolean;
}): Promise<Foto> {
  const formulario = new FormData();
  formulario.append("arquivo", dados.arquivo);
  if (dados.legenda.trim()) formulario.append("legenda", dados.legenda.trim());
  if (dados.dataFoto) formulario.append("data_foto", dados.dataFoto);
  formulario.append("principal", dados.principal ? "true" : "false");
  return chamarApi<Foto>("POST", `/veiculos/${veiculoId}/fotos`, formulario);
}

export function editarFoto(veiculoId: number, fotoId: number, legenda: string,
  dataFoto: string): Promise<Foto> {
  return chamarApi<Foto>("PUT", `/veiculos/${veiculoId}/fotos/${fotoId}`, {
    legenda: legenda.trim() || null,
    data_foto: dataFoto,
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
