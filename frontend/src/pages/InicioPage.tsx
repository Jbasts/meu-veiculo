import { useEffect, useState } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeDiagnostico, IconeSeta, IconeSetaBaixo } from "../components/Icones";
import { TOM_DA_GRAVIDADE } from "../components/PecasDiagnostico";
import { destinoDaPendencia, IconeDaSituacao, TOM_DA_SITUACAO } from "../components/PecasManutencao";
import { Hodometro, Placa } from "../components/PecasVeiculo";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { listarDiagnosticos } from "../services/diagnosticoService";
import { listarPendentes } from "../services/manutencaoService";
import { rotuloGravidade, type DiagnosticoResumo } from "../types/diagnostico";
import { resumoDoPrazo, type Pendencia } from "../types/manutencao";
import { formatarDataIso } from "../utils/datas";

const MAXIMO_DE_ALERTAS = 5;

/** "Diagnóstico aberto, gravidade média" */
function textoDoDiagnostico(d: DiagnosticoResumo): string {
  return `Diagnóstico ${d.status === "em_observacao" ? "em observação" : "aberto"}, `
    + `gravidade ${rotuloGravidade(d.gravidade).toLowerCase()}`;
}

/**
 * "Precisa de atenção": manutenções atrasadas e próximas e problemas em
 * aberto do veículo em uso. Cada fonte falha sozinha, sem esconder a outra.
 */
function PrecisaDeAtencao({ veiculoId }: { veiculoId: number }) {
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
  return (
    <>
      {falhou && <p className="texto-suave">Não foi possível carregar os alertas de manutenção.</p>}
      {falhouProblemas && <p className="texto-suave">Não foi possível carregar os diagnósticos em aberto.</p>}
      {(temManutencao || temProblema) && (
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

// Tela inicial (PDF, página 2). Mostra o veículo em uso, a quilometragem, os
// alertas de manutenção e os problemas em aberto. Os atalhos e os indicadores
// de gastos e consumo entram com os módulos correspondentes.
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
              : "Cadastre seu carro para acompanhar a quilometragem, as fotos e, nas próximas etapas, manutenções e gastos."}
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

      <PrecisaDeAtencao key={emUso.id} veiculoId={emUso.id} />

      <section className="cartao">
        <p className="cartao__titulo">Em construção</p>
        <p className="texto-suave">
          Os atalhos e os indicadores de gastos e consumo aparecem aqui quando esses módulos
          ficarem prontos. Nada é mostrado com valores de exemplo.
        </p>
      </section>

      <Link to={`/veiculos/${emUso.id}`} className="botao botao--secundario">
        Ver dados e fotos do veículo
      </Link>
    </main>
  );
}
