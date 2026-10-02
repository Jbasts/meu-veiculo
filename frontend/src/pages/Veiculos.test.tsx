// Fluxos de veículos, quilometragem e fotos nas telas, com a API simulada.

import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { Foto, LeituraKm, Veiculo } from "../types/veiculo";
import { hojeIso, mesDaData } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};

const LEITURA: LeituraKm = {
  id: 31, veiculo_id: 7, quilometragem: 85000, data_leitura: "2026-09-20", origem: "cadastro",
  origem_id: null, corrige_id: null, valida: true, editavel: true, anulada_em: null,
  motivo_anulacao: null, criado_em: "2026-09-20T09:00:00-03:00",
};

const FOTO: Foto = {
  id: 5, veiculo_id: 7, tipo_mime: "image/jpeg", tamanho_bytes: 204800, legenda: "Frente",
  data_foto: "2026-09-20", principal: false, projeto_id: null, momento: null,
  diagnostico_id: null, manutencao_id: null, criado_em: "2026-09-20T09:00:00-03:00",
};

function pagina<T>(itens: T[], total = itens.length) {
  return json(200, { itens, total, pagina: 1, por_pagina: 20 });
}

const LOGADO = { "GET /api/auth/eu": () => json(200, PAULA) };
const MES_ATUAL = mesDaData(hojeIso());

const COM_CIVIC = {
  ...LOGADO,
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  "GET /api/veiculos/7/fotos?pagina=1&por_pagina=3": () => pagina<Foto>([]),
  "GET /api/veiculos/7/manutencoes/pendentes": () => json(200, { km_atual: 85000, itens: [] }),
  // Sem diagnósticos: Início (5 mais graves), aba Abertos e "Resolvidos recentemente".
  "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=5": () => pagina([]),
  "GET /api/veiculos/7/diagnosticos?filtro=abertos&pagina=1&por_pagina=20": () => pagina([]),
  "GET /api/veiculos/7/diagnosticos?filtro=resolvidos&pagina=1&por_pagina=3": () => pagina([]),
  // Finanças do mês atual, sem lançamentos.
  [`GET /api/veiculos/7/financas/resumo?ano=${MES_ATUAL.ano}&mes=${MES_ATUAL.mes}`]: () => json(200, {
    ano: MES_ATUAL.ano, mes: MES_ATUAL.mes, total: "0.00", quantidade: 0, categorias: [],
    previsto_manutencoes: "0.00", quantidade_manutencoes_previstas: 0, previsto_gastos: "0.00",
    quantidade_gastos_previstos: 0 }),
  "GET /api/veiculos/7/gastos/pendentes?pagina=1&por_pagina=50": () => pagina([]),
  [`GET /api/veiculos/7/financas/lancamentos?ano=${MES_ATUAL.ano}&mes=${MES_ATUAL.mes}&pagina=1&por_pagina=50`]:
    () => pagina([]),
};

function corpoDe(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return opcoes.body;
}

describe("Início e navegação", () => {
  it("sem veículo, convida a cadastrar em vez de mostrar números", async () => {
    apiFalsa(LOGADO);
    renderizarApp("/");
    expect(await screen.findByText("Você ainda não cadastrou um veículo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Cadastrar veículo" })).toHaveAttribute("href", "/veiculos/novo");
    expect(screen.queryByText("Quilometragem")).not.toBeInTheDocument();
  });

  it("mostra o veículo em uso, a placa e a data da leitura", async () => {
    apiFalsa(COM_CIVIC);
    renderizarApp("/");
    expect(await screen.findByRole("heading", { name: "Civic 2020" })).toBeInTheDocument();
    expect(screen.getByText("ABC-1234")).toBeInTheDocument();
    expect(screen.getByLabelText("85000 quilômetros")).toBeInTheDocument();
    expect(screen.getByText("Atualizada em 20/09/2026")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Atualizar km" })).toHaveAttribute("href", "/veiculos/7/km");
  });

  it("leitura antiga sem data aparece como desconhecida, não como uma data inventada", async () => {
    apiFalsa({ ...COM_CIVIC, "GET /api/veiculos": () => json(200, [{ ...CIVIC, data_leitura_km: null }]) });
    renderizarApp("/");
    expect(await screen.findByText("Data da leitura desconhecida")).toBeInTheDocument();
  });

  it("a barra inferior leva às cinco áreas", async () => {
    apiFalsa(COM_CIVIC);
    renderizarApp("/");
    const barra = await screen.findByRole("navigation", { name: "Navegação principal" });
    expect(within(barra).getAllByRole("link").map((l) => l.textContent)).toEqual(
      ["Início", "Manutenção", "Diagnóstico", "Finanças", "Mais"]);
    expect(within(barra).getByRole("link", { name: "Início" })).toHaveAttribute("aria-current", "page");

    await userEvent.click(within(barra).getByRole("link", { name: "Manutenção" }));
    expect(await screen.findByRole("tab", { name: "Pendentes" })).toBeInTheDocument();
    await userEvent.click(within(barra).getByRole("link", { name: "Diagnóstico" }));
    expect(await screen.findByText("Nenhum problema em aberto")).toBeInTheDocument();
    expect(within(barra).getByRole("link", { name: "Diagnóstico" })).toHaveAttribute("aria-current", "page");
    await userEvent.click(within(barra).getByRole("link", { name: "Finanças" }));
    expect(await screen.findByText("Nenhuma despesa neste mês")).toBeInTheDocument();
    expect(within(barra).getByRole("link", { name: "Finanças" })).toHaveAttribute("aria-current", "page");

    await userEvent.click(screen.getByRole("link", { name: "Mais" }));
    expect(await screen.findByRole("heading", { name: "Mais" })).toBeInTheDocument();
    expect(screen.getByText("1 veículo")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Meu veículo/ })).toHaveAttribute("href", "/veiculos/7");
  });

  it("erro ao carregar os veículos permite tentar de novo", async () => {
    let falhar = true;
    apiFalsa({
      ...LOGADO,
      "GET /api/veiculos": () => (falhar ? json(500, null) : json(200, [CIVIC])),
    });
    renderizarApp("/");
    await userEvent.click(await screen.findByRole("button", { name: "Tentar de novo" }));
    expect(screen.getByRole("alert")).toBeInTheDocument();
    falhar = false;
    await userEvent.click(screen.getByRole("button", { name: "Tentar de novo" }));
    expect(await screen.findByRole("heading", { name: "Civic 2020" })).toBeInTheDocument();
  });

  it("sessão encerrada no meio do uso volta para Entrar", async () => {
    apiFalsa({
      ...LOGADO,
      "GET /api/veiculos": () => json(401, { mensagem: "Sua sessão terminou. Entre de novo.", campos: null }),
    });
    renderizarApp("/");
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });
});

describe("Meus veículos", () => {
  const ARGO: Veiculo = { ...CIVIC, id: 8, marca: "Fiat", modelo: "Argo", ano: 2021, placa: "BRA2E19", em_uso: false };
  const GOL: Veiculo = { ...CIVIC, id: 9, marca: "Volkswagen", modelo: "Gol", ano: 2015, placa: "QWE4567", em_uso: false, ativo: false };

  it("separa ativos de inativos e troca o veículo em uso", async () => {
    let emUso = 7;
    const buscar = apiFalsa({
      ...LOGADO,
      "GET /api/veiculos": () => json(200, [
        { ...CIVIC, em_uso: emUso === 7 }, { ...ARGO, em_uso: emUso === 8 }, GOL,
      ]),
      "POST /api/veiculos/8/selecionar": () => {
        emUso = 8;
        return json(200, { ...ARGO, em_uso: true });
      },
    });
    renderizarApp("/veiculos");
    const ativos = await screen.findByRole("list", { name: "Veículos ativos" });
    expect(within(ativos).getByText("Honda Civic 2020")).toBeInTheDocument();
    expect(within(ativos).getByText("BRA2E19")).toBeInTheDocument();
    const inativos = screen.getByRole("list", { name: "Veículos inativos" });
    expect(within(inativos).getByText("Volkswagen Gol 2015")).toBeInTheDocument();
    expect(within(inativos).queryByRole("button")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Usar Fiat Argo 2021" }));
    await screen.findByRole("button", { name: "Usar Honda Civic 2020" });
    expect(chamadasPara(buscar, "POST /api/veiculos/8/selecionar")).toHaveLength(1);
  });
});

describe("Cadastrar veículo", () => {
  async function preencher(placa = "abc-1234") {
    await userEvent.type(await screen.findByLabelText("Marca"), "Honda");
    await userEvent.type(screen.getByLabelText("Modelo"), "Civic");
    await userEvent.type(screen.getByLabelText("Ano"), "2020");
    await userEvent.type(screen.getByLabelText("Placa"), placa);
    await userEvent.type(screen.getByLabelText("Quilometragem atual"), "85000");
    await userEvent.type(screen.getByLabelText("Tamanho do tanque (litros)"), "47,5");
  }

  it("envia os dados, com dinheiro em texto e sem campos de dono", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos": () => json(200, []),
      "POST /api/veiculos": () => json(201, CIVIC),
    });
    renderizarApp("/veiculos/novo");
    await preencher();
    expect(screen.getByLabelText("Quilometragem atual")).toHaveValue("85.000");
    await userEvent.click(screen.getByRole("radio", { name: "Gasolina" }));
    fireEvent.change(screen.getByLabelText("Data da compra"), { target: { value: "2022-03-15" } });
    await userEvent.type(screen.getByLabelText("Valor pago (R$)"), "65.000,00");
    await userEvent.type(screen.getByLabelText("Quilometragem na compra"), "22000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));

    expect(await screen.findByText("Veículo cadastrado.")).toBeInTheDocument();
    expect(JSON.parse(corpoDe(buscar, "POST /api/veiculos") as string)).toEqual({
      marca: "Honda", modelo: "Civic", versao: null, ano: 2020, placa: "ABC-1234", cor: null,
      tipo_combustivel: "gasolina", quilometragem: 85000, data_aquisicao: "2022-03-15",
      valor_aquisicao: "65000.00", km_aquisicao: 22000, capacidade_tanque: "47.500",
    });
  });

  it("pede o tamanho do tanque, menos no elétrico", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos": () => json(200, []),
      "POST /api/veiculos": () => json(201, { ...CIVIC, tipo_combustivel: "eletrico", capacidade_tanque: null }),
    });
    renderizarApp("/veiculos/novo");
    await userEvent.type(await screen.findByLabelText("Marca"), "BYD");
    await userEvent.type(screen.getByLabelText("Modelo"), "Dolphin");
    await userEvent.type(screen.getByLabelText("Ano"), "2024");
    await userEvent.type(screen.getByLabelText("Placa"), "BYD1A23");
    await userEvent.type(screen.getByLabelText("Quilometragem atual"), "1000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));
    expect(screen.getByText("Informe o tamanho do tanque em litros (está no manual do veículo).")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Tamanho do tanque (litros)"), "47,55");
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));
    expect(screen.getByText("Tamanho inválido. Exemplo: 47 ou 47,5.")).toBeInTheDocument();
    // Elétrico não tem tanque: o campo some e vai vazio.
    await userEvent.click(screen.getByRole("radio", { name: "Elétrico" }));
    expect(screen.queryByLabelText("Tamanho do tanque (litros)")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));
    expect(await screen.findByText("Veículo cadastrado.")).toBeInTheDocument();
    expect(JSON.parse(corpoDe(buscar, "POST /api/veiculos") as string).capacidade_tanque).toBeNull();
  });

  it("veículo antigo sem o tamanho do tanque: aviso na tela do veículo", async () => {
    apiFalsa({ ...COM_CIVIC, "GET /api/veiculos/7": () => json(200, { ...CIVIC, capacidade_tanque: null, tanque_pendente: true }) });
    renderizarApp("/veiculos/7");
    expect(await screen.findByText(/Falta o tamanho do tanque no cadastro/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Informar agora" })).toHaveAttribute("href", "/veiculos/7/editar");
  });

  it("valida na tela antes de enviar", async () => {
    const buscar = apiFalsa(LOGADO);
    renderizarApp("/veiculos/novo");
    await userEvent.click(await screen.findByRole("button", { name: "Salvar veículo" }));
    for (const mensagem of ["Informe a marca.", "Informe o modelo.", "Informe a placa.",
      "Informe a quilometragem atual."]) {
      expect(screen.getByText(mensagem)).toBeInTheDocument();
    }
    await preencher("1234-ABC");
    await userEvent.type(screen.getByLabelText("Valor pago (R$)"), "muito caro");
    await userEvent.type(screen.getByLabelText("Quilometragem na compra"), "90000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));
    expect(screen.getByText("Placa inválida. Use o formato ABC-1234 ou ABC1D23.")).toBeInTheDocument();
    expect(screen.getByText("Valor inválido. Exemplo: 65.000,00.")).toBeInTheDocument();
    expect(screen.getByText("A quilometragem na compra não pode ser maior que a atual.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos")).toHaveLength(0);
  });

  it("mostra no campo o erro devolvido pelo servidor (placa repetida)", async () => {
    const mensagem = "Já existe um veículo com esta placa nesta conta.";
    apiFalsa({
      ...LOGADO,
      "POST /api/veiculos": () => json(409, { mensagem, campos: { placa: mensagem } }),
    });
    renderizarApp("/veiculos/novo");
    await preencher();
    await userEvent.click(screen.getByRole("button", { name: "Salvar veículo" }));
    await waitFor(() => expect(screen.getByLabelText("Placa")).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getAllByText(mensagem)).toHaveLength(2);
  });

  it("edição não tem campo de quilometragem e preserva placa antiga fora do formato", async () => {
    const antigo = { ...CIVIC, placa: "XY123" };
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos/7": () => json(200, antigo),
      "PUT /api/veiculos/7": () => json(200, { ...antigo, cor: "Prata" }),
    });
    renderizarApp("/veiculos/7/editar");
    expect(await screen.findByLabelText("Marca")).toHaveValue("Honda");
    expect(screen.getByLabelText("Valor pago (R$)")).toHaveValue("65.000,00");
    expect(screen.queryByLabelText("Quilometragem atual")).not.toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Cor"), "Prata");
    await userEvent.click(screen.getByRole("button", { name: "Salvar alterações" }));
    await waitFor(() => expect(chamadasPara(buscar, "PUT /api/veiculos/7")).toHaveLength(1));
    const enviado = JSON.parse(corpoDe(buscar, "PUT /api/veiculos/7") as string);
    expect(enviado).toMatchObject({ placa: "XY123", cor: "Prata", valor_aquisicao: "65000.00" });
    expect(enviado).not.toHaveProperty("quilometragem");
  });
});

describe("Meu veículo", () => {
  it("mostra os dados e inativa só depois de confirmar", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "POST /api/veiculos/7/inativar": () => json(200, { ...CIVIC, ativo: false, em_uso: false }),
    });
    renderizarApp("/veiculos/7");
    expect(await screen.findByRole("heading", { name: "Honda Civic 2020" })).toBeInTheDocument();
    expect(screen.getByText("mar/2022")).toBeInTheDocument();
    expect(screen.getByText("R$ 65.000,00")).toBeInTheDocument();
    expect(screen.getByText("22.000 km")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Inativar veículo" }));
    const dialogo = screen.getByRole("alertdialog", { name: "Inativar este veículo?" });
    expect(within(dialogo).getByText(/Nada é apagado/)).toBeInTheDocument();
    await userEvent.click(within(dialogo).getByRole("button", { name: "Cancelar" }));
    expect(chamadasPara(buscar, "POST /api/veiculos/7/inativar")).toHaveLength(0);

    await userEvent.click(screen.getByRole("button", { name: "Inativar veículo" }));
    await userEvent.click(screen.getByRole("button", { name: "Inativar" }));
    expect(await screen.findByRole("button", { name: "Reativar veículo" })).toBeInTheDocument();
    expect(screen.getByText(/Veículo inativo/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Editar veículo" })).not.toBeInTheDocument();
  });

  it("veículo de outra pessoa aparece como não encontrado", async () => {
    apiFalsa({
      ...LOGADO,
      "GET /api/veiculos/99": () => json(404, { mensagem: "Veículo não encontrado.", campos: null }),
    });
    renderizarApp("/veiculos/99");
    expect(await screen.findByText("Veículo não encontrado.")).toBeInTheDocument();
  });
});

describe("Quilometragem", () => {
  const LISTA = "GET /api/veiculos/7/leituras?pagina=1&por_pagina=20";

  it("registra uma leitura com a data de hoje e atualiza a tela", async () => {
    let atual = CIVIC;
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos": () => json(200, [atual]),
      [LISTA]: () => pagina([LEITURA]),
      "POST /api/veiculos/7/leituras": () => {
        atual = { ...CIVIC, quilometragem: 85450, data_leitura_km: hojeIso() };
        return json(201, atual);
      },
    });
    renderizarApp("/veiculos/7/km");
    expect(await screen.findByText("Cadastro do veículo", { exact: false })).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85450");
    await userEvent.click(screen.getByRole("button", { name: "Salvar leitura" }));
    expect(await screen.findByText("Quilometragem atualizada.")).toBeInTheDocument();
    expect(screen.getByText("85.450 km")).toBeInTheDocument();
    expect(JSON.parse(corpoDe(buscar, "POST /api/veiculos/7/leituras") as string)).toEqual({
      quilometragem: 85450, data_leitura: hojeIso(),
    });
  });

  it("leitura antiga é guardada sem mudar a quilometragem atual, e a tela explica", async () => {
    apiFalsa({
      ...COM_CIVIC,
      [LISTA]: () => pagina([LEITURA]),
      "POST /api/veiculos/7/leituras": () => json(201, CIVIC),
    });
    renderizarApp("/veiculos/7/km");
    await userEvent.type(await screen.findByLabelText("Quilometragem"), "70000");
    fireEvent.change(screen.getByLabelText("Data da leitura"), { target: { value: "2026-01-10" } });
    await userEvent.click(screen.getByRole("button", { name: "Salvar leitura" }));
    expect(await screen.findByText(/A quilometragem atual não mudou/)).toBeInTheDocument();
  });

  it("mostra no campo a leitura que contradiz o histórico", async () => {
    const mensagem = "Esta leitura não combina com o histórico: em 20/09/2026 o hodômetro marcava 85.000 km.";
    apiFalsa({
      ...COM_CIVIC,
      [LISTA]: () => pagina([LEITURA]),
      "POST /api/veiculos/7/leituras": () => json(422, { mensagem, campos: { quilometragem: mensagem } }),
    });
    renderizarApp("/veiculos/7/km");
    await userEvent.type(await screen.findByLabelText("Quilometragem"), "84000");
    await userEvent.click(screen.getByRole("button", { name: "Salvar leitura" }));
    expect(await screen.findByText(mensagem)).toBeInTheDocument();
    expect(screen.getByLabelText("Quilometragem")).toHaveAttribute("aria-invalid", "true");
  });

  it("não aceita data futura nem campo vazio", async () => {
    const buscar = apiFalsa({ ...COM_CIVIC, [LISTA]: () => pagina([LEITURA]) });
    renderizarApp("/veiculos/7/km");
    await userEvent.click(await screen.findByRole("button", { name: "Salvar leitura" }));
    expect(screen.getByText("Informe a quilometragem.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Quilometragem"), "86000");
    fireEvent.change(screen.getByLabelText("Data da leitura"), { target: { value: "2999-01-01" } });
    await userEvent.click(screen.getByRole("button", { name: "Salvar leitura" }));
    expect(screen.getByText("A data da leitura não pode ser no futuro.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/leituras")).toHaveLength(0);
  });

  it("corrige uma leitura errada e mostra a anulada no histórico", async () => {
    const errada: LeituraKm = { ...LEITURA, id: 32, quilometragem: 854500, origem: "manual" };
    let corrigida = false;
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos/7": () => json(200, { ...CIVIC, quilometragem: 854500 }),
      [LISTA]: () => (corrigida
        ? pagina([
          { ...errada, id: 33, quilometragem: 85450, corrige_id: 32 },
          { ...errada, valida: false, editavel: false, anulada_em: "2026-09-30T10:00:00-03:00",
            motivo_anulacao: "Zero a mais" },
          LEITURA,
        ])
        : pagina([errada, LEITURA])),
      "POST /api/veiculos/7/leituras/32/corrigir": () => {
        corrigida = true;
        return json(200, { ...CIVIC, quilometragem: 85450 });
      },
    });
    renderizarApp("/veiculos/7/km");
    const item = (await screen.findByText("854.500 km", { selector: ".leitura__km" })).closest("li")!;
    await userEvent.click(within(item).getByRole("button", { name: "Corrigir" }));
    await userEvent.type(within(item).getByLabelText("Quilometragem correta"), "85450");
    await userEvent.type(within(item).getByLabelText("Motivo (opcional)"), "Zero a mais");
    await userEvent.click(within(item).getByRole("button", { name: "Salvar correção" }));

    expect(await screen.findByText("Leitura corrigida.")).toBeInTheDocument();
    expect(JSON.parse(corpoDe(buscar, "POST /api/veiculos/7/leituras/32/corrigir") as string)).toEqual({
      quilometragem: 85450, motivo: "Zero a mais",
    });
    expect(await screen.findByText("Motivo: Zero a mais")).toBeInTheDocument();
    expect(screen.getByText("Anulada")).toBeInTheDocument();
  });

  it("anula só depois de confirmar; leitura de abastecimento não tem botões", async () => {
    const manual: LeituraKm = { ...LEITURA, id: 32, quilometragem: 99000, origem: "manual" };
    const deAbastecimento: LeituraKm = {
      ...LEITURA, id: 34, quilometragem: 84000, origem: "abastecimento", origem_id: 3, editavel: false,
    };
    const buscar = apiFalsa({
      ...COM_CIVIC,
      [LISTA]: () => pagina([manual, LEITURA, deAbastecimento]),
      "POST /api/veiculos/7/leituras/32/anular": () => json(200, CIVIC),
    });
    renderizarApp("/veiculos/7/km");
    const doAbastecimento = (await screen.findByText("84.000 km")).closest("li")!;
    expect(within(doAbastecimento).queryByRole("button")).not.toBeInTheDocument();
    expect(within(doAbastecimento).getByText(/edite o registro de abastecimento/)).toBeInTheDocument();

    const item = screen.getByText("99.000 km").closest("li")!;
    await userEvent.click(within(item).getByRole("button", { name: "Anular" }));
    expect(chamadasPara(buscar, "POST /api/veiculos/7/leituras/32/anular")).toHaveLength(0);
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Anular" }));
    expect(await screen.findByText("Leitura anulada.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/leituras/32/anular")).toHaveLength(1);
  });

  it("veículo inativo mostra o histórico sem formulário nem botões", async () => {
    apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos/7": () => json(200, { ...CIVIC, ativo: false, em_uso: false }),
      [LISTA]: () => pagina([LEITURA]),
    });
    renderizarApp("/veiculos/7/km");
    expect(await screen.findByText(/Veículo inativo/)).toBeInTheDocument();
    expect(await screen.findByText("Cadastro do veículo", { exact: false })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar leitura" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Corrigir" })).not.toBeInTheDocument();
  });
});

describe("Fotos", () => {
  const GALERIA = "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30";

  function arquivoDeFoto(tamanho = 2048, nome = "carro.jpg") {
    return new File([new Uint8Array(tamanho)], nome, { type: "image/jpeg" });
  }

  it("galeria vazia explica como adicionar", async () => {
    apiFalsa({ ...COM_CIVIC, [GALERIA]: () => pagina<Foto>([]) });
    renderizarApp("/veiculos/7/fotos");
    expect(await screen.findByText("Nenhuma foto ainda")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Adicionar foto" })).toHaveAttribute("href", "/veiculos/7/fotos/nova");
  });

  it("agrupa por mês e busca cada imagem no endereço protegido", async () => {
    apiFalsa({
      ...COM_CIVIC,
      [GALERIA]: () => pagina<Foto>([
        { ...FOTO, id: 6, data_foto: "2026-09-24", principal: true, legenda: null },
        FOTO,
        { ...FOTO, id: 4, data_foto: "2026-07-18", legenda: "Antes" },
      ]),
    });
    renderizarApp("/veiculos/7/fotos");
    expect(await screen.findByRole("heading", { name: "Setembro de 2026" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Julho de 2026" })).toBeInTheDocument();
    expect(screen.getByText("3 fotos")).toBeInTheDocument();
    expect(screen.getByAltText("Frente")).toHaveAttribute("src", "/api/veiculos/7/fotos/5/arquivo");
    expect(screen.getByAltText("Foto de 24/09/2026")).toBeInTheDocument();
    expect(screen.getByText("Capa")).toBeInTheDocument();
  });

  it("envia a foto escolhida com legenda, data e opção de capa", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      [GALERIA]: () => pagina([FOTO]),
      "POST /api/veiculos/7/fotos": () => json(201, FOTO),
    });
    renderizarApp("/veiculos/7/fotos/nova");
    const arquivo = arquivoDeFoto();
    await userEvent.upload(await screen.findByLabelText("Escolher foto da galeria"), arquivo);
    expect(screen.getByText(/carro\.jpg/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Legenda"), "Frente");
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));

    expect(await screen.findByText("Foto adicionada.")).toBeInTheDocument();
    const formulario = corpoDe(buscar, "POST /api/veiculos/7/fotos") as FormData;
    expect(formulario).toBeInstanceOf(FormData);
    expect(formulario.get("arquivo")).toBe(arquivo);
    expect(formulario.get("legenda")).toBe("Frente");
    expect(formulario.get("data_foto")).toBe(hojeIso());
    expect(formulario.get("principal")).toBe("false");
    // Sem Content-Type manual: o navegador define o separador do formulário.
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/veiculos/7/fotos");
    expect(new Headers(opcoes.headers).has("Content-Type")).toBe(false);
    expect(new Headers(opcoes.headers).get("X-MV-Requisicao")).toBe("1");
  });

  it("vindo de \"Alterar capa\", a chave de capa já vem ligada", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "POST /api/veiculos/7/fotos": () => json(201, { ...FOTO, principal: true }),
    });
    renderizarApp("/veiculos/7/fotos/nova?capa=1");
    expect(await screen.findByRole("switch", { name: "Usar como capa" })).toHaveAttribute("aria-checked", "true");
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"), arquivoDeFoto());
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(await screen.findByText("Foto de capa atualizada.")).toBeInTheDocument();
    expect((corpoDe(buscar, "POST /api/veiculos/7/fotos") as FormData).get("principal")).toBe("true");
  });

  it("recusa na tela arquivo acima de 10 MB e envio sem foto", async () => {
    const buscar = apiFalsa(COM_CIVIC);
    renderizarApp("/veiculos/7/fotos/nova");
    await userEvent.click(await screen.findByRole("button", { name: "Salvar foto" }));
    expect(screen.getByText("Escolha uma foto.")).toBeInTheDocument();
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"),
      arquivoDeFoto(10_485_761, "enorme.jpg"));
    expect(screen.getByText("Foto grande demais. O limite é 10 MB.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(chamadasPara(buscar, "POST /api/veiculos/7/fotos")).toHaveLength(0);
  });

  it("mostra o motivo quando o servidor recusa o conteúdo do arquivo", async () => {
    const mensagem = "Formato não aceito. Envie uma foto JPEG, PNG, WebP ou HEIC.";
    apiFalsa({
      ...COM_CIVIC,
      "POST /api/veiculos/7/fotos": () => json(422, { mensagem, campos: { arquivo: mensagem } }),
    });
    renderizarApp("/veiculos/7/fotos/nova");
    await userEvent.upload(await screen.findByLabelText("Escolher foto da galeria"), arquivoDeFoto());
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(await screen.findByText(mensagem)).toBeInTheDocument();
  });

  it("na foto: usa como capa e apaga só depois de confirmar", async () => {
    const buscar = apiFalsa({
      ...COM_CIVIC,
      "GET /api/veiculos/7/fotos/5": () => json(200, FOTO),
      "POST /api/veiculos/7/fotos/5/capa": () => json(200, { ...FOTO, principal: true }),
      "DELETE /api/veiculos/7/fotos/5": () => json(204, null),
      [GALERIA]: () => pagina<Foto>([]),
    });
    renderizarApp("/veiculos/7/fotos/5");
    expect(await screen.findByLabelText("Legenda")).toHaveValue("Frente");
    await userEvent.click(screen.getByRole("button", { name: "Usar como capa" }));
    expect(await screen.findByText("Esta foto agora é a capa do veículo.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Deixar de usar como capa" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Apagar foto" }));
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/fotos/5")).toHaveLength(0);
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Apagar" }));
    expect(await screen.findByText("Foto apagada.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "DELETE /api/veiculos/7/fotos/5")).toHaveLength(1);
  });
});
