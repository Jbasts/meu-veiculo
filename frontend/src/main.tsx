import "@fontsource/barlow/400.css";
import "@fontsource/barlow/500.css";
import "@fontsource/barlow/600.css";
import "@fontsource/barlow-condensed/600.css";
import "@fontsource/barlow-condensed/700.css";
import "./styles/tema.css";
import "./styles/veiculos.css";
import "./styles/manutencao.css";
import "./styles/diagnostico.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";

const raiz = document.getElementById("raiz");
if (!raiz) {
  throw new Error("Elemento #raiz não encontrado no index.html");
}

createRoot(raiz).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
