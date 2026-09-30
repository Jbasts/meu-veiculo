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
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
  },
});
