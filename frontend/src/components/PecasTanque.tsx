// Peças do tanque: seletor do nível do marcador e textos do consumo
// (exato pelo tanque cheio ou estimado pelo marcador, com a faixa possível).

import { useId } from "react";
import { Link } from "react-router";

import { NIVEIS, rotuloDoNivel, unidade, type NivelTanque, type SituacaoConsumo } from "../types/abastecimento";
import { formatarDataIso } from "../utils/datas";
import { formatarDecimal, formatarInteiro } from "../utils/formatos";

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

/** "3/4 em 02/10/2026" (o último registro do tanque). */
export function textoDoUltimoNivel(n: NivelTanque): string {
  if (n.nivel === null || n.data === null) return "";
  const de = n.origem === "abastecimento" ? "no abastecimento de" : "em";
  return `${rotuloDoNivel(n.nivel)} ${de} ${formatarDataIso(n.data)}`;
}

/** Marcador desenhado: 8 partes (oitavos), preenchidas até o nível. */
function Medidor({ nivel }: { nivel: number }) {
  return (
    <div className="medidor-tanque" aria-hidden="true">
      {Array.from({ length: 8 }, (_, i) => (
        <span key={i} className={`medidor-tanque__parte${i < nivel ? " medidor-tanque__parte--cheia" : ""}${nivel <= 2 && i < nivel ? " medidor-tanque__parte--baixa" : ""}`} />
      ))}
    </div>
  );
}

/**
 * Cartão "Nível do tanque" (Início e aba Combustível): o último nível
 * registrado e, se o carro rodou depois, a estimativa de agora pelo consumo
 * médio. Sem registro, "Dados insuficientes" e o motivo (nunca um nível inventado).
 */
export function NivelDoTanqueCartao({ veiculoId, nivel: n, podeAtualizar = true }: {
  veiculoId: number; nivel: NivelTanque; podeAtualizar?: boolean;
}) {
  const atualizar = podeAtualizar && (
    <Link to={`/veiculos/${veiculoId}/km`} className="link">Atualizar km e nível</Link>
  );
  if (!n.disponivel || n.nivel === null) {
    return (
      <section className="cartao custo" aria-label="Nível do tanque">
        <div className="custo__topo"><span className="texto-suave">Nível do tanque</span>{atualizar}</div>
        <p className="indicador__indisponivel">Dados insuficientes</p>
        <p className="texto-suave">{n.motivo}</p>
      </section>
    );
  }
  const estimado = n.nivel_estimado !== null;
  const mostrado = estimado ? n.nivel_estimado! : n.nivel;
  return (
    <section className="cartao custo" aria-label="Nível do tanque">
      <div className="custo__topo"><span className="texto-suave">Nível do tanque</span>{atualizar}</div>
      <p className="custo__valor">{estimado && "≈ "}{rotuloDoNivel(mostrado)}</p>
      <Medidor nivel={mostrado} />
      {estimado ? (
        <p className="texto-suave">
          Estimado agora: {textoDoUltimoNivel(n)}, depois {formatarInteiro(n.km_desde!)} km rodados
          {" "}a {formatarDecimal(n.km_por_litro!, 1)} km/L (consumo médio).
        </p>
      ) : (
        <p className="texto-suave">
          {n.km_desde
            ? `Último registro: ${textoDoUltimoNivel(n)}. Depois, ${formatarInteiro(n.km_desde)} km rodados `
              + "(ainda sem consumo médio para estimar)."
            : `Registrado: ${textoDoUltimoNivel(n)}.`}
        </p>
      )}
    </section>
  );
}
