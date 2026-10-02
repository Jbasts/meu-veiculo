import { existsSync, readFileSync } from "node:fs";
import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// HTTPS na rede de casa ("npm run dev:https" e "npm run app:https"): usa o
// certificado criado pelo mkcert (README, seção 18.8). Os dois arquivos ficam
// em frontend/certificados, que não vai para o Git (a chave é secreta).
const PASTA_CERTIFICADOS = resolve(import.meta.dirname, "certificados");
const CERTIFICADO = resolve(PASTA_CERTIFICADOS, "meu-veiculo.pem");
const CHAVE = resolve(PASTA_CERTIFICADOS, "meu-veiculo-chave.pem");

function lerCertificado() {
  if (!existsSync(CERTIFICADO) || !existsSync(CHAVE)) {
    throw new Error(
      `HTTPS: não encontrei meu-veiculo.pem e meu-veiculo-chave.pem na pasta ${PASTA_CERTIFICADOS}. ` +
        "Crie os dois com o mkcert (README, seção 18.8) ou use \"npm run dev:celular\" / " +
        "\"npm run app:celular\" (sem HTTPS).",
    );
  }
  return { cert: readFileSync(CERTIFICADO), key: readFileSync(CHAVE) };
}

// O frontend chama sempre "/api/...". Em desenvolvimento, o Vite repassa
// essas chamadas para o backend (proxy). Assim, frontend e API ficam no
// mesmo endereço: o navegador (e depois o celular) só precisa conhecer o
// endereço do frontend, e o PostgreSQL nunca fica exposto.
export default defineConfig(({ mode }) => {
  const https = mode === "https" ? lerCertificado() : undefined;
  // xfwd: repassa o endereço de quem acessou (X-Forwarded-For). O backend
  // usa esse endereço no limite de tentativas de login. Com HTTPS, só o
  // trecho celular → Vite é criptografado; Vite → backend fica dentro do
  // próprio computador (127.0.0.1).
  const proxy = { "/api": { target: "http://127.0.0.1:8000", xfwd: true } };
  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      https,
      proxy,
    },
    // "npm run app:celular" / "app:https": versão gerada pelo build (com o
    // service worker da PWA), servida na porta 4173, com o mesmo proxy /api.
    // O backend continua só em 127.0.0.1: o celular fala com o Vite, e o
    // Vite fala com o backend no próprio computador.
    preview: {
      port: 4173,
      strictPort: true,
      https,
      proxy,
    },
    test: {
      environment: "jsdom",
      setupFiles: ["./src/tests/setup.ts"],
    },
  };
});
