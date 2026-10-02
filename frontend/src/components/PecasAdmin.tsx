// Peças da área de administração.

import type { UsuarioAdmin } from "../types/admin";
import { diaDoInstante, formatarDataIso, hojeIso } from "../utils/datas";

/** "acesso hoje", "acesso em 21/09/2026" ou "nunca entrou". */
export function textoDoAcesso(usuario: Pick<UsuarioAdmin, "ultimo_acesso">, hoje = hojeIso()): string {
  if (!usuario.ultimo_acesso) return "nunca entrou";
  const dia = diaDoInstante(usuario.ultimo_acesso);
  return dia === hoje ? "acesso hoje" : `acesso em ${formatarDataIso(dia)}`;
}

/** "1 veículo, acesso hoje" ou "2 veículos, conta desativada" (como no PDF). */
export function resumoDoUsuario(usuario: UsuarioAdmin, hoje = hojeIso()): string {
  const veiculos = usuario.veiculos === 1 ? "1 veículo" : `${usuario.veiculos} veículos`;
  return `${veiculos}, ${usuario.ativo ? textoDoAcesso(usuario, hoje) : "conta desativada"}`;
}

export function SeloPerfil({ perfil }: { perfil: UsuarioAdmin["perfil"] }) {
  return <span className="selo selo--neutro">{perfil === "admin" ? "Admin" : "Padrão"}</span>;
}
