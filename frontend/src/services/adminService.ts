// Chamadas à área de administração (/api/admin/...). O backend recusa (403) quem não é admin:
// esconder o menu é só conforto, a proteção está lá.

import type {
  ConviteCriado,
  LinkEnviado,
  PaginaUsuariosAdmin,
  PaginaVeiculosAdmin,
  ResumoAdmin,
  UsuarioDetalheAdmin,
} from "../types/admin";
import type { Perfil } from "../types/usuario";
import { chamarApi } from "./apiCliente";

function consulta(valores: Record<string, string | number | null | undefined>): string {
  const parametros = new URLSearchParams();
  for (const [chave, valor] of Object.entries(valores)) {
    if (valor !== null && valor !== undefined && valor !== "") parametros.set(chave, String(valor));
  }
  return parametros.toString();
}

export function obterResumoAdmin(): Promise<ResumoAdmin> {
  return chamarApi<ResumoAdmin>("GET", "/admin/resumo");
}

export function listarUsuarios(busca: string, perfil: Perfil | null, pagina = 1,
  porPagina = 30): Promise<PaginaUsuariosAdmin> {
  return chamarApi<PaginaUsuariosAdmin>("GET",
    `/admin/usuarios?${consulta({ busca: busca.trim(), perfil, pagina, por_pagina: porPagina })}`);
}

export function listarTodosOsVeiculos(busca: string, pagina = 1, porPagina = 30): Promise<PaginaVeiculosAdmin> {
  return chamarApi<PaginaVeiculosAdmin>("GET",
    `/admin/veiculos?${consulta({ busca: busca.trim(), pagina, por_pagina: porPagina })}`);
}

export function obterUsuario(id: number): Promise<UsuarioDetalheAdmin> {
  return chamarApi<UsuarioDetalheAdmin>("GET", `/admin/usuarios/${id}`);
}

export function alterarUsuario(id: number, perfil: Perfil, ativo: boolean): Promise<UsuarioDetalheAdmin> {
  return chamarApi<UsuarioDetalheAdmin>("PUT", `/admin/usuarios/${id}`, { perfil, ativo });
}

export function enviarLinkDeSenha(id: number): Promise<LinkEnviado> {
  return chamarApi<LinkEnviado>("POST", `/admin/usuarios/${id}/enviar-link`);
}

export function convidarUsuario(nome: string, email: string): Promise<ConviteCriado> {
  return chamarApi<ConviteCriado>("POST", "/admin/usuarios", { nome, email });
}
