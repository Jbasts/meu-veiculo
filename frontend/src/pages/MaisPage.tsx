import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import BotaoSair from "../components/BotaoSair";
import { IconeCadeado, IconeCarro, IconeFerramentas, IconeProjeto, IconeSeta } from "../components/Icones";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { listarProjetos } from "../services/projetoService";

function ItemComIcone({ para, icone, titulo, descricao }: {
  para: string; icone: ReactNode; titulo: string; descricao: string;
}) {
  return (
    <Link to={para} className="menu__item">
      <span className="menu__icone">{icone}</span>
      <span className="menu__texto">
        <span className="menu__titulo">{titulo}</span>
        <span className="menu__descricao">{descricao}</span>
      </span>
      <IconeSeta tamanho={22} />
    </Link>
  );
}

/** "1 em andamento", "Nenhum projeto"... (contagem do veículo em uso, vinda do backend). */
function useResumoDosProjetos(veiculoId: number | undefined): string {
  const [texto, setTexto] = useState("Melhorias, gastos e fotos de antes e depois");
  useEffect(() => {
    if (!veiculoId) return;
    let cancelado = false;
    listarProjetos(veiculoId, "todos", 1, 1).then((r) => {
      if (cancelado) return;
      const andamento = r.por_status.em_andamento;
      const planejados = r.por_status.planejado;
      if (r.total === 0) setTexto("Nenhum projeto ainda");
      else if (andamento > 0) setTexto(`${andamento} em andamento`);
      else if (planejados > 0) setTexto(planejados === 1 ? "1 planejado" : `${planejados} planejados`);
      else setTexto(r.total === 1 ? "1 projeto" : `${r.total} projetos`);
    }).catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [veiculoId]);
  return texto;
}

// Tela "Mais" (PDF, página 14). Histórico e Administração entram na etapa 9.
export default function MaisPage() {
  const { usuario } = useAuth();
  const { veiculos, emUso } = useVeiculos();
  if (!usuario) return null;
  const ativos = veiculos.filter((v) => v.ativo).length;
  const resumoProjetos = useResumoDosProjetos(emUso?.id);

  return (
    <main className="conteudo conteudo--topo">
      <h1 className="titulo-pagina">Mais</h1>

      <section className="cartao cartao--perfil">
        <AvatarInicial nome={usuario.nome} />
        <div>
          <p className="cartao__titulo">{usuario.nome}</p>
          <span className="selo selo--ok">{usuario.perfil === "admin" ? "Admin" : "Padrão"}</span>{" "}
          <span className="texto-suave">
            {ativos === 1 ? "1 veículo" : `${ativos} veículos`}
          </span>
        </div>
      </section>

      <nav className="menu" aria-label="Veículos">
        {emUso && (
          <ItemComIcone para={`/veiculos/${emUso.id}`} icone={<IconeCarro />} titulo="Meu veículo"
            descricao="Dados, fotos e quilometragem" />
        )}
        {emUso && (
          <ItemComIcone para={`/veiculos/${emUso.id}/projetos`} icone={<IconeProjeto />} titulo="Projetos"
            descricao={resumoProjetos} />
        )}
        <ItemComIcone para="/veiculos" icone={<IconeCarro />} titulo="Meus veículos"
          descricao="Trocar o veículo em uso, cadastrar ou inativar" />
      </nav>

      <nav className="menu menu--espaco" aria-label="Conta">
        <ItemComIcone para="/conta" icone={<IconeCadeado />} titulo="Conta e senha"
          descricao={usuario.email} />
        <ItemComIcone para="/situacao" icone={<IconeFerramentas />} titulo="Situação do sistema"
          descricao="API, banco de dados e migrations" />
        <BotaoSair />
      </nav>
    </main>
  );
}
