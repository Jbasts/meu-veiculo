// Fluxos de manutenção nas telas (pendentes, planos, manutenções e fotos ligadas),
// com a API simulada.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import {
  progressoDoPlano,
  resumoDoPrazo,
  textoIntervalo,
  textoPrevisao,
  type ManutencaoDetalhe,
  type Pendencia,
  type Plano,
} from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};

function pendencia(alteracoes: Partial<Pendencia>): Pendencia {
  return {
    tipo: "plano", situacao: "em_dia", titulo: "Troca de óleo", sistema: "motor", plano_id: 1,
    manutencao_id: null, proxima_data: null, proxima_km: 90000, dias_restantes: null,
    km_restantes: 5000, intervalo_km: 10000, intervalo_meses: null, agendada_id: null,
    agendada_data: null, ...alteracoes,
  };
}

const PLANO: Plano = {
  id: 1, veiculo_id: 7, nome: "Troca de óleo", sistema: "motor", intervalo_km: 10000,
  intervalo_meses: null, data_base: null, km_base: 80000, ativo: true,
  criado_em: "2026-09-01T10:00:00-03:00", situacao: "em_dia", referencia_data: null,
  referencia_km: 80000, proxima_data: null, proxima_km: 90000, dias_restantes: null,
  km_restantes: 5000,
};

const MANUTENCAO: ManutencaoDetalhe = {
  id: 12, veiculo_id: 7, plano_id: null, descricao: "Troca das bieletas", sistema: "suspensao",
  status: "realizada", data: "2026-09-24", quilometragem: 85000, valor: "280.00",
  oficina: "Oficina do Zé", garantia_ate: "2026-12-24", garantia_km: null, proxima_data: null,
  proxima_km: null, observacao: null, criado_em: "2026-09-24T10:00:00-03:00", plano_nome: null,
  garantia_situacao: "vigente", garantia_explicacao: "Em garantia até 24/12/2026.", total_fotos: 0,
  itens: [], total_pecas: null, total_mao_de_obra: null, diagnosticos: [],
};

/** O exemplo da Paula: 70 + 45 de peças, 20 + 30 de mão de obra. */
const DETALHADA: ManutencaoDetalhe = {
  ...MANUTENCAO, descricao: "Troca dos filtros", valor: "165.00",
  itens: [
    { id: 1, tipo: "peca", nome: "Filtro de óleo", valor: "70.00" },
    { id: 2, tipo: "peca", nome: "Filtro de ar", valor: "45.00" },
    { id: 3, tipo: "mao_de_obra", nome: "Troca do filtro de óleo", valor: "20.00" },
    { id: 4, tipo: "mao_de_obra", nome: "Troca do filtro de ar", valor: "30.00" },
  ],
  total_pecas: "115.00", total_mao_de_obra: "50.00",
};

const PENDENTES = "GET /api/veiculos/7/manutencoes/pendentes";
const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  [PENDENTES]: () => json(200, { km_atual: 85000, itens: [] }),
  "GET /api/veiculos/7/planos": () => json(200, [PLANO]),
  // Início: nenhum diagnóstico em aberto.
  "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=5": () => json(200, {
    itens: [], total: 0, pagina: 1, por_pagina: 5 }),
};

function corpoJson(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return JSON.parse(opcoes.body as string);
}

describe("textos dos prazos", () => {
  it("descreve intervalo e previsão", () => {
    expect(textoIntervalo({ intervalo_km: 10000, intervalo_meses: 12 })).toBe("A cada 10.000 km ou 12 meses");
    expect(textoIntervalo({ intervalo_km: null, intervalo_meses: 1 })).toBe("A cada 1 mês");
    expect(textoPrevisao({ proxima_km: 86000, proxima_data: "2026-10-15" })).toBe(
      "aos 86.000 km ou em 15/10/2026");
  });

  it("destaca o atraso, o limite mais perto ou a falta de base", () => {
    expect(resumoDoPrazo(pendencia({ situacao: "atrasada", dias_restantes: -23, km_restantes: null })))
      .toEqual({ valor: "23 dias", rotulo: "de atraso" });
    expect(resumoDoPrazo(pendencia({ situacao: "atrasada", dias_restantes: 40, km_restantes: -300 })))
      .toEqual({ valor: "300 km", rotulo: "além do limite" });
    expect(resumoDoPrazo(pendencia({ situacao: "proxima", km_restantes: 1000 })))
      .toEqual({ valor: "1.000 km", rotulo: "restantes" });
    expect(resumoDoPrazo(pendencia({ situacao: "proxima", dias_restantes: 21, km_restantes: 9000 })))
      .toEqual({ valor: "21 dias", rotulo: "restantes" });
    // Desconhecido não vira zero.
    expect(resumoDoPrazo(pendencia({ situacao: "sem_base", km_restantes: null, proxima_km: null })).valor)
      .toBe("Sem base");
  });

  it("calcula a barra de progresso só com dados conhecidos", () => {
    expect(progressoDoPlano(pendencia({ km_restantes: 5000 }))).toBe(0.5);
    expect(progressoDoPlano(pendencia({ km_restantes: -200 }))).toBe(1);
    expect(progressoDoPlano(pendencia({ km_restantes: null }))).toBeNull();
  });
});

describe("Manutenção: abas", () => {
  it("agrupa as pendências por situação e mostra cada obrigação uma vez", async () => {
    apiFalsa({
      ...BASE,
      [PENDENTES]: () => json(200, { km_atual: 85000, itens: [
        pendencia({ situacao: "atrasada", titulo: "Revisão geral", plano_id: 2, intervalo_km: null,
          intervalo_meses: 12, proxima_km: null, km_restantes: null, proxima_data: "2026-09-01",
          dias_restantes: -23 }),
        pendencia({ situacao: "proxima", titulo: "Filtro de ar", plano_id: 3, proxima_km: 86000,
          km_restantes: 1000, agendada_id: 40, agendada_data: "2026-10-02" }),
        pendencia({ tipo: "agendada", situacao: "proxima", titulo: "Alinhamento", plano_id: null,
          manutencao_id: 41, proxima_km: null, km_restantes: null, proxima_data: "2026-10-05",
          dias_restantes: 5, intervalo_km: null }),
        pendencia({ situacao: "sem_base", titulo: "Correia dentada", plano_id: 4, proxima_km: null,
          km_restantes: null }),
        pendencia({}),
      ] }),
    });
    renderizarApp("/manutencao");

    const atrasada = await screen.findByRole("region", { name: "Atrasada" });
    expect(within(atrasada).getByText("Revisão geral")).toBeInTheDocument();
    expect(within(atrasada).getByText("23 dias")).toBeInTheDocument();
    expect(within(atrasada).getByText("de atraso")).toBeInTheDocument();

    const proximas = screen.getByRole("region", { name: "Próximas" });
    expect(within(proximas).getByText("1.000 km")).toBeInTheDocument();
    // O plano com manutenção agendada aparece uma vez, com a data dentro do item;
    // "Registrar" conclui essa agendada em vez de criar outra.
    expect(within(proximas).getAllByText("Filtro de ar")).toHaveLength(1);
    expect(within(proximas).getByRole("link", { name: "Agendada para 02/10/2026" }))
      .toHaveAttribute("href", "/veiculos/7/manutencoes/40");
    expect(within(proximas).getByRole("link", { name: "Registrar Filtro de ar" }))
      .toHaveAttribute("href", "/veiculos/7/manutencoes/40/editar?concluir=1");
    expect(within(proximas).getByText("Agendada para 05/10/2026")).toBeInTheDocument();

    const semBase = screen.getByRole("region", { name: "Dados insuficientes" });
    expect(within(semBase).getByText("Sem base")).toBeInTheDocument();
    expect(within(semBase).queryByText("restantes")).not.toBeInTheDocument();

    const emDia = screen.getByRole("region", { name: "Em dia" });
    expect(within(emDia).getByRole("link", { name: "Registrar Troca de óleo" }))
      .toHaveAttribute("href", "/veiculos/7/manutencoes/nova?plano=1");
  });

  it("sem pendências, explica como criar", async () => {
    apiFalsa(BASE);
    renderizarApp("/manutencao");
    expect(await screen.findByText("Nenhuma pendência")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Nova manutenção" }))
      .toHaveAttribute("href", "/veiculos/7/manutencoes/nova");
  });

  it("troca de aba: realizadas com valores e planos com situação", async () => {
    apiFalsa({
      ...BASE,
      "GET /api/veiculos/7/manutencoes?status=realizada&pagina=1&por_pagina=20": () => json(200, {
        itens: [MANUTENCAO], total: 1, pagina: 1, por_pagina: 20,
      }),
      "GET /api/veiculos/7/planos": () => json(200, [
        PLANO, { ...PLANO, id: 5, nome: "Velas", ativo: false, situacao: null },
      ]),
    });
    renderizarApp("/manutencao");
    await userEvent.click(await screen.findByRole("tab", { name: "Realizadas" }));
    const realizadas = await screen.findByRole("list", { name: "Manutenções realizadas" });
    expect(within(realizadas).getByText("Troca das bieletas")).toBeInTheDocument();
    expect(within(realizadas).getByText("R$ 280,00")).toBeInTheDocument();
    expect(within(realizadas).getByText(/24\/09\/2026 · 85\.000 km · Suspensão/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("tab", { name: "Planos" }));
    const planos = await screen.findByRole("list", { name: "Planos de manutenção" });
    expect(within(planos).getAllByText("A cada 10.000 km · Motor")).toHaveLength(2);
    expect(within(planos).getByText("Em dia")).toBeInTheDocument();
    expect(within(planos).getByText("Inativo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Novo plano" })).toHaveAttribute("href", "/veiculos/7/planos/novo");
  });

  it("sem veículo em uso, orienta a cadastrar", async () => {
    apiFalsa({ "GET /api/auth/eu": () => json(200, PAULA) });
    renderizarApp("/manutencao");
    expect(await screen.findByText("Nenhum veículo em uso")).toBeInTheDocument();
  });

  it("o Início mostra as manutenções atrasadas e próximas", async () => {
    apiFalsa({
      ...BASE,
      [PENDENTES]: () => json(200, { km_atual: 85000, itens: [
        pendencia({ situacao: "atrasada", titulo: "Revisão geral", plano_id: 2, km_restantes: -500 }),
        pendencia({}),
      ] }),
    });
    renderizarApp("/");
    const atencao = await screen.findByRole("region", { name: "Precisa de atenção" });
    expect(within(atencao).getByText("Revisão geral")).toBeInTheDocument();
    expect(within(atencao).getByText("Atrasada: 500 km além do limite")).toBeInTheDocument();
    expect(within(atencao).queryByText("Troca de óleo")).not.toBeInTheDocument();  // em dia não alerta
  });
});

describe("Nova manutenção", () => {
  it("registra uma manutenção realizada com garantia por km como limite do hodômetro", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/manutencoes": () => json(201, MANUTENCAO),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Troca das bieletas");
    await userEvent.selectOptions(screen.getByLabelText("Sistema"), "suspensao");
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85000");
    await userEvent.type(screen.getByLabelText("Valor total (R$)"), "280");
    await userEvent.type(screen.getByLabelText("Ou até (km)"), "95000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));

    expect(await screen.findByText("Manutenção registrada.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/manutencoes")).toEqual({
      descricao: "Troca das bieletas", sistema: "suspensao", status: "realizada", data: hojeIso(),
      quilometragem: 85000, valor: "280.00", oficina: null, plano_id: null, garantia_ate: null,
      garantia_km: 95000, proxima_data: null, proxima_km: null, observacao: null, itens: [],
    });
  });

  it("valida garantia menor que a quilometragem e data futura", async () => {
    const buscar = apiFalsa(BASE);
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Pneus");
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85000");
    await userEvent.type(screen.getByLabelText("Ou até (km)"), "10000");
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2999-01-01" } });
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(screen.getByText(/quilometragem limite da garantia/)).toBeInTheDocument();
    expect(screen.getByText(/não pode ter data no futuro/)).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/manutencoes")).toHaveLength(0);
  });

  it("vinda de um plano, já chega preenchida e exige quilometragem", async () => {
    const buscar = apiFalsa({ ...BASE,
      "POST /api/veiculos/7/manutencoes": () => json(201, { ...MANUTENCAO, plano_id: 1 }),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/manutencoes/nova?plano=1");
    expect(await screen.findByLabelText("Descrição")).toHaveValue("Troca de óleo");
    expect(screen.getByLabelText("Sistema")).toHaveValue("motor");
    expect(screen.getByLabelText("Plano de manutenção")).toHaveValue("1");
    // Em manutenção de plano não há lembrete manual: a próxima vem do plano.
    expect(screen.queryByLabelText("Próxima em")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(screen.getByText(/o plano conta o prazo em quilômetros/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85200");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    await waitFor(() => expect(chamadasPara(buscar, "POST /api/veiculos/7/manutencoes")).toHaveLength(1));
    expect(corpoJson(buscar, "POST /api/veiculos/7/manutencoes")).toMatchObject({
      plano_id: 1, quilometragem: 85200, status: "realizada" });
  });

  it("agendar esconde garantia e lembrete e envia sem eles", async () => {
    const agendada = { ...MANUTENCAO, status: "agendada", garantia_ate: null,
      garantia_situacao: "nao_se_aplica" };
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/manutencoes": () => json(201, agendada),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, agendada) });
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Alinhamento");
    await userEvent.type(screen.getByLabelText("Ou até (km)"), "99000");
    await userEvent.click(screen.getByRole("radio", { name: "Agendar" }));
    expect(screen.queryByLabelText("Garantia até")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Próxima em")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Valor total estimado (R$)")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2999-01-01" } });
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(await screen.findByText("Manutenção agendada.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/manutencoes")).toMatchObject({
      status: "agendada", data: "2999-01-01", garantia_km: null, garantia_ate: null, valor: null });
  });

  it("mostra no campo o erro do servidor (plano de outro veículo)", async () => {
    const mensagem = "Plano não encontrado neste veículo.";
    apiFalsa({ ...BASE,
      "POST /api/veiculos/7/manutencoes": () => json(422, { mensagem, campos: { plano_id: mensagem } }) });
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Óleo");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    await waitFor(() =>
      expect(screen.getByLabelText("Plano de manutenção")).toHaveAttribute("aria-invalid", "true"));
  });
});

describe("Peças e mão de obra no formulário", () => {
  async function preencher(rotulo: string, texto: string) {
    await userEvent.type(screen.getByLabelText(rotulo), texto);
  }

  it("adiciona uma a uma, mostra subtotais e total e envia os itens sem total", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/manutencoes": () => json(201, DETALHADA),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, DETALHADA) });
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Troca dos filtros");
    expect(screen.getByLabelText("Valor total (R$)")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 1", "Filtro de óleo");
    await preencher("Valor da peça 1", "70,00");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 2", "Filtro de ar");
    await preencher("Valor da peça 2", "45");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar mão de obra" }));
    await preencher("Mão de obra 1", "Troca do filtro de óleo");
    await preencher("Valor da mão de obra 1", "20,00");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar mão de obra" }));
    await preencher("Mão de obra 2", "Troca do filtro de ar");
    await preencher("Valor da mão de obra 2", "30,00");

    // Com itens, o total manual some: o total é a soma.
    expect(screen.queryByLabelText("Valor total (R$)")).not.toBeInTheDocument();
    const resumo = screen.getByRole("list", { name: "Resumo dos valores" });
    expect(within(resumo).getByText("Total de peças").nextSibling).toHaveTextContent("R$ 115,00");
    expect(within(resumo).getByText("Total de mão de obra").nextSibling).toHaveTextContent("R$ 50,00");
    expect(within(resumo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 165,00");

    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(await screen.findByText("Manutenção registrada.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/manutencoes")).toMatchObject({
      valor: null,
      itens: [
        { tipo: "peca", nome: "Filtro de óleo", valor: "70.00" },
        { tipo: "peca", nome: "Filtro de ar", valor: "45.00" },
        { tipo: "mao_de_obra", nome: "Troca do filtro de óleo", valor: "20.00" },
        { tipo: "mao_de_obra", nome: "Troca do filtro de ar", valor: "30.00" },
      ],
    });
  });

  it("remove uma linha e recalcula; sem itens, o valor manual volta", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.click(await screen.findByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 1", "Arruela");
    await preencher("Valor da peça 1", "0,10");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 2", "Anel");
    await preencher("Valor da peça 2", "0,20");
    const resumo = screen.getByRole("list", { name: "Resumo dos valores" });
    expect(within(resumo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 0,30");

    await userEvent.click(screen.getByRole("button", { name: "Remover peça 1" }));
    expect(screen.getByLabelText("Peça 1")).toHaveValue("Anel");
    expect(within(resumo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 0,20");

    await userEvent.click(screen.getByRole("button", { name: "Remover peça 1" }));
    expect(screen.queryByRole("list", { name: "Resumo dos valores" })).not.toBeInTheDocument();
    expect(screen.getByLabelText("Valor total (R$)")).toBeInTheDocument();
  });

  it("não envia item sem nome ou com valor inválido", async () => {
    const buscar = apiFalsa(BASE);
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Freios");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Valor da peça 1", "abc");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar mão de obra" }));
    await preencher("Mão de obra 1", "Troca das pastilhas");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(screen.getByLabelText("Peça 1")).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByText("Valor inválido. Exemplo: 70,00.")).toBeInTheDocument();
    expect(screen.getByText("Informe o valor.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/manutencoes")).toHaveLength(0);
  });

  it("mostra na linha certa o erro que o servidor devolve para um item", async () => {
    const mensagem = "Use no máximo duas casas decimais (centavos).";
    apiFalsa({ ...BASE, "POST /api/veiculos/7/manutencoes": () => json(422, {
      mensagem: "Confira os dados enviados.", campos: { "itens.1.valor": mensagem } }) });
    renderizarApp("/veiculos/7/manutencoes/nova");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Filtros");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 1", "Filtro de óleo");
    await preencher("Valor da peça 1", "70");
    await userEvent.click(screen.getByRole("button", { name: "+ Adicionar mão de obra" }));
    await preencher("Mão de obra 1", "Troca");
    await preencher("Valor da mão de obra 1", "20");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    await waitFor(() => expect(screen.getByLabelText("Valor da mão de obra 1"))
      .toHaveAttribute("aria-invalid", "true"));
    expect(screen.getByLabelText("Valor da peça 1")).not.toHaveAttribute("aria-invalid");
  });

  it("na edição, carrega os itens e envia a lista inteira", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes/12": () => json(200, DETALHADA),
      "PUT /api/veiculos/7/manutencoes/12": () => json(200, DETALHADA) });
    renderizarApp("/veiculos/7/manutencoes/12/editar");
    expect(await screen.findByLabelText("Peça 2")).toHaveValue("Filtro de ar");
    expect(screen.getByLabelText("Valor da mão de obra 1")).toHaveValue("20,00");
    expect(screen.queryByLabelText("Valor total (R$)")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Remover mão de obra 2" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    await waitFor(() => expect(chamadasPara(buscar, "PUT /api/veiculos/7/manutencoes/12")).toHaveLength(1));
    const corpo = corpoJson(buscar, "PUT /api/veiculos/7/manutencoes/12");
    expect(corpo.valor).toBeNull();
    expect(corpo.itens.map((i: { nome: string }) => i.nome)).toEqual([
      "Filtro de óleo", "Filtro de ar", "Troca do filtro de óleo"]);
  });

  it("agendada mostra os valores como estimados", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/manutencoes/nova?status=agendada");
    await userEvent.click(await screen.findByRole("button", { name: "+ Adicionar peça" }));
    await preencher("Peça 1", "Pneu");
    await preencher("Valor da peça 1", "450");
    const resumo = screen.getByRole("list", { name: "Resumo dos valores" });
    expect(within(resumo).getByText("Valor estimado das peças")).toBeInTheDocument();
    expect(within(resumo).getByText("Valor estimado da mão de obra")).toBeInTheDocument();
    expect(within(resumo).getByText("Total estimado").nextSibling).toHaveTextContent("R$ 450,00");
  });
});

describe("Popup \"Ver valores\"", () => {
  it("no detalhe, mostra cada peça e mão de obra com subtotais e total", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/manutencoes/12": () => json(200, DETALHADA) });
    renderizarApp("/veiculos/7/manutencoes/12");
    await userEvent.click(await screen.findByRole("button", { name: "Ver valores" }));
    const dialogo = screen.getByRole("dialog", { name: "Valores" });

    const pecas = within(dialogo).getByRole("region", { name: "Peças" });
    expect(within(pecas).getByText("Filtro de óleo").nextSibling).toHaveTextContent("R$ 70,00");
    expect(within(pecas).getByText("Filtro de ar").nextSibling).toHaveTextContent("R$ 45,00");
    expect(within(pecas).getByText("Total de peças").nextSibling).toHaveTextContent("R$ 115,00");

    const maoDeObra = within(dialogo).getByRole("region", { name: "Mão de obra" });
    expect(within(maoDeObra).getByText("Troca do filtro de óleo").nextSibling).toHaveTextContent("R$ 20,00");
    expect(within(maoDeObra).getByText("Total de mão de obra").nextSibling).toHaveTextContent("R$ 50,00");

    expect(within(dialogo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 165,00");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Fechar" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("sem itens, avisa que só existe o valor total", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/manutencoes/12");
    await userEvent.click(await screen.findByRole("button", { name: "Ver valores" }));
    const dialogo = screen.getByRole("dialog", { name: "Valores" });
    expect(within(dialogo).getByText(/só o valor total, sem detalhamento/)).toBeInTheDocument();
    expect(within(dialogo).queryByRole("region", { name: "Peças" })).not.toBeInTheDocument();
    expect(within(dialogo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 280,00");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("agendada mostra valores estimados", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/manutencoes/12": () => json(200, {
      ...DETALHADA, status: "agendada", garantia_situacao: "nao_se_aplica" }) });
    renderizarApp("/veiculos/7/manutencoes/12");
    await userEvent.click(await screen.findByRole("button", { name: "Ver valores" }));
    const dialogo = screen.getByRole("dialog", { name: "Valores" });
    expect(within(dialogo).getByText("Valor estimado das peças")).toBeInTheDocument();
    expect(within(dialogo).getByText("Valor estimado da mão de obra")).toBeInTheDocument();
    expect(within(dialogo).getByText("Total estimado").nextSibling).toHaveTextContent("R$ 165,00");
  });

  it("na aba Realizadas, cada manutenção abre os próprios valores", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes?status=realizada&pagina=1&por_pagina=20": () => json(200, {
        itens: [DETALHADA, { ...MANUTENCAO, id: 13 }], total: 2, pagina: 1, por_pagina: 20 }),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, DETALHADA) });
    renderizarApp("/manutencao?aba=realizadas");
    await userEvent.click(await screen.findByRole("button", { name: "Ver valores de Troca dos filtros" }));
    const dialogo = await screen.findByRole("dialog", { name: "Valores" });
    expect(await within(dialogo).findByText("Filtro de ar")).toBeInTheDocument();
    expect(within(dialogo).getByText("Total da manutenção").nextSibling).toHaveTextContent("R$ 165,00");
    expect(chamadasPara(buscar, "GET /api/veiculos/7/manutencoes/12")).toHaveLength(1);
    expect(chamadasPara(buscar, "GET /api/veiculos/7/manutencoes/13")).toHaveLength(0);
  });
});

describe("Manutenção: detalhe, conclusão e exclusão", () => {
  const AGENDADA: ManutencaoDetalhe = {
    ...MANUTENCAO, status: "agendada", data: "2999-01-01", garantia_ate: null,
    garantia_situacao: "nao_se_aplica", garantia_explicacao: "Manutenção ainda não realizada.",
  };

  it("mostra a garantia com a explicação e não afirma garantia sem informação", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/manutencoes/12");
    expect(await screen.findByRole("heading", { name: "Troca das bieletas" })).toBeInTheDocument();
    const garantia = screen.getByRole("region", { name: "Garantia" });
    expect(within(garantia).getByText("Vigente")).toBeInTheDocument();
    expect(within(garantia).getByText("Em garantia até 24/12/2026.")).toBeInTheDocument();
    expect(screen.getByText("R$ 280,00")).toBeInTheDocument();
    expect(screen.getByText("Manutenção avulsa")).toBeInTheDocument();
  });

  it("sem dados de garantia, diz 'sem informação'", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/manutencoes/12": () => json(200, {
      ...MANUTENCAO, garantia_ate: null, garantia_situacao: "sem_informacao",
      garantia_explicacao: "Sem informação de garantia." }) });
    renderizarApp("/veiculos/7/manutencoes/12");
    const garantia = await screen.findByRole("region", { name: "Garantia" });
    expect(within(garantia).getByText("Sem informação")).toBeInTheDocument();
    expect(within(garantia).queryByText("Vigente")).not.toBeInTheDocument();
  });

  it("marcar como realizada abre o formulário já com o status trocado e a data de hoje", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes/12": () => json(200, AGENDADA),
      "PUT /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/manutencoes/12");
    await userEvent.click(await screen.findByRole("link", { name: "Marcar como realizada" }));
    expect(await screen.findByRole("radio", { name: "Já foi feita" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByLabelText("Data")).toHaveValue(hojeIso());
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    await waitFor(() => expect(chamadasPara(buscar, "PUT /api/veiculos/7/manutencoes/12")).toHaveLength(1));
    expect(corpoJson(buscar, "PUT /api/veiculos/7/manutencoes/12")).toMatchObject({
      status: "realizada", data: hojeIso(), descricao: "Troca das bieletas", valor: "280.00" });
  });

  it("apaga só depois de confirmar, avisando das fotos ligadas", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes/12": () => json(200, { ...MANUTENCAO, total_fotos: 2 }),
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&manutencao_id=12": () => json(200, {
        itens: [], total: 0, pagina: 1, por_pagina: 30 }),
      "DELETE /api/veiculos/7/manutencoes/12": () => json(204, null),
      "GET /api/veiculos/7/manutencoes?status=realizada&pagina=1&por_pagina=20": () => json(200, {
        itens: [], total: 0, pagina: 1, por_pagina: 20 }),
    });
    renderizarApp("/veiculos/7/manutencoes/12");
    await userEvent.click(await screen.findByRole("button", { name: "Apagar manutenção" }));
    const dialogo = screen.getByRole("alertdialog");
    expect(within(dialogo).getByText(/as 2 fotos ligadas/)).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/manutencoes/12")).toHaveLength(0);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Manutenção apagada.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/manutencoes/12")).toHaveLength(1);
  });
});

describe("Planos", () => {
  it("cria um plano sugerindo contar a partir de hoje e da quilometragem atual", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/planos": () => json(201, PLANO) });
    renderizarApp("/veiculos/7/planos/novo");
    await userEvent.type(await screen.findByLabelText("Nome"), "Revisão geral");
    await userEvent.type(screen.getByLabelText("Quilômetros"), "10000");
    await userEvent.type(screen.getByLabelText("Meses"), "12");
    expect(screen.getByLabelText("Quilometragem")).toHaveValue("85.000");
    expect(screen.getByLabelText("Data")).toHaveValue(hojeIso());
    await userEvent.clear(screen.getByLabelText("Quilometragem"));
    await userEvent.type(screen.getByLabelText("Quilometragem"), "80000");
    await userEvent.click(screen.getByRole("button", { name: "Criar plano" }));
    expect(await screen.findByText("Plano criado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/planos")).toEqual({
      nome: "Revisão geral", sistema: "outros", intervalo_km: 10000, intervalo_meses: 12,
      data_base: hojeIso(), km_base: 80000,
    });
  });

  it("exige um intervalo e uma base coerente; base do intervalo não usado não é enviada", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/planos": () => json(201, PLANO) });
    renderizarApp("/veiculos/7/planos/novo");
    await userEvent.type(await screen.findByLabelText("Nome"), "Fluido de freio");
    await userEvent.click(screen.getByRole("button", { name: "Criar plano" }));
    expect(screen.getByText("Informe o intervalo em quilômetros, em meses ou os dois.")).toBeInTheDocument();
    expect(screen.queryByLabelText("Quilometragem")).not.toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Meses"), "24");
    expect(screen.queryByLabelText("Quilometragem")).not.toBeInTheDocument();  // só a base de data
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2999-01-01" } });
    await userEvent.click(screen.getByRole("button", { name: "Criar plano" }));
    expect(screen.getByText("A data não pode ser no futuro.")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Data"), { target: { value: "2026-01-10" } });
    await userEvent.click(screen.getByRole("button", { name: "Criar plano" }));
    await waitFor(() => expect(chamadasPara(buscar, "POST /api/veiculos/7/planos")).toHaveLength(1));
    expect(corpoJson(buscar, "POST /api/veiculos/7/planos")).toMatchObject({
      intervalo_km: null, intervalo_meses: 24, data_base: "2026-01-10", km_base: null });
  });

  it("plano antigo sem base pede a informação e permite corrigir", async () => {
    const semBase: Plano = { ...PLANO, km_base: null, situacao: "sem_base", referencia_km: null,
      proxima_km: null, km_restantes: null };
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/planos/1": () => json(200, semBase),
      "PUT /api/veiculos/7/planos/1": () => json(200, PLANO) });
    renderizarApp("/veiculos/7/planos/1");
    expect(await screen.findByText("Dados insuficientes")).toBeInTheDocument();
    expect(screen.getByText(/Falta informar quando foi feita pela última vez/)).toBeInTheDocument();
    expect(screen.getByLabelText("Quilometragem")).toHaveValue("");
    await userEvent.type(screen.getByLabelText("Quilometragem"), "80000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    expect(corpoJson(buscar, "PUT /api/veiculos/7/planos/1")).toMatchObject({ km_base: 80000 });
    expect(await screen.findByText("Em dia")).toBeInTheDocument();
  });

  it("desativa e apaga o plano com confirmação", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/planos/1": () => json(200, PLANO),
      "POST /api/veiculos/7/planos/1/desativar": () => json(200, { ...PLANO, ativo: false, situacao: null }),
      "DELETE /api/veiculos/7/planos/1": () => json(204, null),
      "GET /api/veiculos/7/planos": () => json(200, []) });
    renderizarApp("/veiculos/7/planos/1");
    await userEvent.click(await screen.findByRole("button", { name: "Desativar plano" }));
    expect(await screen.findByText("Plano desativado.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reativar plano" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Apagar plano" }));
    expect(screen.getByText(/continuam no\s+histórico, como avulsas/)).toBeInTheDocument();
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Plano apagado.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/planos/1")).toHaveLength(1);
  });
});

describe("Fotos ligadas a manutenção", () => {
  it("aberta a partir da manutenção, a foto já vai ligada a ela", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes?pagina=1&por_pagina=100": () => json(200, {
        itens: [MANUTENCAO], total: 1, pagina: 1, por_pagina: 100 }),
      "POST /api/veiculos/7/fotos": () => json(201, { id: 9 }),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, MANUTENCAO) });
    renderizarApp("/veiculos/7/fotos/nova?manutencao=12");
    expect(await screen.findByRole("radio", { name: "Manutenção" })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByLabelText("Manutenção")).toHaveValue("12");
    expect(screen.getByRole("option", { name: "Troca das bieletas (24/09/2026)" })).toBeInTheDocument();
    const arquivo = new File([new Uint8Array(2048)], "nota.jpg", { type: "image/jpeg" });
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"), arquivo);
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(await screen.findByRole("heading", { name: "Troca das bieletas" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/veiculos/7/fotos");
    expect((opcoes.body as FormData).get("manutencao_id")).toBe("12");
  });

  it("escolher ligar a uma manutenção sem dizer qual é recusado na tela", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes?pagina=1&por_pagina=100": () => json(200, {
        itens: [MANUTENCAO], total: 1, pagina: 1, por_pagina: 100 }) });
    renderizarApp("/veiculos/7/fotos/nova");
    await userEvent.click(await screen.findByRole("radio", { name: "Manutenção" }));
    await screen.findByLabelText("Manutenção");
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"),
      new File([new Uint8Array(2048)], "nota.jpg", { type: "image/jpeg" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(screen.getByText("Escolha a manutenção.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/fotos")).toHaveLength(0);
  });

  it("a galeria filtra pelas fotos de manutenção", async () => {
    const foto = { id: 5, veiculo_id: 7, tipo_mime: "image/jpeg", tamanho_bytes: 2048, legenda: "Nota",
      data_foto: "2026-09-24", principal: false, projeto_id: null, momento: null, diagnostico_id: null,
      manutencao_id: 12, criado_em: "2026-09-24T10:00:00-03:00" };
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30": () => json(200, {
        itens: [foto, { ...foto, id: 6, legenda: "Frente", manutencao_id: null }], total: 2, pagina: 1, por_pagina: 30 }),
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=manutencao": () => json(200, {
        itens: [foto], total: 1, pagina: 1, por_pagina: 30 }) });
    renderizarApp("/veiculos/7/fotos");
    expect(await screen.findByText("2 fotos")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Manutenções" }));
    expect(await screen.findByText("1 foto")).toBeInTheDocument();
    expect(screen.queryByAltText("Frente")).not.toBeInTheDocument();
    expect(chamadasPara(buscar, "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=manutencao")).toHaveLength(1);
  });
});
