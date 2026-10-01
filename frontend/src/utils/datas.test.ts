import { describe, expect, it } from "vitest";

import { formatarDataIso, mesDaData, nomeDoMes, somarMeses } from "./datas";

describe("formatarDataIso", () => {
  it("converte AAAA-MM-DD para DD/MM/AAAA", () => {
    expect(formatarDataIso("2026-09-24")).toBe("24/09/2026");
  });

  it("não volta um dia por causa do fuso (primeiro dia do mês)", () => {
    // new Date("2026-09-01") em UTC-3 mostraria 31/08/2026.
    expect(formatarDataIso("2026-09-01")).toBe("01/09/2026");
  });

  it("recusa formato inesperado", () => {
    expect(() => formatarDataIso("24/09/2026")).toThrow();
  });
});

describe("meses", () => {
  it("anda entre meses e anos sem passar por Date", () => {
    expect(mesDaData("2026-09-20")).toEqual({ ano: 2026, mes: 9 });
    expect(somarMeses({ ano: 2026, mes: 1 }, -1)).toEqual({ ano: 2025, mes: 12 });
    expect(somarMeses({ ano: 2026, mes: 12 }, 1)).toEqual({ ano: 2027, mes: 1 });
    expect(nomeDoMes({ ano: 2026, mes: 9 })).toBe("Setembro de 2026");
  });
});
