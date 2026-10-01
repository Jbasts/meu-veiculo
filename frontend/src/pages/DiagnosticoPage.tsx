import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeMaisSinal } from "../components/Icones";
import { CartaoDiagnostico, LinhaEncerrado } from "../components/PecasDiagnostico";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarDiagnosticos } from "../services/diagnosticoService";
import { emAberto, type DiagnosticoResumo, type FiltroDiagnostico } from "../types/diagnostico";
import type { Veiculo } from "../types/veiculo";
import { formatarKm } from "../utils/formatos";

const ABAS: { valor: FiltroDiagnostico; rotulo: string }[] = [
  { valor: "abertos", rotulo: "Abertos" },
  { valor: "resolvidos", rotulo: "Resolvidos" },
  { valor: "todos", rotulo: "Todos" },
];
const POR_PAGINA = 20;
const RECENTES = 3;

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof ErroDaApi ? falha.message : padrao;
}

/** Abertos em cartões; resolvidos e descartados numa lista (como no PDF). */
function Itens({ veiculoId, itens }: { veiculoId: number; itens: DiagnosticoResumo[] }) {
  const abertos = itens.filter((d) => emAberto(d.status));
  const encerrados = itens.filter((d) => !emAberto(d.status));
  return (
    <>
      {abertos.length > 0 && (
        <ul className="lista-diagnosticos" aria-label="Problemas em aberto">
          {abertos.map((d) => <CartaoDiagnostico key={d.id} veiculoId={veiculoId} diagnostico={d} />)}
        </ul>
      )}
      {encerrados.length > 0 && (
        <ul className="cartao lista-simples" aria-label="Problemas encerrados">
          {encerrados.map((d) => <LinhaEncerrado key={d.id} veiculoId={veiculoId} diagnostico={d} />)}
        </ul>
      )}
    </>
  );
}

const VAZIO: Record<FiltroDiagnostico, { titulo: string; texto: string }> = {
  abertos: {
    titulo: "Nenhum problema em aberto",
    texto: "Notou um barulho, um vazamento ou uma luz no painel? Registre pelo botão + para acompanhar até resolver.",
  },
  resolvidos: {
    titulo: "Nenhum problema resolvido",
    texto: "Os problemas resolvidos com uma manutenção ou descartados aparecem aqui.",
  },
  todos: {
    titulo: "Nenhum diagnóstico registrado",
    texto: "Registre o primeiro problema pelo botão +.",
  },
};

function Lista({ veiculo, filtro, aoContar }: {
  veiculo: Veiculo; filtro: FiltroDiagnostico; aoContar?: (total: number) => void;
}) {
  const [itens, setItens] = useState<DiagnosticoResumo[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const resultado = await listarDiagnosticos(veiculo.id, filtro, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? resultado.itens : [...atuais, ...resultado.itens]));
      setTotal(resultado.total);
      setPagina(numero);
      setErro(null);
      aoContar?.(resultado.total);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os diagnósticos."));
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id, filtro, aoContar]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return <Carregando />;
  if (total === 0) {
    return (
      <section className="cartao">
        <p className="cartao__titulo">{VAZIO[filtro].titulo}</p>
        <p className="texto-suave">{VAZIO[filtro].texto}</p>
      </section>
    );
  }
  return (
    <>
      <Itens veiculoId={veiculo.id} itens={itens} />
      {itens.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
    </>
  );
}

/** "Resolvidos recentemente", embaixo dos abertos. Some se não houver nenhum. */
function ResolvidosRecentes({ veiculo, aoVerTodos }: { veiculo: Veiculo; aoVerTodos: () => void }) {
  const [itens, setItens] = useState<DiagnosticoResumo[] | null>(null);
  const [total, setTotal] = useState(0);

  useEffect(() => {
    let cancelado = false;
    listarDiagnosticos(veiculo.id, "resolvidos", 1, RECENTES)
      .then((resultado) => {
        if (!cancelado) {
          setItens(resultado.itens);
          setTotal(resultado.total);
        }
      })
      .catch(() => {
        if (!cancelado) setItens([]); // a lista principal já mostra o erro, se houver
      });
    return () => {
      cancelado = true;
    };
  }, [veiculo.id]);

  if (!itens || itens.length === 0) return null;
  return (
    <section aria-label="Resolvidos recentemente">
      <h2 className="titulo-secao">Resolvidos recentemente</h2>
      <ul className="cartao lista-simples">
        {itens.map((d) => <LinhaEncerrado key={d.id} veiculoId={veiculo.id} diagnostico={d} />)}
      </ul>
      {total > RECENTES && (
        <p className="link-direita">
          <button type="button" className="botao-link" onClick={aoVerTodos}>Ver todos ({total})</button>
        </p>
      )}
    </section>
  );
}

/** A mesma tela para um veículo escolhido pelo endereço (/veiculos/:veiculoId/diagnosticos). */
export function DiagnosticoDoVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Diagnóstico</h1>
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Conteudo veiculo={veiculo} />;
}

// Tela "Diagnóstico" (PDF, página 6), com as abas Abertos, Resolvidos e Todos,
// para o veículo em uso.
export default function DiagnosticoPage() {
  const { carregando, erro, emUso, recarregar } = useVeiculos();

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Diagnóstico</h1>
        <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  if (!emUso) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Diagnóstico</h1>
        <section className="cartao">
          <p className="cartao__titulo">Nenhum veículo em uso</p>
          <p className="texto-suave">Cadastre ou reative um veículo para registrar problemas.</p>
        </section>
        <Link to="/veiculos" className="botao botao--primario">Ver meus veículos</Link>
      </main>
    );
  }
  return <Conteudo veiculo={emUso} />;
}

function Conteudo({ veiculo }: { veiculo: Veiculo }) {
  const [parametros, setParametros] = useSearchParams();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const pedida = parametros.get("aba");
  const aba: FiltroDiagnostico = ABAS.some((a) => a.valor === pedida) ? (pedida as FiltroDiagnostico) : "abertos";
  const [totalAbertos, setTotalAbertos] = useState<number | null>(null);

  // O número da aba "Abertos (2)" aparece mesmo quando outra aba está aberta.
  useEffect(() => {
    if (aba === "abertos") return; // a própria lista informa
    let cancelado = false;
    listarDiagnosticos(veiculo.id, "abertos", 1, 1)
      .then((resultado) => {
        if (!cancelado) setTotalAbertos(resultado.total);
      })
      .catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [veiculo.id, aba]);

  function irPara(valor: FiltroDiagnostico) {
    setParametros(valor === "abertos" ? {} : { aba: valor }, { replace: true });
  }

  return (
    <main className="conteudo conteudo--topo">
      <header className="cabecalho-pagina">
        <div>
          <h1 className="titulo-pagina">Diagnóstico</h1>
          <p className="texto-suave cabecalho-pagina__sub">
            {veiculo.modelo} {veiculo.ano} · {formatarKm(veiculo.quilometragem)}
          </p>
        </div>
        {veiculo.ativo && (
          <Link to={`/veiculos/${veiculo.id}/diagnosticos/novo`}
            className="botao-redondo botao-redondo--grande" aria-label="Novo diagnóstico">
            <IconeMaisSinal />
          </Link>
        )}
      </header>
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {!veiculo.ativo && (
        <Alerta tipo="info">Veículo inativo: o histórico pode ser consultado, mas não alterado.</Alerta>
      )}

      <div className="abas" role="tablist" aria-label="Situação dos diagnósticos">
        {ABAS.map(({ valor, rotulo }) => (
          <button key={valor} type="button" role="tab" aria-selected={aba === valor}
            className={`abas__item${aba === valor ? " abas__item--ativa" : ""}`}
            onClick={() => irPara(valor)}>
            {valor === "abertos" && totalAbertos !== null ? `${rotulo} (${totalAbertos})` : rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {aba === "abertos" && (
          <>
            <Lista key={`${veiculo.id}-abertos`} veiculo={veiculo} filtro="abertos" aoContar={setTotalAbertos} />
            <ResolvidosRecentes key={veiculo.id} veiculo={veiculo} aoVerTodos={() => irPara("resolvidos")} />
          </>
        )}
        {aba === "resolvidos" && <Lista key={`${veiculo.id}-resolvidos`} veiculo={veiculo} filtro="resolvidos" />}
        {aba === "todos" && <Lista key={`${veiculo.id}-todos`} veiculo={veiculo} filtro="todos" />}
      </div>
    </main>
  );
}
