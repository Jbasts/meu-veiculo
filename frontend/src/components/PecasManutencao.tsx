// Peças da área de manutenção: o cartão de uma pendência (como no PDF,
// página 5) e o selo de situação.

import { Link } from "react-router";

import {
  progressoDoPlano,
  resumoDoPrazo,
  ROTULO_SITUACAO,
  textoIntervalo,
  textoPrevisao,
  type Pendencia,
  type Situacao,
} from "../types/manutencao";
import { formatarDataIso } from "../utils/datas";
import { IconeCheck, IconeRelogio } from "./Icones";
import type { TomStatus } from "./SeloStatus";

export const TOM_DA_SITUACAO: Record<Situacao, TomStatus> = {
  atrasada: "alerta",
  proxima: "aviso",
  em_dia: "ok",
  sem_base: "neutro",
};

function IconeAlerta() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 4l9 16H3z" /><path d="M12 10v4" /><path d="M12 17h.01" />
    </svg>
  );
}

export function IconeDaSituacao({ situacao }: { situacao: Situacao }) {
  return (
    <span className={`pendencia__icone pendencia__icone--${TOM_DA_SITUACAO[situacao]}`}>
      {situacao === "atrasada" ? <IconeAlerta /> : situacao === "em_dia" ? <IconeCheck /> : <IconeRelogio />}
    </span>
  );
}

/** Para onde leva o toque numa pendência. */
export function destinoDaPendencia(veiculoId: number, item: Pendencia): string {
  return item.tipo === "plano"
    ? `/veiculos/${veiculoId}/planos/${item.plano_id}`
    : `/veiculos/${veiculoId}/manutencoes/${item.manutencao_id}`;
}

export function descricaoDaPendencia(item: Pendencia): string {
  if (item.tipo === "agendada") {
    return `Agendada para ${item.proxima_data ? formatarDataIso(item.proxima_data) : "data a definir"}`;
  }
  if (item.situacao === "sem_base") {
    return `${textoIntervalo(item)}. Falta informar a última vez.`;
  }
  const previsao = textoPrevisao(item);
  if (item.tipo === "lembrete") return `Lembrete: próxima ${previsao}`;
  return `${textoIntervalo(item)}. Prevista ${previsao}`;
}

export function CartaoPendencia({ veiculoId, item, podeRegistrar = true }: {
  veiculoId: number; item: Pendencia; podeRegistrar?: boolean;
}) {
  const resumo = resumoDoPrazo(item);
  const progresso = item.tipo === "plano" ? progressoDoPlano(item) : null;
  const tom = TOM_DA_SITUACAO[item.situacao];
  return (
    <li className="pendencia">
      <Link to={destinoDaPendencia(veiculoId, item)} className="pendencia__principal">
        <IconeDaSituacao situacao={item.situacao} />
        <span className="pendencia__texto">
          <span className="pendencia__titulo">{item.titulo}</span>
          <span className="pendencia__descricao">{descricaoDaPendencia(item)}</span>
        </span>
        <span className={`pendencia__prazo pendencia__prazo--${tom}`}>
          <strong>{resumo.valor}</strong>
          <span>{resumo.rotulo}</span>
        </span>
      </Link>
      {progresso !== null && (
        <div className="pendencia__barra" aria-hidden="true">
          <div className={`pendencia__barra-cheia pendencia__barra-cheia--${tom}`}
            style={{ width: `${Math.round(progresso * 100)}%` }} />
        </div>
      )}
      {item.tipo === "plano" && podeRegistrar && (
        <div className="pendencia__acoes">
          {item.agendada_id !== null && item.agendada_data !== null ? (
            <Link to={`/veiculos/${veiculoId}/manutencoes/${item.agendada_id}`} className="link">
              Agendada para {formatarDataIso(item.agendada_data)}
            </Link>
          ) : (
            <span className="texto-suave">{ROTULO_SITUACAO[item.situacao]}</span>
          )}
          {/* Com manutenção agendada, "Registrar" conclui essa agendada em vez de criar outra. */}
          <Link className="botao-pequeno" aria-label={`Registrar ${item.titulo}`}
            to={item.agendada_id !== null
              ? `/veiculos/${veiculoId}/manutencoes/${item.agendada_id}/editar?concluir=1`
              : `/veiculos/${veiculoId}/manutencoes/nova?plano=${item.plano_id}`}>
            Registrar
          </Link>
        </div>
      )}
    </li>
  );
}
