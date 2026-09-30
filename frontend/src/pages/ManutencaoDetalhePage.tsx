import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import { IconeLapis, IconeMaisSinal } from "../components/Icones";
import { FotoProtegida } from "../components/PecasVeiculo";
import SeloStatus, { type TomStatus } from "../components/SeloStatus";
import TopoComVoltar from "../components/TopoComVoltar";
import { BotaoVerValores, rotulosDosValores } from "../components/ValoresManutencao";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarFotos } from "../services/fotoService";
import { apagarManutencao, obterManutencao } from "../services/manutencaoService";
import {
  rotuloSistema,
  textoPrevisao,
  type ManutencaoDetalhe,
  type SituacaoGarantia,
} from "../types/manutencao";
import type { Foto } from "../types/veiculo";
import { formatarDataIso } from "../utils/datas";
import { formatarDinheiro, formatarKm } from "../utils/formatos";

const TOM_DA_GARANTIA: Record<SituacaoGarantia, TomStatus> = {
  vigente: "ok", vencida: "alerta", sem_informacao: "neutro", nao_se_aplica: "neutro",
};

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <li className="lista-status__linha">
      <span className="texto-suave">{rotulo}</span>
      <strong className="lista-status__valor">{valor}</strong>
    </li>
  );
}

// Detalhe de uma manutenção: dados, garantia, fotos (nota fiscal, peça
// trocada) e as ações de editar, concluir e apagar.
export default function ManutencaoDetalhePage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { recarregar: recarregarLista } = useVeiculos();
  const { manutencaoId } = useParams();
  const id = Number(manutencaoId);
  const navegar = useNavigate();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const [manutencao, setManutencao] = useState<ManutencaoDetalhe | null>(null);
  const [fotos, setFotos] = useState<Foto[]>([]);
  const [erroDados, setErroDados] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);

  const carregarDados = useCallback(async (veiculoId: number) => {
    try {
      const detalhe = await obterManutencao(veiculoId, id);
      setManutencao(detalhe);
      setErroDados(null);
      if (detalhe.total_fotos > 0) {
        setFotos((await listarFotos(veiculoId, 1, 30, { manutencaoId: id })).itens);
      }
    } catch (falha) {
      setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar a manutenção.");
    }
  }, [id]);

  useEffect(() => {
    if (veiculo?.id) void carregarDados(veiculo.id);
  }, [veiculo?.id, carregarDados]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Manutenção" voltarPara="/manutencao" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  const base = `/veiculos/${veiculo.id}`;
  if (erroDados || !manutencao) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Manutenção" voltarPara={`${base}/manutencoes`} />
        {erroDados
          ? <ErroComNovaTentativa mensagem={erroDados} aoTentar={() => void carregarDados(veiculo.id)} />
          : <Carregando />}
      </main>
    );
  }

  const realizada = manutencao.status === "realizada";
  const caminho = `${base}/manutencoes/${manutencao.id}`;
  const temLembrete = manutencao.proxima_data !== null || manutencao.proxima_km !== null;

  async function apagar() {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    try {
      await apagarManutencao(veiculo!.id, manutencao!.id);
      await recarregarLista();
      navegar(`${base}/manutencoes${realizada ? "?aba=realizadas" : ""}`, {
        replace: true, state: { mensagem: "Manutenção apagada." },
      });
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setOcupado(false);
      setConfirmando(false);
    }
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Manutenção"
        voltarPara={`${base}/manutencoes${realizada ? "?aba=realizadas" : ""}`}
        acao={veiculo.ativo ? (
          <Link to={`${caminho}/editar`} className="botao-icone" aria-label="Editar manutenção">
            <IconeLapis />
          </Link>
        ) : null} />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}

      <p className="linha-selos">
        <span className="selo selo--neutro">{rotuloSistema(manutencao.sistema)}</span>
        <SeloStatus tom={realizada ? "ok" : "aviso"}>{realizada ? "Realizada" : "Agendada"}</SeloStatus>
      </p>
      <h2 className="titulo-pagina titulo-pagina--veiculo">{manutencao.descricao}</h2>

      <ul className="cartao lista-status">
        <Linha rotulo={realizada ? "Data" : "Agendada para"} valor={formatarDataIso(manutencao.data)} />
        <Linha rotulo={realizada ? "Quilometragem" : "Quilometragem prevista"}
          valor={manutencao.quilometragem !== null ? formatarKm(manutencao.quilometragem) : "Não informada"} />
        <Linha rotulo={rotulosDosValores(realizada).total} valor={formatarDinheiro(manutencao.valor)} />
        <Linha rotulo="Plano" valor={manutencao.plano_nome ?? "Manutenção avulsa"} />
        {manutencao.oficina && <Linha rotulo="Oficina" valor={manutencao.oficina} />}
        {temLembrete && <Linha rotulo="Lembrete da próxima" valor={textoPrevisao(manutencao)} />}
      </ul>
      <div className="acao-valores">
        <BotaoVerValores veiculoId={veiculo.id} manutencaoId={manutencao.id} detalhe={manutencao} />
      </div>

      {realizada && (
        <section className="cartao" aria-label="Garantia">
          <p className="cartao__titulo">
            Garantia{" "}
            <SeloStatus tom={TOM_DA_GARANTIA[manutencao.garantia_situacao]}>
              {manutencao.garantia_situacao === "vigente" ? "Vigente"
                : manutencao.garantia_situacao === "vencida" ? "Vencida" : "Sem informação"}
            </SeloStatus>
          </p>
          <p className="texto-suave">{manutencao.garantia_explicacao}</p>
        </section>
      )}

      {manutencao.observacao && (
        <section className="cartao" aria-label="Observação">
          <p className="cartao__titulo">Observação</p>
          <p className="texto-com-linhas">{manutencao.observacao}</p>
        </section>
      )}

      <div className="cabecalho-secao">
        <h2 className="titulo-secao">Fotos</h2>
        <span className="texto-suave">
          {manutencao.total_fotos === 0 ? "Nenhuma" : manutencao.total_fotos}
        </span>
      </div>
      <div className="tira-fotos">
        {veiculo.ativo && (
          <Link to={`${base}/fotos/nova?manutencao=${manutencao.id}`} className="tira-fotos__adicionar">
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

      {veiculo.ativo && !realizada && (
        <Link to={`${caminho}/editar?concluir=1`} className="botao botao--primario">
          Marcar como realizada
        </Link>
      )}
      {veiculo.ativo && (
        <button type="button" className="botao botao--texto-perigo" disabled={ocupado}
          onClick={() => setConfirmando(true)}>
          Apagar manutenção
        </button>
      )}

      {confirmando && (
        <DialogoConfirmacao titulo="Apagar esta manutenção?" textoConfirmar="Apagar" perigo
          ocupado={ocupado} aoCancelar={() => setConfirmando(false)} aoConfirmar={() => void apagar()}>
          <p>
            O registro sai do histórico{realizada ? " e das despesas" : ""}
            {manutencao.total_fotos > 0 ? `, junto com ${manutencao.total_fotos === 1 ? "a foto ligada" : `as ${manutencao.total_fotos} fotos ligadas`} a ele` : ""}.
            {realizada && manutencao.quilometragem !== null
              ? " A leitura de quilometragem desta manutenção também é retirada." : ""}
            {" "}Não dá para desfazer.
          </p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
