// Registro do service worker (public/sw.js), que torna o app instalável e
// mostra a página "sem conexão" quando o servidor não responde.
//
// Só é registrado:
// - na versão gerada por "npm run build" (no "npm run dev" ele atrapalharia a
//   atualização automática das telas enquanto o código muda);
// - em contexto seguro: https://... ou http://localhost. Num endereço como
//   http://192.168.0.10, o navegador não permite service worker (README, seção 18).

export function deveRegistrarServiceWorker(producao: boolean, contextoSeguro: boolean, temSuporte: boolean): boolean {
  return producao && contextoSeguro && temSuporte;
}

export function registrarServiceWorker(): void {
  const temSuporte = typeof navigator !== "undefined" && "serviceWorker" in navigator;
  if (!deveRegistrarServiceWorker(import.meta.env.PROD, window.isSecureContext, temSuporte)) {
    return;
  }
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/sw.js").catch(() => {
      // Sem service worker o app funciona igual; só não fica instalável.
      console.warn("Não foi possível registrar o service worker do Meu Veículo.");
    });
  });
}
