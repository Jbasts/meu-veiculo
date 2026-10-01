import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import { IconeCheck, IconeLapis, IconeMaisSinal } from "../components/Icones";
import {
  AntesDepois,
  BarraOrcamento,
  TOM_DO_STATUS_PROJETO,
  textoDaDiferenca,
} from "../components/PecasProjeto";
import { FotoProtegida } from "../components/PecasVeiculo";
import SeloStatus from "../components/SeloStatus";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  adicionarItem,
  apagarItem,
  apagarProjeto,
  concluirProjeto,
  editarItem,
  mudarSituacao,
  obterProjeto,
  type AcaoProjeto,
} from "../services/projetoService";
import { ROTULO_STATUS_PROJETO, rotuloCategoriaProjeto, type ItemProjeto, type ProjetoDetalhe } from "../types/projeto";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, formatarMesAnoCurto, hojeIso } from "../utils/datas";
import { dinheiroParaCampo, formatarDinheiro, lerDinheiro } from "../utils/formatos";

type Dialogo = null | "concluir" | "cancelar" | "apagar" | { item: ItemProjeto | null };

// Detalhe de um projeto (PDF, página 19).
export default function ProjetoDetalhePage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { projetoId } = useParams();
  const id = Number(projetoId);
  const [projeto, setProjeto] = useState<ProjetoDetalhe | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  const carregarDados = useCallback(async (veiculoId: number) => {
    try {
      setProjeto(await obterProjeto(veiculoId, id));
      setErroDados(null);
    } catch (falha) {
      setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o projeto.");
    }
  }, [id]);

  useEffect(() => {
    if (veiculo?.id) void carregarDados(veiculo.id);
  }, [veiculo?.id, carregarDados]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Projeto" voltarPara="/projetos" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."} aoTentar={() => void recarregar()} />
      </main>
    );
  }
  if (erroDados || !projeto) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Projeto" voltarPara={`/veiculos/${veiculo.id}/projetos`} />
        {erroDados ? <ErroComNovaTentativa mensagem={erroDados} aoTentar={() => void carregarDados(veiculo.id)} />
          : <Carregando />}
      </main>
    );
  }
  return <Detalhe veiculo={veiculo} projeto={projeto} aoMudar={setProjeto} />;
}

/** Fotos além da primeira de cada momento (a primeira já está nos quadros). */
function OutrasFotos({ veiculoId, ids, rotulo }: { veiculoId: number; ids: number[]; rotulo: string }) {
  if (ids.length <= 1) return null;
  return (
    <div className="tira-fotos" aria-label={`Outras fotos de ${rotulo.toLowerCase()}`}>
      {ids.slice(1).map((fotoId) => (
        <Link key={fotoId} to={`/veiculos/${veiculoId}/fotos/${fotoId}`} className="tira-fotos__item">
          <FotoProtegida veiculoId={veiculoId} fotoId={fotoId} descricao={`Foto de ${rotulo.toLowerCase()}`} />
          <span className="etiqueta-foto">{rotulo}</span>
        </Link>
      ))}
    </div>
  );
}

function Detalhe({ veiculo, projeto: p, aoMudar }: {
  veiculo: Veiculo; projeto: ProjetoDetalhe; aoMudar: (p: ProjetoDetalhe) => void;
}) {
  const navegar = useNavigate();
  const local = useLocation();
  const hoje = hojeIso();
  const [mensagem, setMensagem] = useState<string | null>((local.state as { mensagem?: string } | null)?.mensagem ?? null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [dialogo, setDialogo] = useState<Dialogo>(null);
  const [dataConclusao, setDataConclusao] = useState(hoje);
  const [erroDialogo, setErroDialogo] = useState<Record<string, string>>({});
  const [item, setItem] = useState({ descricao: "", valor: "", data: hoje });

  const base = `/veiculos/${veiculo.id}`;
  const aberto = p.status === "planejado" || p.status === "em_andamento";
  const podeAlterar = veiculo.ativo;
  const podeGastar = podeAlterar && aberto;

  async function executar(acao: () => Promise<ProjetoDetalhe>, sucesso: string, campos = false): Promise<void> {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    setMensagem(null);
    try {
      aoMudar(await acao());
      setMensagem(sucesso);
      setDialogo(null);
    } catch (falha) {
      if (campos && falha instanceof ErroDaApi && Object.keys(falha.campos).length) {
        setErroDialogo(falha.campos);
      } else {
        setErroAcao(falha instanceof ErroDaApi ? falha.message : "Algo deu errado. Tente de novo.");
        setDialogo(null);
      }
    } finally {
      setOcupado(false);
    }
  }

  function abrirItem(existente: ItemProjeto | null) {
    setItem(existente ? { descricao: existente.descricao, valor: dinheiroParaCampo(existente.valor), data: existente.data }
      : { descricao: "", valor: "", data: hoje });
    setErroDialogo({});
    setDialogo({ item: existente });
  }

  function salvarItem(existente: ItemProjeto | null) {
    const valor = lerDinheiro(item.valor);
    const erros: Record<string, string> = {};
    if (!item.descricao.trim()) erros.descricao = "Informe o que foi comprado ou pago.";
    if (valor === null) erros.valor = "Informe o valor.";
    else if (valor === undefined) erros.valor = "Valor inválido. Exemplo: 400,00.";
    if (!item.data) erros.data = "Informe a data.";
    else if (item.data > hoje) erros.data = "A data do gasto não pode ser no futuro.";
    setErroDialogo(erros);
    if (Object.keys(erros).length || typeof valor !== "string") return;
    const dados = { descricao: item.descricao.trim(), valor, data: item.data };
    void executar(() => (existente ? editarItem(veiculo.id, p.id, existente.id, dados)
      : adicionarItem(veiculo.id, p.id, dados)), existente ? "Gasto atualizado." : "Gasto adicionado.", true);
  }

  async function apagar() {
    if (ocupado) return;
    setOcupado(true);
    try {
      await apagarProjeto(veiculo.id, p.id);
      navegar(`${base}/projetos`, { replace: true, state: { mensagem: "Projeto apagado." } });
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setOcupado(false);
      setDialogo(null);
    }
  }

  const acao = (tipo: AcaoProjeto, texto: string) => () => void executar(() => mudarSituacao(veiculo.id, p.id, tipo), texto);
  const lateralDireita = p.status === "concluido" && p.data_conclusao ? `Concluído em ${formatarDataIso(p.data_conclusao)}`
    : p.data_prevista ? `Previsto para ${formatarMesAnoCurto(p.data_prevista)}` : "";

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Projeto" voltarPara={`${base}/projetos`} acao={podeAlterar ? (
        <Link to={`${base}/projetos/${p.id}/editar`} className="botao-icone" aria-label="Editar projeto"><IconeLapis /></Link>
      ) : null} />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}

      <p className="linha-selos">
        <span className="selo selo--neutro">{rotuloCategoriaProjeto(p.categoria)}</span>
        <SeloStatus tom={TOM_DO_STATUS_PROJETO[p.status]}>{ROTULO_STATUS_PROJETO[p.status]}</SeloStatus>
      </p>
      <h2 className="titulo-pagina titulo-pagina--veiculo">{p.nome}</h2>
      {p.descricao && <p className="texto-com-linhas">{p.descricao}</p>}

      <section className="cartao orcamento-projeto" aria-label="Orçamento">
        <p className="orcamento-projeto__topo">
          <span className="orcamento-projeto__gasto">{formatarDinheiro(p.gasto)}</span>
          <span className="texto-suave">{p.orcamento !== null ? `de ${formatarDinheiro(p.orcamento)}` : "sem orçamento"}</span>
        </p>
        <BarraOrcamento projeto={p} />
        <p className="projeto__rodape">
          <span className="texto-suave">{textoDaDiferenca(p) || (p.percentual !== null ? `${p.percentual}% do orçamento` : "")}</span>
          <span className="texto-suave">{lateralDireita}</span>
        </p>
      </section>

      <h2 className="titulo-secao">Antes e depois</h2>
      <AntesDepois veiculoId={veiculo.id} projeto={p} podeAdicionar={podeAlterar} grande />
      <OutrasFotos veiculoId={veiculo.id} ids={p.fotos_antes} rotulo="Antes" />
      <OutrasFotos veiculoId={veiculo.id} ids={p.fotos_depois} rotulo="Depois" />
      {podeAlterar && (p.foto_antes_id !== null || p.foto_depois_id !== null) && (
        <p className="acoes-texto acoes-texto--esquerda">
          <Link to={`${base}/fotos/nova?projeto=${p.id}&momento=antes`} className="link">+ Foto de antes</Link>
          <Link to={`${base}/fotos/nova?projeto=${p.id}&momento=depois`} className="link">+ Foto de depois</Link>
        </p>
      )}

      <h2 className="titulo-secao">Gastos do projeto</h2>
      {p.itens.length === 0 ? (
        <p className="texto-suave">Nenhum gasto ainda.</p>
      ) : (
        <ul className="cartao lista-simples" aria-label="Gastos do projeto">
          {p.itens.map((i) => (
            <li key={i.id}>
              {podeGastar ? (
                <button type="button" className="lista-simples__item lista-simples__botao" onClick={() => abrirItem(i)}
                  aria-label={`Editar ${i.descricao}`}>
                  <span className="lista-simples__texto">
                    <span className="lista-simples__titulo">{i.descricao}</span>
                    <span className="texto-suave">{formatarDataIso(i.data)}</span>
                  </span>
                  <strong>{formatarDinheiro(i.valor)}</strong>
                </button>
              ) : (
                <div className="lista-simples__item">
                  <span className="lista-simples__texto">
                    <span className="lista-simples__titulo">{i.descricao}</span>
                    <span className="texto-suave">{formatarDataIso(i.data)}</span>
                  </span>
                  <strong>{formatarDinheiro(i.valor)}</strong>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {podeGastar && (
        <button type="button" className="botao botao--secundario botao--adicionar" onClick={() => abrirItem(null)}>
          <IconeMaisSinal tamanho={20} /> Adicionar gasto
        </button>
      )}
      {podeAlterar && !aberto && (
        <p className="texto-suave">
          {p.status === "concluido" ? "Projeto concluído" : "Projeto cancelado"}: os gastos continuam nas despesas.
          Para alterar, reabra o projeto.
        </p>
      )}

      {podeAlterar && p.status === "planejado" && (
        <button type="button" className="botao botao--secundario botao--espaco" disabled={ocupado}
          onClick={acao("iniciar", "Projeto iniciado.")}>
          Iniciar projeto
        </button>
      )}
      {podeAlterar && aberto && (
        <>
          <button type="button" className="botao botao--primario botao--espaco" disabled={ocupado}
            onClick={() => {
              setDataConclusao(hoje);
              setErroDialogo({});
              setDialogo("concluir");
            }}>
            <IconeCheck tamanho={20} /> Marcar como concluído
          </button>
          <div className="acoes-texto">
            <button type="button" className="botao-link" disabled={ocupado} onClick={() => setDialogo("cancelar")}>
              Cancelar projeto
            </button>
          </div>
        </>
      )}
      {podeAlterar && !aberto && (
        <button type="button" className="botao botao--secundario botao--espaco" disabled={ocupado}
          onClick={acao("reabrir", "Projeto reaberto.")}>
          Reabrir projeto
        </button>
      )}
      {podeAlterar && (
        <button type="button" className="botao botao--texto-perigo" disabled={ocupado} onClick={() => setDialogo("apagar")}>
          Apagar projeto
        </button>
      )}

      {dialogo === "concluir" && (
        <DialogoConfirmacao titulo="Marcar como concluído?" textoConfirmar="Concluir" ocupado={ocupado}
          aoCancelar={() => setDialogo(null)}
          aoConfirmar={() => {
            if (!dataConclusao || dataConclusao > hoje) {
              setErroDialogo({ data_conclusao: dataConclusao ? "A data não pode ser no futuro." : "Informe a data." });
              return;
            }
            void executar(() => concluirProjeto(veiculo.id, p.id, dataConclusao), "Projeto concluído.", true);
          }}>
          <p>Depois de concluído, os gastos só podem ser alterados reabrindo o projeto.</p>
          <CampoTexto rotulo="Data de conclusão" type="date" max={hoje} value={dataConclusao}
            onChange={(e) => setDataConclusao(e.target.value)} erro={erroDialogo.data_conclusao} />
        </DialogoConfirmacao>
      )}
      {dialogo === "cancelar" && (
        <DialogoConfirmacao titulo="Cancelar este projeto?" textoConfirmar="Cancelar projeto" perigo ocupado={ocupado}
          aoCancelar={() => setDialogo(null)}
          aoConfirmar={() => void executar(() => mudarSituacao(veiculo.id, p.id, "cancelar"), "Projeto cancelado.")}>
          <p>
            {p.itens.length > 0 ? `Os ${formatarDinheiro(p.gasto)} já gastos continuam nas despesas. ` : ""}
            Dá para reabrir depois.
          </p>
        </DialogoConfirmacao>
      )}
      {dialogo === "apagar" && (
        <DialogoConfirmacao titulo="Apagar este projeto?" textoConfirmar="Apagar" perigo ocupado={ocupado}
          aoCancelar={() => setDialogo(null)} aoConfirmar={() => void apagar()}>
          <p>
            {p.itens.length > 0 ? `Os gastos (${formatarDinheiro(p.gasto)}) saem das despesas` : "O projeto sai da lista"}
            {p.total_fotos > 0 ? ` e ${p.total_fotos === 1 ? "a foto ligada é apagada" : `as ${p.total_fotos} fotos ligadas são apagadas`}` : ""}.
            {" "}Se o projeto não vai mais acontecer, prefira "Cancelar projeto": os gastos continuam registrados.
            Não dá para desfazer.
          </p>
        </DialogoConfirmacao>
      )}
      {dialogo !== null && typeof dialogo === "object" && (
        <DialogoConfirmacao titulo={dialogo.item ? "Editar gasto" : "Adicionar gasto"}
          textoConfirmar={dialogo.item ? "Salvar" : "Adicionar"} ocupado={ocupado}
          aoCancelar={() => setDialogo(null)} aoConfirmar={() => salvarItem(dialogo.item)}>
          <CampoTexto rotulo="O que foi" value={item.descricao} maxLength={150} placeholder="Ex.: Jogo de rodas aro 17"
            onChange={(e) => setItem({ ...item, descricao: e.target.value })} erro={erroDialogo.descricao} />
          <div className="dupla">
            <CampoTexto rotulo="Valor (R$)" inputMode="decimal" value={item.valor} maxLength={20} placeholder="0,00"
              onChange={(e) => setItem({ ...item, valor: e.target.value })} erro={erroDialogo.valor} />
            <CampoTexto rotulo="Data" type="date" max={hoje} value={item.data}
              onChange={(e) => setItem({ ...item, data: e.target.value })} erro={erroDialogo.data} />
          </div>
          {dialogo.item && (
            <button type="button" className="botao-link" disabled={ocupado}
              onClick={() => void executar(() => apagarItem(veiculo.id, p.id, dialogo.item!.id), "Gasto apagado.")}>
              Apagar este gasto
            </button>
          )}
        </DialogoConfirmacao>
      )}
    </main>
  );
}
