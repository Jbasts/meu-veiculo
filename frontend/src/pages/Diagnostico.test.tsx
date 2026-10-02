// Fluxos de diagnóstico nas telas (lista, cadastro, detalhe, resolução com
// manutenção, Início e fotos), com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { DiagnosticoDetalhe, DiagnosticoResumo } from "../types/diagnostico";
import type { ManutencaoDetalhe } from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";

const CIVIC: Veiculo = {
  id: 7, usuario_id: 1, marca: "Honda", modelo: "Civic", versao: null, ano: 2020,
  placa: "ABC1234", cor: null, tipo_combustivel: "flex", quilometragem: 85000,
  data_leitura_km: "2026-09-20", km_aquisicao: 22000, data_aquisicao: "2022-03-15",
  valor_aquisicao: "65000.00", ativo: true, criado_em: "2026-09-01T10:00:00-03:00",
  em_uso: true, foto_capa_id: null, capacidade_tanque: "56.0", tanque_pendente: false,
};

const BARULHO: DiagnosticoResumo = {
  id: 5, veiculo_id: 7, titulo: "Barulho na suspensão dianteira",
  descricao: "Estalo seco ao passar em lombadas.", sistema: "suspensao", gravidade: "media",
  status: "em_observacao", data_identificacao: "2026-09-23", quilometragem: 85000,
  data_resolucao: null, solucao: null, manutencao_id: null, criado_em: "2026-09-23T10:00:00-03:00",
  total_notas: 2, manutencao: null,
};

const AR: DiagnosticoResumo = {
  ...BARULHO, id: 6, titulo: "Ar-condicionado gelando pouco", sistema: "ar_condicionado",
  gravidade: "baixa", status: "aberto", data_identificacao: "2026-09-10", quilometragem: 84300,
  total_notas: 0,
};

const VIBRACAO: DiagnosticoResumo = {
  ...BARULHO, id: 3, titulo: "Vibração no volante", sistema: "pneus", status: "resolvido",
  data_identificacao: "2026-08-20", data_resolucao: "2026-09-02", manutencao_id: 30, total_notas: 0,
  manutencao: { id: 30, descricao: "Troca de pneus", status: "realizada", data: "2026-09-02", valor: "1800.00" },
};

const DETALHE: DiagnosticoDetalhe = {
  ...BARULHO,
  notas: [
    { id: 2, data: "2026-09-24", texto: "Oficina suspeita das bieletas. Orçamento de R$ 280,00.",
      criado_em: "2026-09-24T10:00:00-03:00" },
    { id: 1, data: "2026-09-23", texto: "Primeiro registro. O barulho aparece só em lombadas.",
      criado_em: "2026-09-23T10:00:00-03:00" },
  ],
  manutencao: null,
  garantias: [{ manutencao_id: 20, descricao: "Amortecedores dianteiros", data: "2026-05-12",
    explicacao: "Amortecedores dianteiros em 12/05/2026, com garantia até 12/05/2027." }],
  total_fotos: 0,
};

const MANUTENCAO: ManutencaoDetalhe = {
  id: 12, veiculo_id: 7, plano_id: null, descricao: "Troca das bieletas", sistema: "suspensao",
  status: "realizada", data: "2026-09-24", quilometragem: 85000, valor: "280.00",
  oficina: null, garantia_ate: null, garantia_km: null, proxima_data: null, proxima_km: null,
  observacao: null, criado_em: "2026-09-24T10:00:00-03:00", plano_nome: null,
  garantia_situacao: "sem_informacao", garantia_explicacao: "Sem informação.", total_fotos: 0,
  itens: [], total_pecas: null, total_mao_de_obra: null, diagnosticos: [],
};

function pagina<T>(itens: T[], porPagina: number, total = itens.length) {
  return json(200, { itens, total, pagina: 1, por_pagina: porPagina });
}

const LISTA = "/api/veiculos/7/diagnosticos";
const ABERTOS = `GET ${LISTA}?filtro=abertos&pagina=1&por_pagina=20`;
const RECENTES = `GET ${LISTA}?filtro=resolvidos&pagina=1&por_pagina=3`;
const DETALHE_5 = `GET ${LISTA}/5`;
const BASE = {
  "GET /api/auth/eu": () => json(200, PAULA),
  "GET /api/veiculos": () => json(200, [CIVIC]),
  "GET /api/veiculos/7": () => json(200, CIVIC),
  [ABERTOS]: () => pagina([], 20),
  [RECENTES]: () => pagina([], 3),
  [DETALHE_5]: () => json(200, DETALHE),
};

function corpoJson(buscar: ReturnType<typeof apiFalsa>, chave: string) {
  const [[, opcoes]] = chamadasPara(buscar, chave);
  return JSON.parse(opcoes.body as string);
}

describe("Diagnóstico: lista", () => {
  it("mostra os abertos em cartões e os resolvidos recentemente com o valor", async () => {
    apiFalsa({ ...BASE,
      [ABERTOS]: () => pagina([BARULHO, AR], 20),
      [RECENTES]: () => pagina([VIBRACAO], 3) });
    renderizarApp("/diagnostico");

    expect(await screen.findByRole("tab", { name: "Abertos (2)" })).toHaveAttribute("aria-selected", "true");
    const abertos = screen.getByRole("list", { name: "Problemas em aberto" });
    const [primeiro, segundo] = within(abertos).getAllByRole("link");
    expect(within(primeiro).getByText("Barulho na suspensão dianteira")).toBeInTheDocument();
    expect(within(primeiro).getByText("Gravidade média")).toBeInTheDocument();
    expect(within(primeiro).getByText("Desde 23/09/2026, aos 85.000 km")).toBeInTheDocument();
    expect(within(primeiro).getByText("Em observação")).toBeInTheDocument();
    expect(within(primeiro).getByText("2 anotações")).toBeInTheDocument();
    expect(primeiro).toHaveAttribute("href", "/veiculos/7/diagnosticos/5");
    expect(within(segundo).getByText("Sem anotações")).toBeInTheDocument();
    expect(within(segundo).getByText("Aberto")).toBeInTheDocument();

    const recentes = await screen.findByRole("region", { name: "Resolvidos recentemente" });
    expect(within(recentes).getByText("Resolvido em 02/09/2026 com Troca de pneus")).toBeInTheDocument();
    expect(within(recentes).getByText("R$ 1.800,00")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Novo diagnóstico" })).toHaveAttribute(
      "href", "/veiculos/7/diagnosticos/novo");
  });

  it("banco vazio: explica como registrar e não mostra números inventados", async () => {
    apiFalsa(BASE);
    renderizarApp("/diagnostico");
    expect(await screen.findByText("Nenhum problema em aberto")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Abertos (0)" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "Resolvidos recentemente" })).not.toBeInTheDocument();
  });

  it("a aba Resolvidos mantém o número de abertos no título da aba", async () => {
    apiFalsa({ ...BASE,
      [ABERTOS]: () => pagina([BARULHO, AR], 20),
      [`GET ${LISTA}?filtro=resolvidos&pagina=1&por_pagina=20`]: () => pagina([VIBRACAO], 20),
      [`GET ${LISTA}?filtro=abertos&pagina=1&por_pagina=1`]: () => pagina([BARULHO], 1, 2) });
    renderizarApp("/diagnostico");
    await userEvent.click(await screen.findByRole("tab", { name: "Resolvidos" }));
    const encerrados = await screen.findByRole("list", { name: "Problemas encerrados" });
    expect(within(encerrados).getByText("Vibração no volante")).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Abertos (2)" })).toBeInTheDocument();
  });
});

describe("Novo diagnóstico", () => {
  it("registra o problema com sistema, gravidade e quilometragem", async () => {
    const buscar = apiFalsa({ ...BASE, [`POST ${LISTA}`]: () => json(201, DETALHE) });
    renderizarApp("/veiculos/7/diagnosticos/novo");

    await userEvent.type(await screen.findByLabelText("O que está acontecendo?"), "Barulho na suspensão dianteira");
    await userEvent.type(screen.getByLabelText("Detalhes"), "Estalo seco ao passar em lombadas.");
    await userEvent.click(screen.getByRole("radio", { name: "Suspensão" }));
    expect(screen.getByText("Resolver nas próximas semanas.")).toBeInTheDocument(); // média, o padrão
    await userEvent.click(screen.getByRole("radio", { name: "Alta" }));
    expect(screen.getByText("Resolver o quanto antes.")).toBeInTheDocument();
    expect(screen.getByText("Hoje. Toque para alterar.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Quilometragem"), "85000");
    await userEvent.click(screen.getByRole("button", { name: "Registrar problema" }));

    expect(await screen.findByText("Problema registrado.")).toBeInTheDocument();
    expect(corpoJson(buscar, `POST ${LISTA}`)).toEqual({
      titulo: "Barulho na suspensão dianteira", descricao: "Estalo seco ao passar em lombadas.",
      sistema: "suspensao", gravidade: "alta", data_identificacao: hojeIso(), quilometragem: 85000,
    });
  });

  it("sem título não envia; erro do servidor aparece no campo", async () => {
    const buscar = apiFalsa({ ...BASE, [`POST ${LISTA}`]: () => json(422, {
      mensagem: "Confira os campos.",
      campos: { quilometragem: "Esta quilometragem não combina com o histórico." } }) });
    renderizarApp("/veiculos/7/diagnosticos/novo");
    await userEvent.click(await screen.findByRole("button", { name: "Registrar problema" }));
    expect(screen.getByText("Conte em poucas palavras o que está acontecendo.")).toBeInTheDocument();
    expect(chamadasPara(buscar, `POST ${LISTA}`)).toHaveLength(0);

    await userEvent.type(screen.getByLabelText("O que está acontecendo?"), "Barulho");
    await userEvent.type(screen.getByLabelText("Quilometragem"), "90000");
    await userEvent.click(screen.getByRole("button", { name: "Registrar problema" }));
    expect(await screen.findByText("Esta quilometragem não combina com o histórico.")).toBeInTheDocument();
  });
});

describe("Detalhe do diagnóstico", () => {
  it("mostra dados, aviso de garantia e anotações da mais recente para a mais antiga", async () => {
    apiFalsa(BASE);
    renderizarApp("/veiculos/7/diagnosticos/5");
    expect(await screen.findByRole("heading", { name: "Barulho na suspensão dianteira" })).toBeInTheDocument();
    const identificado = screen.getByText("Identificado em").closest("div")!;
    expect(within(identificado).getByText("23/09/2026")).toBeInTheDocument();
    expect(within(screen.getByText("Quilometragem").closest("div")!).getByText("85.000 km")).toBeInTheDocument();
    const garantia = screen.getByRole("region", { name: "Garantia" });
    expect(within(garantia).getByText("Há peça em garantia neste sistema")).toBeInTheDocument();
    expect(within(garantia).getByRole("link", { name: "Ver manutenção" })).toHaveAttribute(
      "href", "/veiculos/7/manutencoes/20");
    const notas = within(screen.getByRole("list", { name: "Anotações" })).getAllByRole("listitem");
    expect(notas.map((n) => n.textContent)).toEqual([
      expect.stringContaining("24/09/2026Oficina suspeita"),
      expect.stringContaining("23/09/2026Primeiro registro"),
    ]);
    expect(screen.getByRole("link", { name: "Resolver com uma manutenção" })).toHaveAttribute(
      "href", "/veiculos/7/manutencoes/nova?diagnostico=5");
  });

  it("adiciona uma anotação com a data de hoje", async () => {
    const buscar = apiFalsa({ ...BASE, [`POST ${LISTA}/5/notas`]: () => json(201, {
      ...DETALHE, notas: [{ id: 3, data: hojeIso(), texto: "Troquei de oficina.", criado_em: "" }, ...DETALHE.notas],
    }) });
    renderizarApp("/veiculos/7/diagnosticos/5");
    await userEvent.click(await screen.findByRole("button", { name: "Adicionar anotação" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar anotação" }));
    expect(screen.getByText("Escreva a anotação.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Anotação"), "Troquei de oficina.");
    await userEvent.click(screen.getByRole("button", { name: "Salvar anotação" }));
    expect(await screen.findByText("Anotação adicionada.")).toBeInTheDocument();
    expect(corpoJson(buscar, `POST ${LISTA}/5/notas`)).toEqual({ texto: "Troquei de oficina.", data: hojeIso() });
    expect(screen.getByText("Troquei de oficina.")).toBeInTheDocument();
  });

  it("descarta com motivo só depois de confirmar", async () => {
    const buscar = apiFalsa({ ...BASE, [`POST ${LISTA}/5/descartar`]: () => json(200, {
      ...DETALHE, status: "descartado", data_resolucao: "2026-09-30", solucao: "Era a tampa solta.",
      garantias: [] }) });
    renderizarApp("/veiculos/7/diagnosticos/5");
    await userEvent.click(await screen.findByRole("button", { name: "Marcar como descartado" }));
    const dialogo = screen.getByRole("alertdialog");
    await userEvent.type(within(dialogo).getByLabelText("Motivo (opcional)"), "Era a tampa solta.");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Descartar" }));
    expect(await screen.findByText("Diagnóstico descartado.")).toBeInTheDocument();
    expect(corpoJson(buscar, `POST ${LISTA}/5/descartar`)).toEqual({ motivo: "Era a tampa solta." });
    expect(screen.getByText("Motivo: Era a tampa solta.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reabrir diagnóstico" })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Resolver com uma manutenção" })).not.toBeInTheDocument();
  });

  it("usa uma manutenção já registrada do veículo", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes?pagina=1&por_pagina=100": () => pagina([MANUTENCAO], 100),
      [`POST ${LISTA}/5/vincular`]: () => json(200, { ...DETALHE, status: "resolvido",
        data_resolucao: "2026-09-24", manutencao_id: 12, garantias: [],
        manutencao: { id: 12, descricao: "Troca das bieletas", status: "realizada", data: "2026-09-24",
          valor: "280.00" } }) });
    renderizarApp("/veiculos/7/diagnosticos/5");
    await userEvent.click(await screen.findByRole("button", { name: "Usar uma manutenção já registrada" }));
    const dialogo = screen.getByRole("alertdialog");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Usar esta" }));
    expect(await within(dialogo).findByText("Escolha a manutenção.")).toBeInTheDocument();
    await userEvent.selectOptions(within(dialogo).getByLabelText("Manutenção"), "12");
    await userEvent.click(within(dialogo).getByRole("button", { name: "Usar esta" }));
    expect(await screen.findByText("Diagnóstico resolvido.")).toBeInTheDocument();
    expect(corpoJson(buscar, `POST ${LISTA}/5/vincular`)).toEqual({ manutencao_id: 12 });
    const resolucao = screen.getByRole("region", { name: "Resolução" });
    expect(within(resolucao).getByText("Resolvido em 24/09/2026")).toBeInTheDocument();
    expect(within(resolucao).getByText(/R\$ 280,00/)).toBeInTheDocument();
  });

  it("com manutenção agendada, avisa que resolve ao concluir e não oferece resolver de novo", async () => {
    apiFalsa({ ...BASE, [DETALHE_5]: () => json(200, { ...DETALHE, manutencao_id: 40,
      manutencao: { id: 40, descricao: "Troca das bieletas", status: "agendada", data: "2026-10-05",
        valor: "280.00" } }) });
    renderizarApp("/veiculos/7/diagnosticos/5");
    const aviso = await screen.findByRole("region", { name: "Manutenção agendada" });
    expect(within(aviso).getByText("Manutenção agendada para 05/10/2026")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: "Resolver com uma manutenção" })).not.toBeInTheDocument();
  });

  it("veículo inativo: mostra o histórico sem ações", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7": () => json(200, { ...CIVIC, ativo: false }) });
    renderizarApp("/veiculos/7/diagnosticos/5");
    expect(await screen.findByRole("heading", { name: "Barulho na suspensão dianteira" })).toBeInTheDocument();
    for (const nome of ["Adicionar anotação", "Marcar como descartado", "Apagar diagnóstico"]) {
      expect(screen.queryByRole("button", { name: nome })).not.toBeInTheDocument();
    }
    expect(screen.queryByRole("link", { name: "Editar diagnóstico" })).not.toBeInTheDocument();
  });
});

describe("Resolver com uma manutenção nova", () => {
  const COM_FORM = {
    ...BASE,
    "GET /api/veiculos/7/planos": () => json(200, []),
  };

  it("mostra a faixa 'Resolvendo o diagnóstico', já usa o sistema dele e envia pela resolução", async () => {
    const buscar = apiFalsa({ ...COM_FORM, [`POST ${LISTA}/5/resolver`]: () => json(201, {
      diagnostico: { ...DETALHE, status: "resolvido" }, manutencao: MANUTENCAO }) });
    renderizarApp("/veiculos/7/manutencoes/nova?diagnostico=5");

    const faixa = await screen.findByRole("region", { name: "Resolvendo o diagnóstico" });
    expect(within(faixa).getByText("Barulho na suspensão dianteira")).toBeInTheDocument();
    expect(within(faixa).getByText("Ao salvar, ele será marcado como resolvido.")).toBeInTheDocument();
    expect(screen.getByLabelText("Sistema")).toHaveValue("suspensao");

    await userEvent.type(screen.getByLabelText("Descrição"), "Troca das bieletas");
    await userEvent.type(screen.getByLabelText("Valor total (R$)"), "280");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));

    expect(await screen.findByText("Manutenção registrada e diagnóstico resolvido.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/veiculos/7/manutencoes")).toHaveLength(0);
    expect(corpoJson(buscar, `POST ${LISTA}/5/resolver`)).toMatchObject({
      descricao: "Troca das bieletas", sistema: "suspensao", status: "realizada", valor: "280.00",
    });
  });

  it("agendando, explica que o diagnóstico continua aberto até a conclusão", async () => {
    apiFalsa(COM_FORM);
    renderizarApp("/veiculos/7/manutencoes/nova?diagnostico=5");
    await userEvent.click(await screen.findByRole("radio", { name: "Agendar" }));
    expect(screen.getByText(/continua aberto e será resolvido quando a manutenção for marcada como realizada/))
      .toBeInTheDocument();
  });

  it("mostra o erro do servidor quando o diagnóstico já foi resolvido (envio repetido)", async () => {
    apiFalsa({ ...COM_FORM, [`POST ${LISTA}/5/resolver`]: () => json(409, {
      mensagem: "Este diagnóstico já foi resolvido.", campos: {} }) });
    renderizarApp("/veiculos/7/manutencoes/nova?diagnostico=5");
    await userEvent.type(await screen.findByLabelText("Descrição"), "Troca");
    await userEvent.click(screen.getByRole("button", { name: "Salvar manutenção" }));
    expect(await screen.findByText("Este diagnóstico já foi resolvido.")).toBeInTheDocument();
  });
});

describe("Manutenção ligada a diagnósticos", () => {
  const LIGADO = { id: 5, titulo: "Barulho na suspensão dianteira", status: "resolvido" as const,
    gravidade: "media" as const, data_identificacao: "2026-09-23" };

  it("o detalhe lista o problema resolvido e avisa ao apagar que ele será reaberto", async () => {
    apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes/12": () => json(200, { ...MANUTENCAO, diagnosticos: [LIGADO] }) });
    renderizarApp("/veiculos/7/manutencoes/12");
    const secao = await screen.findByRole("region", { name: "Diagnósticos ligados" });
    expect(within(secao).getByRole("link", { name: /Barulho na suspensão dianteira/ })).toHaveAttribute(
      "href", "/veiculos/7/diagnosticos/5");
    await userEvent.click(screen.getByRole("button", { name: "Apagar manutenção" }));
    expect(within(screen.getByRole("alertdialog")).getByText(/volta a ficar em aberto/)).toBeInTheDocument();
  });

  it("na edição, avisa que voltar para agendada reabre o diagnóstico", async () => {
    apiFalsa({ ...BASE, "GET /api/veiculos/7/planos": () => json(200, []),
      "GET /api/veiculos/7/manutencoes/12": () => json(200, { ...MANUTENCAO, diagnosticos: [LIGADO] }) });
    renderizarApp("/veiculos/7/manutencoes/12/editar");
    expect(await screen.findByText(/Esta manutenção resolveu o diagnóstico/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: "Agendar" }));
    expect(screen.getByText(/volta a ficar aberto/)).toBeInTheDocument();
  });
});

describe("Início e fotos", () => {
  it("o Início mostra os problemas em aberto em 'Precisa de atenção'", async () => {
    apiFalsa({ ...BASE,
      "GET /api/veiculos/7/manutencoes/pendentes": () => json(200, { km_atual: 85000, itens: [] }),
      [`GET ${LISTA}?filtro=abertos&pagina=1&por_pagina=5`]: () => pagina([BARULHO, AR], 5) });
    renderizarApp("/");
    const atencao = await screen.findByRole("region", { name: "Precisa de atenção" });
    expect(within(atencao).getByText("Diagnóstico em observação, gravidade média")).toBeInTheDocument();
    expect(within(atencao).getByText("Diagnóstico aberto, gravidade baixa")).toBeInTheDocument();
    expect(within(atencao).getByRole("link", { name: /Barulho na suspensão/ })).toHaveAttribute(
      "href", "/veiculos/7/diagnosticos/5");
  });

  it("aberta a partir do diagnóstico, a foto já vai ligada a ele", async () => {
    const buscar = apiFalsa({ ...BASE,
      [`GET ${LISTA}?filtro=todos&pagina=1&por_pagina=100`]: () => pagina([BARULHO, VIBRACAO], 100),
      "POST /api/veiculos/7/fotos": () => json(201, { id: 9 }) });
    renderizarApp("/veiculos/7/fotos/nova?diagnostico=5");
    expect(await screen.findByRole("radio", { name: "Diagnóstico" })).toHaveAttribute("aria-checked", "true");
    expect(await screen.findByLabelText("Diagnóstico")).toHaveValue("5");
    await userEvent.upload(screen.getByLabelText("Escolher foto da galeria"),
      new File([new Uint8Array(2048)], "vazamento.jpg", { type: "image/jpeg" }));
    await userEvent.click(screen.getByRole("button", { name: "Salvar foto" }));
    expect(await screen.findByRole("heading", { name: "Barulho na suspensão dianteira" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/veiculos/7/fotos");
    expect((opcoes.body as FormData).get("diagnostico_id")).toBe("5");
    expect((opcoes.body as FormData).get("manutencao_id")).toBeNull();
  });

  it("a galeria filtra pelas fotos de diagnóstico", async () => {
    const buscar = apiFalsa({ ...BASE,
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30": () => pagina([], 30),
      "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=diagnostico": () => pagina([], 30) });
    renderizarApp("/veiculos/7/fotos");
    await userEvent.click(await screen.findByRole("button", { name: "Diagnósticos" }));
    await screen.findByText(/Nenhuma foto/);
    expect(chamadasPara(buscar, "GET /api/veiculos/7/fotos?pagina=1&por_pagina=30&vinculo=diagnostico"))
      .toHaveLength(1);
  });
});
