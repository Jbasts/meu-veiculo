// PWA: manifesto, registro e service worker (public/sw.js).
//
// O service worker roda aqui com um "self" e um "caches" falsos, para conferir
// a regra mais importante: nada de /api passa por ele nem vai para o cache.

import { describe, expect, it, vi } from "vitest";

import codigoSw from "../../public/sw.js?raw";
import textoManifesto from "../../public/manifest.webmanifest?raw";
import textoOffline from "../../public/offline.html?raw";
import { deveRegistrarServiceWorker } from "../utils/pwa";

const ORIGEM = "http://localhost:4173";
const arquivosPublicos = Object.keys(import.meta.glob("/public/*"));

type Ouvinte = (evento: unknown) => void;

function carregarServiceWorker(opcoes: { fetch?: () => Promise<Response>; cachesExistentes?: string[] } = {}) {
  const ouvintes: Record<string, Ouvinte> = {};
  const guardado = new Map<string, string[]>();
  const apagados: string[] = [];
  const paginaOffline = new Response("<h1>Sem conexão com o servidor</h1>", { status: 200 });
  const caches = {
    open: vi.fn(async (nome: string) => ({
      addAll: async (lista: string[]) => {
        guardado.set(nome, lista);
      },
    })),
    keys: vi.fn(async () => opcoes.cachesExistentes ?? []),
    delete: vi.fn(async (nome: string) => {
      apagados.push(nome);
      return true;
    }),
    match: vi.fn(async (caminho: string) => (caminho === "/offline.html" ? paginaOffline : undefined)),
  };
  const self = {
    location: { origin: ORIGEM },
    addEventListener: (tipo: string, ouvinte: Ouvinte) => {
      ouvintes[tipo] = ouvinte;
    },
    skipWaiting: vi.fn(async () => undefined),
    clients: { claim: vi.fn(async () => undefined) },
  };
  const buscar = vi.fn(opcoes.fetch ?? (async () => new Response("rede")));
  new Function("self", "caches", "fetch", codigoSw)(self, caches, buscar);

  function pedir(caminho: string, metodo = "GET", modo = "cors") {
    const respondWith = vi.fn();
    const url = caminho.startsWith("http") ? caminho : `${ORIGEM}${caminho}`;
    ouvintes.fetch({ request: { url, method: metodo, mode: modo }, respondWith });
    return respondWith;
  }

  async function disparar(tipo: "install" | "activate") {
    let espera: Promise<unknown> = Promise.resolve();
    ouvintes[tipo]({ waitUntil: (p: Promise<unknown>) => (espera = p) });
    await espera;
  }

  return { pedir, disparar, guardado, apagados, buscar, paginaOffline };
}

describe("service worker", () => {
  it("não intercepta nenhuma chamada à API, nem ao abrir um endereço da API direto", () => {
    const sw = carregarServiceWorker();
    expect(sw.pedir("/api/veiculos")).not.toHaveBeenCalled();
    expect(sw.pedir("/api/auth/sair", "POST")).not.toHaveBeenCalled();
    expect(sw.pedir("/api/veiculos/3/fotos/9/arquivo", "GET", "no-cors")).not.toHaveBeenCalled();
    expect(sw.pedir("/api/veiculos/3/fotos/9/arquivo", "GET", "navigate")).not.toHaveBeenCalled();
    expect(sw.pedir("/api", "GET", "navigate")).not.toHaveBeenCalled();
  });

  it("deixa arquivos, gravações e outros sites seguirem direto para a rede", () => {
    const sw = carregarServiceWorker();
    expect(sw.pedir("/assets/index-abc123.js", "GET", "cors")).not.toHaveBeenCalled();
    expect(sw.pedir("/financas", "POST", "navigate")).not.toHaveBeenCalled();
    expect(sw.pedir("https://exemplo.com/financas", "GET", "navigate")).not.toHaveBeenCalled();
  });

  it("abre a tela pela rede quando há conexão", async () => {
    const sw = carregarServiceWorker();
    const respondWith = sw.pedir("/financas", "GET", "navigate");
    expect(respondWith).toHaveBeenCalledTimes(1);
    const resposta: Response = await respondWith.mock.calls[0][0];
    expect(await resposta.text()).toBe("rede");
  });

  it("sem conexão, mostra a página guardada de aviso, não dados", async () => {
    const sw = carregarServiceWorker({ fetch: () => Promise.reject(new TypeError("Failed to fetch")) });
    const respondWith = sw.pedir("/veiculos/3", "GET", "navigate");
    const resposta: Response = await respondWith.mock.calls[0][0];
    expect(resposta).toBe(sw.paginaOffline);
  });

  it("guarda só a página de aviso e apaga caches de versões antigas", async () => {
    const sw = carregarServiceWorker({ cachesExistentes: ["mv-1", "mv-2"] });
    await sw.disparar("install");
    const tudoGuardado = [...sw.guardado.values()].flat();
    expect(tudoGuardado).toEqual(["/offline.html"]);
    expect(tudoGuardado.some((caminho) => caminho.startsWith("/api"))).toBe(false);
    await sw.disparar("activate");
    expect(sw.apagados).toEqual(["mv-1"]);
  });
});

describe("manifesto", () => {
  const manifesto = JSON.parse(textoManifesto) as {
    name: string;
    start_url: string;
    display: string;
    lang: string;
    icons: { src: string; sizes: string; type: string; purpose: string }[];
  };

  it("tem nome, início, modo app e idioma", () => {
    expect(manifesto.name).toBe("Meu Veículo");
    expect(manifesto.start_url).toBe("/");
    expect(manifesto.display).toBe("standalone");
    expect(manifesto.lang).toBe("pt-BR");
  });

  it("tem os ícones de 192 e 512 exigidos para instalar, e todos existem em public/", () => {
    const tamanhos = manifesto.icons.filter((i) => i.purpose === "any").map((i) => i.sizes);
    expect(tamanhos).toEqual(expect.arrayContaining(["192x192", "512x512"]));
    expect(manifesto.icons.some((i) => i.purpose === "maskable")).toBe(true);
    for (const icone of manifesto.icons) {
      expect(arquivosPublicos).toContain(`/public${icone.src}`);
    }
    expect(arquivosPublicos).toContain("/public/offline.html");
    expect(arquivosPublicos).toContain("/public/apple-touch-icon.png");
  });

  it("a página sem conexão não depende de nenhum outro arquivo", () => {
    expect(textoOffline).not.toMatch(/(src|href)=/);
  });
});

describe("registro do service worker", () => {
  it("só registra na versão gerada pelo build, em contexto seguro e com suporte", () => {
    expect(deveRegistrarServiceWorker(true, true, true)).toBe(true);
    expect(deveRegistrarServiceWorker(false, true, true)).toBe(false);
    // http://192.168.x.x no celular não é contexto seguro.
    expect(deveRegistrarServiceWorker(true, false, true)).toBe(false);
    expect(deveRegistrarServiceWorker(true, true, false)).toBe(false);
  });
});
