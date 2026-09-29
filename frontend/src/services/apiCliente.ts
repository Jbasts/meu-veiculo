// Cliente único para falar com o backend.
//
// Todas as chamadas vão para "/api/...", no mesmo endereço do frontend.
// Em desenvolvimento, o Vite repassa para o backend (veja vite.config.ts).
// Nenhuma senha ou chave fica no frontend: quem fala com o banco é só o backend.

export type RespostaApi =
  | { tipo: "resposta"; status: number; corpo: unknown }
  | { tipo: "sem_conexao" };

export async function requisitarApi(caminho: string, opcoes: RequestInit = {}): Promise<RespostaApi> {
  if (!caminho.startsWith("/")) {
    throw new Error(`O caminho da API deve começar com "/": ${caminho}`);
  }
  const cabecalhos = new Headers(opcoes.headers);
  if (!cabecalhos.has("Accept")) {
    cabecalhos.set("Accept", "application/json");
  }

  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, { ...opcoes, headers: cabecalhos });
  } catch {
    return { tipo: "sem_conexao" };
  }
  // Se o backend estiver desligado, o proxy devolve uma página de erro, não JSON.
  const corpo: unknown = await resposta.json().catch(() => null);
  return { tipo: "resposta", status: resposta.status, corpo };
}
