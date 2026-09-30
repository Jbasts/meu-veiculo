import { useId, type InputHTMLAttributes } from "react";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  rotulo: string;
  erro?: string | null;
  dica?: string;
}

// Campo com rótulo, dica e mensagem de erro ligados ao input (acessível a leitores de tela).
export default function CampoTexto({ rotulo, erro, dica, ...atributos }: Props) {
  const id = useId();
  const idAjuda = `${id}-ajuda`;
  return (
    <div className="campo">
      <label className="campo__rotulo" htmlFor={id}>
        {rotulo}
      </label>
      <input
        id={id}
        className={`campo__entrada${erro ? " campo__entrada--erro" : ""}`}
        aria-invalid={erro ? true : undefined}
        aria-describedby={erro || dica ? idAjuda : undefined}
        {...atributos}
      />
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
