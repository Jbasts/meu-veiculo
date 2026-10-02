// Formatos de backend/app/schemas/admin_schema.py. Nenhum tem senha ou token.

import type { Perfil } from "./usuario";

export interface UsuarioAdmin {
  id: number;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
  /** null = nunca entrou (por exemplo, convite ainda não aceito). */
  ultimo_acesso: string | null;
  criado_em: string;
  veiculos_ativos: number;
  veiculos: number;
}

export interface VeiculoComDono {
  id: number;
  usuario_id: number;
  marca: string;
  modelo: string;
  ano: number;
  placa: string;
  ativo: boolean;
  dono_nome: string;
  dono_ativo: boolean;
}

export interface PaginaUsuariosAdmin {
  itens: UsuarioAdmin[];
  total: number;
  pagina: number;
  por_pagina: number;
  por_perfil: Record<Perfil, number>;
}

export interface PaginaVeiculosAdmin {
  itens: VeiculoComDono[];
  total: number;
  pagina: number;
  por_pagina: number;
}

export interface UsuarioDetalheAdmin {
  usuario: UsuarioAdmin;
  veiculos: VeiculoComDono[];
}

export interface ResumoAdmin {
  usuarios: number;
  veiculos: number;
}

export interface LinkEnviado {
  tipo: "convite" | "recuperacao";
  mensagem: string;
}

export interface ConviteCriado {
  detalhe: UsuarioDetalheAdmin;
  mensagem: string;
}
