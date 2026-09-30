import { describe, expect, it, vi } from "vitest";

import { chamarApi, ErroDaApi, MENSAGEM_SEM_CONEXAO, requisitarApi } from "./apiCliente";

describe("requisitarApi", () => {
  it("chama /api no mesmo servidor, pedindo JSON e com o cabeçalho do app", async () => {
    const buscar = vi.fn().mockResolvedValue(new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal("fetch", buscar);
    const resposta = await requisitarApi("/saude");
    expect(resposta).toEqual({ tipo: "resposta", status: 200, corpo: { ok: true } });
    const [url, opcoes] = buscar.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/saude");
    const cabecalhos = new Headers(opcoes.headers);
    expect(cabecalhos.get("Accept")).toBe("application/json");
    expect(cabecalhos.get("X-MV-Requisicao")).toBe("1");
    expect(opcoes.credentials).toBe("same-origin");
  });

  it("informa falta de conexão sem lançar erro", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect(await requisitarApi("/saude")).toEqual({ tipo: "sem_conexao" });
  });

  it("aceita resposta que não é JSON (proxy com backend desligado)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad Gateway", { status: 502 })));
    expect(await requisitarApi("/saude")).toEqual({ tipo: "resposta", status: 502, corpo: null });
  });

  it("aceita resposta 204 sem corpo", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 204 })));
    expect(await requisitarApi("/auth/sair", { method: "POST" })).toEqual({
      tipo: "resposta",
      status: 204,
      corpo: null,
    });
  });

  it("recusa caminho sem barra inicial", async () => {
    await expect(requisitarApi("saude")).rejects.toThrow();
  });
});

describe("chamarApi", () => {
  it("envia JSON e devolve o corpo quando dá certo", async () => {
    const buscar = vi.fn().mockResolvedValue(new Response('{"id":1}', { status: 201 }));
    vi.stubGlobal("fetch", buscar);
    expect(await chamarApi("POST", "/auth/cadastro", { nome: "Ana" })).toEqual({ id: 1 });
    const [, opcoes] = buscar.mock.calls[0] as [string, RequestInit];
    expect(opcoes.method).toBe("POST");
    expect(opcoes.body).toBe('{"nome":"Ana"}');
    expect(new Headers(opcoes.headers).get("Content-Type")).toBe("application/json");
  });

  it("transforma a resposta de erro em ErroDaApi com mensagem e campos", async () => {
    const corpo = { mensagem: "E-mail já cadastrado.", campos: { email: "E-mail já cadastrado." } };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(corpo), { status: 409 })));
    const erro = await chamarApi("POST", "/auth/cadastro", {}).catch((e: unknown) => e);
    expect(erro).toBeInstanceOf(ErroDaApi);
    expect((erro as ErroDaApi).status).toBe(409);
    expect((erro as ErroDaApi).message).toBe("E-mail já cadastrado.");
    expect((erro as ErroDaApi).campos).toEqual({ email: "E-mail já cadastrado." });
  });

  it("sem conexão vira ErroDaApi com mensagem amigável", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    await expect(chamarApi("GET", "/auth/eu")).rejects.toThrow(MENSAGEM_SEM_CONEXAO);
  });
});
