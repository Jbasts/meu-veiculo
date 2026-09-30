import type { ReactNode } from "react";

interface Props {
  enviando: boolean;
  textoEnviando?: string;
  children: ReactNode;
}

// Botão de envio de formulário: fica desativado enquanto envia,
// para evitar envio duplicado (dois toques rápidos).
export default function BotaoEnviar({ enviando, textoEnviando = "Enviando…", children }: Props) {
  return (
    <button type="submit" className="botao botao--primario" disabled={enviando} aria-busy={enviando}>
      {enviando ? textoEnviando : children}
    </button>
  );
}
