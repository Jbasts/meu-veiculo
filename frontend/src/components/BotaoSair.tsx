import { useState } from "react";
import { useNavigate } from "react-router";

import { useAuth } from "../contexts/AuthContext";

function IconeSair() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 4H5a1 1 0 0 0-1 1v14a1 1 0 0 0 1 1h4" />
      <path d="M14 8l4 4-4 4" />
      <path d="M18 12H9" />
    </svg>
  );
}

// "Sair" em vermelho, como no PDF (tela Mais).
export default function BotaoSair() {
  const { sair } = useAuth();
  const navegar = useNavigate();
  const [saindo, setSaindo] = useState(false);

  async function aoClicar() {
    if (saindo) return;
    setSaindo(true);
    try {
      await sair();
    } finally {
      navegar("/entrar", { replace: true });
    }
  }

  return (
    <button type="button" className="menu__item menu__item--perigo" onClick={() => void aoClicar()}
      disabled={saindo}>
      <IconeSair />
      <span>{saindo ? "Saindo…" : "Sair"}</span>
    </button>
  );
}
