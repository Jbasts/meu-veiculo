import { useId, useState, type InputHTMLAttributes } from "react";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type"> {
  rotulo: string;
  erro?: string | null;
  dica?: string;
}

function IconeOlho({ aberto }: { aberto: boolean }) {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z" />
      <circle cx="12" cy="12" r="3" />
      {!aberto && <path d="M4 4l16 16" />}
    </svg>
  );
}

// Campo de senha com o botão de olho do PDF (mostrar/esconder).
export default function CampoSenha({ rotulo, erro, dica, ...atributos }: Props) {
  const id = useId();
  const idAjuda = `${id}-ajuda`;
  const [visivel, setVisivel] = useState(false);
  return (
    <div className="campo">
      <label className="campo__rotulo" htmlFor={id}>
        {rotulo}
      </label>
      <div className="campo__com-botao">
        <input
          id={id}
          type={visivel ? "text" : "password"}
          className={`campo__entrada${erro ? " campo__entrada--erro" : ""}`}
          aria-invalid={erro ? true : undefined}
          aria-describedby={erro || dica ? idAjuda : undefined}
          {...atributos}
        />
        <button
          type="button"
          className="campo__botao-olho"
          onClick={() => setVisivel((v) => !v)}
          aria-label={visivel ? `Esconder ${rotulo.toLowerCase()}` : `Mostrar ${rotulo.toLowerCase()}`}
          aria-pressed={visivel}
        >
          <IconeOlho aberto={!visivel} />
        </button>
      </div>
      {erro ? (
        <p id={idAjuda} className="campo__erro" role="alert">
          {erro}
        </p>
      ) : (
        dica && (
          <p id={idAjuda} className="campo__dica">
            {dica}
          </p>
        )
      )}
    </div>
  );
}
