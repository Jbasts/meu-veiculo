import { render as renderizar, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router";
import { describe, expect, it, vi } from "vitest";

import type { Saude } from "../types/saude";
import SituacaoSistemaPage from "./SituacaoSistemaPage";

function render(elemento: ReactElement) {
  return renderizar(<MemoryRouter>{elemento}</MemoryRouter>);
}

function saude(parcial: Partial<Saude>): Saude {
  return {
    api: "ok",
    banco: "ok",
    situacao_banco: "controlado",
    versao_migracao: "0001",
    versao_mais_recente: "0001",
    migracoes_pendentes: [],
    fuso_horario: "America/Sao_Paulo",
    data_hoje: "2026-09-29",
    mensagem: "Tudo certo: API, banco e migrations em dia.",
    ...parcial,
  };
}

function respostaJson(status: number, corpo: unknown): Response {
  return new Response(JSON.stringify(corpo), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("SituacaoSistemaPage", () => {
  it("mostra API, banco e migrations em dia", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respostaJson(200, saude({}))));
    render(<SituacaoSistemaPage />);
    expect(await screen.findByText("Em dia (versão 0001)")).toBeInTheDocument();
    expect(screen.getByText("Conectado")).toBeInTheDocument();
    expect(screen.getByText("29/09/2026")).toBeInTheDocument();
    expect(screen.getByText("America/Sao_Paulo")).toBeInTheDocument();
  });

  it("avisa migration pendente", async () => {
    const corpo = saude({
      situacao_banco: "vazio",
      versao_migracao: null,
      migracoes_pendentes: ["0001"],
      mensagem: "Há 1 migration(s) pendente(s). Rode 'python gerenciar.py migrar'.",
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respostaJson(200, corpo)));
    render(<SituacaoSistemaPage />);
    expect(await screen.findByText("Pendente: 0001")).toBeInTheDocument();
    expect(screen.getByText(/gerenciar\.py migrar/)).toBeInTheDocument();
  });

  it("mostra banco indisponível quando a API responde 503", async () => {
    const corpo = saude({
      banco: "indisponivel",
      situacao_banco: null,
      versao_migracao: null,
      versao_mais_recente: null,
      data_hoje: null,
      mensagem: "A API está no ar, mas não conseguiu falar com o banco de dados.",
    });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(respostaJson(503, corpo)));
    render(<SituacaoSistemaPage />);
    expect(await screen.findByText("Indisponível")).toBeInTheDocument();
    expect(screen.getByText("No ar")).toBeInTheDocument();
  });

  it("mostra API fora do ar e permite verificar de novo", async () => {
    const buscar = vi
      .fn()
      .mockRejectedValueOnce(new TypeError("Failed to fetch"))
      .mockResolvedValueOnce(respostaJson(200, saude({})));
    vi.stubGlobal("fetch", buscar);
    render(<SituacaoSistemaPage />);
    expect(await screen.findByText("Sem resposta")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Verificar novamente" }));
    expect(await screen.findByText("Em dia (versão 0001)")).toBeInTheDocument();
    expect(buscar).toHaveBeenCalledTimes(2);
  });
});
