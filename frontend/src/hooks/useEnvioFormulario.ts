import { useCallback, useRef, useState } from "react";

import { ErroDaApi } from "../services/apiCliente";

// Controle comum dos formulários: estado "enviando", trava contra envio
// duplicado e erros vindos da API (mensagem geral e por campo).
export function useEnvioFormulario() {
  const [enviando, setEnviando] = useState(false);
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({});
  const emAndamento = useRef(false);

  const enviar = useCallback(async (acao: () => Promise<void>): Promise<boolean> => {
    if (emAndamento.current) return false; // segundo toque enquanto o primeiro não terminou
    emAndamento.current = true;
    setEnviando(true);
    setErroGeral(null);
    setErrosCampo({});
    try {
      await acao();
      return true;
    } catch (erro) {
      if (erro instanceof ErroDaApi) {
        setErrosCampo(erro.campos);
        setErroGeral(erro.message);
      } else {
        setErroGeral("Algo deu errado. Tente de novo.");
      }
      return false;
    } finally {
      emAndamento.current = false;
      setEnviando(false);
    }
  }, []);

  return { enviando, erroGeral, errosCampo, setErrosCampo, enviar };
}
