import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeMaisSinal } from "../components/Icones";
import { CartaoPendencia, TOM_DA_SITUACAO } from "../components/PecasManutencao";
import SeloStatus from "../components/SeloStatus";
import { BotaoVerValores } from "../components/ValoresManutencao";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarManutencoes, listarPendentes, listarPlanos } from "../services/manutencaoService";
import {
  ROTULO_SITUACAO,
  rotuloSistema,
  textoIntervalo,
  textoPrevisao,
  type Manutencao,
  type Pendencia,
  type Plano,
  type Situacao,
} from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso } from "../utils/datas";
import { formatarDinheiro, formatarKm } from "../utils/formatos";

type Aba = "pendentes" | "realizadas" | "planos";
const ABAS: { valor: Aba; rotulo: string }[] = [
  { valor: "pendentes", rotulo: "Pendentes" },
  { valor: "realizadas", rotulo: "Realizadas" },
  { valor: "planos", rotulo: "Planos" },
];
const GRUPOS: { situacao: Situacao; titulo: string }[] = [
  { situacao: "atrasada", titulo: "Atrasada" },
  { situacao: "proxima", titulo: "Próximas" },
  { situacao: "sem_base", titulo: "Dados insuficientes" },
  { situacao: "em_dia", titulo: "Em dia" },
];
const POR_PAGINA = 20;

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof ErroDaApi ? falha.message : padrao;
}

function AbaPendentes({ veiculo }: { veiculo: Veiculo }) {
  const [itens, setItens] = useState<Pendencia[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setItens((await listarPendentes(veiculo.id)).itens);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar as pendências."));
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />;
  if (itens === null) return <Carregando />;
  if (itens.length === 0) {
    return (
      <section className="cartao">
        <p className="cartao__titulo">Nenhuma pendência</p>
        <p className="texto-suave">
          Crie um plano (por exemplo, "troca de óleo a cada 10.000 km") na aba Planos, ou agende
          uma manutenção pelo botão +. Os prazos aparecem aqui.
        </p>
      </section>
    );
  }
  return (
    <>
      {GRUPOS.map(({ situacao, titulo }) => {
        const doGrupo = itens.filter((i) => i.situacao === situacao);
        if (doGrupo.length === 0) return null;
        return (
          <section key={situacao} aria-label={titulo}>
            <h2 className="rotulo-secao">{titulo}</h2>
            {situacao === "sem_base" && (
              <p className="texto-suave secao__dica secao__dica--solta">
                Sem saber quando foi feita pela última vez, não dá para dizer se está em dia.
                Abra o plano e informe.
              </p>
            )}
            <ul className="cartao lista-pendencias">
              {doGrupo.map((item) => (
                <CartaoPendencia key={`${item.tipo}-${item.plano_id ?? item.manutencao_id}`}
                  veiculoId={veiculo.id} item={item} podeRegistrar={veiculo.ativo} />
              ))}
            </ul>
          </section>
        );
      })}
    </>
  );
}

function AbaRealizadas({ veiculo }: { veiculo: Veiculo }) {
  const [itens, setItens] = useState<Manutencao[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const resultado = await listarManutencoes(veiculo.id, {
        status: "realizada", pagina: numero, porPagina: POR_PAGINA,
      });
      setItens((atuais) => (numero === 1 ? resultado.itens : [...atuais, ...resultado.itens]));
      setTotal(resultado.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar as manutenções."));
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return <Carregando />;
  if (total === 0) {
    return (
      <section className="cartao">
        <p className="cartao__titulo">Nenhuma manutenção realizada</p>
        <p className="texto-suave">Registre a primeira pelo botão +.</p>
      </section>
    );
  }
  return (
    <>
      <ul className="cartao lista-simples" aria-label="Manutenções realizadas">
        {itens.map((m) => (
          <li key={m.id}>
            <Link to={`/veiculos/${veiculo.id}/manutencoes/${m.id}`} className="lista-simples__item">
              <span className="lista-simples__texto">
                <span className="lista-simples__titulo">{m.descricao}</span>
                <span className="texto-suave">
                  {formatarDataIso(m.data)}
                  {m.quilometragem !== null ? ` · ${formatarKm(m.quilometragem)}` : ""}
                  {` · ${rotuloSistema(m.sistema)}`}
                </span>
              </span>
              <strong>{formatarDinheiro(m.valor)}</strong>
            </Link>
            <div className="lista-simples__acoes">
              <BotaoVerValores veiculoId={veiculo.id} manutencaoId={m.id} pequeno
                rotulo={`Ver valores de ${m.descricao}`} />
            </div>
          </li>
        ))}
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

function AbaPlanos({ veiculo }: { veiculo: Veiculo }) {
  const [planos, setPlanos] = useState<Plano[] | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async () => {
    try {
      setPlanos(await listarPlanos(veiculo.id));
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os planos."));
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />;
  if (planos === null) return <Carregando />;
  if (planos.length === 0) {
    return (
      <>
        <section className="cartao">
          <p className="cartao__titulo">Nenhum plano</p>
          <p className="texto-suave">
            Um plano é uma manutenção que se repete: por quilometragem, por tempo ou pelos dois.
            O aplicativo avisa quando estiver chegando a hora.
          </p>
        </section>
        <Link to={`/veiculos/${veiculo.id}/planos/novo`} className="botao botao--primario">
          Criar plano
        </Link>
      </>
    );
  }
  return (
    <ul className="cartao lista-simples" aria-label="Planos de manutenção">
      {planos.map((plano) => (
        <li key={plano.id}>
          <Link to={`/veiculos/${veiculo.id}/planos/${plano.id}`} className="lista-simples__item">
            <span className="lista-simples__texto">
              <span className="lista-simples__titulo">{plano.nome}</span>
              <span className="texto-suave">
                {textoIntervalo(plano)} · {rotuloSistema(plano.sistema)}
              </span>
              {plano.situacao && plano.situacao !== "sem_base" && (
                <span className="texto-suave">Próxima {textoPrevisao(plano)}</span>
              )}
            </span>
            {plano.situacao
              ? <SeloStatus tom={TOM_DA_SITUACAO[plano.situacao]}>{ROTULO_SITUACAO[plano.situacao]}</SeloStatus>
              : <SeloStatus tom="neutro">Inativo</SeloStatus>}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * A mesma tela para um veículo escolhido pelo endereço
 * (/veiculos/:veiculoId/manutencoes): é por aqui que se consulta o histórico
 * de um veículo inativo ou que não é o veículo em uso.
 */
export function ManutencaoDoVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Manutenção</h1>
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Conteudo veiculo={veiculo} />;
}

// Tela "Manutenção" (PDF, página 5), com as abas Pendentes, Realizadas e Planos,
// para o veículo em uso.
export default function ManutencaoPage() {
  const { carregando, erro, emUso, recarregar } = useVeiculos();

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Manutenção</h1>
        <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  if (!emUso) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Manutenção</h1>
        <section className="cartao">
          <p className="cartao__titulo">Nenhum veículo em uso</p>
          <p className="texto-suave">Cadastre ou reative um veículo para registrar manutenções.</p>
        </section>
        <Link to="/veiculos" className="botao botao--primario">Ver meus veículos</Link>
      </main>
    );
  }
  return <Conteudo veiculo={emUso} />;
}

function Conteudo({ veiculo: emUso }: { veiculo: Veiculo }) {
  const [parametros, setParametros] = useSearchParams();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const pedida = parametros.get("aba");
  const aba: Aba = ABAS.some((a) => a.valor === pedida) ? (pedida as Aba) : "pendentes";

  const novo = aba === "planos"
    ? { para: `/veiculos/${emUso.id}/planos/novo`, rotulo: "Novo plano" }
    : { para: `/veiculos/${emUso.id}/manutencoes/nova`, rotulo: "Nova manutenção" };

  return (
    <main className="conteudo conteudo--topo">
      <header className="cabecalho-pagina">
        <div>
          <h1 className="titulo-pagina">Manutenção</h1>
          <p className="texto-suave cabecalho-pagina__sub">
            {emUso.modelo} {emUso.ano} · {formatarKm(emUso.quilometragem)}
          </p>
        </div>
        {emUso.ativo && (
          <Link to={novo.para} className="botao-redondo botao-redondo--grande" aria-label={novo.rotulo}>
            <IconeMaisSinal />
          </Link>
        )}
      </header>
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {!emUso.ativo && (
        <Alerta tipo="info">Veículo inativo: o histórico pode ser consultado, mas não alterado.</Alerta>
      )}

      <div className="abas" role="tablist" aria-label="Seções de manutenção">
        {ABAS.map(({ valor, rotulo }) => (
          <button key={valor} type="button" role="tab" aria-selected={aba === valor}
            className={`abas__item${aba === valor ? " abas__item--ativa" : ""}`}
            onClick={() => setParametros(valor === "pendentes" ? {} : { aba: valor }, { replace: true })}>
            {rotulo}
          </button>
        ))}
      </div>

      <div role="tabpanel">
        {aba === "pendentes" && <AbaPendentes key={emUso.id} veiculo={emUso} />}
        {aba === "realizadas" && <AbaRealizadas key={emUso.id} veiculo={emUso} />}
        {aba === "planos" && <AbaPlanos key={emUso.id} veiculo={emUso} />}
      </div>
    </main>
  );
}
