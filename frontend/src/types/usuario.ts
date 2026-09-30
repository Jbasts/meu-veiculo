// Formato de backend/app/schemas/auth_schema.py (UsuarioResposta).

export type Perfil = "admin" | "padrao";

export interface Usuario {
  id: number;
  nome: string;
  email: string;
  perfil: Perfil;
  ativo: boolean;
}
