import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { convidarUsuario } from "../services/adminService";
import { erroEmail, erroObrigatorio, soErros } from "../utils/validacao";

// Botão "+" de "Usuários e veículos": cria a conta de outra pessoa com perfil
// padrão. Ninguém define senha aqui: a pessoa recebe um convite por e-mail
// (link de uso único) e cria a própria senha.
export default function AdminConvitePage() {
  const { usuario } = useAuth();
  const navegar = useNavigate();
  const [nome, setNome] = useState("");
  const [email, setEmail] = useState("");
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  if (usuario?.perfil !== "admin") {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Criar conta" voltarPara="/mais" />
        <Alerta tipo="erro">Área restrita a administradores.</Alerta>
      </main>
    );
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros = soErros({
      nome: erroObrigatorio(nome, "Informe o nome da pessoa."),
      email: erroEmail(email),
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    await enviar(async () => {
      const criado = await convidarUsuario(nome, email);
      navegar(`/admin/usuarios/${criado.detalhe.usuario.id}`, { state: { mensagem: criado.mensagem } });
    });
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Criar conta" voltarPara="/admin" estilo="grande" />
        <p className="subtitulo">
          A conta começa com perfil padrão. A pessoa recebe um convite por e-mail para criar a
          própria senha; você não vê nem define a senha dela.
        </p>
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        <form onSubmit={aoEnviar} noValidate>
          <CampoTexto rotulo="Nome" autoComplete="off" value={nome} maxLength={120}
            onChange={(e) => setNome(e.target.value)} erro={errosCampo.nome} />
          <CampoTexto rotulo="E-mail" type="email" inputMode="email" autoComplete="off"
            placeholder="nome@email.com" value={email} onChange={(e) => setEmail(e.target.value)}
            erro={errosCampo.email} />
          <BotaoEnviar enviando={enviando} textoEnviando="Criando…">Criar conta e enviar convite</BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
