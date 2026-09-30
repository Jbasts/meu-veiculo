// Fluxos de conta nas telas: entrar, criar conta, recuperar e trocar senha, sair.

import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { apiFalsa, chamadasPara, json, PAULA, renderizarApp } from "../tests/apiFalsa";

const NAO_LOGADO = { "GET /api/auth/eu": () => json(401, { mensagem: "Entre na sua conta.", campos: null }) };
const LOGADO = { "GET /api/auth/eu": () => json(200, PAULA) };

beforeEach(() => {
  window.history.replaceState(null, "", "/");
});

describe("proteção das telas", () => {
  it("quem não entrou vai para a tela Entrar", async () => {
    apiFalsa(NAO_LOGADO);
    renderizarApp("/conta");
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
  });

  it("quem já entrou e abre Entrar vai para o início", async () => {
    apiFalsa(LOGADO);
    renderizarApp("/entrar");
    expect(await screen.findByRole("heading", { name: "Olá, Paula" })).toBeInTheDocument();
  });
});

describe("Entrar", () => {
  it("entra e vai para o início", async () => {
    const buscar = apiFalsa({ ...NAO_LOGADO, "POST /api/auth/entrar": () => json(200, PAULA) });
    renderizarApp("/entrar");
    await userEvent.type(await screen.findByLabelText("E-mail"), "paula@email.com");
    await userEvent.type(screen.getByLabelText("Senha"), "meu carro azul 2020");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByRole("heading", { name: "Olá, Paula" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/auth/entrar");
    expect(JSON.parse(opcoes.body as string)).toEqual({
      email: "paula@email.com",
      senha: "meu carro azul 2020",
    });
  });

  it("mostra a mensagem do servidor quando a senha está errada", async () => {
    apiFalsa({
      ...NAO_LOGADO,
      "POST /api/auth/entrar": () => json(401, { mensagem: "E-mail ou senha incorretos.", campos: null }),
    });
    renderizarApp("/entrar");
    await userEvent.type(await screen.findByLabelText("E-mail"), "paula@email.com");
    await userEvent.type(screen.getByLabelText("Senha"), "errada123");
    await userEvent.click(screen.getByRole("button", { name: "Entrar" }));
    expect(await screen.findByText("E-mail ou senha incorretos.")).toBeInTheDocument();
  });

  it("valida os campos antes de enviar", async () => {
    const buscar = apiFalsa(NAO_LOGADO);
    renderizarApp("/entrar");
    await userEvent.click(await screen.findByRole("button", { name: "Entrar" }));
    expect(screen.getByText("Informe o e-mail.")).toBeInTheDocument();
    expect(screen.getByText("Informe a senha.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/auth/entrar")).toHaveLength(0);
  });

  it("não envia duas vezes com dois cliques rápidos", async () => {
    let liberar: (r: Response) => void = () => undefined;
    const buscar = apiFalsa({
      ...NAO_LOGADO,
      "POST /api/auth/entrar": () => new Promise<Response>((r) => (liberar = r)),
    });
    renderizarApp("/entrar");
    await userEvent.type(await screen.findByLabelText("E-mail"), "paula@email.com");
    await userEvent.type(screen.getByLabelText("Senha"), "meu carro azul 2020");
    const botao = screen.getByRole("button", { name: "Entrar" });
    await userEvent.click(botao);
    await userEvent.click(screen.getByRole("button", { name: "Entrando…" }));
    expect(chamadasPara(buscar, "POST /api/auth/entrar")).toHaveLength(1);
    liberar(json(200, PAULA));
    expect(await screen.findByRole("heading", { name: "Olá, Paula" })).toBeInTheDocument();
  });

  it("mostra e esconde a senha no botão de olho", async () => {
    apiFalsa(NAO_LOGADO);
    renderizarApp("/entrar");
    const senha = await screen.findByLabelText("Senha");
    expect(senha).toHaveAttribute("type", "password");
    await userEvent.click(screen.getByRole("button", { name: "Mostrar senha" }));
    expect(senha).toHaveAttribute("type", "text");
  });
});

describe("Criar conta", () => {
  async function preencher(confirmacao = "meu carro azul 2020") {
    await userEvent.type(await screen.findByLabelText("Nome"), "Paula Bastos");
    await userEvent.type(screen.getByLabelText("E-mail"), "paula@email.com");
    await userEvent.type(screen.getByLabelText("Senha"), "meu carro azul 2020");
    await userEvent.type(screen.getByLabelText("Confirmar senha"), confirmacao);
    await userEvent.click(screen.getByRole("button", { name: "Criar conta" }));
  }

  it("cria a conta e entra", async () => {
    const buscar = apiFalsa({ ...NAO_LOGADO, "POST /api/auth/cadastro": () => json(201, PAULA) });
    renderizarApp("/criar-conta");
    await preencher();
    expect(await screen.findByRole("heading", { name: "Olá, Paula" })).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/auth/cadastro");
    expect(JSON.parse(opcoes.body as string)).not.toHaveProperty("perfil");
  });

  it("avisa quando a confirmação é diferente", async () => {
    const buscar = apiFalsa(NAO_LOGADO);
    renderizarApp("/criar-conta");
    await preencher("outra coisa");
    expect(screen.getByText("A confirmação não é igual à senha.")).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/auth/cadastro")).toHaveLength(0);
  });

  it("mostra no campo o erro devolvido pelo servidor", async () => {
    const mensagem = "Este e-mail já está cadastrado.";
    apiFalsa({
      ...NAO_LOGADO,
      "POST /api/auth/cadastro": () => json(409, { mensagem, campos: { email: mensagem } }),
    });
    renderizarApp("/criar-conta");
    await preencher();
    const campoEmail = await screen.findByLabelText("E-mail");
    await waitFor(() => expect(campoEmail).toHaveAttribute("aria-invalid", "true"));
    expect(screen.getAllByText(mensagem)).toHaveLength(2); // aviso geral + campo
  });
});

describe("Recuperar senha", () => {
  it("mostra a mesma confirmação, exista ou não a conta", async () => {
    const mensagem = "Se houver uma conta com esse e-mail, enviamos um link.";
    apiFalsa({ ...NAO_LOGADO, "POST /api/auth/recuperar-senha": () => json(202, { mensagem }) });
    renderizarApp("/esqueci-senha");
    await userEvent.type(await screen.findByLabelText("E-mail"), "paula@email.com");
    await userEvent.click(screen.getByRole("button", { name: "Enviar link" }));
    expect(await screen.findByText(mensagem)).toBeInTheDocument();
  });

  it("sem token no endereço, avisa que o link está incompleto", async () => {
    apiFalsa(NAO_LOGADO);
    renderizarApp("/redefinir-senha");
    expect(await screen.findByText(/link está incompleto/)).toBeInTheDocument();
  });

  it("envia o token do link, tira o token do endereço e confirma", async () => {
    window.history.replaceState(null, "", "/redefinir-senha#token=abc123");
    const buscar = apiFalsa({
      ...NAO_LOGADO,
      "POST /api/auth/redefinir-senha": () => json(200, { mensagem: "Senha redefinida." }),
    });
    renderizarApp("/redefinir-senha");
    await userEvent.type(await screen.findByLabelText("Nova senha"), "frase nova e comprida");
    await userEvent.type(screen.getByLabelText("Confirmar nova senha"), "frase nova e comprida");
    expect(window.location.hash).toBe("");
    await userEvent.click(screen.getByRole("button", { name: "Salvar senha nova" }));
    expect(await screen.findByText("Senha redefinida.")).toBeInTheDocument();
    const [[, opcoes]] = chamadasPara(buscar, "POST /api/auth/redefinir-senha");
    expect(JSON.parse(opcoes.body as string).token).toBe("abc123");
  });
});

describe("Conta e senha", () => {
  it("troca a senha e limpa os campos", async () => {
    apiFalsa({
      ...LOGADO,
      "POST /api/auth/alterar-senha": () => json(200, { mensagem: "Senha alterada." }),
    });
    renderizarApp("/conta");
    await userEvent.type(await screen.findByLabelText("Senha atual"), "meu carro azul 2020");
    await userEvent.type(screen.getByLabelText("Nova senha"), "frase nova e comprida");
    await userEvent.type(screen.getByLabelText("Confirmar nova senha"), "frase nova e comprida");
    await userEvent.click(screen.getByRole("button", { name: "Salvar nova senha" }));
    expect(await screen.findByText("Senha alterada.")).toBeInTheDocument();
    expect(screen.getByLabelText("Senha atual")).toHaveValue("");
  });

  it("sair encerra a sessão e volta para Entrar", async () => {
    let logado = true;
    const buscar = apiFalsa({
      "GET /api/auth/eu": () => (logado ? json(200, PAULA) : json(401, { mensagem: "", campos: null })),
      "POST /api/auth/sair": () => {
        logado = false;
        return json(204, null);
      },
    });
    renderizarApp("/conta");
    await userEvent.click(await screen.findByRole("button", { name: "Sair" }));
    expect(await screen.findByRole("heading", { name: "Entrar" })).toBeInTheDocument();
    expect(chamadasPara(buscar, "POST /api/auth/sair")).toHaveLength(1);
    expect(screen.queryByText("Paula Bastos")).not.toBeInTheDocument();
  });
});
