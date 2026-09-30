import { useState, type FormEvent } from "react";
import { Link } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import TopoComVoltar from "../components/TopoComVoltar";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { solicitarRecuperacao } from "../services/authService";
import { erroEmail, soErros } from "../utils/validacao";

// "Esqueci minha senha": a resposta é sempre a mesma, exista ou não a conta.
export default function EsqueciSenhaPage() {
  const [email, setEmail] = useState("");
  const [confirmacao, setConfirmacao] = useState<string | null>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros = soErros({ email: erroEmail(email) });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    await enviar(async () => {
      const resposta = await solicitarRecuperacao(email);
      setConfirmacao(resposta.mensagem);
    });
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Esqueci minha senha" voltarPara="/entrar" estilo="grande" />
        {confirmacao ? (
          <>
            <Alerta tipo="sucesso">{confirmacao}</Alerta>
            <p className="texto-suave">O link vale por pouco tempo e só pode ser usado uma vez.</p>
            <Link to="/entrar" className="botao botao--secundario">
              Voltar para Entrar
            </Link>
          </>
        ) : (
          <>
            <p className="subtitulo">
              Informe o e-mail da sua conta. Vamos enviar um link para você criar uma senha nova.
            </p>
            {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
            <form onSubmit={aoEnviar} noValidate>
              <CampoTexto rotulo="E-mail" type="email" inputMode="email" autoComplete="email"
                placeholder="nome@email.com" value={email} onChange={(e) => setEmail(e.target.value)}
                erro={errosCampo.email} />
              <BotaoEnviar enviando={enviando}>Enviar link</BotaoEnviar>
            </form>
          </>
        )}
      </main>
    </div>
  );
}
