// Peças do tanque: seletor do nível do marcador e textos do consumo
// (exato pelo tanque cheio ou estimado pelo marcador, com a faixa possível).

import { useId } from "react";

import { NIVEIS, rotuloDoNivel, unidade, type SituacaoConsumo } from "../types/abastecimento";
import { formatarDecimal } from "../utils/formatos";

/** Como o marcador aparece no botão: 0, ½, 1, 1½ ... 4 (quartos do tanque). */
const NO_BOTAO = ["0", "½", "1", "1½", "2", "2½", "3", "3½", "4"];

/**
 * Nível do marcador em oitavos do tanque, com botões como os quartos do
 * marcador do carro ("1,5/4" = 3 oitavos). opcional: mostra "Não sei".
 */
export function SeletorDeNivel({ rotulo, valor, aoMudar, erro, dica, opcional = false }: {
  rotulo: string;
  valor: number | null;
  aoMudar: (nivel: number | null) => void;
  erro?: string;
  dica?: string;
  opcional?: boolean;
}) {
  const id = useId();
  return (
    <div className="campo nivel" role="radiogroup" aria-labelledby={id}>
      <span className="campo__rotulo" id={id}>
        {rotulo}
        {valor !== null && <strong className="nivel__escolhido"> {rotuloDoNivel(valor)}</strong>}
      </span>
      <div className="nivel__barra">
        {NIVEIS.map((n) => (
          <button key={n.valor} type="button" role="radio" aria-checked={valor === n.valor}
            aria-label={n.rotulo}
            className={`nivel__parte${valor !== null && n.valor <= valor ? " nivel__parte--cheia" : ""}${valor === n.valor ? " nivel__parte--escolhida" : ""}`}
            onClick={() => aoMudar(n.valor)}>
            {NO_BOTAO[n.valor]}
          </button>
        ))}
      </div>
      <div className="nivel__legenda">
        <span>Vazio</span>
        {opcional && (
          <button type="button" role="radio" aria-checked={valor === null}
            className={`botao-link nivel__nao-sei${valor === null ? " nivel__nao-sei--ativo" : ""}`}
            onClick={() => aoMudar(null)}>
            Não sei
          </button>
        )}
        <span>Cheio</span>
      </div>
      {dica && !erro && <p className="campo__dica">{dica}</p>}
      {erro && <p className="campo__erro" role="alert">{erro}</p>}
    </div>
  );
}

/** "≈ 10,4 km/L" e "entre 9,1 e 11,2 (pelo marcador)", ou só "11,3 km/L" no tanque cheio. */
export function textoDoKmPorLitro(s: SituacaoConsumo, combustivel: string): string {
  const valor = `${formatarDecimal(s.km_por_litro!, 1)} ${unidade(combustivel).consumo}`;
  return s.estimado ? `≈ ${valor}` : valor;
}

export function faixaDoMarcador(minimo: string | null, maximo: string | null): string | null {
  if (!minimo || !maximo) return null;
  return `Pelo marcador: entre ${formatarDecimal(minimo, 1)} e ${formatarDecimal(maximo, 1)}`;
}
