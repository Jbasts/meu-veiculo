import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router";

import { useAuth } from "../contexts/AuthContext";

function Carregando() {
  return (
    <div className="pagina pagina--centro" aria-busy="true">
      <p className="texto-suave">Carregando…</p>
    </div>
  );
}

/** Só para quem está logado; os demais vão para "Entrar" e voltam depois. */
export function RotaProtegida({ children }: { children: ReactNode }) {
  const { carregando, usuario } = useAuth();
  const local = useLocation();
  if (carregando) return <Carregando />;
  if (!usuario) {
    return <Navigate to="/entrar" replace state={{ destino: local.pathname }} />;
  }
  return <>{children}</>;
}

/** Telas de entrada: quem já está logado vai direto para o início. */
export function RotaSoParaVisitante({ children }: { children: ReactNode }) {
  const { carregando, usuario } = useAuth();
  if (carregando) return <Carregando />;
  if (usuario) return <Navigate to="/" replace />;
  return <>{children}</>;
}
