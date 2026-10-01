import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoArea, CampoSelecao, DialogoConfirmacao } from "../components/Formulario";
import { IconeLapis, IconeManutencao, IconeMaisSinal } from "../components/Icones";
import { SeloGravidade, TOM_DO_STATUS } from "../components/PecasDiagnostico";
import { FotoProtegida } from "../components/PecasVeiculo";
import SeloStatus from "../components/SeloStatus";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  adicionarNota,
  apagarDiagnostico,
  apagarNota,
  definirAcompanhamento,
  descartarDiagnostico,
  obterDiagnostico,
  reabrirDiagnostico,
  resolverComManutencaoExistente,
} from "../services/diagnosticoService";
import { listarFotos } from "../services/fotoService";
import { listarManutencoes } from "../services/manutencaoService";
import { emAberto, ROTULO_STATUS, type DiagnosticoDetalhe, type Nota } from "../types/diagnostico";
import { rotuloSistema, type Manutencao } from "../types/manutencao";
import type { Foto, Veiculo } from "../types/veiculo";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarDinheiro, formatarKm } from "../utils/formatos";

type Dialogo = null | "descartar" | "existente" | "apagar" | { nota: Nota };

function IconeEscudo() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" aria-hidden="true" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z" />
    </svg>
  );
}

/** "Adicionar anotação": texto e data (hoje, por padrão). */
function NovaAnotacao({ aoSalvar, aoCancelar }: {
  aoSalvar: (texto: string, data: string) => Promise<string | null>; aoCancelar: () => void;
}) {
  const hoje = hojeIso();
  const [texto, setTexto] = useState("");
  const [data, setData] = useState(hoje);
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    if (salvando) return;
    if (!texto.trim()) {
      setErro("Escreva a anotação.");
      return;
    }
    setSalvando(true);
    const problema = await aoSalvar(texto.trim(), data);
    setSalvando(false);
    setErro(problema);
  }

  return (
    <form className="cartao nova-anotacao" onSubmit={aoEnviar} noValidate aria-label="Nova anotação">
      <CampoArea rotulo="Anotação" value={texto} maxLength={2000} erro={erro}
        placeholder="O que você observou, o que a oficina disse, orçamento..."
        onChange={(e) => setTexto(e.target.value)} />
      <CampoTexto rotulo="Data da anotação" type="date" max={hoje} value={data}
        onChange={(e) => setData(e.target.value)} />
      <div className="dupla dupla--botoes">
        <button type="button" className="botao botao--secundario" onClick={aoCancelar} disabled={salvando}>
          Cancelar
        </button>
        <button type="submit" className="botao botao--primario" disabled={salvando}>
          {salvando ? "Salvando…" : "Salvar anotação"}
        </button>
      </div>
    </form>
  );
}

// Detalhe de um diagnóstico (PDF, página 8): dados, aviso de garantia,
// anotações, fotos e as ações de resolver, observar, descartar e reabrir.
export default function DiagnosticoDetalhePage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { diagnosticoId } = useParams();
  const id = Number(diagnosticoId);
  const [diagnostico, setDiagnostico] = useState<DiagnosticoDetalhe | null>(null);
  const [fotos, setFotos] = useState<Foto[]>([]);
  const [erroDados, setErroDados] = useState<string | null>(null);

  const carregarDados = useCallback(async (veiculoId: number) => {
    try {
      const detalhe = await obterDiagnostico(veiculoId, id);
      setDiagnostico(detalhe);
      setErroDados(null);
      if (detalhe.total_fotos > 0) {
        setFotos((await listarFotos(veiculoId, 1, 30, { diagnosticoId: id })).itens);
      }
    } catch (falha) {
      setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o diagnóstico.");
    }
  }, [id]);

  useEffect(() => {
    if (veiculo?.id) void carregarDados(veiculo.id);
  }, [veiculo?.id, carregarDados]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Diagnóstico" voltarPara="/diagnostico" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  if (erroDados || !diagnostico) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Diagnóstico" voltarPara={`/veiculos/${veiculo.id}/diagnosticos`} />
        {erroDados
          ? <ErroComNovaTentativa mensagem={erroDados} aoTentar={() => void carregarDados(veiculo.id)} />
          : <Carregando />}
      </main>
    );
  }
  return <Detalhe veiculo={veiculo} diagnostico={diagnostico} fotos={fotos} aoMudar={setDiagnostico} />;
}

function Detalhe({ veiculo, diagnostico: d, fotos, aoMudar }: {
  veiculo: Veiculo; diagnostico: DiagnosticoDetalhe; fotos: Foto[];
  aoMudar: (novo: DiagnosticoDetalhe) => void;
}) {
  const navegar = useNavigate();
  const local = useLocation();
  const { recarregar: recarregarLista } = useVeiculos();
  const [mensagem, setMensagem] = useState<string | null>(
    (local.state as { mensagem?: string } | null)?.mensagem ?? null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [anotando, setAnotando] = useState(false);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [motivo, setMotivo] = useState("");
  const [manutencoes, setManutencoes] = useState<Manutencao[] | null>(null);
  const [escolhida, setEscolhida] = useState("");
  const [erroEscolha, setErroEscolha] = useState<string | null>(null);

  const base = `/veiculos/${veiculo.id}`;
  const caminho = `${base}/diagnosticos/${d.id}`;
  const aberto = emAberto(d.status);
  const prevista = aberto && d.manutencao?.status === "agendada" ? d.manutencao : null;
  const podeAlterar = veiculo.ativo;

  // A lista de manutenções só é buscada quando a pessoa abre "Usar uma manutenção já registrada".
  useEffect(() => {
    if (dialogo !== "existente" || manutencoes !== null) return;
    let cancelado = false;
    listarManutencoes(veiculo.id, { porPagina: 100 })
      .then((pagina) => {
        if (!cancelado) setManutencoes(pagina.itens);
      })
      .catch((falha) => {
        if (!cancelado) {
          setErroEscolha(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar as manutenções.");
          setManutencoes([]);
        }
      });
    return () => {
      cancelado = true;
    };
  }, [dialogo, manutencoes, veiculo.id]);

  /** Executa uma ação e mostra o diagnóstico atualizado (ou o erro). */
  async function executar(acao: () => Promise<DiagnosticoDetalhe>, sucesso: string): Promise<boolean> {
    if (ocupado) return false;
    setOcupado(true);
    setErroAcao(null);
    setMensagem(null);
    try {
      aoMudar(await acao());
      setMensagem(sucesso);
      setDialogo(null);
      return true;
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Algo deu errado. Tente de novo.");
      setDialogo(null);
      return false;
    } finally {
      setOcupado(false);
    }
  }

  async function salvarAnotacao(texto: string, data: string): Promise<string | null> {
    try {
      aoMudar(await adicionarNota(veiculo.id, d.id, texto, data));
      setAnotando(false);
      setMensagem("Anotação adicionada.");
      return null;
    } catch (falha) {
      if (falha instanceof ErroDaApi) return falha.campos.texto ?? falha.campos.data ?? falha.message;
      return "Não foi possível salvar a anotação.";
    }
  }

  async function usarExistente() {
    if (!escolhida) {
      setErroEscolha("Escolha a manutenção.");
      return;
    }
    const escolhidaAgendada = manutencoes?.find((m) => String(m.id) === escolhida)?.status === "agendada";
    await executar(() => resolverComManutencaoExistente(veiculo.id, d.id, Number(escolhida)),
      escolhidaAgendada ? "Manutenção agendada ligada ao diagnóstico." : "Diagnóstico resolvido.");
  }

  async function apagar() {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    try {
      await apagarDiagnostico(veiculo.id, d.id);
      if (d.quilometragem !== null) await recarregarLista();
      navegar(`${base}/diagnosticos`, { replace: true, state: { mensagem: "Diagnóstico apagado." } });
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setOcupado(false);
      setDialogo(null);
    }
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Diagnóstico" voltarPara={`${base}/diagnosticos${aberto ? "" : "?aba=resolvidos"}`}
        acao={podeAlterar ? (
          <Link to={`${caminho}/editar`} className="botao-icone" aria-label="Editar diagnóstico">
            <IconeLapis />
          </Link>
        ) : null} />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}

      <p className="linha-selos">
        <span className="selo selo--neutro">{rotuloSistema(d.sistema)}</span>
        <SeloGravidade gravidade={d.gravidade} />
        <SeloStatus tom={TOM_DO_STATUS[d.status]}>{ROTULO_STATUS[d.status]}</SeloStatus>
      </p>
      <h2 className="titulo-pagina titulo-pagina--veiculo">{d.titulo}</h2>

      <dl className="dados-dupla">
        <div>
          <dt className="texto-suave">Identificado em</dt>
          <dd>{formatarDataIso(d.data_identificacao)}</dd>
        </div>
        <div>
          <dt className="texto-suave">Quilometragem</dt>
          <dd>{d.quilometragem !== null ? formatarKm(d.quilometragem) : "Não informada"}</dd>
        </div>
      </dl>
      {d.descricao && <p className="texto-com-linhas">{d.descricao}</p>}

      {d.status === "resolvido" && d.manutencao && (
        <section className="cartao caixa-diagnostico caixa-diagnostico--ok" aria-label="Resolução">
          <p className="cartao__titulo">Resolvido em {formatarDataIso(d.data_resolucao ?? d.manutencao.data)}</p>
          <p>Com a manutenção “{d.manutencao.descricao}”, de {formatarDinheiro(d.manutencao.valor)}.</p>
          <Link to={`${base}/manutencoes/${d.manutencao.id}`} className="link">Ver manutenção</Link>
        </section>
      )}
      {d.status === "descartado" && (
        <section className="cartao caixa-diagnostico" aria-label="Descarte">
          <p className="cartao__titulo">
            Descartado{d.data_resolucao ? ` em ${formatarDataIso(d.data_resolucao)}` : ""}
          </p>
          <p className="texto-suave">{d.solucao ? `Motivo: ${d.solucao}` : "Nenhum motivo informado."}</p>
        </section>
      )}
      {prevista && (
        <section className="cartao caixa-diagnostico caixa-diagnostico--aviso" aria-label="Manutenção agendada">
          <p className="cartao__titulo">Manutenção agendada para {formatarDataIso(prevista.data)}</p>
          <p>
            “{prevista.descricao}”. Quando ela for marcada como realizada, este diagnóstico será
            resolvido automaticamente.
          </p>
          <Link to={`${base}/manutencoes/${prevista.id}`} className="link">Ver manutenção</Link>
        </section>
      )}

      {d.garantias.length > 0 && (
        <section className="cartao caixa-garantia" aria-label="Garantia">
          <IconeEscudo />
          <div>
            <p className="cartao__titulo">Há peça em garantia neste sistema</p>
            {d.garantias.map((g) => (
              <div key={g.manutencao_id} className="caixa-garantia__item">
                <p>{g.explicacao}</p>
                <Link to={`${base}/manutencoes/${g.manutencao_id}`} className="link">Ver manutenção</Link>
              </div>
            ))}
            <p className="texto-suave caixa-garantia__dica">
              Confira com a oficina se a garantia cobre este problema.
            </p>
          </div>
        </section>
      )}

      <h2 className="titulo-secao">Anotações</h2>
      {d.notas.length === 0 ? (
        <p className="texto-suave">Nenhuma anotação ainda.</p>
      ) : (
        <ol className="linha-tempo" aria-label="Anotações">
          {d.notas.map((nota) => (
            <li key={nota.id} className="linha-tempo__item">
              <span className="texto-suave linha-tempo__data">{formatarDataIso(nota.data)}</span>
              <p className="texto-com-linhas linha-tempo__texto">{nota.texto}</p>
              {podeAlterar && (
                <button type="button" className="botao-link linha-tempo__apagar"
                  aria-label={`Apagar anotação de ${formatarDataIso(nota.data)}`}
                  onClick={() => setDialogo({ nota })}>
                  Apagar
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
      {podeAlterar && (anotando
        ? <NovaAnotacao aoSalvar={salvarAnotacao} aoCancelar={() => setAnotando(false)} />
        : (
          <button type="button" className="botao botao--secundario botao--adicionar"
            onClick={() => setAnotando(true)}>
            <IconeMaisSinal tamanho={20} /> Adicionar anotação
          </button>
        ))}

      <div className="cabecalho-secao">
        <h2 className="titulo-secao">Fotos</h2>
        <span className="texto-suave">{d.total_fotos === 0 ? "Nenhuma" : d.total_fotos}</span>
      </div>
      <div className="tira-fotos">
        {podeAlterar && (
          <Link to={`${base}/fotos/nova?diagnostico=${d.id}`} className="tira-fotos__adicionar">
            <IconeMaisSinal />
            Adicionar
          </Link>
        )}
        {fotos.map((foto) => (
          <Link key={foto.id} to={`${base}/fotos/${foto.id}`} className="tira-fotos__item">
            <FotoProtegida veiculoId={veiculo.id} fotoId={foto.id}
              descricao={foto.legenda ?? `Foto de ${formatarDataIso(foto.data_foto)}`} />
          </Link>
        ))}
      </div>

      {podeAlterar && aberto && !prevista && (
        <>
          <Link to={`${base}/manutencoes/nova?diagnostico=${d.id}`} className="botao botao--primario">
            <IconeManutencao tamanho={20} /> Resolver com uma manutenção
          </Link>
          <button type="button" className="botao botao--secundario botao--espaco"
            onClick={() => {
              setEscolhida("");
              setErroEscolha(null);
              setDialogo("existente");
            }}>
            Usar uma manutenção já registrada
          </button>
        </>
      )}
      {podeAlterar && aberto && (
        <div className="acoes-texto">
          <button type="button" className="botao-link" disabled={ocupado}
            onClick={() => void executar(
              () => definirAcompanhamento(veiculo.id, d.id, d.status === "aberto" ? "em_observacao" : "aberto"),
              d.status === "aberto" ? "Diagnóstico em observação." : "Diagnóstico marcado como aberto.")}>
            {d.status === "aberto" ? "Marcar como em observação" : "Voltar para aberto"}
          </button>
          <button type="button" className="botao-link" disabled={ocupado}
            onClick={() => {
              setMotivo("");
              setDialogo("descartar");
            }}>
            Marcar como descartado
          </button>
        </div>
      )}
      {podeAlterar && !aberto && (
        <button type="button" className="botao botao--secundario" disabled={ocupado}
          onClick={() => void executar(() => reabrirDiagnostico(veiculo.id, d.id), "Diagnóstico reaberto.")}>
          Reabrir diagnóstico
        </button>
      )}
      {podeAlterar && (
        <button type="button" className="botao botao--texto-perigo" disabled={ocupado}
          onClick={() => setDialogo("apagar")}>
          Apagar diagnóstico
        </button>
      )}

      {dialogo === "descartar" && (
        <DialogoConfirmacao titulo="Marcar como descartado?" textoConfirmar="Descartar" ocupado={ocupado}
          aoCancelar={() => setDialogo(null)}
          aoConfirmar={() => void executar(() => descartarDiagnostico(veiculo.id, d.id, motivo),
            "Diagnóstico descartado.")}>
          <p>Use quando não era um problema ou quando ele sumiu sozinho. Dá para reabrir depois.</p>
          {prevista && <p>A manutenção agendada continua na agenda, só deixa de estar ligada a ele.</p>}
          <CampoArea rotulo="Motivo (opcional)" value={motivo} maxLength={2000} rows={3}
            placeholder="Ex.: era a tampa do porta-malas solta"
            onChange={(e) => setMotivo(e.target.value)} />
        </DialogoConfirmacao>
      )}
      {dialogo === "existente" && (
        <DialogoConfirmacao titulo="Usar uma manutenção já registrada" textoConfirmar="Usar esta"
          ocupado={ocupado} aoCancelar={() => setDialogo(null)} aoConfirmar={() => void usarExistente()}>
          <p>
            Uma manutenção realizada resolve o diagnóstico na data dela. Uma agendada fica ligada e
            resolve quando for marcada como realizada.
          </p>
          {manutencoes === null ? <Carregando texto="Carregando manutenções…" />
            : manutencoes.length === 0 && !erroEscolha
              ? <p className="campo__dica">Este veículo ainda não tem manutenções registradas.</p>
              : (
                <CampoSelecao rotulo="Manutenção" value={escolhida} erro={erroEscolha}
                  onChange={(e) => {
                    setEscolhida(e.target.value);
                    setErroEscolha(null);
                  }}
                  opcoes={[
                    { valor: "", rotulo: "Escolha…" },
                    ...manutencoes.map((m) => ({
                      valor: String(m.id),
                      rotulo: `${m.descricao} (${m.status === "agendada" ? "agendada para " : ""}${formatarDataIso(m.data)})`,
                    })),
                  ]} />
              )}
        </DialogoConfirmacao>
      )}
      {dialogo === "apagar" && (
        <DialogoConfirmacao titulo="Apagar este diagnóstico?" textoConfirmar="Apagar" perigo
          ocupado={ocupado} aoCancelar={() => setDialogo(null)} aoConfirmar={() => void apagar()}>
          <p>
            O diagnóstico sai do histórico junto com as anotações
            {d.total_fotos > 0 ? ` e ${d.total_fotos === 1 ? "a foto ligada" : `as ${d.total_fotos} fotos ligadas`} a ele` : ""}.
            {d.manutencao ? " A manutenção ligada continua registrada." : ""}
            {" "}Não dá para desfazer.
          </p>
        </DialogoConfirmacao>
      )}
      {dialogo !== null && typeof dialogo === "object" && (
        <DialogoConfirmacao titulo="Apagar esta anotação?" textoConfirmar="Apagar" perigo
          ocupado={ocupado} aoCancelar={() => setDialogo(null)}
          aoConfirmar={() => void executar(() => apagarNota(veiculo.id, d.id, dialogo.nota.id),
            "Anotação apagada.")}>
          <p>“{dialogo.nota.texto}”</p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
