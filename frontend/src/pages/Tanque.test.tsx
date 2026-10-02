// Tanque: marcação do km e do nível, avisos (tamanho do tanque e marcação do mês),
// consumo estimado pelo marcador e consumo por mês, com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { MarcacaoTanque, ResumoCombustivel } from "../types/abastecimento";
import type { PainelInicio } from "../types/painel";
import type { Veiculo } from "../types/veiculo";
import { hojeIso, mesDaData } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};
const HOJE = hojeIso();
const ATUAL = mesDaData(HOJE);

const MEDIA = {
  combustivel: "gasolina" as const, km_por_litro: "10.0", distancia: 280, quantidade: "28.000", ciclos: 1,
  estimada: true, margem: "3.500", km_por_litro_minimo: "8.9", km_por_litro_maximo: "11.4",
  inicio: "2026-09-01", fim: "2026-09-20",
};
const RESUMO: ResumoCombustivel = {
  combustiveis: ["gasolina", "etanol"], medias: [MEDIA], comparacao: null, postos_recentes: [],
  ultima_quilometragem: 85000, capacidade_tanque: "56.0", tanque_pendente: false,
  marcacao_do_mes_pendente: true, meses: [{ ...MEDIA, ano: 2026, mes: 9 }],
  nivel_tanque: { disponivel: false, motivo: "Ainda não há nível registrado.", nivel: null, data: null, quilometragem: null, origem: null, km_desde: null, nivel_estimado: null, km_por_litro: null },
};

const MARCACAO: MarcacaoTanque = {
  id: 3, veiculo_id: 7, data: "2026-09-01", quilometragem: 84000, nivel: 3,
  criado_em: "2026-09-01T10:00:00-03:00",
  consumo: { tipo: "primeiro_nivel", km_por_litro: null, motivo: null, estimado: false,
    km_por_litro_minimo: null, km_por_litro_maximo: null },
};

function pagina<T>(itens: T[]) {
  return json(200, { itens, total: itens.length, pagina: 1, por_pagina: 30 });
}

const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  "GET /api/veiculos/7/combustivel/resumo": () => json(200, RESUMO),
  "GET /api/veiculos/7/abastecimentos?pagina=1&por_pagina=30": () => pagina([]),
  "GET /api/veiculos/7/tanque/marcacoes?pagina=1&por_pagina=30": () => pagina([MARCACAO]),
  [`GET /api/veiculos/7/financas/resumo?ano=${ATUAL.ano}&mes=${ATUAL.mes}`]: () => json(200, {
    periodo: "mes", ano: ATUAL.ano, mes: ATUAL.mes, total: "0.00", quantidade: 0, categorias: [],
    previsto_manutencoes: "0.00", quantidade_manutencoes_previstas: 0, previsto_gastos: "0.00",
    quantidade_gastos_previstos: 0 }),
};

describe("Aba Combustível com o marcador do tanque", () => {
  it("mostra a média estimada com a faixa, o consumo por mês, as marcações e o aviso do mês", async () => {
    apiFalsa(BASE);
    renderizarApp("/financas?aba=combustivel");

    const medias = await screen.findByRole("region", { name: "Consumo médio" });
    expect(medias.textContent).toContain("≈ 10,0 km/L");
    expect(medias.textContent).toContain("Pelo marcador: entre 8,9 e 11,4");

    const aviso = screen.getByRole("region", { name: "Marcação do mês" });
    expect(within(aviso).getByRole("link", { name: "Marcar km e nível" }))
      .toHaveAttribute("href", "/veiculos/7/tanque/marcacoes/nova");

    const meses = screen.getByRole("region", { name: "Consumo por mês" });
    expect(meses.textContent).toContain("280 km com 28 L");
    expect(meses.textContent).toContain("≈ 10,0 km/L");
    expect(meses.textContent).toContain("8,9 a 11,4");

    const marcacoes = await screen.findByRole("region", { name: "Marcações do tanque" });
    const [item] = within(marcacoes).getAllByRole("link");
    expect(item).toHaveAttribute("href", "/veiculos/7/tanque/marcacoes/3");
    expect(item.textContent).toContain("Marcador em 1,5/4");
    expect(item.textContent).toContain("01/09/2026, 84.000 km");
    expect(item.textContent).toContain("Primeiro nível marcado");
  });

  it("pede o tamanho do tanque quando falta no cadastro", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/combustivel/resumo": () => json(200, {
      ...RESUMO, capacidade_tanque: null, tanque_pendente: true, marcacao_do_mes_pendente: false }) });
    renderizarApp("/financas?aba=combustivel");
    const aviso = await screen.findByRole("region", { name: "Tamanho do tanque" });
    expect(within(aviso).getByRole("link", { name: "Informar o tamanho do tanque" }))
      .toHaveAttribute("href", "/veiculos/7/editar");
  });
});

describe("Marcação do tanque", () => {
  it("registra km e nível com quanto falta para encher", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/tanque/marcacoes": () => json(201, MARCACAO) });
    renderizarApp("/veiculos/7/tanque/marcacoes/nova");
    await userEvent.type(await screen.findByLabelText("Quilometragem"), "85300");
    await userEvent.click(screen.getByRole("button", { name: "Salvar marcação" }));
    expect(screen.getByText("Escolha o nível do marcador.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "1,5/4" }));
    expect(screen.getByText("1,5/4: faltam cerca de 35 L para encher o tanque de 56 L.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar marcação" }));
    expect(await screen.findByText("Marcação registrada.")).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/veiculos/7/tanque/marcacoes");
    expect(JSON.parse(opcoes.body as string)).toEqual({ data: HOJE, quilometragem: 85300, nivel: 3 });
  });

  it("sem o tamanho do tanque, não deixa marcar e mostra o caminho", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7": () => json(200, { ...CIVIC, capacidade_tanque: null, tanque_pendente: true }) });
    renderizarApp("/veiculos/7/tanque/marcacoes/nova");
    expect(await screen.findByRole("link", { name: "Informar agora" })).toHaveAttribute("href", "/veiculos/7/editar");
    expect(screen.queryByRole("button", { name: "Salvar marcação" })).not.toBeInTheDocument();
  });

  it("abre uma marcação com o consumo do trecho e apaga", async () => {
    const comConsumo: MarcacaoTanque = { ...MARCACAO, consumo: { tipo: "consumo", km_por_litro: "10.4", motivo: null,
      estimado: true, km_por_litro_minimo: "9.1", km_por_litro_maximo: "11.9" } };
    const buscar = apiFalsa({
      ...BASE,
      "GET /api/veiculos/7/tanque/marcacoes/3": () => json(200, comConsumo),
      "DELETE /api/veiculos/7/tanque/marcacoes/3": () => new Response(null, { status: 204 }),
    });
    renderizarApp("/veiculos/7/tanque/marcacoes/3");
    expect(await screen.findByText(/Consumo do trecho até aqui: ≈ 10,4 km\/L\. Pelo marcador: entre 9,1 e 11,9/))
      .toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Apagar marcação" }));
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Marcação apagada.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/tanque/marcacoes/3")).toHaveLength(1);
  });
});

describe("Início com os avisos do tanque", () => {
  const PAINEL: PainelInicio = {
    gastos_do_mes: { ano: 2026, mes: 10, total: "0.00", quantidade: 0, parcelas: [] },
    consumo: { disponivel: true, motivo: null, combustivel: "gasolina", valor: "10.0", ciclos: 1, distancia: 280,
      quantidade: "28.000", inicio: "2026-09-01", fim: "2026-09-20", estimado: true, minimo: "8.9", maximo: "11.4" },
    custo_por_km: { disponivel: false, motivo: "Sem dados.", base: null, aviso_base: null, inicio: null, fim: null,
      km_inicio: null, km_fim: null, distancia: null, despesas: null, valor: null, parcelas: [] },
    contas: { vencidas: 0, total_vencidas: "0.00", vencem_hoje: 0 },
    tanque: { tamanho_pendente: true, marcacao_do_mes_pendente: true },
    gastos_futuros: { quantidade: 0, total: "0.00", proximos: [] },
    nivel_tanque: { disponivel: false, motivo: "Ainda não há nível registrado.", nivel: null, data: null, quilometragem: null, origem: null, km_desde: null, nivel_estimado: null, km_por_litro: null },
  };

  it("mostra o consumo estimado e os dois avisos em Precisa de atenção", async () => {
    apiFalsa({
      ...BASE,
      "GET /api/veiculos/7/painel": () => json(200, PAINEL),
      "GET /api/veiculos/7/manutencoes/pendentes": () => json(200, { km_atual: 85000, itens: [] }),
      "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=5": () => json(200, {
        itens: [], total: 0, pagina: 1, por_pagina: 5 }),
    });
    renderizarApp("/");
    const tanque = await screen.findByRole("list", { name: "Tanque" });
    const [tamanho, marcacao] = within(tanque).getAllByRole("link");
    expect(tamanho).toHaveAttribute("href", "/veiculos/7/editar");
    expect(tamanho.textContent).toContain("Informe o tamanho do tanque");
    expect(marcacao).toHaveAttribute("href", "/veiculos/7/tanque/marcacoes/nova");
    const consumo = screen.getByRole("link", { name: "Consumo médio" });
    expect(consumo.textContent).toContain("≈ 10,0");
    expect(consumo.textContent).toContain("Pelo marcador: entre 8,9 e 11,4");
  });
});

describe("Nível do tanque no Início, na aba Combustível e no abastecimento", () => {
  const ESTIMADO = {
    disponivel: true, motivo: null, nivel: 8, data: "2026-09-30", quilometragem: 84500,
    origem: "abastecimento" as const, km_desde: 500, nivel_estimado: 2, km_por_litro: "12.5",
  };
  const REGISTRADO = { ...ESTIMADO, nivel: 6, origem: "marcacao" as const, km_desde: 0, nivel_estimado: null,
    km_por_litro: null };
  const INICIO = {
    "GET /api/veiculos/7/manutencoes/pendentes": () => json(200, { km_atual: 85000, itens: [] }),
    "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=5": () => json(200, {
      itens: [], total: 0, pagina: 1, por_pagina: 5 }),
  };
  const PAINEL_BASE: PainelInicio = {
    gastos_do_mes: { ano: 2026, mes: 10, total: "0.00", quantidade: 0, parcelas: [] },
    consumo: { disponivel: false, motivo: "Sem dados.", combustivel: null, valor: null, ciclos: 0, distancia: null,
      quantidade: null, inicio: null, fim: null, estimado: false, minimo: null, maximo: null },
    custo_por_km: { disponivel: false, motivo: "Sem dados.", base: null, aviso_base: null, inicio: null, fim: null,
      km_inicio: null, km_fim: null, distancia: null, despesas: null, valor: null, parcelas: [] },
    contas: { vencidas: 0, total_vencidas: "0.00", vencem_hoje: 0 },
    tanque: { tamanho_pendente: false, marcacao_do_mes_pendente: false },
    gastos_futuros: { quantidade: 0, total: "0.00", proximos: [] },
    nivel_tanque: ESTIMADO,
  };

  it("Início mostra a estimativa de agora e de onde ela vem", async () => {
    apiFalsa({ ...BASE, ...INICIO, "GET /api/veiculos/7/painel": () => json(200, PAINEL_BASE) });
    renderizarApp("/");
    const cartao = await screen.findByRole("region", { name: "Nível do tanque" });
    expect(cartao.textContent).toContain("≈ 1/4");
    expect(cartao.textContent).toContain("Cheio no abastecimento de 30/09/2026, depois 500 km rodados a 12,5 km/L");
    expect(within(cartao).getByRole("link", { name: "Atualizar km e nível" })).toHaveAttribute("href", "/veiculos/7/km");
  });

  it("Início sem registro mostra dados insuficientes, nunca um nível inventado", async () => {
    apiFalsa({ ...BASE, ...INICIO, "GET /api/veiculos/7/painel": () => json(200, {
      ...PAINEL_BASE, nivel_tanque: RESUMO.nivel_tanque }) });
    renderizarApp("/");
    const cartao = await screen.findByRole("region", { name: "Nível do tanque" });
    expect(cartao.textContent).toContain("Dados insuficientes");
    expect(cartao.textContent).toContain("Ainda não há nível registrado.");
    expect(cartao.textContent).not.toMatch(/Vazio|Cheio/);
  });

  it("aba Combustível mostra o nível registrado sem estimar quando não rodou", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/combustivel/resumo": () => json(200, {
      ...RESUMO, nivel_tanque: REGISTRADO }) });
    renderizarApp("/financas?aba=combustivel");
    const cartao = await screen.findByRole("region", { name: "Nível do tanque" });
    expect(cartao.textContent).toContain("3/4");
    expect(cartao.textContent).not.toContain("≈");
    expect(cartao.textContent).toContain("Registrado: 3/4 em 30/09/2026.");
  });

  it("formulário de abastecimento lembra o último nível ao lado do marcador", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/combustivel/resumo": () => json(200, {
      ...RESUMO, nivel_tanque: ESTIMADO }) });
    renderizarApp("/veiculos/7/abastecimentos/novo");
    expect(await screen.findByText(/Último nível: Cheio no abastecimento de 30\/09\/2026 \(≈ 1\/4 agora\)\./))
      .toBeInTheDocument();
  });
});
