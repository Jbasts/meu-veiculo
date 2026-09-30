import type { Usuario } from "../types/usuario";
import { chamarApi, ErroDaApi } from "./apiCliente";

interface Mensagem {
  mensagem: string;
}

export function cadastrar(dados: {
  nome: string;
  email: string;
  senha: string;
  confirmacao_senha: string;
}): Promise<Usuario> {
  return chamarApi<Usuario>("POST", "/auth/cadastro", dados);
}

export function entrar(email: string, senha: string): Promise<Usuario> {
  return chamarApi<Usuario>("POST", "/auth/entrar", { email, senha });
}

export async function sair(): Promise<void> {
  await chamarApi<null>("POST", "/auth/sair");
}

/** Usuário da sessão atual, ou null se ninguém estiver logado. */
export async function obterUsuarioAtual(): Promise<Usuario | null> {
  try {
    return await chamarApi<Usuario>("GET", "/auth/eu");
  } catch (erro) {
    if (erro instanceof ErroDaApi && erro.status === 401) return null;
    throw erro;
  }
}

export function alterarSenha(dados: {
  senha_atual: string;
  nova_senha: string;
  confirmacao_senha: string;
}): Promise<Mensagem> {
  return chamarApi<Mensagem>("POST", "/auth/alterar-senha", dados);
}

export function solicitarRecuperacao(email: string): Promise<Mensagem> {
  return chamarApi<Mensagem>("POST", "/auth/recuperar-senha", { email });
}

export function redefinirSenha(dados: {
  token: string;
  nova_senha: string;
  confirmacao_senha: string;
}): Promise<Mensagem> {
  return chamarApi<Mensagem>("POST", "/auth/redefinir-senha", dados);
}
