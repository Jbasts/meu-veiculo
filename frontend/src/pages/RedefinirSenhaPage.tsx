import { useEffect, useState, type FormEvent } from "react";
import { Link } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoSenha from "../components/CampoSenha";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { redefinirSenha } from "../services/authService";
import { erroConfirmacao, erroSenhaNova, SENHA_MINIMO, soErros } from "../utils/validacao";

// O link do e-mail é ".../redefinir-senha#token=...". A parte depois do "#"
// não vai para nenhum servidor. Assim que a tela abre, o token sai do
// endereço (para não ficar no histórico do navegador) e fica só na memória.
function lerTokenDoEndereco(): string | null {
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token");
}

export default function RedefinirSenhaPage() {
  const { esquecerUsuario } = useAuth();
  const [token] = useState(lerTokenDoEndereco);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
  }, []);
  const [senha, setSenha] = useState("");
  const [confirmacao, setConfirmacao] = useState("");
  const [concluido, setConcluido] = useState<string | null>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    if (!token) return;
    const erros = soErros({
      nova_senha: erroSenhaNova(senha),
      confirmacao_senha: erroConfirmacao(senha, confirmacao),
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    await enviar(async () => {
      const resposta = await redefinirSenha({ token, nova_senha: senha, confirmacao_senha: confirmacao });
      // Todas as sessões foram encerradas no servidor, inclusive a deste aparelho.
      esquecerUsuario();
      setConcluido(resposta.mensagem);
    });
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Criar senha nova" voltarPara="/entrar" estilo="grande" />
        {!token ? (
          <>
            <Alerta tipo="erro">
              Este link está incompleto. Abra o link do e-mail de novo ou peça outro.
            </Alerta>
            <Link to="/esqueci-senha" className="botao botao--secundario">
              Pedir um link novo
            </Link>
          </>
        ) : concluido ? (
          <>
            <Alerta tipo="sucesso">{concluido}</Alerta>
            <Link to="/entrar" className="botao botao--primario">
              Entrar
            </Link>
          </>
        ) : (
          <>
            {erroGeral && (
              <Alerta tipo="erro">
                {erroGeral}
                {errosCampo.token && (
                  <>
                    {" "}
                    <Link to="/esqueci-senha" className="link">
                      Pedir um link novo
                    </Link>
                  </>
                )}
              </Alerta>
            )}
            <form onSubmit={aoEnviar} noValidate>
              <CampoSenha rotulo="Nova senha" autoComplete="new-password" value={senha}
                onChange={(e) => setSenha(e.target.value)} erro={errosCampo.nova_senha}
                dica={`Pelo menos ${SENHA_MINIMO} caracteres.`} />
              <CampoSenha rotulo="Confirmar nova senha" autoComplete="new-password" value={confirmacao}
                onChange={(e) => setConfirmacao(e.target.value)} erro={errosCampo.confirmacao_senha} />
              <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
                Salvar senha nova
              </BotaoEnviar>
            </form>
          </>
        )}
      </main>
    </div>
  );
}
