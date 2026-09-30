import { useState, type FormEvent } from "react";

import Alerta from "../components/Alerta";
import AvatarInicial from "../components/AvatarInicial";
import BotaoEnviar from "../components/BotaoEnviar";
import BotaoSair from "../components/BotaoSair";
import CampoSenha from "../components/CampoSenha";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { ErroDaApi } from "../services/apiCliente";
import { alterarSenha } from "../services/authService";
import {
  erroConfirmacao,
  erroObrigatorio,
  erroSenhaNova,
  SENHA_MINIMO,
  soErros,
} from "../utils/validacao";

// "Conta e senha" (item da tela Mais, no PDF).
export default function ContaPage() {
  const { usuario, esquecerUsuario } = useAuth();
  const [senhaAtual, setSenhaAtual] = useState("");
  const [novaSenha, setNovaSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [sucesso, setSucesso] = useState<string | null>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  if (!usuario) return null;

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setSucesso(null);
    const erros = soErros({
      senha_atual: erroObrigatorio(senhaAtual, "Informe a senha atual."),
      nova_senha: erroSenhaNova(novaSenha),
      confirmacao_senha: erroConfirmacao(novaSenha, confirmacao),
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    await enviar(async () => {
      try {
        const resposta = await alterarSenha({
          senha_atual: senhaAtual,
          nova_senha: novaSenha,
          confirmacao_senha: confirmacao,
        });
        setSucesso(resposta.mensagem);
        setSenhaAtual("");
        setNovaSenha("");
        setConfirmacao("");
      } catch (erro) {
        // Sessão encerrada (conta desativada ou senha trocada em outro aparelho).
        if (erro instanceof ErroDaApi && erro.status === 401) esquecerUsuario();
        throw erro;
      }
    });
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Conta e senha" voltarPara="/mais" />

        <section className="cartao cartao--perfil">
          <AvatarInicial nome={usuario.nome} />
          <div>
            <p className="cartao__titulo">{usuario.nome}</p>
            <p className="texto-suave">{usuario.email}</p>
            <span className="selo selo--ok">{usuario.perfil === "admin" ? "Admin" : "Padrão"}</span>
          </div>
        </section>

        <h2 className="titulo-secao">Trocar senha</h2>
        {sucesso && <Alerta tipo="sucesso">{sucesso}</Alerta>}
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        <form onSubmit={aoEnviar} noValidate>
          <CampoSenha rotulo="Senha atual" autoComplete="current-password" value={senhaAtual}
            onChange={(e) => setSenhaAtual(e.target.value)} erro={errosCampo.senha_atual} />
          <CampoSenha rotulo="Nova senha" autoComplete="new-password" value={novaSenha}
            onChange={(e) => setNovaSenha(e.target.value)} erro={errosCampo.nova_senha}
            dica={`Pelo menos ${SENHA_MINIMO} caracteres. Os outros aparelhos conectados vão sair.`} />
          <CampoSenha rotulo="Confirmar nova senha" autoComplete="new-password" value={confirmacao}
            onChange={(e) => setConfirmacao(e.target.value)} erro={errosCampo.confirmacao_senha} />
          <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
            Salvar nova senha
          </BotaoEnviar>
        </form>

        <nav className="menu menu--espaco" aria-label="Sair da conta">
          <BotaoSair />
        </nav>
      </main>
    </div>
  );
}
