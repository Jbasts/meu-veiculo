// Apoio aos testes: uma API falsa (fetch simulado) e o app num roteador em memória.

import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { vi } from "vitest";

import { RotasDoApp } from "../App";
import { AuthProvider } from "../contexts/AuthContext";
import type { Usuario } from "../types/usuario";

export const PAULA: Usuario = {
  id: 1,
  nome: "Paula Bastos",
  email: "paula@email.com",
  perfil: "padrao",
  ativo: true,
};

export function json(status: number, corpo: unknown): Response {
  return new Response(corpo === null ? null : JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

type Tratador = (corpo: unknown, opcoes: RequestInit) => Response | Promise<Response>;

/**
 * Simula a API: chave "MÉTODO /caminho" → resposta. Devolve o mock para conferir chamadas.
 * Quem não simular "GET /api/veiculos" recebe uma conta sem veículos.
 */
export function apiFalsa(rotas: Record<string, Tratador>) {
  const todas: Record<string, Tratador> = { "GET /api/veiculos": () => json(200, []), ...rotas };
  const buscar = vi.fn(async (url: string, opcoes: RequestInit = {}) => {
    const chave = `${opcoes.method ?? "GET"} ${url}`;
    const tratador = todas[chave];
    if (!tratador) throw new Error(`Rota não simulada no teste: ${chave}`);
    const corpo = typeof opcoes.body === "string" ? JSON.parse(opcoes.body) : undefined;
    return tratador(corpo, opcoes);
  });
  vi.stubGlobal("fetch", buscar);
  return buscar;
}

export function chamadasPara(buscar: ReturnType<typeof apiFalsa>, chave: string): [string, RequestInit][] {
  return buscar.mock.calls
    .map(([url, opcoes]): [string, RequestInit] => [url, opcoes ?? {}])
    .filter(([url, opcoes]) => `${opcoes.method ?? "GET"} ${url}` === chave);
}

export function renderizarApp(endereco: string) {
  return render(
    <MemoryRouter initialEntries={[endereco]}>
      <AuthProvider>
        <RotasDoApp />
      </AuthProvider>
    </MemoryRouter>,
  );
}
