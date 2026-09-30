// Estados comuns de uma tela que busca dados: carregando e erro com "tentar de novo".

import Alerta from "./Alerta";

export function Carregando({ texto = "Carregando…" }: { texto?: string }) {
  return (
    <p className="texto-suave estado-tela" role="status" aria-busy="true">
      {texto}
    </p>
  );
}

export function ErroComNovaTentativa({ mensagem, aoTentar }: { mensagem: string; aoTentar: () => void }) {
  return (
    <div className="estado-tela">
      <Alerta tipo="erro">{mensagem}</Alerta>
      <button type="button" className="botao botao--secundario" onClick={aoTentar}>
        Tentar de novo
      </button>
    </div>
  );
}
