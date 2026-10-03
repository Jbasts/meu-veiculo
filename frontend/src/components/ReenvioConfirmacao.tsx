import { useState } from "react";

import Alerta from "./Alerta";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { reenviarConfirmacao } from "../services/authService";

// Botão "Reenviar link de confirmação" (depois de criar a conta e no Entrar,
// quando a conta ainda não confirmou o e-mail). Cada envio troca o link: só o
// último e-mail vale.
export default function ReenvioConfirmacao({ email }: { email: string }) {
  const [enviado, setEnviado] = useState<string | null>(null);
  const { enviando, erroGeral, enviar } = useEnvioFormulario();

  async function aoClicar() {
    setEnviado(null);
    await enviar(async () => {
      const resposta = await reenviarConfirmacao(email);
      setEnviado(resposta.mensagem);
    });
  }

  return (
    <div className="reenvio-confirmacao">
      {enviado && <Alerta tipo="sucesso">{enviado}</Alerta>}
      {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
      <button type="button" className="botao botao--secundario" onClick={aoClicar}
        disabled={enviando}>
        {enviando ? "Enviando…" : "Reenviar link de confirmação"}
      </button>
    </div>
  );
}
