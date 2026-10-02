// Projetos (lista, cadastro, detalhe, gastos, conclusão) e fotos de antes/depois, com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { PaginaProjetos, Projeto, ProjetoDetalhe } from "../types/projeto";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};
const HOJE = hojeIso();

/** Os três projetos do PDF (página 16). */
const RODAS: Projeto = {
  id: 1, veiculo_id: 7, nome: "Rodas de liga leve", descricao: "Trocar as rodas originais por um jogo aro 17.",
  categoria: "exterior", orcamento: "4500.00", data_prevista: "2026-10-31", status: "em_andamento",
  data_conclusao: null, criado_em: "2026-07-01T10:00:00-03:00", gasto: "3800.00", percentual: 84,
  diferenca: "700.00", quantidade_itens: 2, foto_antes_id: 30, foto_depois_id: null,
};
const CAMERA: Projeto = {
  ...RODAS, id: 2, nome: "Câmera de ré", categoria: "interior", orcamento: "600.00", data_prevista: "2026-12-15",
  status: "planejado", gasto: "0.00", percentual: 0, diferenca: "600.00", quantidade_itens: 0, foto_antes_id: null,
};
const INSULFILM: Projeto = {
  ...RODAS, id: 3, nome: "Insulfilm", orcamento: "500.00", status: "concluido", data_conclusao: "2026-08-15",
  gasto: "450.00", percentual: 90, diferenca: "50.00", quantidade_itens: 1, foto_antes_id: null,
};
const DETALHE: ProjetoDetalhe = {
  ...RODAS,
  itens: [
    { id: 11, descricao: "Jogo de rodas aro 17", data: "2026-07-20", valor: "3400.00" },
    { id: 12, descricao: "Parafusos antifurto", data: "2026-07-20", valor: "400.00" },
  ],
  fotos_antes: [30], fotos_depois: [], total_fotos: 1,
};

function pagina(itens: Projeto[], porStatus = { planejado: 1, em_andamento: 1, concluido: 1, cancelado: 0 }): Response {
  const corpo: PaginaProjetos = { itens, total: itens.length, pagina: 1, por_pagina: 20, por_status: porStatus };
  return json(200, corpo);
}

const LISTA = "GET /api/veiculos/7/projetos?filtro=todos&pagina=1&por_pagina=20";
const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  [LISTA]: () => pagina([RODAS, CAMERA, INSULFILM]),
  "GET /api/veiculos/7/projetos/1": () => json(200, DETALHE),
  "GET /api/veiculos/7/projetos?filtro=todos&pagina=1&por_pagina=1": () => pagina([RODAS]),
};

function corpoJson(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return JSON.parse(opcoes.body as string);
}

describe("Projetos: lista", () => {
  it("mostra orçamento, situação e antes/depois como no PDF", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/projetos");
    const lista = await screen.findByRole("list", { name: "Projetos" });
    const [rodas, camera, insulfilm] = within(lista).getAllByRole("listitem");
    expect(rodas.textContent).toContain("R$ 3.800,00 de R$ 4.500,00");
    expect(rodas.textContent).toContain("84% do orçamento");
    expect(rodas.textContent).toContain("Restam R$ 700,00");
    expect(within(rodas).getByRole("link", { name: /Foto de antes/ })).toHaveAttribute("href", "/veiculos/7/fotos/30");
    expect(within(rodas).getByRole("link", { name: /Foto depois/ })).toHaveAttribute(
      "href", "/veiculos/7/fotos/nova?projeto=1&momento=depois");
    expect(camera.textContent).toContain("Previsto para dez/2026");
    expect(camera.textContent).toContain("Nenhum gasto ainda");
    expect(insulfilm.textContent).toContain("Concluído em 15/08/2026");
    expect(insulfilm.textContent).toContain("R$ 50,00 abaixo");
    expect(screen.getByRole("link", { name: "Novo projeto" })).toHaveAttribute("href", "/veiculos/7/projetos/novo");
  });

  it("filtra pela situação", async () => {
    const CONCLUIDOS = "GET /api/veiculos/7/projetos?filtro=concluido&pagina=1&por_pagina=20";
    const buscar = apiFalsa({ ...BASE, [CONCLUIDOS]: () => pagina([INSULFILM]) });
    renderizarApp("/veiculos/7/projetos");
    await userEvent.click(await screen.findByRole("button", { name: "Concluídos" }));
    expect(await screen.findByText("Insulfilm")).toBeInTheDocument();
    expect(chamadasPara(buscar, CONCLUIDOS)).toHaveLength(1);
  });

  it("sem orçamento e com orçamento excedido não inventam percentual", async () => {
    apiFalsa({ ...BASE, [LISTA]: () => pagina([
      { ...RODAS, id: 4, nome: "Som", orcamento: null, percentual: null, diferenca: null, foto_antes_id: null },
      { ...RODAS, id: 5, nome: "Suspensão", orcamento: "500.00", gasto: "650.00", percentual: 130,
        diferenca: "-150.00", foto_antes_id: null },
    ]) });
    renderizarApp("/veiculos/7/projetos");
    const [som, suspensao] = within(await screen.findByRole("list", { name: "Projetos" })).getAllByRole("listitem");
    expect(som.textContent).toContain("gastos (sem orçamento)");
    expect(som.textContent).toContain("Sem orçamento");
    expect(som.textContent).not.toContain("%");
    expect(suspensao.textContent).toContain("R$ 150,00 acima do orçamento");
  });

  it("o menu Mais mostra quantos estão em andamento", async () => {
    apiFalsa(BASE);
    renderizarApp("/mais");
    const item = await screen.findByRole("link", { name: /Projetos/ });
    expect(item).toHaveAttribute("href", "/veiculos/7/projetos");
    expect(await within(item).findByText("1 em andamento")).toBeInTheDocument();
  });
});

describe("Novo projeto", () => {
  it("cria com orçamento em texto e situação escolhida", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/projetos": () => json(201, DETALHE) });
    renderizarApp("/veiculos/7/projetos/novo");
    await userEvent.type(await screen.findByLabelText("Nome"), "Rodas de liga leve");
    await userEvent.click(screen.getByRole("radio", { name: "Exterior" }));
    await userEvent.type(screen.getByLabelText("Orçamento (R$)"), "4.500,00");
    await userEvent.click(screen.getByRole("radio", { name: "Já começou" }));
    await userEvent.click(screen.getByRole("button", { name: "Criar projeto" }));
    expect(await screen.findByText("Projeto criado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/projetos")).toEqual({
      nome: "Rodas de liga leve", descricao: null, categoria: "exterior", orcamento: "4500.00",
      data_prevista: null, status: "em_andamento" });
  });

  it("sem nome não envia", async () => {
    const buscar = apiFalsa(BASE);
    renderizarApp("/veiculos/7/projetos/novo");
    await userEvent.click(await screen.findByRole("button", { name: "Criar projeto" }));
    expect(screen.getByText("Dê um nome ao projeto.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/projetos")).toHaveLength(0);
  });
});

describe("Detalhe do projeto", () => {
  it("mostra gastos e orçamento e adiciona um gasto", async () => {
    const buscar = apiFalsa({ ...BASE, "POST /api/veiculos/7/projetos/1/itens": () => json(201, {
      ...DETALHE, gasto: "3850.00", diferenca: "650.00", percentual: 86,
      itens: [...DETALHE.itens, { id: 13, descricao: "Calibragem", data: HOJE, valor: "50.00" }] }) });
    renderizarApp("/veiculos/7/projetos/1");
    expect(await screen.findByRole("heading", { name: "Rodas de liga leve" })).toBeInTheDocument();
    const orcamento = screen.getByRole("region", { name: "Orçamento" });
    expect(orcamento.textContent).toContain("R$ 3.800,00");
    expect(orcamento.textContent).toContain("de R$ 4.500,00");
    expect(orcamento.textContent).toContain("Restam R$ 700,00");
    expect(orcamento.textContent).toContain("Previsto para out/2026");
    const gastos = screen.getByRole("list", { name: "Gastos do projeto" });
    expect(within(gastos).getAllByRole("listitem").map((i) => i.textContent)).toEqual([
      "Jogo de rodas aro 1720/07/2026R$ 3.400,00", "Parafusos antifurto20/07/2026R$ 400,00"]);

    await userEvent.click(screen.getByRole("button", { name: "Adicionar gasto" }));
    const dialogo = screen.getByRole("alertdialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Adicionar" }));
    expect(within(dialogo).getByText("Informe o que foi comprado ou pago.")).toBeInTheDocument();
    await userEvent.type(within(dialogo).getByLabelText("O que foi"), "Calibragem");
    await userEvent.type(within(dialogo).getByLabelText("Valor (R$)"), "50");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Adicionar" }));
    expect(await screen.findByText("Gasto adicionado.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/projetos/1/itens")).toEqual({
      descricao: "Calibragem", valor: "50.00", data: HOJE });
    expect(screen.getByRole("region", { name: "Orçamento" }).textContent).toContain("R$ 3.850,00");
  });

  it("conclui com a data escolhida; concluído não aceita gasto até reabrir", async () => {
    const buscar = apiFalsa({ ...BASE,
      "POST /api/veiculos/7/projetos/1/concluir": () => json(200, { ...DETALHE, status: "concluido",
        data_conclusao: HOJE }),
      "POST /api/veiculos/7/projetos/1/reabrir": () => json(200, DETALHE) });
    renderizarApp("/veiculos/7/projetos/1");
    await userEvent.click(await screen.findByRole("button", { name: "Marcar como concluído" }));
    const dialogo = screen.getByRole("alertdialog");
    expect(within(dialogo).getByLabelText("Data de conclusão")).toHaveValue(HOJE);
    await userEvent.click(within(dialogo).getByRole("button", { name: "Concluir" }));
    expect(await screen.findByText("Projeto concluído.")).toBeInTheDocument();
    expect(corpoJson(buscar, "POST /api/veiculos/7/projetos/1/concluir")).toEqual({ data_conclusao: HOJE });
    expect(screen.queryByRole("button", { name: "Adicionar gasto" })).not.toBeInTheDocument();
    expect(screen.getByText(/Para alterar, reabra o projeto/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reabrir projeto" }));
    expect(await screen.findByText("Projeto reaberto.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Adicionar gasto" })).toBeInTheDocument();
  });

  it("cancelar avisa que os gastos continuam; apagar sugere cancelar", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/projetos/1");
    await userEvent.click(await screen.findByRole("button", { name: "Cancelar projeto" }));
    expect(within(screen.getByRole("alertdialog")).getByText(/R\$ 3\.800,00 já gastos continuam nas despesas/))
      .toBeInTheDocument();
    await userEvent.click(within(screen.getByRole("alertdialog")).getByRole("button", { name: "Cancelar" }));
    await userEvent.click(screen.getByRole("button", { name: "Apagar projeto" }));
    const apagar = screen.getByRole("alertdialog");
    expect(within(apagar).getByText(/saem das despesas e a foto ligada é apagada/)).toBeInTheDocument();
    expect(within(apagar).getByText(/prefira "Cancelar projeto"/)).toBeInTheDocument();
  });

  it("quadro vazio de depois leva para Nova foto já ligada ao projeto", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/projetos/1");
    expect(await screen.findByRole("link", { name: /Foto depois/ })).toHaveAttribute(
      "href", "/veiculos/7/fotos/nova?projeto=1&momento=depois");
    expect(screen.getByText("Ao concluir")).toBeInTheDocument();
  });
});

describe("Fotos de antes e depois", () => {
  it("aberta pelo projeto, a foto vai ligada a ele com o momento escolhido", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/projetos?filtro=todos&pagina=1&por_pagina=100": () => pagina([RODAS, CAMERA]),
      "POST /api/veiculos/7/fotos": () => json(201, { id: 31 }) });
    renderizarApp("/veiculos/7/fotos/nova?projeto=1&momento=depois");
    expect(await screen.findByRole("radio", { name: "Projeto" })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByLabelText("Projeto")).toHaveValue("1");
    expect(screen.getByRole("radio", { name: "Depois" })).toHaveAttribute("aria-checked", "true");
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"),
      new File([new Uint8Array(2048)], "rodas.jpg", { type: "image/jpeg" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(await screen.findByRole("heading", { name: "Rodas de liga leve" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/veiculos/7/fotos");
    expect((opcoes.body as FormData).get("projeto_id")).toBe("1");
    expect((opcoes.body as FormData).get("momento")).toBe("depois");
  });

  it("a galeria filtra pelas fotos de projeto", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30": () => json(200, { itens: [], total: 0, pagina: 1, por_pagina: 30 }),
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=projeto": () =>
        json(200, { itens: [], total: 0, pagina: 1, por_pagina: 30 }) });
    renderizarApp("/veiculos/7/fotos");
    await userEvent.click(await screen.findByRole("button", { name: "Projetos" }));
    await screen.findByText(/Nenhuma foto/);
    expect(chamadasPara(buscar, "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=projeto")).toHaveLength(1);
  });
});
