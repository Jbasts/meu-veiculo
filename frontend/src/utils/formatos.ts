// Formatação e leitura de quilometragem, placa e dinheiro.
//
// Dinheiro nunca vira número com ponto flutuante aqui: a API manda e recebe
// texto ("65000.00"), e estas funções trabalham só com os dígitos.

/** 85000 -> "85.000" */
export function formatarInteiro(valor: number): string {
  return String(Math.trunc(valor)).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

export function formatarKm(valor: number): string {
  return `${formatarInteiro(valor)} km`;
}

/** Deixa só os dígitos do que foi digitado ("85.000 km" -> "85000"). */
export function soDigitos(texto: string): string {
  return texto.replace(/\D/g, "");
}

/** Dígitos digitados -> texto com pontos de milhar, para mostrar no campo. */
export function mascararInteiro(texto: string): string {
  const digitos = soDigitos(texto).replace(/^0+(?=\d)/, "");
  return digitos.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
}

/** "85.000" -> 85000; vazio -> null. */
export function lerInteiro(texto: string): number | null {
  const digitos = soDigitos(texto);
  return digitos ? Number(digitos) : null;
}

/** "ABC1234" -> "ABC-1234" (placa antiga); a Mercosul ("BRA2E19") fica sem hífen. */
export function formatarPlaca(placa: string): string {
  return /^[A-Z]{3}\d{4}$/.test(placa) ? `${placa.slice(0, 3)}-${placa.slice(3)}` : placa;
}

/** O mesmo que o backend faz: maiúsculas, sem hífen e sem espaços. */
export function normalizarPlaca(texto: string): string {
  return texto.replace(/[\s-]/g, "").toUpperCase();
}

export function placaValida(texto: string): boolean {
  return /^[A-Z]{3}\d[A-Z0-9]\d{2}$/.test(normalizarPlaca(texto));
}

/** "65000.00" (da API) -> "R$ 65.000,00" */
export function formatarDinheiro(valor: string): string {
  const [inteiros, centavos = ""] = valor.split(".");
  return `R$ ${mascararInteiro(inteiros) || "0"},${centavos.padEnd(2, "0").slice(0, 2)}`;
}

/** "65000.00" -> "65.000,00" (para preencher o campo na edição). */
export function dinheiroParaCampo(valor: string | null): string {
  return valor ? formatarDinheiro(valor).replace("R$ ", "") : "";
}

/**
 * O que a pessoa digitou -> texto para a API.
 * "R$ 65.000,00" -> "65000.00"; "65000" -> "65000.00"; "1.234,5" -> "1234.50".
 * Vazio -> null. Texto que não é um valor em reais -> undefined.
 */
export function lerDinheiro(texto: string): string | null | undefined {
  const limpo = texto.replace(/R\$/i, "").replace(/\s/g, "");
  if (!limpo) return null;
  const partes = /^(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,2}))?$/.exec(limpo);
  if (!partes) return undefined;
  const inteiros = partes[1].replace(/\./g, "").replace(/^0+(?=\d)/, "");
  return `${inteiros}.${(partes[2] ?? "").padEnd(2, "0")}`;
}

/**
 * Soma valores no formato da API ("70.00") em centavos inteiros, sem ponto
 * flutuante: ["0.10", "0.20"] -> "0.30". Só para mostrar na tela; o total que
 * vale é o que o backend calcula.
 */
export function somarDinheiro(valores: string[]): string {
  const centavos = valores.reduce((soma, valor) => {
    const [inteiros, fracao = ""] = valor.split(".");
    return soma + BigInt(inteiros || "0") * 100n + BigInt(fracao.padEnd(2, "0").slice(0, 2));
  }, 0n);
  const texto = centavos.toString().padStart(3, "0");
  return `${texto.slice(0, -2)}.${texto.slice(-2)}`;
}

/** 2_500_000 -> "2,4 MB" */
export function formatarTamanho(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1).replace(".", ",")} MB`;
}

/**
 * Número com até 3 casas digitado pela pessoa -> texto para a API.
 * "38,5" -> "38.500"; "40" -> "40.000"; "6,25" -> "6.250". Vazio -> null.
 * Mais de 3 casas ou texto que não é número -> undefined.
 */
export function lerDecimal3(texto: string): string | null | undefined {
  const limpo = texto.replace(/R\$/i, "").replace(/\s/g, "");
  if (!limpo) return null;
  const partes = /^(\d{1,3}(?:\.\d{3})+|\d+)(?:,(\d{1,3}))?$/.exec(limpo);
  if (!partes) return undefined;
  const inteiros = partes[1].replace(/\./g, "").replace(/^0+(?=\d)/, "");
  return `${inteiros}.${(partes[2] ?? "").padEnd(3, "0")}`;
}

/** "38.500" (da API) -> "38,5"; "40.000" -> "40" (sem zeros sobrando). */
export function formatarDecimal(valor: string, minimoDeCasas = 0): string {
  const [inteiros, fracao = ""] = valor.split(".");
  let casas = fracao.replace(/0+$/, "");
  if (casas.length < minimoDeCasas) casas = casas.padEnd(minimoDeCasas, "0");
  return `${mascararInteiro(inteiros) || "0"}${casas ? `,${casas}` : ""}`;
}

/**
 * Litros × preço por litro (os dois com 3 casas, como a API usa), arredondado
 * para centavos meio para cima, em inteiros: "38.500" × "4.290" -> "165.17".
 * Só para mostrar na tela; o valor gravado é o que o backend calcula.
 */
export function multiplicarParaCentavos(litros: string, preco: string): string {
  const milesimos = (texto: string) => {
    const [i, f = ""] = texto.split(".");
    return BigInt(i || "0") * 1000n + BigInt(f.padEnd(3, "0").slice(0, 3));
  };
  const produto = milesimos(litros) * milesimos(preco); // em milionésimos de real
  const centavos = (produto + 5000n) / 10000n;            // meio para cima
  const texto = centavos.toString().padStart(3, "0");
  return `${texto.slice(0, -2)}.${texto.slice(-2)}`;
}
