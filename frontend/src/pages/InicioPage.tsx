import { Link } from "react-router";

import AvatarInicial from "../components/AvatarInicial";
import BotaoSair from "../components/BotaoSair";
import { useAuth } from "../contexts/AuthContext";

function Seta() {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 5l7 7-7 7" />
    </svg>
  );
}

// Início provisório da etapa 2: mostra a conta logada. A tela inicial do PDF
// (veículo, quilometragem, alertas e gastos) é montada nas próximas etapas.
export default function InicioPage() {
  const { usuario } = useAuth();
  if (!usuario) return null;
  const primeiroNome = usuario.nome.split(" ")[0];

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <h1 className="titulo-pagina">Olá, {primeiroNome}</h1>

        <section className="cartao cartao--perfil">
          <AvatarInicial nome={usuario.nome} />
          <div>
            <p className="cartao__titulo">{usuario.nome}</p>
            <span className="selo selo--ok">{usuario.perfil === "admin" ? "Admin" : "Padrão"}</span>
          </div>
        </section>

        <section className="cartao">
          <p className="cartao__titulo">Seus veículos</p>
          <p className="texto-suave">
            O cadastro de veículos chega na próxima etapa do projeto. Por enquanto, você já pode
            gerenciar sua conta e sua senha.
          </p>
        </section>

        <nav className="menu" aria-label="Opções da conta">
          <Link to="/conta" className="menu__item">
            <span>Conta e senha</span>
            <Seta />
          </Link>
          <Link to="/situacao" className="menu__item">
            <span>Situação do sistema</span>
            <Seta />
          </Link>
          <BotaoSair />
        </nav>
      </main>
    </div>
  );
}
