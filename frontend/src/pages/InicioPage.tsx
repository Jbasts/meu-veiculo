import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeSetaBaixo } from "../components/Icones";
import { Hodometro, Placa } from "../components/PecasVeiculo";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { formatarDataIso } from "../utils/datas";

// Tela inicial (PDF, página 2). Nesta etapa mostra o veículo em uso e a
// quilometragem. Os atalhos, os alertas de manutenção e os indicadores de
// gastos e consumo entram com os módulos correspondentes (etapas 4 a 9).
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

      <section className="cartao">
        <p className="cartao__titulo">Em construção</p>
        <p className="texto-suave">
          Os atalhos, os alertas de manutenção e os indicadores de gastos e consumo aparecem aqui
          quando esses módulos ficarem prontos. Nada é mostrado com valores de exemplo.
        </p>
      </section>

      <Link to={`/veiculos/${emUso.id}`} className="botao botao--secundario">
        Ver dados e fotos do veículo
      </Link>
    </main>
  );
}
