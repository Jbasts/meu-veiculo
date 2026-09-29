import { describe, expect, it } from "vitest";

import { formatarDataIso } from "./datas";

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
