// Service worker do Meu Veículo (PWA).
//
// O que ele faz, e só isso:
// 1. Guarda a página "sem conexão" (offline.html), que não depende de outro arquivo.
// 2. Quando uma TELA do app não abre por falta de conexão, mostra essa página.
//
// O que ele NÃO faz, de propósito:
// - Não guarda nenhuma resposta de /api (veículos, gastos, fotos...). Os dados
//   da conta nunca ficam no Cache Storage, então sair ou trocar de conta não
//   deixa nada para trás. A API ainda manda "Cache-Control: no-store".
// - Não promete uso offline: cadastrar e consultar exigem conexão com o servidor.
//
// Para publicar uma versão nova deste arquivo, troque VERSAO: o cache antigo
// é apagado quando a nova versão assume.

const VERSAO = "mv-2";
const ARQUIVOS_FIXOS = ["/offline.html"];

self.addEventListener("install", (evento) => {
  evento.waitUntil(
    caches.open(VERSAO).then((cache) => cache.addAll(ARQUIVOS_FIXOS)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evento) => {
  evento.waitUntil(
    caches
      .keys()
      .then((nomes) => Promise.all(nomes.filter((nome) => nome !== VERSAO).map((nome) => caches.delete(nome))))
      .then(() => self.clients.claim()),
  );
});

async function telaOuAvisoSemConexao(requisicao) {
  try {
    return await fetch(requisicao);
  } catch {
    const guardada = await caches.match("/offline.html");
    return (
      guardada ??
      new Response("Sem conexão com o servidor do Meu Veículo.", {
        status: 503,
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      })
    );
  }
}

self.addEventListener("fetch", (evento) => {
  const requisicao = evento.request;
  const endereco = new URL(requisicao.url);
  // Outros sites, a API e tudo que não é abrir uma tela seguem direto para a rede.
  if (endereco.origin !== self.location.origin) return;
  if (endereco.pathname === "/api" || endereco.pathname.startsWith("/api/")) return;
  if (requisicao.method !== "GET" || requisicao.mode !== "navigate") return;
  evento.respondWith(telaOuAvisoSemConexao(requisicao));
});
