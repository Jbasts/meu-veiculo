import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";

import AbaCombustivel from "../components/AbaCombustivel";
import Alerta from "../components/Alerta";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import {
  IconeBomba,
  IconeCalendario,
  IconeManutencao,
  IconeMaisSinal,
  IconeProjeto,
  IconeRecibo,
  IconeSeta,
  IconeSetaEsquerda,
} from "../components/Icones";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  listarLancamentos,
  listarPendentes,
  obterResumo,
  pagarGasto,
  type Periodo,
} from "../services/gastoService";
import {
  rotuloCategoria,
  type Lancamento,
  type Pendente,
  type ResumoMes,
  type TipoLancamento,
} from "../types/gasto";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, hojeIso, mesDaData, nomeDoMes, somarMeses } from "../utils/datas";
import { formatarDinheiro, formatarInteiro, somarDinheiro } from "../utils/formatos";

type Aba = "gastos" | "combustivel";
type TipoPeriodo = Periodo["tipo"];
const POR_PAGINA = 50;
const PERIODOS: { valor: TipoPeriodo; rotulo: string }[] = [
  { valor: "mes", rotulo: "Mês" },
  { valor: "ano", rotulo: "Ano" },
  { valor: "total", rotulo: "Total" },
];
/** Textos que mudam com o período ("no mês", "neste ano"...). */
const TEXTOS: Record<TipoPeriodo, { no: string; vazio: string; rotulo: string; contas: [string, string] }> = {
  mes: { no: "no mês", vazio: "Nenhuma despesa neste mês", rotulo: "Total do mês",
    contas: ["conta que vence no mês", "contas que vencem no mês"] },
  ano: { no: "no ano", vazio: "Nenhuma despesa neste ano", rotulo: "Total do ano",
    contas: ["conta que vence no ano", "contas que vencem no ano"] },
  total: { no: "desde o primeiro registro", vazio: "Nenhuma despesa registrada", rotulo: "Total geral",
    contas: ["conta pendente", "contas pendentes"] },
};

function chaveDoPeriodo(p: Periodo): string {
  return p.tipo === "total" ? "total" : p.tipo === "ano" ? `ano-${p.ano}` : `mes-${p.ano}-${p.mes}`;
}

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof ErroDaApi ? falha.message : padrao;
}

function plural(n: number, um: string, varios: string): string {
  return `${formatarInteiro(n)} ${n === 1 ? um : varios}`;
}

// --------------------------------------------------------------------- resumo

function ResumoDoPeriodo({ veiculo, periodo, versao }: { veiculo: Veiculo; periodo: Periodo; versao: number }) {
  const [resumo, setResumo] = useState<ResumoMes | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setResumo(await obterResumo(veiculo.id, periodo));
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar o resumo."));
    }
  }, [veiculo.id, chaveDoPeriodo(periodo)]);

  useEffect(() => {
    void carregar();
  }, [carregar, versao]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />;
  if (!resumo) return <Carregando />;
  const temPrevisto = resumo.quantidade_manutencoes_previstas + resumo.quantidade_gastos_previstos > 0;
  const textos = TEXTOS[periodo.tipo];
  return (
    <>
      <section className="total-mes" aria-label={textos.rotulo}>
        <p className="total-mes__valor">{formatarDinheiro(resumo.total)}</p>
        <p className="texto-suave">
          {resumo.quantidade === 0 ? textos.vazio
            : `${plural(resumo.quantidade, "lançamento", "lançamentos")} ${textos.no}`}
        </p>
      </section>

      {resumo.categorias.length > 0 && (
        <section aria-label="Por categoria">
          <h2 className="rotulo-secao">Por categoria</h2>
          <ul className="cartao categorias">
            {resumo.categorias.map((c) => (
              <li key={c.categoria} className="categorias__linha">
                <span className="categorias__topo">
                  <span>{rotuloCategoria(c.categoria)}</span>
                  <span>
                    <strong>{formatarDinheiro(c.total)}</strong>{" "}
                    <span className="texto-suave">{c.percentual}%</span>
                  </span>
                </span>
                <span className="categorias__barra" aria-hidden="true">
                  <span className={`categorias__cheia categorias__cheia--${c.categoria}`}
                    style={{ width: `${Math.min(100, c.percentual)}%` }} />
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {temPrevisto && (
        <section className="cartao previsto" aria-label="Previsto">
          <p className="cartao__titulo">Previsto (não entra no total)</p>
          {resumo.quantidade_manutencoes_previstas > 0 && (
            <p className="previsto__linha">
              <span>{plural(resumo.quantidade_manutencoes_previstas, "manutenção agendada", "manutenções agendadas")}</span>
              <strong>{formatarDinheiro(resumo.previsto_manutencoes)}</strong>
            </p>
          )}
          {resumo.quantidade_gastos_previstos > 0 && (
            <p className="previsto__linha">
              <span>{plural(resumo.quantidade_gastos_previstos, ...textos.contas)}</span>
              <strong>{formatarDinheiro(resumo.previsto_gastos)}</strong>
            </p>
          )}
        </section>
      )}
    </>
  );
}

// ------------------------------------------------------------------- contas

function textoDoPrazo(p: Pendente): string {
  if (p.situacao === "vence_hoje") return "vence hoje";
  if (p.situacao === "vencido") return `há ${plural(-p.dias, "dia", "dias")}`;
  return `em ${plural(p.dias, "dia", "dias")}`;
}

function ItemPendente({ veiculo, pendente: p, aoPagar }: {
  veiculo: Veiculo; pendente: Pendente; aoPagar: (p: Pendente) => void;
}) {
  const vencido = p.situacao === "vencido";
  const titulo = p.descricao ?? rotuloCategoria(p.categoria);
  return (
    <li className="conta">
      <Link to={`/veiculos/${veiculo.id}/gastos/${p.id}`} className="lista-simples__item conta__principal">
        <span className={`pendencia__icone pendencia__icone--${vencido ? "alerta" : "aviso"}`}>
          <IconeCalendario />
        </span>
        <span className="lista-simples__texto">
          <span className="lista-simples__titulo">{titulo}</span>
          <span className="texto-suave">
            {vencido ? "Venceu" : "Vence"} em {formatarDataIso(p.data_vencimento!)}
          </span>
        </span>
        <span className="conta__valor">
          <strong>{formatarDinheiro(p.valor)}</strong>
          <span className={`alerta-texto alerta-texto--${vencido ? "alerta" : "aviso"}`}>{textoDoPrazo(p)}</span>
        </span>
      </Link>
      {veiculo.ativo && (
        <div className="lista-simples__acoes">
          <button type="button" className="botao-pequeno" aria-label={`Marcar ${titulo} como pago`}
            onClick={() => aoPagar(p)}>
            Marcar como pago
          </button>
        </div>
      )}
    </li>
  );
}

function Contas({ veiculo, versao, aoMudar }: { veiculo: Veiculo; versao: number; aoMudar: () => void }) {
  const [pendentes, setPendentes] = useState<Pendente[] | null>(null);
  const [total, setTotal] = useState(0);
  const [erro, setErro] = useState<string | null>(null);
  const [pagando, setPagando] = useState<Pendente | null>(null);
  const [dataPagamento, setDataPagamento] = useState(hojeIso());
  const [erroPagamento, setErroPagamento] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      const pagina = await listarPendentes(veiculo.id, 1, POR_PAGINA);
      setPendentes(pagina.itens);
      setTotal(pagina.total);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar as contas pendentes."));
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar();
  }, [carregar, versao]);

  async function confirmarPagamento() {
    if (!pagando || ocupado) return;
    if (!dataPagamento || dataPagamento > hojeIso()) {
      setErroPagamento(dataPagamento ? "A data do pagamento não pode ser no futuro." : "Informe a data do pagamento.");
      return;
    }
    setOcupado(true);
    try {
      await pagarGasto(veiculo.id, pagando.id, dataPagamento);
      setAviso(`Pagamento registrado em ${formatarDataIso(dataPagamento)}.`);
      setPagando(null);
      aoMudar(); // o total do mês do pagamento muda
    } catch (falha) {
      if (falha instanceof ErroDaApi) setErroPagamento(falha.campos.data_pagamento ?? falha.message);
      else setErroPagamento("Não foi possível registrar o pagamento.");
    } finally {
      setOcupado(false);
    }
  }

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />;
  if (pendentes === null) return null;
  const vencidas = pendentes.filter((p) => p.situacao === "vencido");
  const futuros = pendentes.filter((p) => p.situacao !== "vencido");
  return (
    <>
      {aviso && <Alerta tipo="sucesso">{aviso}</Alerta>}
      {[{ titulo: "Vencidas", itens: vencidas }, { titulo: "Gastos futuros", itens: futuros }].map(({ titulo, itens }) =>
        itens.length > 0 && (
          <section key={titulo} aria-label={titulo}>
            <h2 className="rotulo-secao rotulo-secao--com-total">
              <span>{titulo}</span>
              <span>{formatarDinheiro(somarDinheiro(itens.map((p) => p.valor)))}</span>
            </h2>
            <ul className="cartao lista-simples">
              {itens.map((p) => (
                <ItemPendente key={p.id} veiculo={veiculo} pendente={p} aoPagar={(escolhido) => {
                  setDataPagamento(hojeIso());
                  setErroPagamento(null);
                  setAviso(null);
                  setPagando(escolhido);
                }} />
              ))}
            </ul>
          </section>
        ))}
      {veiculo.ativo && (
        <Link to={`/veiculos/${veiculo.id}/gastos/novo?futuro=1`} className="botao botao--secundario">
          Lançar gasto futuro
        </Link>
      )}
      {total > pendentes.length && (
        <p className="texto-suave">Mostrando as {pendentes.length} contas com vencimento mais próximo de {total}.</p>
      )}
      {pagando && (
        <DialogoConfirmacao titulo="Marcar como pago?" textoConfirmar="Confirmar pagamento" ocupado={ocupado}
          aoCancelar={() => setPagando(null)} aoConfirmar={() => void confirmarPagamento()}>
          <p>
            {pagando.descricao ?? rotuloCategoria(pagando.categoria)}, {formatarDinheiro(pagando.valor)}.
            O valor entra nas despesas do mês do pagamento.
          </p>
          <CampoTexto rotulo="Data do pagamento" type="date" max={hojeIso()} value={dataPagamento}
            onChange={(e) => setDataPagamento(e.target.value)} erro={erroPagamento} />
        </DialogoConfirmacao>
      )}
    </>
  );
}

// --------------------------------------------------------------- lançamentos

const ICONE_DO_TIPO: Record<TipoLancamento, { Icone: typeof IconeRecibo; tom: string }> = {
  manutencao: { Icone: IconeManutencao, tom: "ok" },
  abastecimento: { Icone: IconeBomba, tom: "aviso" },
  gasto: { Icone: IconeRecibo, tom: "neutro" },
  projeto: { Icone: IconeProjeto, tom: "ok" },
};

function destinoDoLancamento(veiculoId: number, l: Lancamento): string | null {
  if (l.tipo === "manutencao") return `/veiculos/${veiculoId}/manutencoes/${l.origem_id}`;
  if (l.tipo === "gasto") return `/veiculos/${veiculoId}/gastos/${l.origem_id}`;
  if (l.tipo === "abastecimento") return `/veiculos/${veiculoId}/abastecimentos/${l.origem_id}`;
  if (l.tipo === "projeto" && l.projeto_id !== null) return `/veiculos/${veiculoId}/projetos/${l.projeto_id}`;
  return null;
}

function ItemLancamento({ veiculoId, lancamento: l }: { veiculoId: number; lancamento: Lancamento }) {
  const { Icone, tom } = ICONE_DO_TIPO[l.tipo];
  const conteudo = (
    <>
      <span className={`pendencia__icone pendencia__icone--${tom}`}><Icone /></span>
      <span className="lista-simples__texto">
        <span className="lista-simples__titulo">{l.descricao ?? rotuloCategoria(l.categoria)}</span>
        <span className="texto-suave">{formatarDataIso(l.data)}</span>
      </span>
      <strong>{formatarDinheiro(l.valor)}</strong>
    </>
  );
  const destino = destinoDoLancamento(veiculoId, l);
  return (
    <li>
      {destino
        ? <Link to={destino} className="lista-simples__item">{conteudo}</Link>
        : <div className="lista-simples__item">{conteudo}</div>}
    </li>
  );
}

function Lancamentos({ veiculo, periodo, versao }: { veiculo: Veiculo; periodo: Periodo; versao: number }) {
  const [itens, setItens] = useState<Lancamento[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const resultado = await listarLancamentos(veiculo.id, periodo, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? resultado.itens : [...atuais, ...resultado.itens]));
      setTotal(resultado.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os lançamentos."));
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id, chaveDoPeriodo(periodo)]);

  useEffect(() => {
    void carregar(1);
  }, [carregar, versao]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null || total === 0) return null;
  return (
    <section aria-label="Lançamentos">
      <h2 className="rotulo-secao">Lançamentos</h2>
      <ul className="cartao lista-simples">
        {itens.map((l) => <ItemLancamento key={`${l.tipo}-${l.origem_id}`} veiculoId={veiculo.id} lancamento={l} />)}
      </ul>
      {itens.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------- telas

/** A mesma tela para um veículo escolhido pelo endereço (/veiculos/:veiculoId/financas). */
export function FinancasDoVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Finanças</h1>
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Conteudo veiculo={veiculo} />;
}

// Tela "Finanças" (PDF, página 10), aba Gastos, para o veículo em uso.
export default function FinancasPage() {
  const { carregando, erro, emUso, recarregar } = useVeiculos();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Finanças</h1>
        <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  if (!emUso) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Finanças</h1>
        <section className="cartao">
          <p className="cartao__titulo">Nenhum veículo em uso</p>
          <p className="texto-suave">Cadastre ou reative um veículo para registrar gastos.</p>
        </section>
        <Link to="/veiculos" className="botao botao--primario">Ver meus veículos</Link>
      </main>
    );
  }
  return <Conteudo veiculo={emUso} />;
}

/** Lê o período do endereço (?periodo=ano&ano=2025, ?ano=2026&mes=9...); sem nada, o mês atual. */
function periodoDoEndereco(parametros: URLSearchParams, atual: { ano: number; mes: number }): Periodo {
  const tipo = parametros.get("periodo");
  if (tipo === "total") return { tipo: "total" };
  const ano = Number(parametros.get("ano"));
  const anoValido = Number.isInteger(ano) && ano >= 1990 && ano <= atual.ano;
  if (tipo === "ano") return { tipo: "ano", ano: anoValido ? ano : atual.ano };
  const mes = Number(parametros.get("mes"));
  if (anoValido && Number.isInteger(mes) && mes >= 1 && mes <= 12) return { tipo: "mes", ano, mes };
  return { tipo: "mes", ...atual };
}

/** Setas para trocar de mês ou de ano (nunca além do atual). No total, só o título. */
function SeletorDoPeriodo({ periodo, atual, aoMudar }: {
  periodo: Periodo; atual: { ano: number; mes: number }; aoMudar: (p: Periodo) => void;
}) {
  if (periodo.tipo === "total") {
    return <p className="seletor-mes seletor-mes__nome seletor-mes--sozinho">Desde o primeiro registro</p>;
  }
  const ehMes = periodo.tipo === "mes";
  const anterior: Periodo = ehMes ? { tipo: "mes", ...somarMeses(periodo, -1) } : { tipo: "ano", ano: periodo.ano - 1 };
  const proximo: Periodo = ehMes ? { tipo: "mes", ...somarMeses(periodo, 1) } : { tipo: "ano", ano: periodo.ano + 1 };
  const noLimite = ehMes
    ? periodo.ano * 12 + periodo.mes >= atual.ano * 12 + atual.mes
    : periodo.ano >= atual.ano;
  return (
    <nav className="seletor-mes" aria-label={ehMes ? "Escolher mês" : "Escolher ano"}>
      <button type="button" className="botao-icone seletor-mes__botao"
        aria-label={ehMes ? "Mês anterior" : "Ano anterior"} onClick={() => aoMudar(anterior)}>
        <IconeSetaEsquerda />
      </button>
      <p className="seletor-mes__nome" aria-live="polite">
        {ehMes ? nomeDoMes(periodo) : `Ano de ${periodo.ano}`}
      </p>
      <button type="button" className="botao-icone seletor-mes__botao"
        aria-label={ehMes ? "Próximo mês" : "Próximo ano"} disabled={noLimite} onClick={() => aoMudar(proximo)}>
        <IconeSeta />
      </button>
    </nav>
  );
}

function Conteudo({ veiculo }: { veiculo: Veiculo }) {
  const [parametros, setParametros] = useSearchParams();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const [versao, setVersao] = useState(0);
  const atual = mesDaData(hojeIso());
  const aba: Aba = parametros.get("aba") === "combustivel" ? "combustivel" : "gastos";
  const periodo = periodoDoEndereco(parametros, atual);

  /** Guarda aba e período no endereço (voltar de um lançamento cai no mesmo lugar). */
  function irPara(novo: { aba?: Aba; periodo?: Periodo }) {
    const proximaAba = novo.aba ?? aba;
    const p = novo.periodo ?? periodo;
    const valores: Record<string, string> = {};
    if (proximaAba !== "gastos") valores.aba = proximaAba;
    if (p.tipo !== "mes") valores.periodo = p.tipo;
    if (p.tipo === "ano" && p.ano !== atual.ano) valores.ano = String(p.ano);
    if (p.tipo === "mes" && (p.ano !== atual.ano || p.mes !== atual.mes)) {
      valores.ano = String(p.ano);
      valores.mes = String(p.mes);
    }
    setParametros(valores, { replace: true });
  }

  function escolherTipo(tipo: TipoPeriodo) {
    if (tipo === periodo.tipo) return;
    const ano = periodo.tipo === "total" ? atual.ano : periodo.ano;
    irPara({ periodo: tipo === "total" ? { tipo }
      : tipo === "ano" ? { tipo, ano }
        : { tipo, ano, mes: ano === atual.ano ? atual.mes : 12 } });
  }

  return (
    <main className="conteudo conteudo--topo">
      <header className="cabecalho-pagina">
        <div>
          <h1 className="titulo-pagina">Finanças</h1>
          <p className="texto-suave cabecalho-pagina__sub">{veiculo.modelo} {veiculo.ano}</p>
        </div>
        {veiculo.ativo && (aba === "combustivel" ? (
          <Link to={`/veiculos/${veiculo.id}/abastecimentos/novo`} className="botao-redondo botao-redondo--grande"
            aria-label="Novo abastecimento">
            <IconeMaisSinal />
          </Link>
        ) : (
          <Link to={`/veiculos/${veiculo.id}/gastos/novo`} className="botao-redondo botao-redondo--grande"
            aria-label="Novo gasto">
            <IconeMaisSinal />
          </Link>
        ))}
      </header>
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {!veiculo.ativo && (
        <Alerta tipo="info">Veículo inativo: o histórico pode ser consultado, mas não alterado.</Alerta>
      )}

      <div className="abas" role="tablist" aria-label="Seções de finanças">
        {(["gastos", "combustivel"] as const).map((valor) => (
          <button key={valor} type="button" role="tab" aria-selected={aba === valor}
            className={`abas__item${aba === valor ? " abas__item--ativa" : ""}`}
            onClick={() => irPara({ aba: valor })}>
            {valor === "gastos" ? "Gastos" : "Combustível"}
          </button>
        ))}
      </div>

      {aba === "combustivel" ? (
        <div role="tabpanel">
          <AbaCombustivel key={veiculo.id} veiculo={veiculo} />
        </div>
      ) : (
        <div role="tabpanel">
          <div className="opcoes opcoes--periodo" role="group" aria-label="Período">
            {PERIODOS.map(({ valor, rotulo }) => (
              <button key={valor} type="button" aria-pressed={periodo.tipo === valor}
                className={`opcao${periodo.tipo === valor ? " opcao--ativa" : ""}`}
                onClick={() => escolherTipo(valor)}>
                {rotulo}
              </button>
            ))}
          </div>
          <SeletorDoPeriodo periodo={periodo} atual={atual} aoMudar={(p) => irPara({ periodo: p })} />
          <ResumoDoPeriodo key={`${veiculo.id}-${chaveDoPeriodo(periodo)}`} veiculo={veiculo} periodo={periodo}
            versao={versao} />
          <Contas key={veiculo.id} veiculo={veiculo} versao={versao} aoMudar={() => setVersao((v) => v + 1)} />
          <Lancamentos key={`${veiculo.id}-${chaveDoPeriodo(periodo)}-l`} veiculo={veiculo} periodo={periodo}
            versao={versao} />
        </div>
      )}
    </main>
  );
}
