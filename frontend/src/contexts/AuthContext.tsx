// Guarda "quem está logado" para todas as telas.
//
// Ao abrir o app, pergunta ao backend (/api/auth/eu). Os dados da pessoa
// ficam só na memória da página: nada é gravado no navegador
// (localStorage), então, depois de sair, não sobra informação da conta.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { definirAoPerderSessao } from "../services/apiCliente";
import * as authService from "../services/authService";
import type { Usuario } from "../types/usuario";

interface EstadoAuth {
  /** true enquanto confere, ao abrir o app, se já existe uma sessão. */
  carregando: boolean;
  usuario: Usuario | null;
  /** Mensagem quando não foi possível conferir a sessão (servidor fora do ar). */
  erroInicial: string | null;
  entrar: (email: string, senha: string) => Promise<Usuario>;
  sair: () => Promise<void>;
  /** Esquece o usuário localmente (ex.: a API respondeu 401 no meio do uso). */
  esquecerUsuario: () => void;
  recarregar: () => Promise<void>;
}

const ContextoAuth = createContext<EstadoAuth | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erroInicial, setErroInicial] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    setCarregando(true);
    try {
      setUsuario(await authService.obterUsuarioAtual());
      setErroInicial(null);
    } catch (erro) {
      setUsuario(null);
      setErroInicial(erro instanceof Error ? erro.message : "Não foi possível conferir sua sessão.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  const entrar = useCallback(async (email: string, senha: string) => {
    const novo = await authService.entrar(email, senha);
    setUsuario(novo);
    return novo;
  }, []);

  const sair = useCallback(async () => {
    try {
      await authService.sair();
    } finally {
      // Mesmo se o servidor não responder, a tela deixa de mostrar a conta.
      setUsuario(null);
    }
  }, []);

  const esquecerUsuario = useCallback(() => setUsuario(null), []);

  // Sessão encerrada no meio do uso (API respondeu 401): volta para Entrar.
  useEffect(() => {
    definirAoPerderSessao(esquecerUsuario);
    return () => definirAoPerderSessao(null);
  }, [esquecerUsuario]);

  const valor = useMemo<EstadoAuth>(
    () => ({ carregando, usuario, erroInicial, entrar, sair, esquecerUsuario, recarregar }),
    [carregando, usuario, erroInicial, entrar, sair, esquecerUsuario, recarregar],
  );

  return <ContextoAuth.Provider value={valor}>{children}</ContextoAuth.Provider>;
}

export function useAuth(): EstadoAuth {
  const contexto = useContext(ContextoAuth);
  if (!contexto) {
    throw new Error("useAuth precisa estar dentro de <AuthProvider>.");
  }
  return contexto;
}
