import type { ReactNode } from "react";
import { Link } from "react-router";

interface Props {
  titulo: string;
  voltarPara: string;
  /** "grande" = título da página (Criar conta); "barra" = barra fina (Conta e senha). */
  estilo?: "grande" | "barra";
  /** Botão à direita da barra (ex.: lápis de editar, "+" de adicionar). */
  acao?: ReactNode;
}

export default function TopoComVoltar({ titulo, voltarPara, estilo = "barra", acao }: Props) {
  return (
    <header className={`topo topo--${estilo}`}>
      <Link to={voltarPara} className="topo__voltar" aria-label="Voltar">
        <svg viewBox="0 0 24 24" width="26" height="26" aria-hidden="true" fill="none"
          stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 5l-7 7 7 7" />
        </svg>
      </Link>
      {estilo === "barra" ? <h1 className="topo__titulo">{titulo}</h1> : null}
      {estilo === "grande" ? <h1 className="titulo-pagina">{titulo}</h1> : null}
      {acao ? <div className="topo__acao">{acao}</div> : null}
    </header>
  );
}
