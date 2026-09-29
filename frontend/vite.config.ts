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
      "/api": { target: "http://127.0.0.1:8000" },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/tests/setup.ts"],
  },
});
