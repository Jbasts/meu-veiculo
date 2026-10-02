import { useEffect, useState, type ReactNode } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import BotaoSair from "../components/BotaoSair";
import {
  IconeCadeado,
  IconeCarro,
  IconeEscudo,
  IconeFerramentas,
  IconeHistorico,
  IconeProjeto,
  IconeSeta,
} from "../components/Icones";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { obterResumoAdmin } from "../services/adminService";
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

/** "3 usuários, 4 veículos" (só para admin; o backend recusa os demais). */
function useResumoDaAdministracao(ehAdmin: boolean): string {
  const [texto, setTexto] = useState("Usuários e veículos");
  useEffect(() => {
    if (!ehAdmin) return;
    let cancelado = false;
    obterResumoAdmin().then((r) => {
      if (cancelado) return;
      setTexto(`${r.usuarios === 1 ? "1 usuário" : `${r.usuarios} usuários`}, `
        + `${r.veiculos === 1 ? "1 veículo" : `${r.veiculos} veículos`}`);
    }).catch(() => undefined);
    return () => {
      cancelado = true;
    };
  }, [ehAdmin]);
  return texto;
}

// Tela "Mais" (PDF, página 14).
export default function MaisPage() {
  const { usuario } = useAuth();
  const { veiculos, emUso } = useVeiculos();
  const ehAdmin = usuario?.perfil === "admin";
  const resumoProjetos = useResumoDosProjetos(emUso?.id);
  const resumoAdmin = useResumoDaAdministracao(ehAdmin);
  if (!usuario) return null;
  const ativos = veiculos.filter((v) => v.ativo).length;

  return (
    <main className="conteudo conteudo--topo">
      <h1 className="titulo-pagina">Mais</h1>

      <section className="cartao cartao--perfil">
        <AvatarInicial nome={usuario.nome} />
        <div>
          <p className="cartao__titulo">{usuario.nome}</p>
          <span className="selo selo--ok">{ehAdmin ? "Admin" : "Padrão"}</span>{" "}
          <span className="texto-suave">
            {ativos === 1 ? "1 veículo" : `${ativos} veículos`}
          </span>
        </div>
      </section>

      <nav className="menu" aria-label="Veículos">
        {emUso && (
          <ItemComIcone para={`/veiculos/${emUso.id}`} icone={<IconeCarro />} titulo="Meu veículo"
            descricao="Dados, fotos e custo total" />
        )}
        {emUso && (
          <ItemComIcone para={`/veiculos/${emUso.id}/projetos`} icone={<IconeProjeto />} titulo="Projetos"
            descricao={resumoProjetos} />
        )}
        {emUso && (
          <ItemComIcone para="/historico" icone={<IconeHistorico />} titulo="Histórico"
            descricao="Tudo o que foi registrado" />
        )}
        <ItemComIcone para="/veiculos" icone={<IconeCarro />} titulo="Meus veículos"
          descricao="Trocar o veículo em uso, cadastrar ou inativar" />
      </nav>

      {ehAdmin && (
        <>
          <nav className="menu menu--espaco" aria-label="Administração">
            <ItemComIcone para="/admin" icone={<IconeEscudo />} titulo="Administração"
              descricao={resumoAdmin} />
          </nav>
          <p className="texto-suave menu__nota">Só aparece para quem tem perfil admin.</p>
        </>
      )}

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
