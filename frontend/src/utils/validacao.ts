// Validações feitas na tela, antes de enviar. O backend confere tudo de novo
// (ele é a fonte da verdade); aqui é só para avisar mais rápido.

export const SENHA_MINIMO = 8;
export const SENHA_MAXIMO = 128;

const FORMATO_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function erroEmail(email: string): string | null {
  const limpo = email.trim();
  if (!limpo) return "Informe o e-mail.";
  if (!FORMATO_EMAIL.test(limpo)) return "E-mail inválido. Confira se está no formato nome@email.com.";
  return null;
}

export function erroSenhaNova(senha: string): string | null {
  if (senha.length < SENHA_MINIMO) return `A senha precisa ter pelo menos ${SENHA_MINIMO} caracteres.`;
  if (senha.length > SENHA_MAXIMO) return `A senha pode ter no máximo ${SENHA_MAXIMO} caracteres.`;
  if (!senha.trim()) return "A senha não pode ser só espaços.";
  return null;
}

export function erroConfirmacao(senha: string, confirmacao: string): string | null {
  if (!confirmacao) return "Confirme a senha.";
  return senha === confirmacao ? null : "A confirmação não é igual à senha.";
}

export function erroObrigatorio(valor: string, mensagem: string): string | null {
  return valor.trim() ? null : mensagem;
}

/** Tira do objeto os campos sem erro. */
export function soErros(erros: Record<string, string | null>): Record<string, string> {
  return Object.fromEntries(
    Object.entries(erros).filter((par): par is [string, string] => par[1] !== null),
  );
}
