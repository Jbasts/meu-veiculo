// Ícones em traço, no estilo do PDF. Todos são decorativos (aria-hidden):
// o texto ao lado é que descreve a ação.

import type { ReactNode } from "react";

function Icone({ children, tamanho = 24 }: { children: ReactNode; tamanho?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={tamanho} height={tamanho} aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      {children}
    </svg>
  );
}

interface Props {
  tamanho?: number;
}

export const IconeInicio = (p: Props) => (
  <Icone {...p}><path d="M3 11l9-7 9 7" /><path d="M5 10v10h14V10" /><path d="M10 20v-5h4v5" /></Icone>
);
export const IconeManutencao = (p: Props) => (
  <Icone {...p}><path d="M14.5 6.5a4 4 0 0 0 5 5L10 21a2.1 2.1 0 0 1-3-3l9.5-9.5a4 4 0 0 1-2-2z" /><path d="M14.5 6.5l3-3a4 4 0 0 0-5 5" /></Icone>
);
export const IconeDiagnostico = (p: Props) => (
  <Icone {...p}><path d="M6 3v6a5 5 0 0 0 10 0V3" /><path d="M11 14v2a4 4 0 0 0 8 0v-2" /><circle cx="19" cy="12" r="2" /></Icone>
);
export const IconeFinancas = (p: Props) => (
  <Icone {...p}><rect x="3" y="6" width="18" height="13" rx="2" /><path d="M3 10h18" /><path d="M15 15h2" /></Icone>
);
export const IconeMais = (p: Props) => (
  <Icone {...p}><rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" /><rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" /></Icone>
);
export const IconeCarro = (p: Props) => (
  <Icone {...p}><path d="M5 11l2-5h10l2 5" /><rect x="3" y="11" width="18" height="6" rx="2" /><circle cx="7.5" cy="17.5" r="1.5" /><circle cx="16.5" cy="17.5" r="1.5" /></Icone>
);
export const IconeCamera = (p: Props) => (
  <Icone {...p}><path d="M4 8h3l2-3h6l2 3h3v11H4z" /><circle cx="12" cy="13" r="3.5" /></Icone>
);
export const IconeImagem = (p: Props) => (
  <Icone {...p}><rect x="4" y="4" width="16" height="16" rx="2" /><circle cx="15" cy="9" r="1.5" /><path d="M4 17l5-5 4 4 2-2 5 5" /></Icone>
);
export const IconeSeta = (p: Props) => <Icone {...p}><path d="M9 5l7 7-7 7" /></Icone>;
export const IconeSetaBaixo = (p: Props) => <Icone {...p}><path d="M6 9l6 6 6-6" /></Icone>;
export const IconeMaisSinal = (p: Props) => <Icone {...p}><path d="M12 5v14" /><path d="M5 12h14" /></Icone>;
export const IconeLapis = (p: Props) => (
  <Icone {...p}><path d="M4 20l1-4L16 5l3 3L8 19z" /><path d="M14 7l3 3" /></Icone>
);
export const IconeCadeado = (p: Props) => (
  <Icone {...p}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></Icone>
);
export const IconeCheck = (p: Props) => <Icone {...p}><path d="M5 12l5 5 9-10" /></Icone>;
export const IconeRelogio = (p: Props) => (
  <Icone {...p}><circle cx="12" cy="12" r="8.5" /><path d="M12 8v4l3 2" /></Icone>
);
export const IconeFerramentas = (p: Props) => (
  <Icone {...p}><circle cx="12" cy="12" r="3" /><path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" /></Icone>
);
export const IconeBomba = (p: Props) => (
  <Icone {...p}><path d="M4 20V5a1 1 0 0 1 1-1h8a1 1 0 0 1 1 1v15" /><path d="M3 20h12" /><path d="M7 8h4" /><path d="M14 10h2a2 2 0 0 1 2 2v4a1.5 1.5 0 0 0 3 0V8l-3-3" /></Icone>
);
export const IconeRecibo = (p: Props) => (
  <Icone {...p}><path d="M6 3h12v18l-2-1.5-2 1.5-2-1.5-2 1.5-2-1.5L6 21z" /><path d="M9 8h6" /><path d="M9 12h6" /><path d="M9 16h3" /></Icone>
);
export const IconeCalendario = (p: Props) => (
  <Icone {...p}><rect x="4" y="5" width="16" height="15" rx="2" /><path d="M4 10h16" /><path d="M9 3v4" /><path d="M15 3v4" /></Icone>
);
export const IconeSetaEsquerda = (p: Props) => <Icone {...p}><path d="M15 5l-7 7 7 7" /></Icone>;
export const IconeProjeto = (p: Props) => (
  <Icone {...p}><path d="M12 3l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.4 6.8 19.1l1-5.8L3.5 9.2l5.9-.9z" /></Icone>
);
