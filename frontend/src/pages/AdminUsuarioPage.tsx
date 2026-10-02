import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useParams } from "react-router";

import Alerta from "../components/Alerta";
import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { Chave, DialogoConfirmacao, GrupoOpcoes } from "../components/Formulario";
import { IconeCarro, IconeEscudo, IconeSeta } from "../components/Icones";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { alterarUsuario, enviarLinkDeSenha, obterUsuario } from "../services/adminService";
import { ErroDaApi } from "../services/apiCliente";
import type { UsuarioDetalheAdmin } from "../types/admin";
import type { Perfil } from "../types/usuario";
import { diaDoInstante, formatarDataIso } from "../utils/datas";
import { formatarPlaca } from "../utils/formatos";

const PERFIS: { valor: Perfil; rotulo: string }[] = [
  { valor: "padrao", rotulo: "Padrão" },
  { valor: "admin", rotulo: "Admin" },
];
const EXPLICACAO: Record<Perfil, string> = {
  padrao: "Vê apenas os próprios veículos e tudo o que está ligado a eles.",
  admin: "Vê e gerencia usuários, veículos e registros de todos.",
};

// "Usuário" (PDF, página 22): perfil, conta ativa, veículos e link para nova senha.
// O administrador nunca vê nem define a senha de outra pessoa.
export default function AdminUsuarioPage() {
  const { usuarioId } = useParams();
  const id = Number(usuarioId);
  const { usuario: eu } = useAuth();
  const local = useLocation();
  const mensagemInicial = (local.state as { mensagem?: string } | null)?.mensagem ?? null;
  const [detalhe, setDetalhe] = useState<UsuarioDetalheAdmin | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [perfil, setPerfil] = useState<Perfil>("padrao");
  const [ativo, setAtivo] = useState(true);
  const [sucesso, setSucesso] = useState<string | null>(mensagemInicial);
  const [confirmando, setConfirmando] = useState(false);
  const salvar = useEnvioFormulario();
  const link = useEnvioFormulario();

  const carregar = useCallback(async () => {
    if (!Number.isInteger(id) || id <= 0) {
      setErro("Usuário não encontrado.");
      return;
    }
    try {
      const dados = await obterUsuario(id);
      setDetalhe(dados);
      setPerfil(dados.usuario.perfil);
      setAtivo(dados.usuario.ativo);
      setErro(null);
    } catch (falha) {
      setErro(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o usuário.");
    }
  }, [id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (erro) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Usuário" voltarPara="/admin" />
        <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />
      </main>
    );
  }
  if (!detalhe) return <main className="conteudo conteudo--topo"><Carregando /></main>;

  const u = detalhe.usuario;
  const propriaConta = u.id === eu?.id;
  const mudou = perfil !== u.perfil || ativo !== u.ativo;

  async function gravar() {
    setConfirmando(false);
    setSucesso(null);
    await salvar.enviar(async () => {
      const novo = await alterarUsuario(u.id, perfil, ativo);
      setDetalhe(novo);
      setPerfil(novo.usuario.perfil);
      setAtivo(novo.usuario.ativo);
      setSucesso(!novo.usuario.ativo && u.ativo
        ? "Conta desativada. A pessoa saiu de todos os aparelhos."
        : "Alterações salvas.");
    });
  }

  async function mandarLink() {
    setSucesso(null);
    await link.enviar(async () => {
      setSucesso((await enviarLinkDeSenha(u.id)).mensagem);
    });
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Usuário" voltarPara="/admin" />
      {sucesso && <Alerta tipo="sucesso">{sucesso}</Alerta>}
      {(salvar.erroGeral || link.erroGeral) && <Alerta tipo="erro">{salvar.erroGeral ?? link.erroGeral}</Alerta>}

      <section className="perfil-usuario">
        <AvatarInicial nome={u.nome} />
        <div>
          <h1 className="titulo-pagina titulo-pagina--veiculo">{u.nome}</h1>
          <p className="texto-suave">{u.email}</p>
          <p className="texto-suave">
            {u.ultimo_acesso
              ? `Último acesso em ${formatarDataIso(diaDoInstante(u.ultimo_acesso))}`
              : "Nunca entrou (convite ainda não aceito)"}
          </p>
        </div>
      </section>

      {propriaConta ? (
        <Alerta tipo="info">
          Esta é a sua conta. O perfil e a situação dela só podem ser mudados por outro
          administrador, para você não perder o acesso sem querer.
        </Alerta>
      ) : (
        <>
          <GrupoOpcoes rotulo="Perfil de acesso" opcoes={PERFIS} valor={perfil} aoMudar={setPerfil}
            erro={salvar.errosCampo.perfil} />
          <p className="caixa-info faixa-admin__dica"><IconeEscudo tamanho={20} /> {EXPLICACAO[perfil]}</p>
          <Chave titulo="Conta ativa"
            descricao={ativo ? "Pode entrar normalmente no app."
              : "Não consegue entrar; sai de todos os aparelhos ao salvar."}
            ligada={ativo} aoMudar={setAtivo} />
        </>
      )}

      <h2 className="titulo-secao">Veículos ({detalhe.veiculos.length})</h2>
      {detalhe.veiculos.length === 0 ? (
        <p className="texto-suave">Nenhum veículo cadastrado.</p>
      ) : (
        <ul className="cartao lista-simples" aria-label="Veículos do usuário">
          {detalhe.veiculos.map((v) => (
            <li key={v.id}>
              <Link to={`/veiculos/${v.id}`} className="lista-simples__item">
                <span className="pendencia__icone pendencia__icone--neutro"><IconeCarro /></span>
                <span className="lista-simples__texto">
                  <span className="lista-simples__titulo">{v.marca} {v.modelo} {v.ano}</span>
                  <span className="texto-suave">{formatarPlaca(v.placa)}{!v.ativo && " (inativo)"}</span>
                </span>
                <IconeSeta tamanho={20} />
              </Link>
            </li>
          ))}
        </ul>
      )}

      {!propriaConta && (
        <button type="button" className="botao botao--primario" disabled={!mudou || salvar.enviando}
          onClick={() => (u.ativo && !ativo ? setConfirmando(true) : void gravar())}>
          {salvar.enviando ? "Salvando…" : "Salvar alterações"}
        </button>
      )}
      {u.ativo && (
        <button type="button" className="botao botao--secundario botao--espaco" disabled={link.enviando}
          onClick={() => void mandarLink()}>
          {link.enviando ? "Enviando…" : u.ultimo_acesso ? "Enviar link para nova senha" : "Reenviar convite"}
        </button>
      )}
      <p className="texto-suave">
        O link vai para o e-mail da pessoa e só pode ser usado uma vez. Você não vê nem define a senha.
      </p>

      {confirmando && (
        <DialogoConfirmacao titulo={`Desativar a conta de ${u.nome}?`} textoConfirmar="Desativar" perigo
          ocupado={salvar.enviando} aoCancelar={() => setConfirmando(false)} aoConfirmar={() => void gravar()}>
          <p>
            A pessoa sai de todos os aparelhos na hora e não consegue entrar até a conta ser
            reativada. Nada é apagado: veículos e registros continuam guardados.
          </p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
