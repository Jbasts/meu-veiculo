// Cliente único para falar com o backend.
//
// Todas as chamadas vão para "/api/...", no mesmo endereço do frontend.
// Em desenvolvimento, o Vite repassa para o backend (veja vite.config.ts).
// Nenhuma senha ou chave fica no frontend: quem fala com o banco é só o backend.
// A sessão viaja num cookie HttpOnly que o JavaScript não lê; o navegador
// o envia sozinho.

// Cabeçalho exigido pelo backend em toda gravação (proteção contra
// requisições forjadas por outros sites).
const CABECALHO_DO_APP = "X-MV-Requisicao";

export type RespostaApi =
  | { tipo: "resposta"; status: number; corpo: unknown }
  | { tipo: "sem_conexao" };

/** Erro devolvido pela API, com a mensagem geral e as mensagens por campo. */
export class ErroDaApi extends Error {
  readonly status: number;
  readonly campos: Record<string, string>;

  constructor(status: number, mensagem: string, campos: Record<string, string> = {}) {
    super(mensagem);
    this.name = "ErroDaApi";
    this.status = status;
    this.campos = campos;
  }
}

export const MENSAGEM_SEM_CONEXAO =
  "Não foi possível falar com o servidor. Confira sua conexão e tente de novo.";

export async function requisitarApi(caminho: string, opcoes: RequestInit = {}): Promise<RespostaApi> {
  if (!caminho.startsWith("/")) {
    throw new Error(`O caminho da API deve começar com "/": ${caminho}`);
  }
  const cabecalhos = new Headers(opcoes.headers);
  if (!cabecalhos.has("Accept")) {
    cabecalhos.set("Accept", "application/json");
  }
  cabecalhos.set(CABECALHO_DO_APP, "1");

  let resposta: Response;
  try {
    resposta = await fetch(`/api${caminho}`, {
      ...opcoes,
      headers: cabecalhos,
      credentials: "same-origin",
    });
  } catch {
    return { tipo: "sem_conexao" };
  }
  if (resposta.status === 204) {
    return { tipo: "resposta", status: 204, corpo: null };
  }
  // Se o backend estiver desligado, o proxy devolve uma página de erro, não JSON.
  const corpo: unknown = await resposta.json().catch(() => null);
  return { tipo: "resposta", status: resposta.status, corpo };
}

function mensagemDoCorpo(corpo: unknown): { mensagem?: string; campos?: Record<string, string> } {
  if (typeof corpo !== "object" || corpo === null) return {};
  const { mensagem, campos } = corpo as { mensagem?: unknown; campos?: unknown };
  return {
    mensagem: typeof mensagem === "string" ? mensagem : undefined,
    campos:
      typeof campos === "object" && campos !== null ? (campos as Record<string, string>) : undefined,
  };
}

// Quando a API responde 401 no meio do uso (sessão expirada, conta desativada,
// senha trocada em outro aparelho), o app precisa voltar para a tela Entrar.
// O AuthContext registra aqui o que fazer nesse caso.
let aoPerderSessao: (() => void) | null = null;

export function definirAoPerderSessao(acao: (() => void) | null): void {
  aoPerderSessao = acao;
}

/**
 * Chama a API e devolve o corpo em caso de sucesso; lança ErroDaApi nos demais casos.
 * "dados" pode ser um objeto (enviado como JSON) ou um FormData (envio de arquivo).
 */
export async function chamarApi<T>(metodo: string, caminho: string, dados?: unknown): Promise<T> {
  const opcoes: RequestInit = { method: metodo };
  if (dados instanceof FormData) {
    // Sem Content-Type: o navegador define o tipo e o separador do formulário.
    opcoes.body = dados;
  } else if (dados !== undefined) {
    opcoes.body = JSON.stringify(dados);
    opcoes.headers = { "Content-Type": "application/json" };
  }
  const resposta = await requisitarApi(caminho, opcoes);
  if (resposta.tipo === "sem_conexao") {
    throw new ErroDaApi(0, MENSAGEM_SEM_CONEXAO);
  }
  if (resposta.status >= 200 && resposta.status < 300) {
    return resposta.corpo as T;
  }
  // Nas rotas de conta (/auth/...), 401 é resposta normal (senha errada, ninguém logado).
  if (resposta.status === 401 && !caminho.startsWith("/auth/")) {
    aoPerderSessao?.();
  }
  const { mensagem, campos } = mensagemDoCorpo(resposta.corpo);
  throw new ErroDaApi(
    resposta.status,
    mensagem ?? `O servidor não conseguiu atender o pedido (código ${resposta.status}).`,
    campos ?? {},
  );
}
