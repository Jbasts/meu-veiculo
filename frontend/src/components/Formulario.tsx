// Peças de formulário além do CampoTexto: grupo de opções (os botões em
// "pílula" do PDF), chave liga/desliga e diálogo de confirmação.

import {
  useEffect,
  useId,
  useRef,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";

interface PropsSelecao extends Omit<SelectHTMLAttributes<HTMLSelectElement>, "id"> {
  rotulo: string;
  opcoes: { valor: string; rotulo: string }[];
  erro?: string | null;
  dica?: string;
}

/** Lista suspensa com rótulo, dica e erro (ex.: sistema, plano de manutenção). */
export function CampoSelecao({ rotulo, opcoes, erro, dica, ...atributos }: PropsSelecao) {
  const id = useId();
  const idAjuda = `${id}-ajuda`;
  return (
    <div className="campo">
      <label className="campo__rotulo" htmlFor={id}>{rotulo}</label>
      <select id={id} className={`campo__entrada campo__selecao${erro ? " campo__entrada--erro" : ""}`}
        aria-invalid={erro ? true : undefined} aria-describedby={erro || dica ? idAjuda : undefined}
        {...atributos}>
        {opcoes.map((opcao) => (
          <option key={opcao.valor} value={opcao.valor}>{opcao.rotulo}</option>
        ))}
      </select>
      {erro ? <p id={idAjuda} className="campo__erro" role="alert">{erro}</p>
        : dica && <p id={idAjuda} className="campo__dica">{dica}</p>}
    </div>
  );
}

interface PropsArea extends Omit<TextareaHTMLAttributes<HTMLTextAreaElement>, "id"> {
  rotulo: string;
  erro?: string | null;
}

/** Campo de texto com várias linhas (ex.: observação). */
export function CampoArea({ rotulo, erro, ...atributos }: PropsArea) {
  const id = useId();
  const idAjuda = `${id}-ajuda`;
  return (
    <div className="campo">
      <label className="campo__rotulo" htmlFor={id}>{rotulo}</label>
      <textarea id={id} rows={4}
        className={`campo__entrada campo__area${erro ? " campo__entrada--erro" : ""}`}
        aria-invalid={erro ? true : undefined} aria-describedby={erro ? idAjuda : undefined}
        {...atributos} />
      {erro && <p id={idAjuda} className="campo__erro" role="alert">{erro}</p>}
    </div>
  );
}

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
  const cancelar = useRef(aoCancelar);
  useEffect(() => {
    cancelar.current = aoCancelar;
  });

  // Só ao abrir: o foco vai para "Cancelar" (a opção segura). Se isso rodasse
  // a cada nova renderização, o foco sairia do campo que a pessoa está
  // digitando (ex.: o motivo do descarte).
  useEffect(() => {
    botaoCancelar.current?.focus();
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") cancelar.current();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, []);

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
