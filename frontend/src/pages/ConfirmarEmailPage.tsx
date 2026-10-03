import { useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import Alerta from "../components/Alerta";
import TopoComVoltar from "../components/TopoComVoltar";
import { confirmarEmail } from "../services/authService";
import { ErroDaApi, MENSAGEM_SEM_CONEXAO } from "../services/apiCliente";

// O link do e-mail é ".../confirmar-email#token=...". A parte depois do "#"
// não vai para nenhum servidor. Como na tela de senha nova, o token sai do
// endereço assim que a tela abre e fica só na memória.
function lerTokenDoEndereco(): string | null {
  return new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token");
}

type Situacao =
  | { tipo: "confirmando" }
  | { tipo: "confirmado"; mensagem: string }
  | { tipo: "erro"; mensagem: string };

export default function ConfirmarEmailPage() {
  const [token] = useState(lerTokenDoEndereco);
  const [situacao, setSituacao] = useState<Situacao>({ tipo: "confirmando" });
  // O link só vale uma vez: garante um único envio mesmo se a tela montar duas vezes.
  const jaEnviou = useRef(false);

  useEffect(() => {
    if (window.location.hash) {
      window.history.replaceState(window.history.state, "", window.location.pathname);
    }
    if (!token || jaEnviou.current) return;
    jaEnviou.current = true;
    confirmarEmail(token)
      .then((resposta) => setSituacao({ tipo: "confirmado", mensagem: resposta.mensagem }))
      .catch((erro: unknown) =>
        setSituacao({
          tipo: "erro",
          mensagem: erro instanceof ErroDaApi ? erro.message : MENSAGEM_SEM_CONEXAO,
        }),
      );
  }, [token]);

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Confirmar e-mail" voltarPara="/entrar" estilo="grande" />
        {!token ? (
          <>
            <Alerta tipo="erro">
              Este link está incompleto. Abra o link do e-mail de novo ou peça outro na tela Entrar.
            </Alerta>
            <Link to="/entrar" className="botao botao--secundario">
              Ir para Entrar
            </Link>
          </>
        ) : situacao.tipo === "confirmando" ? (
          <p className="subtitulo" role="status">Confirmando seu e-mail…</p>
        ) : situacao.tipo === "confirmado" ? (
          <>
            <Alerta tipo="sucesso">{situacao.mensagem}</Alerta>
            <Link to="/entrar" className="botao botao--primario">
              Entrar
            </Link>
          </>
        ) : (
          <>
            <Alerta tipo="erro">{situacao.mensagem}</Alerta>
            <Link to="/entrar" className="botao botao--secundario">
              Ir para Entrar
            </Link>
          </>
        )}
      </main>
    </div>
  );
}
