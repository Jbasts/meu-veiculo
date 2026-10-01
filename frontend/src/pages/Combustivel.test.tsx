// Aba Combustível (consumo, "Etanol ou gasolina?", abastecimentos) e "Novo abastecimento",
// com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { Abastecimento, ResumoCombustivel } from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { hojeIso, mesDaData } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null,
};
const HOJE = hojeIso();
const ATUAL = mesDaData(HOJE);

const RESUMO: ResumoCombustivel = {
  combustiveis: ["gasolina", "etanol"],
  medias: [
    { combustivel: "gasolina", km_por_litro: "11.3", distancia: 339, quantidade: "30.000", ciclos: 1 },
    { combustivel: "etanol", km_por_litro: "7.9", distancia: 237, quantidade: "30.000", ciclos: 1 },
  ],
  comparacao: { recomendacao: "etanol", motivo: null, limite_percentual: 70, relacao_percentual: 69,
    preco_gasolina: "6.250", preco_etanol: "4.290", precos_simulados: false },
  postos_recentes: ["Shell", "Ipiranga"],
  ultima_quilometragem: 85000,
};
const SEM_DADOS: ResumoCombustivel = {
  ...RESUMO, medias: [], postos_recentes: [],
  comparacao: { recomendacao: null, limite_percentual: null, relacao_percentual: null, preco_gasolina: null,
    preco_etanol: null, precos_simulados: false,
    motivo: "Ainda não dá para comparar: falta o consumo de gasolina e de etanol." },
};

function abastecimento(alteracoes: Partial<Abastecimento>): Abastecimento {
  return {
    id: 1, veiculo_id: 7, data: "2026-09-20", quilometragem: 85339, combustivel: "gasolina", tipo: "comum",
    litros: "40.000", valor_litro: "6.250", valor_total: "250.00", tanque_cheio: true, posto: "Shell",
    criado_em: "2026-09-20T10:00:00-03:00",
    consumo: { tipo: "consumo", km_por_litro: "11.3", motivo: null }, ...alteracoes,
  };
}

const LISTA = [
  abastecimento({}),
  abastecimento({ id: 2, data: "2026-09-08", posto: null, litros: "16.000", valor_total: "100.00",
    tanque_cheio: false, consumo: { tipo: "parcial", km_por_litro: null, motivo: null } }),
];

function pagina<T>(itens: T[], porPagina = 30) {
  return json(200, { itens, total: itens.length, pagina: 1, por_pagina: porPagina });
}

const URL_RESUMO = "GET /api/veiculos/7/combustivel/resumo";
const URL_LISTA = "GET /api/veiculos/7/abastecimentos?pagina=1&por_pagina=30";
const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  [URL_RESUMO]: () => json(200, RESUMO),
  [URL_LISTA]: () => pagina(LISTA),
  // A tela de Finanças também carrega a aba Gastos ao voltar do formulário.
  [`GET /api/veiculos/7/financas/resumo?ano=${ATUAL.ano}&mes=${ATUAL.mes}`]: () => json(200, {
    periodo: "mes", ano: ATUAL.ano, mes: ATUAL.mes, total: "0.00", quantidade: 0, categorias: [],
    previsto_manutencoes: "0.00", quantidade_manutencoes_previstas: 0, previsto_gastos: "0.00",
    quantidade_gastos_previstos: 0 }),
};

function corpoJson(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return JSON.parse(opcoes.body as string);
}

describe("Finanças: aba Combustível", () => {
  it("lista recargas com o tipo e o consumo em km/kWh", async () => {
    apiFalsa({ ...BASE, [URL_LISTA]: () => pagina([abastecimento({ combustivel: "eletrica", tipo: "ac",
      posto: "Casa", litros: "40.000", valor_litro: "0.900", valor_total: "36.00",
      consumo: { tipo: "consumo", km_por_litro: "6.0", motivo: null } })]) });
    renderizarApp("/financas?aba=combustivel");
    const lista = await screen.findByRole("region", { name: "Abastecimentos" });
    const [item] = within(lista).getAllByRole("link");
    expect(item.textContent).toContain("Casa, eletricidade (recarga AC)");
    expect(item.textContent).toContain("40 kWh a R$ 0,90");
    expect(item.textContent).toContain("6,0 km/kWh");
  });

  it("mostra as médias, a comparação com o consumo do carro e os abastecimentos", async () => {
    apiFalsa(BASE);
    renderizarApp("/financas?aba=combustivel");

    const medias = await screen.findByRole("region", { name: "Consumo médio" });
    expect(medias.textContent).toContain("11,3 km/L");
    expect(medias.textContent).toContain("7,9 km/L");
    const comparacao = screen.getByRole("region", { name: "Etanol ou gasolina?" });
    expect(within(comparacao).getByText(/Hoje, o etanol compensa/)).toBeInTheDocument();
    expect(within(comparacao).getByText(/vale a pena até 70% do preço da gasolina\. No último abastecimento, ele custou 69%\./))
      .toBeInTheDocument();

    const lista = await screen.findByRole("region", { name: "Abastecimentos" });
    const [primeiro, segundo] = within(lista).getAllByRole("link");
    expect(primeiro).toHaveAttribute("href", "/veiculos/7/abastecimentos/1");
    expect(primeiro.textContent).toContain("Shell, gasolina comum");
    expect(primeiro.textContent).toContain("20/09/2026, 40 L a R$ 6,25");
    expect(primeiro.textContent).toContain("11,3 km/L");
    expect(segundo.textContent).toContain("Gasolina comum");
    expect(segundo.textContent).toContain("Tanque parcial");
    expect(screen.getByRole("link", { name: "Novo abastecimento" })).toHaveAttribute(
      "href", "/veiculos/7/abastecimentos/novo");
  });

  it("sem dados suficientes, explica em vez de mostrar zero", async () => {
    apiFalsa({ ...BASE, [URL_RESUMO]: () => json(200, SEM_DADOS), [URL_LISTA]: () => pagina([]) });
    renderizarApp("/financas?aba=combustivel");
    expect(await screen.findByText("Ainda não há consumo calculado.")).toBeInTheDocument();
    expect(screen.getByText(/falta o consumo de gasolina e de etanol/)).toBeInTheDocument();
    expect(screen.queryByText(/0,0 km\/L/)).not.toBeInTheDocument();
    expect(await screen.findByText("Nenhum abastecimento")).toBeInTheDocument();
  });

  it("simula com os preços de hoje sem gravar nada", async () => {
    const SIMULADO = "GET /api/veiculos/7/combustivel/resumo?preco_gasolina=6.000&preco_etanol=4.500";
    const buscar = apiFalsa({ ...BASE, [SIMULADO]: () => json(200, { ...RESUMO, comparacao: {
      ...RESUMO.comparacao!, recomendacao: "gasolina", relacao_percentual: 75, preco_gasolina: "6.000",
      preco_etanol: "4.500", precos_simulados: true } }) });
    renderizarApp("/financas?aba=combustivel");
    await userEvent.click(await screen.findByRole("button", { name: "Simular com os preços de hoje" }));
    await userEvent.type(screen.getByLabelText("Gasolina hoje (R$)"), "6");
    await userEvent.type(screen.getByLabelText("Etanol hoje (R$)"), "4,5");
    await userEvent.click(screen.getByRole("button", { name: "Comparar" }));
    expect(await screen.findByText(/Hoje, a gasolina compensa/)).toBeInTheDocument();
    expect(screen.getByText(/Com os preços informados, ele custa 75%/)).toBeInTheDocument();
    expect(chamadasPara(buscar, SIMULADO)).toHaveLength(1);
    expect(buscar.mock.calls.every(([, o]) => (o?.method ?? "GET") === "GET")).toBe(true);
  });
});

describe("Novo abastecimento", () => {
  it("mostra a prévia do total e envia litros e preço como texto, sem total", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/abastecimentos": () => json(201, abastecimento({})) });
    renderizarApp("/veiculos/7/abastecimentos/novo");

    expect(await screen.findByText("Última: 85.000 km")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Etanol" }));
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85450");
    await userEvent.type(screen.getByLabelText("Preço por litro"), "4,29");
    await userEvent.type(screen.getByLabelText("Litros"), "38,5");
    // 38,5 × 4,29 = 165,165 -> R$ 165,17 (meio para cima)
    expect(within(screen.getByRole("region", { name: "Valor total" })).getByText("R$ 165,17")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Ipiranga" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar abastecimento" }));

    expect(await screen.findByText("Abastecimento registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/abastecimentos")).toEqual({
      combustivel: "etanol", tipo: "comum", data: HOJE, quilometragem: 85450, litros: "38.500", valor_litro: "4.290",
      valor_total: null, tanque_cheio: true, posto: "Ipiranga",
    });
  });

  it("corrige pelo cupom e mostra o erro do servidor no campo", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/abastecimentos": () => json(422, {
      mensagem: "Confira os campos.",
      campos: { valor_total: "O valor do cupom difere mais de R$ 50,00 do calculado (R$ 165.17). Confira os litros e o preço." } }) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    await userEvent.type(await screen.findByLabelText("Quilometragem"), "85450");
    await userEvent.type(screen.getByLabelText("Preço por litro"), "4,29");
    await userEvent.type(screen.getByLabelText("Litros"), "38,5");
    await userEvent.click(screen.getByRole("button", { name: /Corrigir pelo cupom/ }));
    // O calculado aparece junto do campo, para conferir o cupom.
    expect(screen.getByText(/Calculado: R\$ 165,17\. Vale o do cupom se a diferença for de até R\$ 50,00\./))
      .toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Valor do cupom (R$)"), "230,00");
    await userEvent.click(screen.getByRole("button", { name: "Salvar abastecimento" }));
    expect((await screen.findAllByText(/difere mais de R\$ 50,00/)).length).toBeGreaterThan(0);
    expect(corpoJson(buscar, "POST /api/veiculos/7/abastecimentos").valor_total).toBe("230.00");
  });

  it("envia o tipo escolhido (comum aditivada)", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/abastecimentos": () => json(201, abastecimento({})) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    expect(await screen.findByRole("radio", { name: "Comum" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "Comum aditivada" }));
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85450");
    await userEvent.type(screen.getByLabelText("Preço por litro"), "6,59");
    await userEvent.type(screen.getByLabelText("Litros"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Salvar abastecimento" }));
    expect(await screen.findByText("Abastecimento registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/abastecimentos")).toMatchObject({
      combustivel: "gasolina", tipo: "comum_aditivada" });
  });

  it("abastecimento antigo sem tipo avisa e salva sem inventar", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/abastecimentos/1": () => json(200, abastecimento({ tipo: null })),
      "PUT /api/veiculos/7/abastecimentos/1": () => json(200, abastecimento({ tipo: null })) });
    renderizarApp("/veiculos/7/abastecimentos/1");
    expect(await screen.findByText(/Não informado \(abastecimento antigo\)/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(corpoJson(buscar, "PUT /api/veiculos/7/abastecimentos/1").tipo).toBeNull();
  });

  it("cada combustível mostra os seus tipos; trocar de combustível volta para o primeiro tipo", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/abastecimentos": () => json(201, abastecimento({})) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    const tipos = await screen.findByRole("radiogroup", { name: "Tipo" });
    expect(within(tipos).getAllByRole("radio").map((r) => r.textContent)).toEqual(
      ["Comum", "Comum aditivada", "Premium", "Premium aditivada"]);
    await userEvent.click(screen.getByRole("radio", { name: "Premium" }));
    await userEvent.click(screen.getByRole("radio", { name: "Etanol" }));
    expect(within(screen.getByRole("radiogroup", { name: "Tipo" })).getAllByRole("radio").map((r) => r.textContent))
      .toEqual(["Comum (hidratado)", "Aditivado", "Premium", "Premium aditivado"]);
    expect(screen.getByRole("radio", { name: "Comum (hidratado)" })).toHaveAttribute("aria-checked", "true");
    await userEvent.click(screen.getByRole("radio", { name: "Premium aditivado" }));
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85450");
    await userEvent.type(screen.getByLabelText("Preço por litro"), "4,59");
    await userEvent.type(screen.getByLabelText("Litros"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Salvar abastecimento" }));
    expect(await screen.findByText("Abastecimento registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/abastecimentos")).toMatchObject({
      combustivel: "etanol", tipo: "premium_aditivado" });
  });

  it("veículo a diesel só mostra os tipos do diesel", async () => {
    apiFalsa({ ...BASE, [URL_RESUMO]: () => json(200, { ...RESUMO, combustiveis: ["diesel"], comparacao: null }) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    expect(await screen.findByText("Combustível: Diesel")).toBeInTheDocument();
    expect(within(screen.getByRole("radiogroup", { name: "Tipo" })).getAllByRole("radio").map((r) => r.textContent))
      .toEqual(["S10", "S10 aditivado", "S500", "S500 aditivado"]);
    expect(screen.getByRole("radio", { name: "S10" })).toHaveAttribute("aria-checked", "true");
  });

  it("veículo elétrico registra recarga AC/DC em kWh, com carga completa", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7": () => json(200, { ...CIVIC, tipo_combustivel: "eletrico" }),
      "GET /api/veiculos": () => json(200, [{ ...CIVIC, tipo_combustivel: "eletrico" }]),
      [URL_RESUMO]: () => json(200, { ...RESUMO, combustiveis: ["eletrica"], comparacao: null, medias: [] }),
      "POST /api/veiculos/7/abastecimentos": () => json(201, abastecimento({ combustivel: "eletrica", tipo: "dc" })) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    expect(await screen.findByText("Combustível: Eletricidade")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Recarga DC" }));
    expect(screen.getByRole("switch", { name: "Carga completa" })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85240");
    await userEvent.type(screen.getByLabelText("Preço por kWh"), "2,50");
    await userEvent.type(screen.getByLabelText("Energia (kWh)"), "40");
    await userEvent.click(screen.getByRole("button", { name: "Salvar abastecimento" }));
    expect(await screen.findByText("Abastecimento registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/abastecimentos")).toMatchObject({
      combustivel: "eletrica", tipo: "dc", litros: "40.000", valor_litro: "2.500" });
  });

  it("não envia sem quilometragem, preço e litros", async () => {
    const buscar = apiFalsa(BASE);
    renderizarApp("/veiculos/7/abastecimentos/novo");
    await userEvent.click(await screen.findByRole("button", { name: "Salvar abastecimento" }));
    expect(screen.getByText("Informe a quilometragem.")).toBeInTheDocument();
    expect(screen.getByText("Informe o preço.")).toBeInTheDocument();
    expect(screen.getByText("Informe os litros.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/abastecimentos")).toHaveLength(0);
  });

  it("veículo só a gasolina não mostra a escolha de combustível", async () => {
    apiFalsa({ ...BASE, [URL_RESUMO]: () => json(200, { ...RESUMO, combustiveis: ["gasolina"], comparacao: null }) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    expect(await screen.findByText("Combustível: Gasolina")).toBeInTheDocument();
    expect(screen.queryByRole("radio", { name: "Etanol" })).not.toBeInTheDocument();
  });

  it("na edição, mostra o consumo do tanque e apaga depois de confirmar", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/abastecimentos/1": () => json(200, abastecimento({})),
      "DELETE /api/veiculos/7/abastecimentos/1": () => json(204, null) });
    renderizarApp("/veiculos/7/abastecimentos/1");
    expect(await screen.findByText("Consumo deste tanque: 11,3 km/L.")).toBeInTheDocument();
    expect(screen.getByLabelText("Litros")).toHaveValue("40,00");
    await userEvent.click(screen.getByRole("button", { name: "Apagar abastecimento" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Abastecimento apagado.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/abastecimentos/1")).toHaveLength(1);
  });
});
