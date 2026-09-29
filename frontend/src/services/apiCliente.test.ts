import { describe, expect, it, vi } from "vitest";

import { requisitarApi } from "./apiCliente";

describe("requisitarApi", () => {
  it("chama o endereço /api no mesmo servidor, pedindo JSON", async () => {
    const buscar = vi.fn().mockResolvedValue(new Response('{"ok":true}', { status: 200 }));
    vi.stubGlobal("fetch", buscar);
    const resposta = await requisitarApi("/saude");
    expect(resposta).toEqual({ tipo: "resposta", status: 200, corpo: { ok: true } });
    const [url, opcoes] = buscar.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("/api/saude");
    expect(new Headers(opcoes.headers).get("Accept")).toBe("application/json");
  });

  it("informa falta de conexão sem lançar erro", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("Failed to fetch")));
    expect(await requisitarApi("/saude")).toEqual({ tipo: "sem_conexao" });
  });

  it("aceita resposta que não é JSON (proxy com backend desligado)", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad Gateway", { status: 502 })));
    expect(await requisitarApi("/saude")).toEqual({ tipo: "resposta", status: 502, corpo: null });
  });

  it("recusa caminho sem barra inicial", async () => {
    await expect(requisitarApi("saude")).rejects.toThrow();
  });
});
