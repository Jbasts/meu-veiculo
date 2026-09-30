import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoSenha from "../components/CampoSenha";
import CampoTexto from "../components/CampoTexto";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import {
  erroConfirmacao,
  erroEmail,
  erroObrigatorio,
  erroSenhaNova,
  SENHA_MINIMO,
  soErros,
} from "../utils/validacao";

function IconeEscudo() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3z" />
    </svg>
  );
}

// Tela "Criar conta" (PDF, página 3).
export default function CadastroPage() {
  const { cadastrar } = useAuth();
  const navegar = useNavigate();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros = soErros({
      nome: erroObrigatorio(nome, "Informe seu nome."),
      email: erroEmail(email),
      senha: erroSenhaNova(senha),
      confirmacao_senha: erroConfirmacao(senha, confirmacao),
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const deuCerto = await enviar(async () => {
      await cadastrar({ nome, email, senha, confirmacao_senha: confirmacao });
    });
    if (deuCerto) navegar("/", { replace: true });
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Criar conta" voltarPara="/entrar" estilo="grande" />
        <p className="subtitulo">Leva um minuto. Depois você cadastra o seu carro.</p>
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        <form onSubmit={aoEnviar} noValidate>
          <CampoTexto rotulo="Nome" autoComplete="name" placeholder="Seu nome" value={nome}
            onChange={(e) => setNome(e.target.value)} erro={errosCampo.nome} />
          <CampoTexto rotulo="E-mail" type="email" inputMode="email" autoComplete="email"
            placeholder="nome@email.com" value={email} onChange={(e) => setEmail(e.target.value)}
            erro={errosCampo.email} />
          <CampoSenha rotulo="Senha" autoComplete="new-password" value={senha}
            onChange={(e) => setSenha(e.target.value)} erro={errosCampo.senha}
            dica={`Pelo menos ${SENHA_MINIMO} caracteres. Uma frase é mais segura e fácil de lembrar.`} />
          <CampoSenha rotulo="Confirmar senha" autoComplete="new-password" value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value)} erro={errosCampo.confirmacao_senha} />
          <div className="caixa-info">
            <IconeEscudo />
            <p>Sua conta começa com perfil padrão: você vê apenas os seus veículos e registros.</p>
          </div>
          <BotaoEnviar enviando={enviando} textoEnviando="Criando conta…">
            Criar conta
          </BotaoEnviar>
        </form>
        <p className="rodape-link">
          Já tem conta?{" "}
          <Link to="/entrar" className="link">
            Entrar
          </Link>
        </p>
      </main>
    </div>
  );
}
