import type { ReactNode } from "react";

// ok = verde-petróleo, aviso = amarelo, alerta = vermelho, neutro = cinza.
export type TomStatus = "ok" | "aviso" | "alerta" | "neutro";

interface Props {
  tom: TomStatus;
  children: ReactNode;
}

export default function SeloStatus({ tom, children }: Props) {
  return <span className={`selo selo--${tom}`}>{children}</span>;
}
