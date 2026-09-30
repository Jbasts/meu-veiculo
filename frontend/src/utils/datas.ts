// Datas "puras" (campos DATE do banco) chegam da API como "AAAA-MM-DD".
// Elas NÃO passam por new Date(): o navegador interpretaria como meia-noite
// em UTC, e no Brasil (UTC-3) a data apareceria como o dia anterior.

const FORMATO_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

const MESES = [
  "janeiro", "fevereiro", "março", "abril", "maio", "junho",
  "julho", "agosto", "setembro", "outubro", "novembro", "dezembro",
];

function partesDaData(dataIso: string): [string, string, string] {
  const partes = FORMATO_ISO.exec(dataIso);
  if (!partes) {
    throw new Error(`Data em formato inesperado: "${dataIso}"`);
  }
  return [partes[1], partes[2], partes[3]];
}

export function formatarDataIso(dataIso: string): string {
  const [ano, mes, dia] = partesDaData(dataIso);
  return `${dia}/${mes}/${ano}`;
}

/** "2022-03-15" -> "mar/2022" (como em "Comprado em" no PDF). */
export function formatarMesAnoCurto(dataIso: string): string {
  const [ano, mes] = partesDaData(dataIso);
  return `${MESES[Number(mes) - 1].slice(0, 3)}/${ano}`;
}

/** "2026-09-20" -> "Setembro de 2026" (títulos da galeria). */
export function formatarMesAnoLongo(dataIso: string): string {
  const [ano, mes] = partesDaData(dataIso);
  const nome = MESES[Number(mes) - 1];
  return `${nome[0].toUpperCase()}${nome.slice(1)} de ${ano}`;
}

/**
 * O dia de hoje no calendário de Brasília, como "AAAA-MM-DD".
 * Usa o fuso America/Sao_Paulo mesmo que o aparelho esteja em outro fuso.
 */
export function hojeIso(agora: Date = new Date()): string {
  const partes = new Intl.DateTimeFormat("en-CA", {
    timeZone: "America/Sao_Paulo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(agora);
  const valor = (tipo: string) => partes.find((p) => p.type === tipo)?.value ?? "";
  return `${valor("year")}-${valor("month")}-${valor("day")}`;
}
