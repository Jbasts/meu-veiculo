// "Ver valores" de uma manutenção: peças e mão de obra, cada uma com o seu
// valor, os subtotais e o total. Os totais vêm do backend (a tela não soma).

import { useEffect, useId, useRef, useState } from "react";

import { ErroDaApi } from "../services/apiCliente";
import { obterManutencao } from "../services/manutencaoService";
import type { ManutencaoDetalhe, TipoItem } from "../types/manutencao";
import { formatarDinheiro } from "../utils/formatos";

/** Rótulos dos subtotais e do total; na agendada, os valores são estimados. */
export function rotulosDosValores(realizada: boolean) {
  return realizada
    ? { pecas: "Total de peças", maoDeObra: "Total de mão de obra", total: "Total da manutenção" }
    : { pecas: "Valor estimado das peças", maoDeObra: "Valor estimado da mão de obra",
        total: "Total estimado" };
}

function Secao({ titulo, tipo, manutencao, rotuloSubtotal, subtotal }: {
  titulo: string; tipo: TipoItem; manutencao: ManutencaoDetalhe; rotuloSubtotal: string;
  subtotal: string;
}) {
  const itens = manutencao.itens.filter((item) => item.tipo === tipo);
  return (
    <section className="valores__secao" aria-label={titulo}>
      <h3 className="valores__titulo">{titulo}</h3>
      {itens.length === 0 ? (
        <p className="texto-suave valores__vazio">Nenhum item informado.</p>
      ) : (
        <ul className="valores__lista">
          {itens.map((item) => (
            <li key={item.id} className="valores__linha">
              <span>{item.nome}</span>
              <span>{formatarDinheiro(item.valor)}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="valores__linha valores__subtotal">
        <span>{rotuloSubtotal}</span>
        <strong>{formatarDinheiro(subtotal)}</strong>
      </p>
    </section>
  );
}

function ConteudoValores({ manutencao }: { manutencao: ManutencaoDetalhe }) {
  const rotulos = rotulosDosValores(manutencao.status === "realizada");
  const detalhada = manutencao.itens.length > 0
    && manutencao.total_pecas !== null && manutencao.total_mao_de_obra !== null;
  return (
    <>
      {detalhada ? (
        <>
          <Secao titulo="Peças" tipo="peca" manutencao={manutencao} rotuloSubtotal={rotulos.pecas}
            subtotal={manutencao.total_pecas!} />
          <Secao titulo="Mão de obra" tipo="mao_de_obra" manutencao={manutencao}
            rotuloSubtotal={rotulos.maoDeObra} subtotal={manutencao.total_mao_de_obra!} />
        </>
      ) : (
        <p className="valores__aviso">
          Esta manutenção tem só o valor total, sem detalhamento de peças e mão de obra.
        </p>
      )}
      <p className="valores__linha valores__total">
        <span>{rotulos.total}</span>
        <strong>{formatarDinheiro(manutencao.valor)}</strong>
      </p>
    </>
  );
}

/** O popup. Recebe a manutenção já carregada ou busca pelo id. */
export function DialogoValores({ veiculoId, manutencaoId, detalhe = null, aoFechar }: {
  veiculoId: number; manutencaoId: number; detalhe?: ManutencaoDetalhe | null; aoFechar: () => void;
}) {
  const id = useId();
  const botaoFechar = useRef<HTMLButtonElement>(null);
  const [manutencao, setManutencao] = useState<ManutencaoDetalhe | null>(detalhe);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    botaoFechar.current?.focus();
    const aoTeclar = (evento: KeyboardEvent) => {
      if (evento.key === "Escape") aoFechar();
    };
    window.addEventListener("keydown", aoTeclar);
    return () => window.removeEventListener("keydown", aoTeclar);
  }, [aoFechar]);

  useEffect(() => {
    if (detalhe) return;
    let cancelado = false;
    obterManutencao(veiculoId, manutencaoId)
      .then((dados) => { if (!cancelado) setManutencao(dados); })
      .catch((falha) => {
        if (!cancelado) {
          setErro(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar os valores.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [veiculoId, manutencaoId, detalhe]);

  return (
    <div className="dialogo__fundo">
      <div className="dialogo" role="dialog" aria-modal="true" aria-labelledby={id}>
        <h2 className="dialogo__titulo" id={id}>Valores</h2>
        {manutencao && <p className="texto-suave valores__descricao">{manutencao.descricao}</p>}
        <div className="dialogo__texto valores">
          {erro ? <p role="alert">{erro}</p>
            : manutencao ? <ConteudoValores manutencao={manutencao} />
              : <p aria-busy="true">Carregando…</p>}
        </div>
        <button type="button" className="botao botao--secundario" onClick={aoFechar} ref={botaoFechar}>
          Fechar
        </button>
      </div>
    </div>
  );
}

/** Botão "Ver valores" que abre o popup. */
export function BotaoVerValores({ veiculoId, manutencaoId, detalhe, pequeno = false, rotulo }: {
  veiculoId: number; manutencaoId: number; detalhe?: ManutencaoDetalhe; pequeno?: boolean;
  rotulo?: string;
}) {
  const [aberto, setAberto] = useState(false);
  return (
    <>
      <button type="button" className={pequeno ? "botao-pequeno" : "botao botao--secundario"}
        aria-label={rotulo} onClick={() => setAberto(true)}>
        Ver valores
      </button>
      {aberto && (
        <DialogoValores veiculoId={veiculoId} manutencaoId={manutencaoId} detalhe={detalhe}
          aoFechar={() => setAberto(false)} />
      )}
    </>
  );
}
