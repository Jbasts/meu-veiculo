import { describe, expect, it } from "vitest";

import { formatarMesAnoCurto, formatarMesAnoLongo, hojeIso } from "./datas";
import {
  dinheiroParaCampo,
  formatarDecimal,
  formatarDinheiro,
  formatarKm,
  formatarPlaca,
  formatarTamanho,
  lerDecimal3,
  lerDinheiro,
  lerInteiro,
  mascararInteiro,
  multiplicarParaCentavos,
  normalizarPlaca,
  placaValida,
  somarDinheiro,
} from "./formatos";

describe("quilometragem", () => {
  it("formata com ponto de milhar", () => {
    expect(formatarKm(85000)).toBe("85.000 km");
    expect(formatarKm(0)).toBe("0 km");
    expect(formatarKm(1234567)).toBe("1.234.567 km");
  });

  it("mascara o que é digitado e lê de volta o número", () => {
    expect(mascararInteiro("85000")).toBe("85.000");
    expect(mascararInteiro("085.4a50")).toBe("85.450");
    expect(lerInteiro("85.450")).toBe(85450);
    expect(lerInteiro("")).toBeNull();
  });
});

describe("placa", () => {
  it("mostra hífen só na placa antiga", () => {
    expect(formatarPlaca("ABC1234")).toBe("ABC-1234");
    expect(formatarPlaca("BRA2E19")).toBe("BRA2E19");
  });

  it("normaliza como o backend e valida os dois formatos", () => {
    expect(normalizarPlaca(" abc-1234 ")).toBe("ABC1234");
    expect(placaValida("abc-1234")).toBe(true);
    expect(placaValida("BRA2E19")).toBe(true);
    expect(placaValida("ABC-12345")).toBe(false);
    expect(placaValida("1234ABC")).toBe(false);
  });
});

describe("dinheiro (sempre texto, nunca ponto flutuante)", () => {
  it("formata o texto da API em reais", () => {
    expect(formatarDinheiro("65000.00")).toBe("R$ 65.000,00");
    expect(formatarDinheiro("0.10")).toBe("R$ 0,10");
    expect(formatarDinheiro("1234567.5")).toBe("R$ 1.234.567,50");
    expect(dinheiroParaCampo("65000.00")).toBe("65.000,00");
    expect(dinheiroParaCampo(null)).toBe("");
  });

  it("lê o que a pessoa digitou", () => {
    expect(lerDinheiro("R$ 65.000,00")).toBe("65000.00");
    expect(lerDinheiro("65000")).toBe("65000.00");
    expect(lerDinheiro("1.234,5")).toBe("1234.50");
    expect(lerDinheiro("0,10")).toBe("0.10");
    expect(lerDinheiro("  ")).toBeNull();
  });

  it("não perde centavos em valores que o ponto flutuante erraria", () => {
    // 0.1 + 0.2 em ponto flutuante dá 0.30000000000000004; aqui nada é somado.
    expect(lerDinheiro("1.000.000,29")).toBe("1000000.29");
    expect(formatarDinheiro("1000000.29")).toBe("R$ 1.000.000,29");
  });

  it("soma em centavos inteiros, sem erro de arredondamento", () => {
    expect(somarDinheiro(["0.10", "0.20"])).toBe("0.30");
    expect(somarDinheiro(["70.00", "45.00"])).toBe("115.00");
    expect(somarDinheiro(["0.05"])).toBe("0.05");
    expect(somarDinheiro([])).toBe("0.00");
    expect(somarDinheiro(["9999999999.99", "0.01"])).toBe("10000000000.00");
  });

  it("recusa texto que não é um valor em reais", () => {
    for (const texto of ["abc", "65,000.00", "10,005", "1.23,00", "-5"]) {
      expect(lerDinheiro(texto)).toBeUndefined();
    }
  });
});

describe("datas e tamanhos", () => {
  it("monta mês e ano sem passar por new Date()", () => {
    expect(formatarMesAnoCurto("2022-03-15")).toBe("mar/2022");
    expect(formatarMesAnoLongo("2026-09-01")).toBe("Setembro de 2026");
  });

  it("hoje é o dia em Brasília, mesmo quando em UTC já é o dia seguinte", () => {
    // 01/10/2026 01:30 em UTC ainda é 30/09/2026 22:30 em Brasília.
    expect(hojeIso(new Date("2026-10-01T01:30:00Z"))).toBe("2026-09-30");
    expect(hojeIso(new Date("2026-10-01T03:00:00Z"))).toBe("2026-10-01");
  });

  it("formata o tamanho do arquivo", () => {
    expect(formatarTamanho(500)).toBe("1 KB");
    expect(formatarTamanho(2_621_440)).toBe("2,5 MB");
  });
});

describe("decimais do abastecimento", () => {
  it("lê litros e preço com até 3 casas, sem float", () => {
    expect(lerDecimal3("38,5")).toBe("38.500");
    expect(lerDecimal3("R$ 6,25")).toBe("6.250");
    expect(lerDecimal3("1.234,567")).toBe("1234.567");
    expect(lerDecimal3("")).toBeNull();
    expect(lerDecimal3("1,2345")).toBeUndefined();
    expect(lerDecimal3("abc")).toBeUndefined();
  });

  it("calcula o total meio para cima, como o backend", () => {
    expect(multiplicarParaCentavos("38.500", "4.290")).toBe("165.17"); // 165,165
    expect(multiplicarParaCentavos("40.000", "6.250")).toBe("250.00");
    expect(multiplicarParaCentavos("0.001", "4.999")).toBe("0.00");
  });

  it("mostra sem zeros sobrando", () => {
    expect(formatarDecimal("38.500")).toBe("38,5");
    expect(formatarDecimal("40.000")).toBe("40");
    expect(formatarDecimal("6.250", 2)).toBe("6,25");
    expect(formatarDecimal("1234.567")).toBe("1.234,567");
  });
});
