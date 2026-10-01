// Peças da área de projetos (PDF, páginas 16 e 19): textos do orçamento, barra
// de progresso e os quadros de antes e depois. Os números vêm do backend.

import { Link } from "react-router";

import type { Projeto, StatusProjeto } from "../types/projeto";
import { formatarDataIso, formatarMesAnoCurto } from "../utils/datas";
import { formatarDinheiro } from "../utils/formatos";
import { IconeCamera } from "./Icones";
import { FotoProtegida } from "./PecasVeiculo";
import type { TomStatus } from "./SeloStatus";

export const TOM_DO_STATUS_PROJETO: Record<StatusProjeto, TomStatus> = {
  planejado: "neutro", em_andamento: "ok", concluido: "ok", cancelado: "alerta",
};

/** "R$ 3.800,00 de R$ 4.500,00" (ou só o gasto, sem orçamento). */
export function GastoDoOrcamento({ projeto: p }: { projeto: Projeto }) {
  return (
    <span className="projeto__valores">
      <strong>{formatarDinheiro(p.gasto)}</strong>
      {p.orcamento !== null ? ` de ${formatarDinheiro(p.orcamento)}` : " gastos (sem orçamento)"}
    </span>
  );
}

/** Barra do orçamento; vermelha quando passou. Sem orçamento, não há barra. */
export function BarraOrcamento({ projeto: p }: { projeto: Projeto }) {
  if (p.orcamento === null) return null;
  const excedido = p.diferenca !== null && p.diferenca.startsWith("-");
  const largura = p.percentual === null ? (excedido ? 100 : 0) : Math.min(100, p.percentual);
  const tom = excedido ? "alerta" : p.status === "concluido" ? "concluido" : "ok";
  return (
    <span className="barra-orcamento" aria-hidden="true">
      <span className={`barra-orcamento__cheia barra-orcamento__cheia--${tom}`} style={{ width: `${largura}%` }} />
    </span>
  );
}

/** Texto à direita: "Restam R$ 700,00", "R$ 50,00 abaixo", "R$ 150,00 acima do orçamento"... */
export function textoDaDiferenca(p: Projeto): string {
  if (p.status === "planejado" && p.quantidade_itens === 0) return "Nenhum gasto ainda";
  if (p.diferenca === null) return "";
  if (p.diferenca.startsWith("-")) return `${formatarDinheiro(p.diferenca.slice(1))} acima do orçamento`;
  if (/^0+\.00$/.test(p.diferenca)) return "Orçamento usado por inteiro";
  return p.status === "concluido" ? `${formatarDinheiro(p.diferenca)} abaixo` : `Restam ${formatarDinheiro(p.diferenca)}`;
}

/** Texto à esquerda: conclusão, percentual, previsão ou a falta de orçamento. */
export function textoDaSituacao(p: Projeto): string {
  if (p.status === "concluido" && p.data_conclusao) return `Concluído em ${formatarDataIso(p.data_conclusao)}`;
  if (p.status === "planejado" && p.quantidade_itens === 0) {
    return p.data_prevista ? `Previsto para ${formatarMesAnoCurto(p.data_prevista)}` : "Planejado";
  }
  if (p.percentual !== null) return `${p.percentual}% do orçamento`;
  if (p.orcamento === null) return "Sem orçamento";
  return "Orçamento de R$ 0,00";
}

/** Os dois quadros de antes e depois. Vazio, o quadro leva para "Nova foto" já ligada ao projeto. */
export function AntesDepois({ veiculoId, projeto: p, podeAdicionar, grande = false }: {
  veiculoId: number; projeto: Projeto; podeAdicionar: boolean; grande?: boolean;
}) {
  const quadros = [
    { momento: "antes", rotulo: "Antes", fotoId: p.foto_antes_id, dica: "" },
    { momento: "depois", rotulo: "Depois", fotoId: p.foto_depois_id, dica: "Ao concluir" },
  ] as const;
  return (
    <div className={`antes-depois${grande ? " antes-depois--grande" : ""}`}>
      {quadros.map((q) => (
        <div key={q.momento} className="antes-depois__quadro">
          {q.fotoId !== null ? (
            <Link to={`/veiculos/${veiculoId}/fotos/${q.fotoId}`} className="antes-depois__foto"
              aria-label={`Foto de ${q.rotulo.toLowerCase()}: ${p.nome}`}>
              <FotoProtegida veiculoId={veiculoId} fotoId={q.fotoId} descricao={`${q.rotulo}: ${p.nome}`} />
              <span className="etiqueta-foto">{q.rotulo}</span>
            </Link>
          ) : podeAdicionar ? (
            <Link to={`/veiculos/${veiculoId}/fotos/nova?projeto=${p.id}&momento=${q.momento}`}
              className="antes-depois__vazio">
              <IconeCamera />
              Foto {q.rotulo.toLowerCase()}
            </Link>
          ) : (
            <span className="antes-depois__vazio antes-depois__vazio--sem-acao">Sem foto de {q.rotulo.toLowerCase()}</span>
          )}
          {grande && q.fotoId === null && q.dica && <span className="texto-suave antes-depois__dica">{q.dica}</span>}
        </div>
      ))}
    </div>
  );
}
