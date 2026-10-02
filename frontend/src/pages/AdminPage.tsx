import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import AvatarInicial from "../components/AvatarInicial";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeCarro, IconeEscudo, IconeLupa, IconeMaisSinal, IconeSeta } from "../components/Icones";
import { resumoDoUsuario, SeloPerfil } from "../components/PecasAdmin";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { ErroDaApi } from "../services/apiCliente";
import { listarTodosOsVeiculos, listarUsuarios } from "../services/adminService";
import type { PaginaUsuariosAdmin, UsuarioAdmin, VeiculoComDono } from "../types/admin";
import type { Perfil } from "../types/usuario";
import { formatarPlaca } from "../utils/formatos";

const POR_PAGINA = 30;

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof ErroDaApi ? falha.message : padrao;
}

/** Campo de busca que só procura ao enviar (Enter ou lupa), sem uma consulta a cada letra. */
function Busca({ rotulo, valor, aoBuscar }: { rotulo: string; valor: string; aoBuscar: (texto: string) => void }) {
  const [texto, setTexto] = useState(valor);
  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    aoBuscar(texto.trim());
  }
  return (
    <form className="busca" role="search" onSubmit={aoEnviar}>
      <input className="busca__entrada" type="search" aria-label={rotulo} placeholder={rotulo}
        value={texto} onChange={(e) => setTexto(e.target.value)} maxLength={100} />
      <button type="submit" className="busca__botao" aria-label="Buscar"><IconeLupa /></button>
    </form>
  );
}

function ListaDeUsuarios({ busca, perfil, aoContar }: {
  busca: string; perfil: Perfil | null; aoContar: (p: PaginaUsuariosAdmin) => void;
}) {
  const { usuario: eu } = useAuth();
  const [itens, setItens] = useState<UsuarioAdmin[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarUsuarios(busca, perfil, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setTotal(r.total);
      setPagina(numero);
      aoContar(r);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os usuários."));
    } finally {
      setCarregando(false);
    }
  }, [busca, perfil, aoContar]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return <Carregando />;
  if (total === 0) {
    return <section className="cartao"><p className="texto-suave">Nenhum usuário encontrado.</p></section>;
  }
  return (
    <>
      <ul className="cartao lista-simples" aria-label="Usuários">
        {itens.map((u) => (
          <li key={u.id}>
            <Link to={`/admin/usuarios/${u.id}`} className="lista-simples__item">
              <AvatarInicial nome={u.nome} />
              <span className="lista-simples__texto">
                <span className="lista-simples__titulo">
                  {u.nome}{u.id === eu?.id && <span className="texto-suave"> (você)</span>}
                </span>
                <span className={u.ativo ? "texto-suave" : "alerta-texto alerta-texto--alerta"}>
                  {resumoDoUsuario(u)}
                </span>
              </span>
              <SeloPerfil perfil={u.perfil} />
            </Link>
          </li>
        ))}
      </ul>
      {itens.length < total && (
        <button type="button" className="botao botao--secundario botao--abaixo" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
    </>
  );
}

function ListaDeVeiculos() {
  const [busca, setBusca] = useState("");
  const [itens, setItens] = useState<VeiculoComDono[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarTodosOsVeiculos(busca, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setTotal(r.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os veículos."));
    } finally {
      setCarregando(false);
    }
  }, [busca]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  return (
    <section aria-label="Todos os veículos">
      <h2 className="rotulo-secao">Todos os veículos</h2>
      <Busca rotulo="Buscar por placa, modelo ou dono" valor={busca} aoBuscar={setBusca} />
      {erro ? <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />
        : total === null ? <Carregando />
          : total === 0 ? <section className="cartao"><p className="texto-suave">Nenhum veículo encontrado.</p></section>
            : (
              <>
                <ul className="cartao lista-simples" aria-label="Veículos">
                  {itens.map((v) => (
                    <li key={v.id}>
                      <Link to={`/veiculos/${v.id}`} className="lista-simples__item">
                        <span className="pendencia__icone pendencia__icone--neutro"><IconeCarro /></span>
                        <span className="lista-simples__texto">
                          <span className="lista-simples__titulo">{v.marca} {v.modelo} {v.ano}</span>
                          <span className="texto-suave">
                            {formatarPlaca(v.placa)}, de {v.dono_nome}{!v.ativo && " (inativo)"}
                          </span>
                        </span>
                        <IconeSeta tamanho={20} />
                      </Link>
                    </li>
                  ))}
                </ul>
                {itens.length < total && (
                  <button type="button" className="botao botao--secundario" disabled={carregando}
                    onClick={() => void carregar(pagina + 1)}>
                    {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
                  </button>
                )}
              </>
            )}
    </section>
  );
}

const FILTROS: { valor: Perfil | null; rotulo: string }[] = [
  { valor: null, rotulo: "Todos" },
  { valor: "admin", rotulo: "Admin" },
  { valor: "padrao", rotulo: "Padrão" },
];

// "Usuários e veículos" (PDF, página 18). Só para admin: o backend responde 403 aos demais.
export default function AdminPage() {
  const { usuario } = useAuth();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const [parametros, setParametros] = useSearchParams();
  const busca = parametros.get("busca") ?? "";
  const pedido = parametros.get("perfil");
  const perfil: Perfil | null = pedido === "admin" || pedido === "padrao" ? pedido : null;
  const [contagem, setContagem] = useState<PaginaUsuariosAdmin["por_perfil"] | null>(null);
  const aoContar = useCallback((p: PaginaUsuariosAdmin) => setContagem(p.por_perfil), []);

  if (usuario?.perfil !== "admin") {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Usuários e veículos" voltarPara="/mais" />
        <Alerta tipo="erro">Área restrita a administradores.</Alerta>
      </main>
    );
  }

  function irPara(novo: { busca?: string; perfil?: Perfil | null }) {
    const valores: Record<string, string> = {};
    const b = novo.busca ?? busca;
    const p = novo.perfil === undefined ? perfil : novo.perfil;
    if (b) valores.busca = b;
    if (p) valores.perfil = p;
    setParametros(valores, { replace: true });
  }

  function rotuloDoFiltro(valor: Perfil | null, rotulo: string): string {
    if (!contagem) return rotulo;
    const n = valor === null ? contagem.admin + contagem.padrao : contagem[valor];
    return `${rotulo} (${n})`;
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Usuários e veículos" voltarPara="/mais" acao={
        <Link to="/admin/usuarios/novo" className="botao-redondo botao-redondo--grande" aria-label="Criar conta">
          <IconeMaisSinal />
        </Link>
      } />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      <section className="faixa-admin faixa-admin--escura">
        <IconeEscudo />
        <div>
          <p className="faixa-admin__titulo">Você está como administrador</p>
          <p>Vê os veículos e registros de todos os usuários. Quem tem perfil padrão vê só o que é seu.</p>
        </div>
      </section>

      <Busca key={busca} rotulo="Buscar por nome ou e-mail" valor={busca} aoBuscar={(b) => irPara({ busca: b })} />
      <div className="opcoes opcoes--rolagem" role="group" aria-label="Filtrar por perfil">
        {FILTROS.map(({ valor, rotulo }) => (
          <button key={rotulo} type="button" aria-pressed={perfil === valor}
            className={`opcao${perfil === valor ? " opcao--ativa" : ""}`}
            onClick={() => irPara({ perfil: valor })}>
            {rotuloDoFiltro(valor, rotulo)}
          </button>
        ))}
      </div>

      <h2 className="rotulo-secao">Usuários</h2>
      <ListaDeUsuarios key={`${busca}-${perfil}`} busca={busca} perfil={perfil} aoContar={aoContar} />
      <ListaDeVeiculos />
    </main>
  );
}
