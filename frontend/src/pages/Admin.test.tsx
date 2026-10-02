// Área de administração (Usuários e veículos, Usuário, Criar conta) e menu Mais, com a API simulada.

import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { resumoDoUsuario, textoDoAcesso } from "../components/PecasAdmin";
import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";
import type { PaginaUsuariosAdmin, UsuarioAdmin, UsuarioDetalheAdmin, VeiculoComDono } from "../types/admin";
import type { Usuario } from "../types/usuario";

const ADMIN: Usuario = { ...PAULA, perfil: "admin" };

const LINHA_PAULA: UsuarioAdmin = {
  id: 1, nome: "Paula Bastos", email: "paula@email.com", perfil: "admin", ativo: true,
  ultimo_acesso: new Date().toISOString(), criado_em: "2026-09-01T10:00:00-03:00", veiculos_ativos: 1, veiculos: 1,
};
const RAFAEL: UsuarioAdmin = {
  ...LINHA_PAULA, id: 2, nome: "Rafael Souza", email: "rafael.souza@email.com", perfil: "padrao",
  ultimo_acesso: "2026-09-21T15:00:00-03:00",
};
const CARLA: UsuarioAdmin = {
  ...RAFAEL, id: 3, nome: "Carla Mendes", email: "carla@email.com", ativo: false, veiculos: 2, veiculos_ativos: 2,
};
const ARGO: VeiculoComDono = {
  id: 20, usuario_id: 2, marca: "Fiat", modelo: "Argo", ano: 2021, placa: "BRA2E19", ativo: true,
  dono_nome: "Rafael Souza", dono_ativo: true,
};

function paginaUsuarios(itens: UsuarioAdmin[]): Response {
  const corpo: PaginaUsuariosAdmin = {
    itens, total: itens.length, pagina: 1, por_pagina: 30,
    por_perfil: { admin: 1, padrao: 2 },
  };
  return json(200, corpo);
}

const USUARIOS = "GET /api/admin/usuarios?pagina=1&por_pagina=30";
const VEICULOS = "GET /api/admin/veiculos?pagina=1&por_pagina=30";
const BASE = {
  "GET /api/auth/eu": () => json(200, ADMIN),
  [USUARIOS]: () => paginaUsuarios([LINHA_PAULA, RAFAEL, CARLA]),
  [VEICULOS]: () => json(200, { itens: [ARGO], total: 1, pagina: 1, por_pagina: 30 }),
  "GET /api/admin/resumo": () => json(200, { usuarios: 3, veiculos: 4 }),
};

describe("Mais", () => {
  it("admin vê Administração com o resumo; padrão não vê", async () => {
    apiFalsa(BASE);
    const { unmount } = renderizarApp("/mais");
    const item = await screen.findByRole("link", { name: /Administração/ });
    expect(item).toHaveAttribute("href", "/admin");
    expect(await within(item).findByText("3 usuários, 4 veículos")).toBeInTheDocument();
    unmount();

    apiFalsa({ "GET /api/auth/eu": () => json(200, PAULA) });
    renderizarApp("/mais");
    await screen.findByRole("heading", { name: "Mais" });
    expect(screen.queryByRole("link", { name: /Administração/ })).not.toBeInTheDocument();
  });
});

describe("Usuários e veículos", () => {
  it("lista usuários e veículos como no PDF", async () => {
    apiFalsa(BASE);
    renderizarApp("/admin");
    const lista = await screen.findByRole("list", { name: "Usuários" });
    const [paula, rafael, carla] = within(lista).getAllByRole("listitem");
    expect(paula.textContent).toBe("PBPaula Bastos (você)1 veículo, acesso hojeAdmin");
    expect(rafael.textContent).toBe("RSRafael Souza1 veículo, acesso em 21/09/2026Padrão");
    expect(carla.textContent).toBe("CMCarla Mendes2 veículos, conta desativadaPadrão");
    expect(within(rafael).getByRole("link")).toHaveAttribute("href", "/admin/usuarios/2");
    expect(screen.getByRole("button", { name: "Todos (3)" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Admin (1)" })).toBeInTheDocument();
    const veiculos = await screen.findByRole("list", { name: "Veículos" });
    expect(within(veiculos).getByRole("link").textContent).toContain("BRA2E19, de Rafael Souza");
    expect(within(veiculos).getByRole("link")).toHaveAttribute("href", "/veiculos/20");
    expect(screen.getByRole("link", { name: "Criar conta" })).toHaveAttribute("href", "/admin/usuarios/novo");
  });

  it("busca e filtro por perfil vão para o backend", async () => {
    const buscar = apiFalsa({
      ...BASE,
      "GET /api/admin/usuarios?busca=rafa&pagina=1&por_pagina=30": () => paginaUsuarios([RAFAEL]),
      "GET /api/admin/usuarios?busca=rafa&perfil=padrao&pagina=1&por_pagina=30": () => paginaUsuarios([RAFAEL]),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin");
    await screen.findByRole("list", { name: "Usuários" });
    await usuario.type(screen.getByRole("searchbox", { name: "Buscar por nome ou e-mail" }), "rafa{Enter}");
    await screen.findByText("Rafael Souza");
    await usuario.click(screen.getByRole("button", { name: /^Padrão/ }));
    await screen.findByRole("button", { name: /^Padrão/, pressed: true });
    expect(chamadasPara(buscar, "GET /api/admin/usuarios?busca=rafa&perfil=padrao&pagina=1&por_pagina=30"))
      .toHaveLength(1);
  });

  it("perfil padrão que digitar o endereço não vê a área", async () => {
    apiFalsa({ "GET /api/auth/eu": () => json(200, PAULA) });
    renderizarApp("/admin");
    expect(await screen.findByText("Área restrita a administradores.")).toBeInTheDocument();
  });
});

describe("Usuário", () => {
  const DETALHE: UsuarioDetalheAdmin = { usuario: RAFAEL, veiculos: [ARGO] };

  it("altera perfil e salva", async () => {
    const buscar = apiFalsa({
      ...BASE,
      "GET /api/admin/usuarios/2": () => json(200, DETALHE),
      "PUT /api/admin/usuarios/2": (corpo) => json(200, { ...DETALHE, usuario: { ...RAFAEL, ...(corpo as object) } }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin/usuarios/2");
    await screen.findByRole("heading", { name: "Rafael Souza" });
    expect(screen.getByText("Último acesso em 21/09/2026")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Salvar alterações" })).toBeDisabled();
    await usuario.click(screen.getByRole("radio", { name: "Admin" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText("Alterações salvas.")).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "PUT /api/admin/usuarios/2");
    expect(JSON.parse(opcoes.body as string)).toEqual({ perfil: "admin", ativo: true });
    expect(screen.getByRole("link", { name: /Fiat Argo 2021/ })).toHaveAttribute("href", "/veiculos/20");
  });

  it("desativar pede confirmação", async () => {
    const buscar = apiFalsa({
      ...BASE,
      "GET /api/admin/usuarios/2": () => json(200, DETALHE),
      "PUT /api/admin/usuarios/2": () => json(200, { ...DETALHE, usuario: { ...RAFAEL, ativo: false } }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin/usuarios/2");
    await usuario.click(await screen.findByRole("switch", { name: "Conta ativa" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));
    const dialogo = await screen.findByRole("alertdialog");
    expect(chamadasPara(buscar, "PUT /api/admin/usuarios/2")).toHaveLength(0);
    await usuario.click(within(dialogo).getByRole("button", { name: "Desativar" }));
    expect(await screen.findByText("Conta desativada. A pessoa saiu de todos os aparelhos.")).toBeInTheDocument();
  });

  it("envia link para nova senha sem mostrar senha", async () => {
    apiFalsa({
      ...BASE,
      "GET /api/admin/usuarios/2": () => json(200, DETALHE),
      "POST /api/admin/usuarios/2/enviar-link": () => json(200, {
        tipo: "recuperacao", mensagem: "Link para criar uma senha nova enviado para rafael.souza@email.com." }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin/usuarios/2");
    await usuario.click(await screen.findByRole("button", { name: "Enviar link para nova senha" }));
    expect(await screen.findByText(/enviado para rafael.souza@email.com/)).toBeInTheDocument();
  });

  it("a própria conta não tem controles de perfil e situação", async () => {
    apiFalsa({ ...BASE, "GET /api/admin/usuarios/1": () => json(200, { usuario: LINHA_PAULA, veiculos: [] }) });
    renderizarApp("/admin/usuarios/1");
    expect(await screen.findByText(/Esta é a sua conta/)).toBeInTheDocument();
    expect(screen.queryByRole("switch")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Salvar alterações" })).not.toBeInTheDocument();
  });

  it("mostra o erro do backend (ex.: último admin)", async () => {
    apiFalsa({
      ...BASE,
      "GET /api/admin/usuarios/2": () => json(200, { ...DETALHE, usuario: { ...RAFAEL, perfil: "admin" } }),
      "PUT /api/admin/usuarios/2": () => json(409, {
        mensagem: "Não é possível desativar nem rebaixar o último administrador ativo." }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin/usuarios/2");
    await usuario.click(await screen.findByRole("radio", { name: "Padrão" }));
    await usuario.click(screen.getByRole("button", { name: "Salvar alterações" }));
    expect(await screen.findByText(/último administrador ativo/)).toBeInTheDocument();
  });
});

describe("Criar conta (+)", () => {
  it("valida, cria e abre o usuário com a mensagem do convite", async () => {
    const buscar = apiFalsa({
      ...BASE,
      "POST /api/admin/usuarios": () => json(201, {
        detalhe: { usuario: { ...CARLA, ativo: true, ultimo_acesso: null }, veiculos: [] },
        mensagem: "Convite enviado para carla@email.com." }),
      "GET /api/admin/usuarios/3": () => json(200, {
        usuario: { ...CARLA, ativo: true, ultimo_acesso: null }, veiculos: [] }),
    });
    const usuario = userEvent.setup();
    renderizarApp("/admin/usuarios/novo");
    await usuario.click(await screen.findByRole("button", { name: "Criar conta e enviar convite" }));
    expect(screen.getByText("Informe o nome da pessoa.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/admin/usuarios")).toHaveLength(0);
    await usuario.type(screen.getByLabelText("Nome"), "Carla Mendes");
    await usuario.type(screen.getByLabelText("E-mail"), "carla@email.com");
    await usuario.click(screen.getByRole("button", { name: "Criar conta e enviar convite" }));
    expect(await screen.findByText("Convite enviado para carla@email.com.")).toBeInTheDocument();
    expect(screen.getByText("Nunca entrou (convite ainda não aceito)")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reenviar convite" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/admin/usuarios");
    expect(JSON.parse(opcoes.body as string)).toEqual({ nome: "Carla Mendes", email: "carla@email.com" });
  });
});

describe("textos de acesso", () => {
  it("hoje, outro dia e nunca, no fuso de Brasília", () => {
    expect(textoDoAcesso({ ultimo_acesso: null })).toBe("nunca entrou");
    // 23h30 de 21/09 em Brasília é 02h30 de 22/09 em UTC: conta como 21/09.
    expect(textoDoAcesso({ ultimo_acesso: "2026-09-22T02:30:00Z" }, "2026-10-01")).toBe("acesso em 21/09/2026");
    expect(textoDoAcesso({ ultimo_acesso: "2026-10-01T12:00:00-03:00" }, "2026-10-01")).toBe("acesso hoje");
    expect(resumoDoUsuario({ ...CARLA }, "2026-10-01")).toBe("2 veículos, conta desativada");
  });
});
