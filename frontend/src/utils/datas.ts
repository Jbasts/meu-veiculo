// Datas "puras" (campos DATE do banco) chegam da API como "AAAA-MM-DD".
// Elas NÃO passam por new Date(): o navegador interpretaria como meia-noite
// em UTC, e no Brasil (UTC-3) a data apareceria como o dia anterior.

const FORMATO_ISO = /^(\d{4})-(\d{2})-(\d{2})$/;

export function formatarDataIso(dataIso: string): string {
  const partes = FORMATO_ISO.exec(dataIso);
  if (!partes) {
    throw new Error(`Data em formato inesperado: "${dataIso}"`);
  }
  const [, ano, mes, dia] = partes;
  return `${dia}/${mes}/${ano}`;
}
