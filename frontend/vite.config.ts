import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// O frontend chama sempre "/api/...". Em desenvolvimento, o Vite repassa
// essas chamadas para o backend (proxy). Assim, frontend e API ficam no
// mesmo endereço: o navegador (e depois o celular) só precisa conhecer o
// endereço do frontend, e o PostgreSQL nunca fica exposto.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      // xfwd: repassa o endereço de quem acessou (X-Forwarded-For). O backend
      // usa esse endereço no limite de tentativas de login.
      "/api": { target: "http://127.0.0.1:8000", xfwd: true },
    },
  },
  // "npm run app:celular": versão gerada pelo build (com o service worker da
  // PWA), servida na porta 4173. Usa o mesmo proxy /api do servidor de
  // desenvolvimento. O backend continua só em 127.0.0.1: o celular fala com
  // o Vite, e o Vite fala com o backend no próprio computador.
  preview: {
    port: 4173,
    strictPort: true,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
  },
});
