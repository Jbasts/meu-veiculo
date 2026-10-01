import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeCheck, IconeMaisSinal } from "../components/Icones";
import {
  AntesDepois,
  BarraOrcamento,
  GastoDoOrcamento,
  TOM_DO_STATUS_PROJETO,
  textoDaDiferenca,
  textoDaSituacao,
} from "../components/PecasProjeto";
import SeloStatus from "../components/SeloStatus";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarProjetos } from "../services/projetoService";
import {
  ROTULO_STATUS_PROJETO,
  rotuloCategoriaProjeto,
  type FiltroProjeto,
  type Projeto,
} from "../types/projeto";
import type { Veiculo } from "../types/veiculo";

const FILTROS: { valor: FiltroProjeto; rotulo: string }[] = [
  { valor: "todos", rotulo: "Todos" },
  { valor: "em_andamento", rotulo: "Em andamento" },
  { valor: "planejado", rotulo: "Planejados" },
  { valor: "concluido", rotulo: "Concluídos" },
  { valor: "cancelado", rotulo: "Cancelados" },
];
const POR_PAGINA = 20;

function CartaoProjeto({ veiculo, projeto: p }: { veiculo: Veiculo; projeto: Projeto }) {
  const mostrarFotos = p.status === "em_andamento" || p.foto_antes_id !== null || p.foto_depois_id !== null;
  return (
    <li className="cartao projeto">
      <Link to={`/veiculos/${veiculo.id}/projetos/${p.id}`} className="projeto__link">
        <span className="projeto__topo">
          <span className="texto-suave">{rotuloCategoriaProjeto(p.categoria)}</span>
          <SeloStatus tom={TOM_DO_STATUS_PROJETO[p.status]}>
            {p.status === "concluido" && <IconeCheck tamanho={14} />} {ROTULO_STATUS_PROJETO[p.status]}
          </SeloStatus>
        </span>
        <span className="projeto__nome">{p.nome}</span>
        <GastoDoOrcamento projeto={p} />
        <BarraOrcamento projeto={p} />
        <span className="projeto__rodape">
          <span className="texto-suave">{textoDaSituacao(p)}</span>
          <span className="texto-suave">{textoDaDiferenca(p)}</span>
        </span>
      </Link>
      {mostrarFotos && <AntesDepois veiculoId={veiculo.id} projeto={p} podeAdicionar={veiculo.ativo} />}
    </li>
  );
}

function Lista({ veiculo, filtro }: { veiculo: Veiculo; filtro: FiltroProjeto }) {
  const [itens, setItens] = useState<Projeto[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarProjetos(veiculo.id, filtro, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setTotal(r.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar os projetos.");
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id, filtro]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return <Carregando />;
  if (total === 0) {
    return (
      <section className="cartao">
        <p className="cartao__titulo">{filtro === "todos" ? "Nenhum projeto ainda" : "Nenhum projeto nesta situação"}</p>
        <p className="texto-suave">
          Um projeto é uma melhoria no carro (rodas, som, película...): com orçamento, gastos e fotos
          de antes e depois. Crie o primeiro pelo botão +.
        </p>
      </section>
    );
  }
  return (
    <>
      <ul className="lista-projetos" aria-label="Projetos">
        {itens.map((p) => <CartaoProjeto key={p.id} veiculo={veiculo} projeto={p} />)}
      </ul>
      {itens.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
    </>
  );
}

function Conteudo({ veiculo }: { veiculo: Veiculo }) {
  const [parametros, setParametros] = useSearchParams();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const pedido = parametros.get("filtro");
  const filtro: FiltroProjeto = FILTROS.some((f) => f.valor === pedido) ? (pedido as FiltroProjeto) : "todos";
  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Projetos" voltarPara="/mais" acao={veiculo.ativo ? (
        <Link to={`/veiculos/${veiculo.id}/projetos/novo`} className="botao-redondo botao-redondo--grande"
          aria-label="Novo projeto">
          <IconeMaisSinal />
        </Link>
      ) : null} />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {!veiculo.ativo && <Alerta tipo="info">Veículo inativo: os projetos podem ser consultados, mas não alterados.</Alerta>}
      <div className="opcoes opcoes--rolagem" role="group" aria-label="Filtrar projetos">
        {FILTROS.map(({ valor, rotulo }) => (
          <button key={valor} type="button" aria-pressed={filtro === valor}
            className={`opcao${filtro === valor ? " opcao--ativa" : ""}`}
            onClick={() => setParametros(valor === "todos" ? {} : { filtro: valor }, { replace: true })}>
            {rotulo}
          </button>
        ))}
      </div>
      <Lista key={`${veiculo.id}-${filtro}`} veiculo={veiculo} filtro={filtro} />
    </main>
  );
}

/** A mesma tela para um veículo escolhido pelo endereço (/veiculos/:veiculoId/projetos). */
export function ProjetosDoVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Projetos" voltarPara="/mais" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Conteudo veiculo={veiculo} />;
}

// Tela "Projetos" (PDF, página 16) do veículo em uso.
export default function ProjetosPage() {
  const { carregando, erro, emUso, recarregar } = useVeiculos();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !emUso) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Projetos" voltarPara="/mais" />
        {erro ? <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} /> : (
          <section className="cartao">
            <p className="cartao__titulo">Nenhum veículo em uso</p>
            <p className="texto-suave">Cadastre ou reative um veículo para criar projetos.</p>
          </section>
        )}
      </main>
    );
  }
  return <Conteudo veiculo={emUso} />;
}
