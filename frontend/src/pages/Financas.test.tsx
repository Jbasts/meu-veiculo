// Finanças (resumo do mês, contas a vencer, lançamentos) e "Novo gasto", com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { Gasto, Lancamento, Pendente, ResumoMes } from "../types/gasto";
import type { Veiculo } from "../types/veiculo";
import { hojeIso, mesDaData, somarMeses } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null,
};

const HOJE = hojeIso();
const ATUAL = mesDaData(HOJE);
const ANTERIOR = somarMeses(ATUAL, -1);

/** O exemplo do PDF: 2.150 + 515,17 + 30 = 2.695,17. */
const RESUMO: ResumoMes = {
  periodo: "mes", ano: ATUAL.ano, mes: ATUAL.mes, total: "2695.17", quantidade: 6,
  categorias: [
    { categoria: "manutencao", total: "2150.00", quantidade: 2, percentual: 80 },
    { categoria: "combustivel", total: "515.17", quantidade: 3, percentual: 19 },
    { categoria: "estacionamento", total: "30.00", quantidade: 1, percentual: 1 },
  ],
  previsto_manutencoes: "350.00", quantidade_manutencoes_previstas: 1,
  previsto_gastos: "0.00", quantidade_gastos_previstos: 0,
};

const VAZIO: ResumoMes = {
  ...RESUMO, total: "0.00", quantidade: 0, categorias: [], previsto_manutencoes: "0.00",
  quantidade_manutencoes_previstas: 0,
};

const LANCAMENTOS: Lancamento[] = [
  { tipo: "manutencao", origem_id: 12, data: HOJE, categoria: "manutencao", descricao: "Troca de óleo", valor: "350.00" },
  { tipo: "abastecimento", origem_id: 3, data: HOJE, categoria: "combustivel", descricao: "Abastecimento, Shell", valor: "250.00" },
  { tipo: "gasto", origem_id: 9, data: HOJE, categoria: "estacionamento", descricao: null, valor: "30.00" },
];

const SEGURO: Pendente = {
  id: 20, veiculo_id: 7, categoria: "seguro", descricao: "Renovação do seguro", data: HOJE,
  valor: "2400.00", pago: false, data_vencimento: "2026-11-10", data_pagamento: null,
  criado_em: "2026-09-24T10:00:00-03:00", situacao: "a_vencer", dias: 47,
};
const IPVA: Pendente = { ...SEGURO, id: 21, categoria: "ipva", descricao: null, valor: "1200.00",
  data_vencimento: "2026-09-27", situacao: "vencido", dias: -3 };

function pagina<T>(itens: T[], porPagina = 50) {
  return json(200, { itens, total: itens.length, pagina: 1, por_pagina: porPagina });
}

const URL_RESUMO = (m = ATUAL) => `GET /api/veiculos/7/financas/resumo?ano=${m.ano}&mes=${m.mes}`;
const URL_LANCAMENTOS = (m = ATUAL) =>
  `GET /api/veiculos/7/financas/lancamentos?ano=${m.ano}&mes=${m.mes}&pagina=1&por_pagina=50`;
const URL_PENDENTES = "GET /api/veiculos/7/gastos/pendentes?pagina=1&por_pagina=50";

const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  [URL_RESUMO()]: () => json(200, VAZIO),
  [URL_LANCAMENTOS()]: () => pagina([]),
  [URL_PENDENTES]: () => pagina([]),
};

function corpoJson(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return JSON.parse(opcoes.body as string);
}

describe("Finanças: aba Gastos", () => {
  it("mostra o total do mês, as categorias com percentual, o previsto e os lançamentos", async () => {
    apiFalsa({ ...BASE, [URL_RESUMO()]: () => json(200, RESUMO),
      [URL_LANCAMENTOS()]: () => pagina(LANCAMENTOS) });
    renderizarApp("/financas");

    expect(await screen.findByText("R$ 2.695,17")).toBeInTheDocument();
    expect(screen.getByText("6 lançamentos no mês")).toBeInTheDocument();
    const categorias = screen.getByRole("region", { name: "Por categoria" });
    const linhas = within(categorias).getAllByRole("listitem").map((l) => l.textContent);
    expect(linhas).toEqual(["ManutençãoR$ 2.150,00 80%", "CombustívelR$ 515,17 19%", "EstacionamentoR$ 30,00 1%"]);
    const previsto = screen.getByRole("region", { name: "Previsto" });
    expect(within(previsto).getByText("1 manutenção agendada")).toBeInTheDocument();
    expect(within(previsto).getByText("R$ 350,00")).toBeInTheDocument();

    const lancamentos = await screen.findByRole("region", { name: "Lançamentos" });
    expect(within(lancamentos).getByRole("link", { name: /Troca de óleo/ })).toHaveAttribute(
      "href", "/veiculos/7/manutencoes/12");
    expect(within(lancamentos).getByRole("link", { name: /Estacionamento/ })).toHaveAttribute(
      "href", "/veiculos/7/gastos/9");
    expect(screen.getByRole("link", { name: "Novo gasto" })).toHaveAttribute("href", "/veiculos/7/gastos/novo");
  });

  it("mês sem despesas não inventa valores e não deixa ir além do mês atual", async () => {
    const buscar = apiFalsa({ ...BASE, [URL_RESUMO(ANTERIOR)]: () => json(200, { ...VAZIO, ...ANTERIOR }),
      [URL_LANCAMENTOS(ANTERIOR)]: () => pagina([]) });
    renderizarApp("/financas");
    expect(await screen.findByText("Nenhuma despesa neste mês")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Por categoria" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Próximo mês" })).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Mês anterior" }));
    await screen.findByText("Nenhuma despesa neste mês");
    expect(chamadasPara(buscar, URL_RESUMO(ANTERIOR))).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Próximo mês" })).toBeEnabled();
  });

  it("separa vencidas e a vencer e marca como pago com a data escolhida", async () => {
    let pendentes = [IPVA, SEGURO];
    const buscar = apiFalsa({ ...BASE,
      [URL_PENDENTES]: () => pagina(pendentes),
      "POST /api/veiculos/7/gastos/21/pagar": () => {
        pendentes = [SEGURO];
        return json(200, { ...IPVA, pago: true, data_pagamento: HOJE });
      } });
    renderizarApp("/financas");

    const vencidas = await screen.findByRole("region", { name: "Vencidas" });
    expect(within(vencidas).getByText("IPVA")).toBeInTheDocument();  // sem descrição: nome da categoria
    expect(within(vencidas).getByText("há 3 dias")).toBeInTheDocument();
    const aVencer = screen.getByRole("region", { name: "A vencer" });
    expect(within(aVencer).getByText("Vence em 10/11/2026")).toBeInTheDocument();
    expect(within(aVencer).getByText("em 47 dias")).toBeInTheDocument();

    await userEvent.click(within(vencidas).getByRole("button", { name: "Marcar IPVA como pago" }));
    const dialogo = screen.getByRole("alertdialog");
    expect(within(dialogo).getByLabelText("Data do pagamento")).toHaveValue(HOJE);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Confirmar pagamento" }));
    expect(await screen.findByText(/Pagamento registrado em/)).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/gastos/21/pagar")).toEqual({ data_pagamento: HOJE });
    expect(screen.queryByRole("region", { name: "Vencidas" })).not.toBeInTheDocument();
    // O total do mês é recarregado do backend (a tela não soma).
    expect(chamadasPara(buscar, URL_RESUMO()).length).toBeGreaterThanOrEqual(2);
  });

  it("o lançamento de abastecimento abre o abastecimento", async () => {
    apiFalsa({ ...BASE, [URL_LANCAMENTOS()]: () => pagina(LANCAMENTOS) });
    renderizarApp("/financas");
    const lancamentos = await screen.findByRole("region", { name: "Lançamentos" });
    expect(within(lancamentos).getByRole("link", { name: /Abastecimento, Shell/ })).toHaveAttribute(
      "href", "/veiculos/7/abastecimentos/3");
  });
});

describe("Finanças: mês, ano e total", () => {
  const URL_ANO = (ano: number) => `GET /api/veiculos/7/financas/resumo?ano=${ano}`;
  const URL_LANC_ANO = (ano: number) =>
    `GET /api/veiculos/7/financas/lancamentos?ano=${ano}&pagina=1&por_pagina=50`;

  it("mostra o total do ano, troca de ano e não passa do ano atual", async () => {
    const buscar = apiFalsa({ ...BASE,
      [URL_ANO(ATUAL.ano)]: () => json(200, { ...RESUMO, periodo: "ano", mes: null, total: "12500.00", quantidade: 40 }),
      [URL_LANC_ANO(ATUAL.ano)]: () => pagina(LANCAMENTOS),
      [URL_ANO(ATUAL.ano - 1)]: () => json(200, { ...VAZIO, periodo: "ano", ano: ATUAL.ano - 1, mes: null }),
      [URL_LANC_ANO(ATUAL.ano - 1)]: () => pagina([]) });
    renderizarApp("/financas");
    await userEvent.click(await screen.findByRole("button", { name: "Ano" }));
    const total = await screen.findByRole("region", { name: "Total do ano" });
    expect(within(total).getByText("R$ 12.500,00")).toBeInTheDocument();
    expect(within(total).getByText("40 lançamentos no ano")).toBeInTheDocument();
    expect(screen.getByText(`Ano de ${ATUAL.ano}`)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Ano" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Próximo ano" })).toBeDisabled();

    await userEvent.click(screen.getByRole("button", { name: "Ano anterior" }));
    expect(await screen.findByText("Nenhuma despesa neste ano")).toBeInTheDocument();
    expect(chamadasPara(buscar, URL_ANO(ATUAL.ano - 1))).toHaveLength(1);
  });

  it("mostra o total geral desde o primeiro registro, sem setas", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/financas/resumo": () => json(200, {
        ...RESUMO, periodo: "total", ano: null, mes: null, total: "45210.30", quantidade: 152 }),
      "GET /api/veiculos/7/financas/lancamentos?pagina=1&por_pagina=50": () => pagina(LANCAMENTOS) });
    renderizarApp("/financas");
    await userEvent.click(await screen.findByRole("button", { name: "Total" }));
    const total = await screen.findByRole("region", { name: "Total geral" });
    expect(within(total).getByText("R$ 45.210,30")).toBeInTheDocument();
    expect(within(total).getByText("152 lançamentos desde o primeiro registro")).toBeInTheDocument();
    expect(screen.getByText("Desde o primeiro registro")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /anterior/ })).not.toBeInTheDocument();
    expect(chamadasPara(buscar, "GET /api/veiculos/7/financas/resumo")).toHaveLength(1);

    await userEvent.click(screen.getByRole("button", { name: "Mês" }));
    expect(await screen.findByRole("region", { name: "Total do mês" })).toBeInTheDocument();
  });
});

describe("Novo gasto", () => {
  const SALVO: Gasto = { ...SEGURO };

  it("registra conta pendente com vencimento, sem data de pagamento", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/gastos": () => json(201, SALVO) });
    renderizarApp("/veiculos/7/gastos/novo");

    await userEvent.type(await screen.findByLabelText("Valor"), "2.400,00");
    await userEvent.click(screen.getByRole("radio", { name: "Seguro" }));
    await userEvent.type(screen.getByLabelText("Descrição"), "Renovação do seguro");
    expect(screen.getByText("Hoje. Toque para alterar.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("switch", { name: "Já foi pago" }));
    expect(screen.getByText("Vai aparecer em \"A vencer\" nas Finanças.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar gasto" }));
    expect(screen.getByText(/Informe o vencimento/)).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/gastos")).toHaveLength(0);

    await userEvent.type(screen.getByLabelText("Vencimento"), "2026-11-10");
    await userEvent.click(screen.getByRole("button", { name: "Salvar gasto" }));
    expect(await screen.findByText("Conta registrada em \"A vencer\".")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/gastos")).toEqual({
      categoria: "seguro", valor: "2400.00", descricao: "Renovação do seguro", data: HOJE,
      pago: false, data_vencimento: "2026-11-10", data_pagamento: null,
    });
  });

  it("gasto pago: a data do pagamento acompanha a data do gasto", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/gastos": () => json(201, {
      ...SALVO, categoria: "estacionamento", pago: true, data_pagamento: HOJE, data_vencimento: null }) });
    renderizarApp("/veiculos/7/gastos/novo");
    await userEvent.type(await screen.findByLabelText("Valor"), "30");
    await userEvent.click(screen.getByRole("radio", { name: "Estacionamento" }));
    expect(screen.getByLabelText("Data do pagamento")).toHaveValue(HOJE);
    await userEvent.click(screen.getByRole("button", { name: "Salvar gasto" }));
    expect(await screen.findByText("Gasto registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/gastos")).toMatchObject({
      valor: "30.00", pago: true, data: HOJE, data_pagamento: HOJE, data_vencimento: null });
  });

  it("sem valor e sem categoria não envia; erro do servidor aparece no campo", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/gastos": () => json(422, {
      mensagem: "Confira os campos.", campos: { valor: "Use no máximo duas casas decimais (centavos)." } }) });
    renderizarApp("/veiculos/7/gastos/novo");
    await userEvent.click(await screen.findByRole("button", { name: "Salvar gasto" }));
    expect(screen.getByText("Informe o valor.")).toBeInTheDocument();
    expect(screen.getByText("Escolha a categoria.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/gastos")).toHaveLength(0);
    await userEvent.type(screen.getByLabelText("Valor"), "10");
    await userEvent.click(screen.getByRole("radio", { name: "Outros" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar gasto" }));
    expect(await screen.findByText("Use no máximo duas casas decimais (centavos).")).toBeInTheDocument();
  });

  it("gasto antigo pago sem data do pagamento: avisa e permite salvar sem inventar a data", async () => {
    const ANTIGO: Gasto = { ...SALVO, id: 30, categoria: "lavagem", descricao: null, valor: "40.00",
      data: "2026-08-05", pago: true, data_vencimento: null, data_pagamento: null };
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/gastos/30": () => json(200, ANTIGO),
      "PUT /api/veiculos/7/gastos/30": () => json(200, ANTIGO),
      [URL_RESUMO({ ano: 2026, mes: 8 })]: () => json(200, { ...VAZIO, ano: 2026, mes: 8 }),
      [URL_LANCAMENTOS({ ano: 2026, mes: 8 })]: () => pagina([]) });
    renderizarApp("/veiculos/7/gastos/30");
    expect(await screen.findByText(/Não informada \(gasto antigo\)/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(corpoJson(buscar, "PUT /api/veiculos/7/gastos/30").data_pagamento).toBeNull();
  });

  it("apaga só depois de confirmar", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/gastos/20": () => json(200, SALVO),
      "DELETE /api/veiculos/7/gastos/20": () => json(204, null) });
    renderizarApp("/veiculos/7/gastos/20");
    await userEvent.click(await screen.findByRole("button", { name: "Apagar gasto" }));
    const dialogo = screen.getByRole("alertdialog");
    expect(within(dialogo).getByText(/sai de "A vencer"/)).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/gastos/20")).toHaveLength(0);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Gasto apagado.")).toBeInTheDocument();
  });

  it("veículo inativo: mostra o gasto sem permitir alterar", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7": () => json(200, { ...CIVIC, ativo: false }),
      "GET /api/veiculos/7/gastos/20": () => json(200, SALVO) });
    renderizarApp("/veiculos/7/gastos/20");
    expect(await screen.findByText(/não alterado/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar alterações" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Apagar gasto" })).not.toBeInTheDocument();
  });
});
