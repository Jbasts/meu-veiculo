import type { ReactNode } from "react";
import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import BotaoSair from "../components/BotaoSair";
import { IconeCadeado, IconeCarro, IconeFerramentas, IconeSeta } from "../components/Icones";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";

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

// Tela "Mais" (PDF, página 14). Projetos, Histórico e Administração entram
// nas etapas 8 e 9; por isso ainda não aparecem aqui.
export default function MaisPage() {
  const { usuario } = useAuth();
  const { veiculos, emUso } = useVeiculos();
  if (!usuario) return null;
  const ativos = veiculos.filter((v) => v.ativo).length;

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
