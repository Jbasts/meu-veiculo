// Peças da área de diagnóstico: selos de gravidade e situação, o cartão de um
// problema em aberto e a linha de um resolvido (como no PDF, página 6).

import { Link } from "react-router";

import {
  ROTULO_STATUS,
  rotuloGravidade,
  type DiagnosticoResumo,
  type Gravidade,
  type StatusDiagnostico,
} from "../types/diagnostico";
import { rotuloSistema } from "../types/manutencao";
import { formatarDataIso } from "../utils/datas";
import { formatarDinheiro, formatarKm } from "../utils/formatos";
import { IconeCheck, IconeDiagnostico, IconeRelogio } from "./Icones";
import SeloStatus, { type TomStatus } from "./SeloStatus";

export const TOM_DA_GRAVIDADE: Record<Gravidade, TomStatus> = {
  baixa: "neutro", media: "aviso", alta: "alerta", critica: "alerta",
};

export const TOM_DO_STATUS: Record<StatusDiagnostico, TomStatus> = {
  aberto: "neutro", em_observacao: "ok", resolvido: "ok", descartado: "neutro",
};

export function SeloGravidade({ gravidade }: { gravidade: Gravidade }) {
  return <SeloStatus tom={TOM_DA_GRAVIDADE[gravidade]}>Gravidade {rotuloGravidade(gravidade).toLowerCase()}</SeloStatus>;
}

/** "Desde 23/09/2026, aos 85.000 km" */
export function textoDesde(d: Pick<DiagnosticoResumo, "data_identificacao" | "quilometragem">): string {
  return `Desde ${formatarDataIso(d.data_identificacao)}`
    + (d.quilometragem !== null ? `, aos ${formatarKm(d.quilometragem)}` : "");
}

/** "Resolvido em 02/09/2026 com Troca de pneus" / "Descartado em 05/08/2026" */
export function textoEncerramento(d: DiagnosticoResumo): string {
  const quando = d.data_resolucao ? ` em ${formatarDataIso(d.data_resolucao)}` : "";
  if (d.status === "descartado") return `Descartado${quando}`;
  return `Resolvido${quando}${d.manutencao ? ` com ${d.manutencao.descricao}` : ""}`;
}

function textoNotas(total: number): string {
  return total === 0 ? "Sem anotações" : total === 1 ? "1 anotação" : `${total} anotações`;
}

/** Cartão de um problema em aberto. */
export function CartaoDiagnostico({ veiculoId, diagnostico: d }: {
  veiculoId: number; diagnostico: DiagnosticoResumo;
}) {
  const prevista = d.manutencao?.status === "agendada" ? d.manutencao : null;
  return (
    <li>
      <Link to={`/veiculos/${veiculoId}/diagnosticos/${d.id}`} className="cartao diagnostico">
        <span className="diagnostico__topo">
          <span className="diagnostico__sistema">
            <IconeDiagnostico tamanho={18} /> {rotuloSistema(d.sistema)}
          </span>
          <SeloGravidade gravidade={d.gravidade} />
        </span>
        <span className="diagnostico__titulo">{d.titulo}</span>
        <span className="texto-suave">{textoDesde(d)}</span>
        {prevista && (
          <span className="diagnostico__prevista">
            Manutenção agendada para {formatarDataIso(prevista.data)}
          </span>
        )}
        <span className="diagnostico__rodape">
          <span className="diagnostico__status">
            {d.status === "em_observacao" ? <IconeRelogio tamanho={18} /> : <span className="diagnostico__bolinha" />}
            {ROTULO_STATUS[d.status]}
          </span>
          <span className="texto-suave">{textoNotas(d.total_notas)}</span>
        </span>
      </Link>
    </li>
  );
}

/** Linha de um problema resolvido ou descartado. */
export function LinhaEncerrado({ veiculoId, diagnostico: d }: {
  veiculoId: number; diagnostico: DiagnosticoResumo;
}) {
  return (
    <li>
      <Link to={`/veiculos/${veiculoId}/diagnosticos/${d.id}`} className="lista-simples__item">
        <span className={`pendencia__icone pendencia__icone--${d.status === "resolvido" ? "ok" : "neutro"}`}>
          <IconeCheck />
        </span>
        <span className="lista-simples__texto">
          <span className="lista-simples__titulo">{d.titulo}</span>
          <span className="texto-suave">{textoEncerramento(d)}</span>
        </span>
        {d.status === "resolvido" && d.manutencao && (
          <strong>{formatarDinheiro(d.manutencao.valor)}</strong>
        )}
      </Link>
    </li>
  );
}
