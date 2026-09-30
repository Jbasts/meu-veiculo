import { useEffect, useState } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeSeta, IconeSetaBaixo } from "../components/Icones";
import { destinoDaPendencia, IconeDaSituacao, TOM_DA_SITUACAO } from "../components/PecasManutencao";
import { Hodometro, Placa } from "../components/PecasVeiculo";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { listarPendentes } from "../services/manutencaoService";
import { resumoDoPrazo, type Pendencia } from "../types/manutencao";
import { formatarDataIso } from "../utils/datas";

/** "Precisa de atenção": manutenções atrasadas e próximas do veículo em uso. */
function AlertasDeManutencao({ veiculoId }: { veiculoId: number }) {
  const [itens, setItens] = useState<Pendencia[] | null>(null);
  const [falhou, setFalhou] = useState(false);

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
    return () => {
      cancelado = true;
    };
  }, [veiculoId]);

  if (falhou) {
    return <p className="texto-suave">Não foi possível carregar os alertas de manutenção.</p>;
  }
  if (itens === null || itens.length === 0) return null;
  return (
    <section aria-label="Precisa de atenção">
      <h2 className="titulo-secao">Precisa de atenção</h2>
      <ul className="cartao lista-simples">
        {itens.slice(0, 5).map((item) => {
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
      {itens.length > 5 && (
        <p className="link-direita">
          <Link to="/manutencao" className="link">Ver todas ({itens.length})</Link>
        </p>
      )}
    </section>
  );
}

// Tela inicial (PDF, página 2). Nesta etapa mostra o veículo em uso e a
// quilometragem e os alertas de manutenção. Os atalhos, os diagnósticos e os
// indicadores de gastos e consumo entram com os módulos correspondentes.
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

      <AlertasDeManutencao key={emUso.id} veiculoId={emUso.id} />

      <section className="cartao">
        <p className="cartao__titulo">Em construção</p>
        <p className="texto-suave">
          Os atalhos, os diagnósticos pendentes e os indicadores de gastos e consumo aparecem aqui
          quando esses módulos ficarem prontos. Nada é mostrado com valores de exemplo.
        </p>
      </section>

      <Link to={`/veiculos/${emUso.id}`} className="botao botao--secundario">
        Ver dados e fotos do veículo
      </Link>
    </main>
  );
}
