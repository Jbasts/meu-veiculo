import { useEffect, useState } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import {
  IconeAlerta,
  IconeBomba,
  IconeDiagnostico,
  IconeManutencao,
  IconeRecibo,
  IconeSeta,
  IconeSetaBaixo,
} from "../components/Icones";
import { BarraEmPartes, periodoCurtoDoCustoPorKm } from "../components/PecasCusto";
import { NivelDoTanqueCartao } from "../components/PecasTanque";
import { TOM_DA_GRAVIDADE } from "../components/PecasDiagnostico";
import { destinoDaPendencia, IconeDaSituacao, TOM_DA_SITUACAO } from "../components/PecasManutencao";
import { Hodometro, Placa } from "../components/PecasVeiculo";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { listarDiagnosticos } from "../services/diagnosticoService";
import { listarPendentes } from "../services/manutencaoService";
import { obterPainel } from "../services/painelService";
import { ROTULO_COMBUSTIVEL, unidade, type Combustivel } from "../types/abastecimento";
import { rotuloGravidade, type DiagnosticoResumo } from "../types/diagnostico";
import { rotuloCategoria } from "../types/gasto";
import { resumoDoPrazo, type Pendencia } from "../types/manutencao";
import type { AvisosDoTanque, ContasEmAtraso, PainelInicio } from "../types/painel";
import { formatarDataIso, nomeDoMes } from "../utils/datas";
import { formatarDecimal, formatarDinheiro } from "../utils/formatos";

const MAXIMO_DE_ALERTAS = 5;

/** "Diagnóstico aberto, gravidade média" */
function textoDoDiagnostico(d: DiagnosticoResumo): string {
  return `Diagnóstico ${d.status === "em_observacao" ? "em observação" : "aberto"}, `
    + `gravidade ${rotuloGravidade(d.gravidade).toLowerCase()}`;
}

/** "2 contas vencidas, R$ 1.288,38 em atraso" e "1 conta vence hoje" (gastos pendentes). */
function AlertasDeContas({ contas }: { contas: ContasEmAtraso }) {
  const linhas: { titulo: string; texto: string; tom: string }[] = [];
  if (contas.vencidas > 0) {
    linhas.push({
      titulo: contas.vencidas === 1 ? "1 conta vencida" : `${contas.vencidas} contas vencidas`,
      texto: `${formatarDinheiro(contas.total_vencidas)} em atraso`,
      tom: "alerta",
    });
  }
  if (contas.vencem_hoje > 0) {
    linhas.push({
      titulo: contas.vencem_hoje === 1 ? "1 conta vence hoje" : `${contas.vencem_hoje} contas vencem hoje`,
      texto: "Veja em Finanças → A vencer",
      tom: "aviso",
    });
  }
  return (
    <ul className="cartao lista-simples" aria-label="Contas a pagar">
      {linhas.map((l) => (
        <li key={l.titulo}>
          <Link to="/financas" className="lista-simples__item">
            <span className={`pendencia__icone pendencia__icone--${l.tom}`}><IconeAlerta /></span>
            <span className="lista-simples__texto">
              <span className="lista-simples__titulo">{l.titulo}</span>
              <span className={`alerta-texto alerta-texto--${l.tom}`}>{l.texto}</span>
            </span>
            <IconeSeta tamanho={20} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** Tamanho do tanque que falta no cadastro e a marcação do início do mês. */
function AlertasDoTanque({ veiculoId, tanque }: { veiculoId: number; tanque: AvisosDoTanque }) {
  const linhas: { titulo: string; texto: string; para: string; tom: string }[] = [];
  if (tanque.tamanho_pendente) {
    linhas.push({
      titulo: "Informe o tamanho do tanque",
      texto: "Atualize o cadastro do veículo: ele confere os litros ao abastecer e usa o nível do marcador",
      para: `/veiculos/${veiculoId}/editar`,
      tom: "aviso",
    });
  }
  if (tanque.marcacao_do_mes_pendente) {
    linhas.push({
      titulo: "Marque o km e o nível do tanque",
      texto: "Uma vez no início do mês: deixa o consumo do mês mais exato",
      para: `/veiculos/${veiculoId}/tanque/marcacoes/nova`,
      tom: "aviso",
    });
  }
  return (
    <ul className="cartao lista-simples" aria-label="Tanque">
      {linhas.map((l) => (
        <li key={l.titulo}>
          <Link to={l.para} className="lista-simples__item">
            <span className={`pendencia__icone pendencia__icone--${l.tom}`}><IconeBomba /></span>
            <span className="lista-simples__texto">
              <span className="lista-simples__titulo">{l.titulo}</span>
              <span className="texto-suave">{l.texto}</span>
            </span>
            <IconeSeta tamanho={20} />
          </Link>
        </li>
      ))}
    </ul>
  );
}

/**
 * "Precisa de atenção": manutenções atrasadas e próximas, problemas em aberto,
 * contas vencidas e avisos do tanque do veículo em uso. Cada fonte falha
 * sozinha, sem esconder a outra.
 */
function PrecisaDeAtencao({ veiculoId, contas, tanque }: {
  veiculoId: number; contas: ContasEmAtraso | null; tanque: AvisosDoTanque | null;
}) {
  const [itens, setItens] = useState<Pendencia[] | null>(null);
  const [falhou, setFalhou] = useState(false);
  const [problemas, setProblemas] = useState<{ itens: DiagnosticoResumo[]; total: number } | null>(null);
  const [falhouProblemas, setFalhouProblemas] = useState(false);

  useEffect(() => {
    let cancelado = false;
    listarPendentes(veiculoId)
      .then((pendentes) => {
        if (!cancelado) {
          setItens(pendentes.itens.filter((i) => i.situacao === "atrasada" || i.situacao === "proxima"));
        }
      })
      .catch(() => {
        if (!cancelado) setFalhou(true);
      });
    // Os abertos vêm dos mais graves para os menos graves.
    listarDiagnosticos(veiculoId, "abertos", 1, MAXIMO_DE_ALERTAS)
      .then((pagina) => {
        if (!cancelado) setProblemas({ itens: pagina.itens, total: pagina.total });
      })
      .catch(() => {
        if (!cancelado) setFalhouProblemas(true);
      });
    return () => {
      cancelado = true;
    };
  }, [veiculoId]);

  const temManutencao = itens !== null && itens.length > 0;
  const temProblema = problemas !== null && problemas.total > 0;
  const temConta = contas !== null && contas.vencidas + contas.vencem_hoje > 0;
  const temTanque = tanque !== null && (tanque.tamanho_pendente || tanque.marcacao_do_mes_pendente);
  return (
    <>
      {falhou && <p className="texto-suave">Não foi possível carregar os alertas de manutenção.</p>}
      {falhouProblemas && <p className="texto-suave">Não foi possível carregar os diagnósticos em aberto.</p>}
      {(temManutencao || temProblema || temConta || temTanque) && (
        <section aria-label="Precisa de atenção">
          <h2 className="titulo-secao">Precisa de atenção</h2>
          {temManutencao && <AlertasDeManutencao veiculoId={veiculoId} itens={itens} />}
          {temProblema && (
            <>
              <ul className="cartao lista-simples" aria-label="Diagnósticos em aberto">
                {problemas.itens.map((d) => (
                  <li key={d.id}>
                    <Link to={`/veiculos/${veiculoId}/diagnosticos/${d.id}`} className="lista-simples__item">
                      <span className={`pendencia__icone pendencia__icone--${TOM_DA_GRAVIDADE[d.gravidade]}`}>
                        <IconeDiagnostico />
                      </span>
                      <span className="lista-simples__texto">
                        <span className="lista-simples__titulo">{d.titulo}</span>
                        <span className="texto-suave">{textoDoDiagnostico(d)}</span>
                      </span>
                      <IconeSeta tamanho={20} />
                    </Link>
                  </li>
                ))}
              </ul>
              {problemas.total > problemas.itens.length && (
                <p className="link-direita">
                  <Link to="/diagnostico" className="link">Ver todos os diagnósticos ({problemas.total})</Link>
                </p>
              )}
            </>
          )}
          {temConta && <AlertasDeContas contas={contas} />}
          {temTanque && <AlertasDoTanque veiculoId={veiculoId} tanque={tanque} />}
        </section>
      )}
    </>
  );
}

function AlertasDeManutencao({ veiculoId, itens }: { veiculoId: number; itens: Pendencia[] }) {
  return (
    <>
      <ul className="cartao lista-simples" aria-label="Manutenções">
        {itens.slice(0, MAXIMO_DE_ALERTAS).map((item) => {
          const resumo = resumoDoPrazo(item);
          return (
            <li key={`${item.tipo}-${item.plano_id ?? item.manutencao_id}`}>
              <Link to={destinoDaPendencia(veiculoId, item)} className="lista-simples__item">
                <IconeDaSituacao situacao={item.situacao} />
                <span className="lista-simples__texto">
                  <span className="lista-simples__titulo">{item.titulo}</span>
                  <span className={`alerta-texto alerta-texto--${TOM_DA_SITUACAO[item.situacao]}`}>
                    {item.situacao === "atrasada" ? "Atrasada" : "Próxima"}: {resumo.valor} {resumo.rotulo}
                  </span>
                </span>
                <IconeSeta tamanho={20} />
              </Link>
            </li>
          );
        })}
      </ul>
      {itens.length > MAXIMO_DE_ALERTAS && (
        <p className="link-direita">
          <Link to="/manutencao" className="link">Ver todas ({itens.length})</Link>
        </p>
      )}
    </>
  );
}

/** Abastecer, Gasto, Manutenção e Problema (PDF, página 2). */
function Atalhos({ veiculoId }: { veiculoId: number }) {
  const base = `/veiculos/${veiculoId}`;
  const atalhos = [
    { para: `${base}/abastecimentos/novo`, rotulo: "Abastecer", Icone: IconeBomba },
    { para: `${base}/gastos/novo`, rotulo: "Gasto", Icone: IconeRecibo },
    { para: `${base}/manutencoes/nova`, rotulo: "Manutenção", Icone: IconeManutencao },
    { para: `${base}/diagnosticos/novo`, rotulo: "Problema", Icone: IconeDiagnostico },
  ];
  return (
    <nav className="atalhos" aria-label="Registrar">
      {atalhos.map(({ para, rotulo, Icone }) => (
        <Link key={rotulo} to={para} className="atalhos__item">
          <Icone />
          <span>{rotulo}</span>
        </Link>
      ))}
    </nav>
  );
}

/** "Gastos em outubro": as mesmas despesas da aba Finanças, em três grupos. */
function GastosDoMesCartao({ painel }: { painel: PainelInicio }) {
  const mes = painel.gastos_do_mes;
  const nome = nomeDoMes({ ano: mes.ano, mes: mes.mes }).split(" ")[0].toLowerCase();
  return (
    <section className="cartao custo" aria-label={`Gastos em ${nome}`}>
      <div className="custo__topo">
        <span className="texto-suave">Gastos em {nome}</span>
        <Link to="/financas" className="link">Ver finanças</Link>
      </div>
      <p className="custo__valor">{formatarDinheiro(mes.total)}</p>
      {mes.parcelas.length > 0
        ? <BarraEmPartes parcelas={mes.parcelas} singular rotulo={`Gastos em ${nome} por grupo`} />
        : <p className="texto-suave">Nenhuma despesa registrada em {nome}.</p>}
    </section>
  );
}

function emQuantosDias(dias: number): string {
  if (dias === 0) return "hoje";
  if (dias === 1) return "amanhã";
  return `em ${dias} dias`;
}

/** "Próximos gastos": contas lançadas para pagar depois (ex.: IPVA do ano que vem). */
function GastosFuturosCartao({ veiculoId, painel }: { veiculoId: number; painel: PainelInicio }) {
  const futuros = painel.gastos_futuros;
  return (
    <section className="cartao custo" aria-label="Próximos gastos">
      <div className="custo__topo">
        <span className="texto-suave">Próximos gastos</span>
        <Link to="/financas" className="link">Ver todos</Link>
      </div>
      {futuros.quantidade === 0 ? (
        <>
          <p className="texto-suave">Nenhum gasto futuro lançado.</p>
          <Link to={`/veiculos/${veiculoId}/gastos/novo?futuro=1`} className="link">
            Lançar gasto futuro
          </Link>
        </>
      ) : (
        <>
          <p className="custo__valor">{formatarDinheiro(futuros.total)}</p>
          <p className="texto-suave">
            {futuros.quantidade === 1 ? "1 gasto previsto" : `${futuros.quantidade} gastos previstos`}
          </p>
          <ul className="lista-simples proximos-gastos">
            {futuros.proximos.map((g) => (
              <li key={g.id}>
                <Link to={`/veiculos/${veiculoId}/gastos/${g.id}`} className="lista-simples__item">
                  <span className="lista-simples__texto">
                    <span className="lista-simples__titulo">{g.descricao ?? rotuloCategoria(g.categoria)}</span>
                    <span className="texto-suave">
                      {formatarDataIso(g.data_vencimento)} · {emQuantosDias(g.dias)}
                    </span>
                  </span>
                  <strong>{formatarDinheiro(g.valor)}</strong>
                </Link>
              </li>
            ))}
          </ul>
        </>
      )}
    </section>
  );
}

/** Consumo médio e custo por km. Sem base, mostra "Dados insuficientes" e o motivo (nunca zero). */
function Indicadores({ veiculoId, painel }: { veiculoId: number; painel: PainelInicio }) {
  const { consumo, custo_por_km: km } = painel;
  const medida = consumo.combustivel ? unidade(consumo.combustivel).consumo : "km/L";
  return (
    <div className="indicadores">
      <Link to="/financas?aba=combustivel" className="cartao indicador" aria-label="Consumo médio">
        <span className="texto-suave">Consumo médio</span>
        {consumo.disponivel && consumo.valor !== null ? (
          <>
            <span className="indicador__valor">
              {consumo.estimado && "≈ "}{formatarDecimal(consumo.valor, 1)} <small>{medida}</small>
            </span>
            <span className="texto-suave">
              {ROTULO_COMBUSTIVEL[consumo.combustivel as Combustivel] ?? consumo.combustivel}
            </span>
            {consumo.estimado && consumo.minimo && consumo.maximo && (
              <span className="indicador__periodo">
                Pelo marcador: entre {formatarDecimal(consumo.minimo, 1)} e {formatarDecimal(consumo.maximo, 1)}
              </span>
            )}
            {consumo.inicio && consumo.fim && (
              <span className="indicador__periodo">
                {formatarDataIso(consumo.inicio)} a {formatarDataIso(consumo.fim)}
              </span>
            )}
          </>
        ) : (
          <>
            <span className="indicador__indisponivel">Dados insuficientes</span>
            <span className="indicador__periodo">{consumo.motivo}</span>
          </>
        )}
      </Link>
      <Link to={`/veiculos/${veiculoId}`} className="cartao indicador" aria-label="Custo por km">
        <span className="texto-suave">Custo por km</span>
        {km.disponivel && km.valor !== null ? (
          <>
            <span className="indicador__valor">{formatarDinheiro(km.valor)}</span>
            <span className="texto-suave">{periodoCurtoDoCustoPorKm(km)}</span>
            {km.fim && <span className="indicador__periodo">até {formatarDataIso(km.fim)}</span>}
          </>
        ) : (
          <>
            <span className="indicador__indisponivel">Dados insuficientes</span>
            <span className="indicador__periodo">{km.motivo}</span>
          </>
        )}
      </Link>
    </div>
  );
}

/** Alertas e indicadores do veículo em uso (os números vêm do backend num pedido só). */
function PainelDoVeiculo({ veiculoId, temTanque }: { veiculoId: number; temTanque: boolean }) {
  const [painel, setPainel] = useState<PainelInicio | null>(null);
  const [falhou, setFalhou] = useState(false);

  useEffect(() => {
    let cancelado = false;
    obterPainel(veiculoId)
      .then((dados) => {
        if (!cancelado) setPainel(dados);
      })
      .catch(() => {
        if (!cancelado) setFalhou(true);
      });
    return () => {
      cancelado = true;
    };
  }, [veiculoId]);

  return (
    <>
      <PrecisaDeAtencao veiculoId={veiculoId} contas={painel?.contas ?? null} tanque={painel?.tanque ?? null} />
      {falhou && <p className="texto-suave">Não foi possível carregar os gastos e os indicadores.</p>}
      {painel && (
        <>
          {temTanque && <NivelDoTanqueCartao veiculoId={veiculoId} nivel={painel.nivel_tanque} />}
          <GastosDoMesCartao painel={painel} />
          <GastosFuturosCartao veiculoId={veiculoId} painel={painel} />
          <Indicadores veiculoId={veiculoId} painel={painel} />
        </>
      )}
    </>
  );
}

// Tela inicial (PDF, página 2): veículo em uso, quilometragem, atalhos,
// "Precisa de atenção", gastos do mês, próximos gastos, consumo médio e custo por km.
export default function InicioPage() {
  const { usuario } = useAuth();
  const { carregando, erro, veiculos, emUso, recarregar } = useVeiculos();
  if (!usuario) return null;
  const primeiroNome = usuario.nome.split(" ")[0];

  if (carregando) {
    return <main className="conteudo conteudo--topo"><Carregando /></main>;
  }
  if (erro) {
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Olá, {primeiroNome}</h1>
        <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} />
      </main>
    );
  }

  if (!emUso) {
    const temInativos = veiculos.length > 0;
    return (
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Olá, {primeiroNome}</h1>
        <section className="cartao">
          <p className="cartao__titulo">
            {temInativos ? "Nenhum veículo ativo" : "Você ainda não cadastrou um veículo"}
          </p>
          <p className="texto-suave">
            {temInativos
              ? "Seus veículos estão inativos. Reative um deles ou cadastre outro para continuar."
              : "Cadastre seu carro para acompanhar quilometragem, gastos, abastecimentos, manutenções e fotos."}
          </p>
        </section>
        <Link to="/veiculos/novo" className="botao botao--primario">Cadastrar veículo</Link>
        {temInativos && (
          <Link to="/veiculos" className="botao botao--secundario botao--espaco">Ver meus veículos</Link>
        )}
      </main>
    );
  }

  return (
    <main className="conteudo conteudo--topo">
      <header className="inicio__topo">
        <div>
          <Link to="/veiculos" className="inicio__veiculo" aria-label="Trocar de veículo">
            <h1 className="titulo-pagina titulo-pagina--veiculo">{emUso.modelo} {emUso.ano}</h1>
            <IconeSetaBaixo tamanho={22} />
          </Link>
          <Placa placa={emUso.placa} />
        </div>
        <Link to="/mais" className="inicio__avatar" aria-label="Minha conta">
          <AvatarInicial nome={usuario.nome} />
        </Link>
      </header>

      <section className="cartao-km" aria-label="Quilometragem">
        <p className="cartao-km__rotulo">Quilometragem</p>
        <Hodometro km={emUso.quilometragem} />
        <div className="cartao-km__rodape">
          <p className="cartao-km__data">
            {emUso.data_leitura_km
              ? `Atualizada em ${formatarDataIso(emUso.data_leitura_km)}`
              : "Data da leitura desconhecida"}
          </p>
          <Link to={`/veiculos/${emUso.id}/km`} className="cartao-km__botao">Atualizar km</Link>
        </div>
      </section>

      <Atalhos veiculoId={emUso.id} />

      <PainelDoVeiculo key={emUso.id} veiculoId={emUso.id} temTanque={emUso.tipo_combustivel !== "eletrico"} />

      <Link to={`/veiculos/${emUso.id}`} className="botao botao--secundario">
        Ver dados, fotos e custo total do veículo
      </Link>
    </main>
  );
}
