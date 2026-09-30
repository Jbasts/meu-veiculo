import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CabecalhoMarca from "../components/CabecalhoMarca";
import CampoSenha from "../components/CampoSenha";
import CampoTexto from "../components/CampoTexto";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { erroEmail, erroObrigatorio, soErros } from "../utils/validacao";

// Tela "Entrar" (PDF, página 1).
export default function LoginPage() {
  const { entrar, erroInicial } = useAuth();
  const navegar = useNavigate();
  const local = useLocation();
  const destino = (local.state as { destino?: string } | null)?.destino ?? "/";
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros = soErros({
      email: erroEmail(email),
      senha: erroObrigatorio(senha, "Informe a senha."),
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const deuCerto = await enviar(async () => {
      await entrar(email, senha);
    });
    if (deuCerto) navegar(destino, { replace: true });
  }

  return (
    <div className="pagina">
      <CabecalhoMarca />
      <main className="conteudo">
        <h2 className="titulo-pagina">Entrar</h2>
        {erroInicial && <Alerta tipo="erro">{erroInicial}</Alerta>}
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        <form onSubmit={aoEnviar} noValidate>
          <CampoTexto
            rotulo="E-mail"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="nome@email.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            erro={errosCampo.email}
          />
          <CampoSenha
            rotulo="Senha"
            autoComplete="current-password"
            value={senha}
            onChange={(e) => setSenha(e.target.value)}
            erro={errosCampo.senha}
          />
          <p className="link-direita">
            <Link to="/esqueci-senha" className="link">
              Esqueci minha senha
            </Link>
          </p>
          <BotaoEnviar enviando={enviando} textoEnviando="Entrando…">
            Entrar
          </BotaoEnviar>
        </form>
        <p className="rodape-link">
          Ainda não tem conta?{" "}
          <Link to="/criar-conta" className="link">
            Criar conta
          </Link>
        </p>
      </main>
    </div>
  );
}
