import type { ResultadoSaude, Saude } from "../types/saude";
import { requisitarApi } from "./apiCliente";

function pareceSaude(valor: unknown): valor is Saude {
  return (
    typeof valor === "object" &&
    valor !== null &&
    (valor as Saude).api === "ok" &&
    typeof (valor as Saude).mensagem === "string"
  );
}

export async function consultarSaude(): Promise<ResultadoSaude> {
  const resposta = await requisitarApi("/saude");
  if (resposta.tipo === "sem_conexao") {
    return { tipo: "api_fora", detalhe: "Sem conexão com o servidor." };
  }
  // 200 = tudo respondeu; 503 = a API respondeu, mas o banco não.
  if ((resposta.status === 200 || resposta.status === 503) && pareceSaude(resposta.corpo)) {
    return { tipo: "resposta", saude: resposta.corpo };
  }
  return {
    tipo: "api_fora",
    detalhe: `O backend não respondeu como esperado (código ${resposta.status}).`,
  };
}
