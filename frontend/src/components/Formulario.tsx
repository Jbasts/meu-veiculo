// Peças de formulário além do CampoTexto: grupo de opções (os botões em
// "pílula" do PDF), chave liga/desliga e diálogo de confirmação.

import { useEffect, useId, useRef, type ReactNode } from "react";

interface PropsOpcoes<T extends string> {
  rotulo: string;
  opcoes: { valor: T; rotulo: string }[];
  valor: T;
  aoMudar: (valor: T) => void;
  erro?: string | null;
}

/** Escolha única entre poucas opções (ex.: combustível). */
export function GrupoOpcoes<T extends string>({ rotulo, opcoes, valor, aoMudar, erro }: PropsOpcoes<T>) {
  const id = useId();
  return (
    <div className="campo" role="radiogroup" aria-labelledby={id}>
      <span className="campo__rotulo" id={id}>{rotulo}</span>
      <div className="opcoes">
        {opcoes.map((opcao) => (
          <button key={opcao.valor} type="button" role="radio" aria-checked={valor === opcao.valor}
            className={`opcao${valor === opcao.valor ? " opcao--ativa" : ""}`}
            onClick={() => aoMudar(opcao.valor)}>
            {opcao.rotulo}
          </button>
        ))}
      </div>
      {erro && <p className="campo__erro" role="alert">{erro}</p>}
    </div>
  );
}

interface PropsChave {
  titulo: string;
  descricao: string;
  ligada: boolean;
  aoMudar: (ligada: boolean) => void;
}

/** Cartão com chave liga/desliga (ex.: "Usar como capa"). */
export function Chave({ titulo, descricao, ligada, aoMudar }: PropsChave) {
  const id = useId();
  return (
    <div className="cartao chave">
      <div>
        <p className="cartao__titulo" id={id}>{titulo}</p>
        <p className="texto-suave chave__descricao">{descricao}</p>
      </div>
      <button type="button" role="switch" aria-checked={ligada} aria-labelledby={id}
        className={`chave__botao${ligada ? " chave__botao--ligada" : ""}`}
        onClick={() => aoMudar(!ligada)}>
        <span className="chave__bolinha" />
      </button>
    </div>
  );
}

interface PropsDialogo {
  titulo: string;
  children: ReactNode;
  textoConfirmar: string;
  perigo?: boolean;
  ocupado?: boolean;
  aoConfirmar: () => void;
  aoCancelar: () => void;
}

/** Pergunta antes de uma ação que não dá para desfazer com um toque. */
export function DialogoConfirmacao({ titulo, children, textoConfirmar, perigo = false,
  ocupado = false, aoConfirmar, aoCancelar }: PropsDialogo) {
  const id = useId();
  const botaoCancelar = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    botaoCancelar.current?.focus();
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") aoCancelar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoCancelar]);

  return (
    <div className="dialogo__fundo">
      <div className="dialogo" role="alertdialog" aria-modal="true" aria-labelledby={id}>
        <h2 className="dialogo__titulo" id={id}>{titulo}</h2>
        <div className="dialogo__texto">{children}</div>
        <div className="dialogo__acoes">
          <button type="button" className="botao botao--secundario" onClick={aoCancelar}
            disabled={ocupado} ref={botaoCancelar}>
            Cancelar
          </button>
          <button type="button" className={`botao ${perigo ? "botao--perigo" : "botao--primario"}`}
            onClick={aoConfirmar} disabled={ocupado} aria-busy={ocupado}>
            {ocupado ? "Aguarde…" : textoConfirmar}
          </button>
        </div>
      </div>
    </div>
  );
}
