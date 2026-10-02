// Tela inicial (atalhos, alertas, gastos do mês, consumo e custo por km), custo no
// "Meu veículo" e Histórico, com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { textosDoEvento } from "./HistoricoPage";
import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { EventoHistorico, PaginaHistorico } from "../types/historico";
import type { CustoPorKm, CustoVeiculo, PainelInicio } from "../types/painel";
import type { Veiculo } from "../types/veiculo";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};

const POR_KM: CustoPorKm = {
  disponivel: true, motivo: null, base: "compra", aviso_base: null, inicio: "2022-03-15",
  fim: "2026-09-20", km_inicio: 22000, km_fim: 85000, distancia: 63000, despesas: "47700.00",
  valor: "0.76",
  parcelas: [
    { grupo: "combustivel", total: "18700.00", por_km: "0.30" },
    { grupo: "manutencao", total: "12500.00", por_km: "0.20" },
    { grupo: "projeto", total: "8300.00", por_km: "0.13" },
    { grupo: "seguro_documentacao", total: "8200.00", por_km: "0.13" },
  ],
};

/** Os números do PDF (página 2). */
const PAINEL: PainelInicio = {
  gastos_do_mes: {
    ano: 2026, mes: 9, total: "2695.17", quantidade: 6,
    parcelas: [
      { grupo: "manutencao", total: "2150.00", percentual: 80 },
      { grupo: "combustivel", total: "515.17", percentual: 19 },
      { grupo: "outros", total: "30.00", percentual: 1 },
    ],
  },
  consumo: {
    disponivel: true, motivo: null, combustivel: "gasolina", valor: "11.3", ciclos: 3,
    distancia: 1200, quantidade: "106.000", inicio: "2026-08-01", fim: "2026-09-20",
    estimado: false, minimo: null, maximo: null,
  },
  custo_por_km: POR_KM,
  contas: { vencidas: 1, total_vencidas: "1200.00", vencem_hoje: 0 },
  tanque: { tamanho_pendente: false, marcacao_do_mes_pendente: false },
  gastos_futuros: { quantidade: 0, total: "0.00", proximos: [] },
  nivel_tanque: { disponivel: false, motivo: "Ainda não há nível registrado.", nivel: null, data: null, quilometragem: null, origem: null, km_desde: null, nivel_estimado: null, km_por_litro: null },
};

const SEM_DADOS: PainelInicio = {
  gastos_do_mes: { ano: 2026, mes: 10, total: "0.00", quantidade: 0, parcelas: [] },
  consumo: {
    disponivel: false, motivo: "Nenhum abastecimento registrado ainda.", combustivel: null, valor: null,
    ciclos: 0, distancia: null, quantidade: null, inicio: null, fim: null,
    estimado: false, minimo: null, maximo: null,
  },
  custo_por_km: {
    ...POR_KM, disponivel: false, valor: null, despesas: null, parcelas: [], base: "primeira_leitura",
    aviso_base: "A compra está sem data e sem km.", distancia: 0,
    motivo: "Ainda não há quilômetros rodados desde a leitura de 01/10/2026.",
  },
  contas: { vencidas: 0, total_vencidas: "0.00", vencem_hoje: 0 },
  tanque: { tamanho_pendente: false, marcacao_do_mes_pendente: false },
  gastos_futuros: { quantidade: 0, total: "0.00", proximos: [] },
  nivel_tanque: { disponivel: false, motivo: "Ainda não há nível registrado.", nivel: null, data: null, quilometragem: null, origem: null, km_desde: null, nivel_estimado: null, km_por_litro: null },
};

function base(painel: PainelInicio) {
  return {
    "GET /api/auth/eu": () => json(200, PAULA),
    "GET /api/veiculos": () => json(200, [CIVIC]),
    "GET /api/veiculos/7": () => json(200, CIVIC),
    "GET /api/veiculos/7/painel": () => json(200, painel),
    "GET /api/veiculos/7/manutencoes/pendentes": () => json(200, { km_atual: 85000, itens: [] }),
    "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=5": () => json(200, {
      itens: [], total: 0, pagina: 1, por_pagina: 5 }),
  };
}

describe("Início", () => {
  it("mostra atalhos, gastos do mês por grupo, consumo e custo por km como no PDF", async () => {
    apiFalsa(base(PAINEL));
    renderizarApp("/");
    const gastos = await screen.findByRole("region", { name: "Gastos em setembro" });
    expect(gastos.textContent).toContain("R$ 2.695,17");
    const legenda = within(gastos).getByRole("list", { name: /por grupo/ });
    expect(within(legenda).getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "ManutençãoR$ 2.150,00", "CombustívelR$ 515,17", "OutrosR$ 30,00"]);
    expect(within(gastos).getByRole("link", { name: "Ver finanças" })).toHaveAttribute("href", "/financas");

    const consumo = screen.getByRole("link", { name: "Consumo médio" });
    expect(consumo.textContent).toContain("11,3 km/L");
    expect(consumo.textContent).toContain("Gasolina");
    expect(consumo.textContent).toContain("01/08/2026 a 20/09/2026");
    const km = screen.getByRole("link", { name: "Custo por km" });
    expect(km.textContent).toContain("R$ 0,76");
    expect(km.textContent).toContain("Desde a compra");

    const atalhos = screen.getByRole("navigation", { name: "Registrar" });
    expect(within(atalhos).getByRole("link", { name: "Abastecer" })).toHaveAttribute("href", "/veiculos/7/abastecimentos/novo");
    expect(within(atalhos).getByRole("link", { name: "Gasto" })).toHaveAttribute("href", "/veiculos/7/gastos/novo");
    expect(within(atalhos).getByRole("link", { name: "Manutenção" })).toHaveAttribute("href", "/veiculos/7/manutencoes/nova");
    expect(within(atalhos).getByRole("link", { name: "Problema" })).toHaveAttribute("href", "/veiculos/7/diagnosticos/novo");
  });

  it("mostra os próximos gastos com o total e os mais próximos", async () => {
    apiFalsa(base({
      ...PAINEL,
      gastos_futuros: {
        quantidade: 4, total: "4245.22",
        proximos: [
          { id: 31, categoria: "lavagem", descricao: null, valor: "40.00", data_vencimento: "2026-10-02", dias: 0 },
          { id: 32, categoria: "seguro", descricao: "Renovação", valor: "2400.00", data_vencimento: "2026-11-11", dias: 40 },
          { id: 33, categoria: "ipva", descricao: "IPVA 2027", valor: "1645.00", data_vencimento: "2027-05-13", dias: 223 },
        ],
      },
    }));
    renderizarApp("/");
    const cartao = await screen.findByRole("region", { name: "Próximos gastos" });
    expect(cartao.textContent).toContain("R$ 4.245,22");
    expect(cartao.textContent).toContain("4 gastos previstos");
    const itens = within(cartao).getAllByRole("listitem").map((l) => l.textContent);
    expect(itens).toEqual([
      "Lavagem02/10/2026 · hojeR$ 40,00",
      "Renovação11/11/2026 · em 40 diasR$ 2.400,00",
      "IPVA 202713/05/2027 · em 223 diasR$ 1.645,00",
    ]);
    expect(within(cartao).getByRole("link", { name: /IPVA 2027/ })).toHaveAttribute("href", "/veiculos/7/gastos/33");
    expect(within(cartao).getByRole("link", { name: "Ver todos" })).toHaveAttribute("href", "/financas");
  });

  it("sem gastos futuros, oferece lançar um", async () => {
    apiFalsa(base(PAINEL));
    renderizarApp("/");
    const cartao = await screen.findByRole("region", { name: "Próximos gastos" });
    expect(cartao.textContent).toContain("Nenhum gasto futuro lançado.");
    expect(within(cartao).getByRole("link", { name: "Lançar gasto futuro" }))
      .toHaveAttribute("href", "/veiculos/7/gastos/novo?futuro=1");
  });

  it("avisa contas vencidas em Precisa de atenção", async () => {
    apiFalsa(base(PAINEL));
    renderizarApp("/");
    const contas = await screen.findByRole("list", { name: "Contas a pagar" });
    expect(contas.textContent).toContain("1 conta vencida");
    expect(contas.textContent).toContain("R$ 1.200,00 em atraso");
  });

  it("indicador sem base mostra dados insuficientes e o motivo, nunca zero", async () => {
    apiFalsa(base(SEM_DADOS));
    renderizarApp("/");
    const consumo = await screen.findByRole("link", { name: "Consumo médio" });
    expect(consumo.textContent).toContain("Dados insuficientes");
    expect(consumo.textContent).toContain("Nenhum abastecimento registrado ainda.");
    expect(consumo.textContent).not.toMatch(/0,0/);
    const km = screen.getByRole("link", { name: "Custo por km" });
    expect(km.textContent).toContain("Dados insuficientes");
    expect(km.textContent).not.toContain("R$ 0,00");
    expect(screen.getByText("Nenhuma despesa registrada em outubro.")).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Precisa de atenção" })).not.toBeInTheDocument();
  });

  it("se os indicadores falharem, o resto do Início continua", async () => {
    const rotas: Record<string, () => Response> = base(PAINEL);
    rotas["GET /api/veiculos/7/painel"] = () => json(500, { mensagem: "Erro" });
    apiFalsa(rotas);
    renderizarApp("/");
    expect(await screen.findByText("Não foi possível carregar os gastos e os indicadores.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Quilometragem" })).toBeInTheDocument();
  });
});

const CUSTO: CustoVeiculo = {
  custo_total: {
    total: "112700.00", valor_aquisicao: "65000.00", despesas: "47700.00", quantidade: 40,
    parcelas: [
      { grupo: "aquisicao", total: "65000.00", percentual: 58 },
      { grupo: "combustivel", total: "18700.00", percentual: 17 },
      { grupo: "manutencao", total: "12500.00", percentual: 11 },
      { grupo: "projeto", total: "8300.00", percentual: 7 },
      { grupo: "seguro", total: "5000.00", percentual: 4 },
      { grupo: "documentacao", total: "3200.00", percentual: 3 },
    ],
  },
  custo_por_km: POR_KM,
};

describe("Meu veículo: custo", () => {
  function rotas(custo: CustoVeiculo) {
    return {
      ...base(PAINEL),
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=3": () => json(200, { itens: [], total: 0, pagina: 1, por_pagina: 3 }),
      "GET /api/veiculos/7/custo": () => json(200, custo),
    };
  }

  it("mostra quanto o carro já custou e o custo por km com o período (PDF, página 15)", async () => {
    apiFalsa(rotas(CUSTO));
    renderizarApp("/veiculos/7");
    const total = await screen.findByRole("region", { name: "Quanto esse carro já me custou" });
    expect(total.textContent).toContain("R$ 112.700,00");
    const linhas = within(total).getAllByRole("listitem").map((l) => l.textContent);
    expect(linhas).toEqual(["AquisiçãoR$ 65.000,00", "CombustívelR$ 18.700,00", "ManutençõesR$ 12.500,00",
      "ProjetosR$ 8.300,00", "SeguroR$ 5.000,00", "DocumentaçãoR$ 3.200,00"]);
    const km = screen.getByRole("region", { name: "Custo por quilômetro" });
    expect(km.textContent).toContain("R$ 0,76 /km");
    expect(km.textContent).toContain(
      "63.000 km rodados desde a compra (15/03/2022 a 20/09/2026), sem contar o valor de aquisição.");
    expect(within(km).getAllByRole("listitem").map((l) => l.textContent)).toEqual([
      "CombustívelR$ 0,30", "ManutençãoR$ 0,20", "ProjetosR$ 0,13", "Seguro e documentaçãoR$ 0,13"]);
    expect(screen.getByRole("link", { name: "Histórico deste veículo" })).toHaveAttribute("href", "/veiculos/7/historico");
  });

  it("sem valor da compra e sem base para o km, explica em vez de inventar", async () => {
    apiFalsa(rotas({
      custo_total: { ...CUSTO.custo_total, valor_aquisicao: null, total: "47700.00",
        parcelas: CUSTO.custo_total.parcelas.slice(1) },
      custo_por_km: SEM_DADOS.custo_por_km,
    }));
    renderizarApp("/veiculos/7");
    const total = await screen.findByRole("region", { name: "Quanto esse carro já me custou" });
    expect(total.textContent).toContain("Valor da compra não informado");
    const km = screen.getByRole("region", { name: "Custo por quilômetro" });
    expect(km.textContent).toContain("Dados insuficientes");
    expect(km.textContent).toContain("Ainda não há quilômetros rodados");
    expect(km.textContent).toContain("A compra está sem data e sem km.");
  });

  it("período alternativo aparece identificado", async () => {
    apiFalsa(rotas({ ...CUSTO, custo_por_km: {
      ...POR_KM, base: "primeira_leitura", aviso_base: "A compra está sem o km.", inicio: "2025-10-01",
      km_inicio: 80000, distancia: 5000, valor: "0.07" } }));
    renderizarApp("/veiculos/7");
    const km = await screen.findByRole("region", { name: "Custo por quilômetro" });
    expect(km.textContent).toContain(
      "5.000 km rodados de 01/10/2025 a 20/09/2026, desde a primeira leitura de quilometragem registrada");
    expect(km.textContent).toContain("A compra está sem o km.");
  });
});

// ------------------------------------------------------------------ histórico

function evento(tipo: EventoHistorico["tipo"], extra: Partial<EventoHistorico>): EventoHistorico {
  return {
    tipo, origem_id: 1, data: "2026-09-20", descricao: "", valor: null, quilometragem: null, sistema: null,
    oficina: null, posto: null, combustivel: null, quantidade: null, categoria: null, descricao_gasto: null,
    projeto_id: null, projeto_nome: null, item_descricao: null, situacao: null, gravidade: null, ...extra,
  };
}

const EVENTOS: EventoHistorico[] = [
  evento("manutencao", { origem_id: 5, descricao: "Troca de óleo", valor: "350.00", quilometragem: 85000 }),
  evento("abastecimento", { origem_id: 9, valor: "250.00", posto: "Shell", combustivel: "gasolina", quantidade: "40.000" }),
  evento("diagnostico", { origem_id: 3, data: "2026-09-18", descricao: "Barulho na suspensão", situacao: "aberto" }),
  evento("gasto", { origem_id: 4, data: "2026-09-18", valor: "30.00", categoria: "estacionamento" }),
  evento("projeto", { origem_id: 11, data: "2026-08-15", valor: "450.00", projeto_id: 2, projeto_nome: "Insulfilm",
    item_descricao: "Película" }),
];

function paginaHistorico(itens: EventoHistorico[], extra: Partial<PaginaHistorico> = {}): Response {
  const corpo: PaginaHistorico = {
    itens, total: itens.length, pagina: 1, por_pagina: 50, periodo: "12_meses", ano: null,
    inicio: "2025-10-01", fim: "2026-09-30",
    meses: [{ ano: 2026, mes: 9, total: "630.00", quantidade: 3 }, { ano: 2026, mes: 8, total: "450.00", quantidade: 1 }],
    anos_disponiveis: [2026, 2025], ...extra,
  };
  return json(200, corpo);
}

const HISTORICO = "GET /api/veiculos/7/historico?periodo=12_meses&pagina=1&por_pagina=50";

describe("Histórico", () => {
  it("agrupa por mês com o total do mês e mostra diagnóstico sem valor", async () => {
    apiFalsa({ ...base(PAINEL), [HISTORICO]: () => paginaHistorico(EVENTOS) });
    renderizarApp("/historico");
    const setembro = await screen.findByRole("region", { name: "Setembro de 2026" });
    expect(within(setembro).getByRole("heading").textContent).toBe("Setembro de 2026R$ 630,00");
    const itens = within(setembro).getAllByRole("listitem");
    expect(itens.map((i) => i.textContent)).toEqual([
      "20setTroca de óleoManutenção, 85.000 kmR$ 350,00",
      "20setAbastecimentoShell, 40,0 L de gasolinaR$ 250,00",
      "18setBarulho na suspensãoProblema registrado, abertosem valor",
      "18setEstacionamentoGasto avulsoR$ 30,00",
    ]);
    expect(within(itens[0]).getByRole("link")).toHaveAttribute("href", "/veiculos/7/manutencoes/5");
    expect(within(itens[2]).getByRole("link")).toHaveAttribute("href", "/veiculos/7/diagnosticos/3");
    const agosto = screen.getByRole("region", { name: "Agosto de 2026" });
    expect(within(agosto).getByRole("link")).toHaveAttribute("href", "/veiculos/7/projetos/2");
    expect(screen.getByText("01/10/2025 a 30/09/2026")).toBeInTheDocument();
  });

  it("filtro por tipo e período vão para o backend", async () => {
    const buscar = apiFalsa({
      ...base(PAINEL),
      [HISTORICO]: () => paginaHistorico(EVENTOS),
      "GET /api/veiculos/7/historico?periodo=12_meses&pagina=1&por_pagina=50&tipo=abastecimento": () =>
        paginaHistorico([EVENTOS[1]]),
      "GET /api/veiculos/7/historico?periodo=ano&pagina=1&por_pagina=50&tipo=abastecimento&ano=2025": () =>
        paginaHistorico([], { periodo: "ano", ano: 2025, inicio: "2025-01-01", fim: "2025-12-31", meses: [] }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/historico");
    await screen.findByRole("region", { name: "Setembro de 2026" });
    await usuario.click(screen.getByRole("button", { name: "Combustível" }));
    expect(await screen.findByText("Shell, 40,0 L de gasolina")).toBeInTheDocument();
    await usuario.selectOptions(screen.getByLabelText("Período"), "2025");
    expect(await screen.findByText("Nada registrado neste período")).toBeInTheDocument();
    expect(chamadasPara(buscar,
      "GET /api/veiculos/7/historico?periodo=ano&pagina=1&por_pagina=50&tipo=abastecimento&ano=2025")).toHaveLength(1);
  });

  it("veículo de outra pessoa responde não encontrado", async () => {
    apiFalsa({ ...base(PAINEL), "GET /api/veiculos/99": () => json(404, { mensagem: "Veículo não encontrado." }) });
    renderizarApp("/veiculos/99/historico");
    expect(await screen.findByText("Veículo não encontrado.")).toBeInTheDocument();
  });

  it("textos do PDF para cada tipo", () => {
    expect(textosDoEvento(evento("abastecimento", { posto: "Ipiranga", combustivel: "etanol", quantidade: "38.500" })))
      .toEqual({ titulo: "Abastecimento", detalhe: "Ipiranga, 38,5 L de etanol" });
    expect(textosDoEvento(evento("abastecimento", { combustivel: "eletrica", quantidade: "40.000" })))
      .toEqual({ titulo: "Recarga", detalhe: "40,0 kWh de eletricidade" });
    expect(textosDoEvento(evento("gasto", { categoria: "ipva", descricao_gasto: "Parcela 1" })))
      .toEqual({ titulo: "IPVA", detalhe: "Parcela 1" });
    expect(textosDoEvento(evento("projeto", { projeto_nome: "Rodas", item_descricao: "Jogo aro 17" })))
      .toEqual({ titulo: "Rodas", detalhe: "Projeto: Jogo aro 17" });
  });
});
