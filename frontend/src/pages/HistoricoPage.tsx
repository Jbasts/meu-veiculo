import { useCallback, useEffect, useState, type ComponentType } from "react";
import { Link, useSearchParams } from "react-router";

import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoSelecao } from "../components/Formulario";
import {
  IconeBomba,
  IconeDiagnostico,
  IconeManutencao,
  IconeProjeto,
  IconeRecibo,
} from "../components/Icones";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarHistorico } from "../services/painelService";
import { ROTULO_COMBUSTIVEL, unidade, type Combustivel } from "../types/abastecimento";
import { ROTULO_STATUS } from "../types/diagnostico";
import { rotuloCategoria } from "../types/gasto";
import {
  FILTROS_HISTORICO,
  type EventoHistorico,
  type FiltroHistorico,
  type PaginaHistorico,
  type PeriodoHistorico,
  type TipoEvento,
} from "../types/historico";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, mesDaData, nomeDoMes } from "../utils/datas";
import { formatarDecimal, formatarDinheiro, formatarKm } from "../utils/formatos";

const POR_PAGINA = 50;
const MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];

const ICONE_DO_TIPO: Record<TipoEvento, { Icone: ComponentType<{ tamanho?: number }>; tom: string }> = {
  manutencao: { Icone: IconeManutencao, tom: "ok" },
  abastecimento: { Icone: IconeBomba, tom: "aviso" },
  gasto: { Icone: IconeRecibo, tom: "neutro" },
  projeto: { Icone: IconeProjeto, tom: "neutro" },
  diagnostico: { Icone: IconeDiagnostico, tom: "alerta" },
};

/** Título e linha de baixo de cada lançamento, como no PDF ("Shell, 40,0 L de gasolina"). */
export function textosDoEvento(e: EventoHistorico): { titulo: string; detalhe: string } {
  const km = e.quilometragem !== null ? `, ${formatarKm(e.quilometragem)}` : "";
  switch (e.tipo) {
    case "manutencao":
      return { titulo: e.descricao, detalhe: `Manutenção${km}` };
    case "abastecimento": {
      const combustivel = (e.combustivel ?? "gasolina") as Combustivel;
      const medida = unidade(combustivel).curta;
      const quantidade = e.quantidade ? `${formatarDecimal(e.quantidade, 1)} ${medida} de ` : "";
      const nome = (ROTULO_COMBUSTIVEL[combustivel] ?? combustivel).toLowerCase();
      return {
        titulo: combustivel === "eletrica" ? "Recarga" : "Abastecimento",
        detalhe: `${e.posto ? `${e.posto}, ` : ""}${quantidade}${nome}`,
      };
    }
    case "gasto":
      return { titulo: rotuloCategoria(e.categoria ?? "outros"), detalhe: e.descricao_gasto ?? "Gasto avulso" };
    case "projeto":
      return { titulo: e.projeto_nome ?? e.descricao, detalhe: `Projeto: ${e.item_descricao ?? ""}` };
    case "diagnostico":
      return {
        titulo: e.descricao,
        detalhe: `Problema registrado${km}${e.situacao ? `, ${ROTULO_STATUS[e.situacao].toLowerCase()}` : ""}`,
      };
  }
}

function destinoDoEvento(veiculoId: number, e: EventoHistorico): string | null {
  const base = `/veiculos/${veiculoId}`;
  if (e.tipo === "manutencao") return `${base}/manutencoes/${e.origem_id}`;
  if (e.tipo === "abastecimento") return `${base}/abastecimentos/${e.origem_id}`;
  if (e.tipo === "gasto") return `${base}/gastos/${e.origem_id}`;
  if (e.tipo === "diagnostico") return `${base}/diagnosticos/${e.origem_id}`;
  return e.projeto_id !== null ? `${base}/projetos/${e.projeto_id}` : null;
}

function ItemDoHistorico({ veiculoId, evento: e }: { veiculoId: number; evento: EventoHistorico }) {
  const { Icone, tom } = ICONE_DO_TIPO[e.tipo];
  const { titulo, detalhe } = textosDoEvento(e);
  const [, mes, dia] = e.data.split("-");
  const conteudo = (
    <>
      <span className="eventos__data" aria-label={formatarDataIso(e.data)}>
        <strong>{dia}</strong>
        <span>{MESES_CURTOS[Number(mes) - 1]}</span>
      </span>
      <span className={`pendencia__icone pendencia__icone--${tom} eventos__icone`}><Icone tamanho={20} /></span>
      <span className="lista-simples__texto">
        <span className="lista-simples__titulo">{titulo}</span>
        <span className="texto-suave">{detalhe}</span>
      </span>
      {e.valor !== null
        ? <strong className="eventos__valor">{formatarDinheiro(e.valor)}</strong>
        : <span className="eventos__valor texto-suave">sem valor</span>}
    </>
  );
  const destino = destinoDoEvento(veiculoId, e);
  return (
    <li className="eventos__item">
      {destino ? <Link to={destino} className="eventos__link">{conteudo}</Link>
        : <div className="eventos__link">{conteudo}</div>}
    </li>
  );
}

/** Agrupa os lançamentos carregados por mês, mantendo a ordem (mais recente primeiro). */
function porMes(itens: EventoHistorico[]): { chave: string; ano: number; mes: number; itens: EventoHistorico[] }[] {
  const grupos: { chave: string; ano: number; mes: number; itens: EventoHistorico[] }[] = [];
  for (const item of itens) {
    const { ano, mes } = mesDaData(item.data);
    const chave = `${ano}-${mes}`;
    const ultimo = grupos[grupos.length - 1];
    if (ultimo && ultimo.chave === chave) ultimo.itens.push(item);
    else grupos.push({ chave, ano, mes, itens: [item] });
  }
  return grupos;
}

function Lista({ veiculo, filtro, periodo, ano, aoCarregarAnos }: {
  veiculo: Veiculo; filtro: FiltroHistorico; periodo: PeriodoHistorico; ano: number | null;
  aoCarregarAnos: (anos: number[]) => void;
}) {
  const [dados, setDados] = useState<PaginaHistorico | null>(null);
  const [itens, setItens] = useState<EventoHistorico[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarHistorico(veiculo.id, filtro, periodo, ano, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setDados(r);
      aoCarregarAnos(r.anos_disponiveis);
      setErro(null);
    } catch (falha) {
      setErro(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o histórico.");
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id, filtro, periodo, ano, aoCarregarAnos]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, dados?.pagina ?? 1))} />;
  if (!dados) return <Carregando />;
  const intervalo = dados.inicio && dados.fim
    ? `${formatarDataIso(dados.inicio)} a ${formatarDataIso(dados.fim)}` : "Desde o primeiro registro";
  if (dados.total === 0) {
    return (
      <>
        <p className="texto-suave historico__periodo">{intervalo}</p>
        <section className="cartao">
          <p className="cartao__titulo">Nada registrado neste período</p>
          <p className="texto-suave">
            Manutenções realizadas, abastecimentos, gastos pagos, gastos de projetos e problemas
            registrados aparecem aqui, do mais recente para o mais antigo.
          </p>
        </section>
      </>
    );
  }
  const totais = new Map(dados.meses.map((m) => [`${m.ano}-${m.mes}`, m.total]));
  return (
    <>
      <p className="texto-suave historico__periodo">{intervalo}</p>
      {porMes(itens).map((grupo) => (
        <section key={grupo.chave} className="historico__mes" aria-label={nomeDoMes(grupo)}>
          <h2 className="historico__titulo-mes">
            <span>{nomeDoMes(grupo)}</span>
            {totais.has(grupo.chave) && <span>{formatarDinheiro(totais.get(grupo.chave) ?? "0")}</span>}
          </h2>
          <ul className="eventos">
            {grupo.itens.map((e) => (
              <ItemDoHistorico key={`${e.tipo}-${e.origem_id}`} veiculoId={veiculo.id} evento={e} />
            ))}
          </ul>
        </section>
      ))}
      {itens.length < dados.total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(dados.pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${dados.total - itens.length} restantes)`}
        </button>
      )}
      <p className="texto-suave historico__nota">
        O total de cada mês soma só os lançamentos com valor. Problemas registrados aparecem sem
        valor: o custo deles é o da manutenção que os resolveu. Manutenções agendadas e contas
        pendentes ficam em Manutenção e em Finanças.
      </p>
    </>
  );
}

function Conteudo({ veiculo, voltarPara }: { veiculo: Veiculo; voltarPara: string }) {
  const [parametros, setParametros] = useSearchParams();
  const [anos, setAnos] = useState<number[]>([]);
  const pedido = parametros.get("tipo");
  const filtro: FiltroHistorico = FILTROS_HISTORICO.some((f) => f.valor === pedido)
    ? (pedido as FiltroHistorico) : "tudo";
  const anoPedido = Number(parametros.get("ano"));
  const periodo: PeriodoHistorico = parametros.get("periodo") === "tudo" ? "tudo"
    : Number.isInteger(anoPedido) && anoPedido > 0 ? "ano" : "12_meses";
  const ano = periodo === "ano" ? anoPedido : null;

  function irPara(novo: { tipo?: FiltroHistorico; periodo?: string }) {
    const valores: Record<string, string> = {};
    const tipo = novo.tipo ?? filtro;
    if (tipo !== "tudo") valores.tipo = tipo;
    const escolha = novo.periodo ?? (periodo === "ano" ? String(ano) : periodo);
    if (escolha === "tudo") valores.periodo = "tudo";
    else if (escolha !== "12_meses") valores.ano = escolha;
    setParametros(valores, { replace: true });
  }

  const opcoesDePeriodo = [
    { valor: "12_meses", rotulo: "Últimos 12 meses" },
    ...[...new Set([...anos, ...(ano ? [ano] : [])])].sort((a, b) => b - a)
      .map((a) => ({ valor: String(a), rotulo: String(a) })),
    { valor: "tudo", rotulo: "Tudo" },
  ];

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Histórico" voltarPara={voltarPara} />
      <p className="texto-suave historico__veiculo">{veiculo.marca} {veiculo.modelo} {veiculo.ano}</p>
      <div className="opcoes opcoes--rolagem" role="group" aria-label="Filtrar por tipo">
        {FILTROS_HISTORICO.map(({ valor, rotulo }) => (
          <button key={valor} type="button" aria-pressed={filtro === valor}
            className={`opcao${filtro === valor ? " opcao--ativa" : ""}`}
            onClick={() => irPara({ tipo: valor })}>
            {rotulo}
          </button>
        ))}
      </div>
      <div className="historico__seletor">
        <CampoSelecao rotulo="Período" opcoes={opcoesDePeriodo}
          value={periodo === "ano" ? String(ano) : periodo}
          onChange={(evento) => irPara({ periodo: evento.target.value })} />
      </div>
      <Lista key={`${veiculo.id}-${filtro}-${periodo}-${ano}`} veiculo={veiculo} filtro={filtro}
        periodo={periodo} ano={ano} aoCarregarAnos={setAnos} />
    </main>
  );
}

/** Histórico de um veículo escolhido pelo endereço (/veiculos/:veiculoId/historico). */
export function HistoricoDoVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Histórico" voltarPara="/mais" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Conteudo veiculo={veiculo} voltarPara={`/veiculos/${veiculo.id}`} />;
}

// Tela "Histórico" (PDF, página 17) do veículo em uso.
export default function HistoricoPage() {
  const { carregando, erro, emUso, recarregar } = useVeiculos();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !emUso) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Histórico" voltarPara="/mais" />
        {erro ? <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} /> : (
          <section className="cartao">
            <p className="cartao__titulo">Nenhum veículo em uso</p>
            <p className="texto-suave">Cadastre ou reative um veículo para ver o histórico.</p>
          </section>
        )}
      </main>
    );
  }
  return <Conteudo veiculo={emUso} voltarPara="/mais" />;
}
