import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import { FotoProtegida } from "../components/PecasVeiculo";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { apagarFoto, editarFoto, obterFoto, removerCapa, usarComoCapa } from "../services/fotoService";
import type { Foto } from "../types/veiculo";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarTamanho } from "../utils/formatos";

// Uma foto da galeria: ver em tamanho maior, editar legenda e data,
// usar como capa ou apagar.
export default function FotoDetalhePage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { recarregar: recarregarLista } = useVeiculos();
  const { fotoId } = useParams();
  const idFoto = Number(fotoId);
  const navegar = useNavigate();
  const hoje = hojeIso();
  const [foto, setFoto] = useState<Foto | null>(null);
  const [erroFoto, setErroFoto] = useState<string | null>(null);
  const [legenda, setLegenda] = useState("");
  const [data, setData] = useState("");
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState(false);
  const [confirmando, setConfirmando] = useState(false);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  const mostrar = useCallback((nova: Foto) => {
    setFoto(nova);
    setLegenda(nova.legenda ?? "");
    setData(nova.data_foto);
  }, []);

  const carregarFoto = useCallback(async (veiculoId: number) => {
    try {
      mostrar(await obterFoto(veiculoId, idFoto));
      setErroFoto(null);
    } catch (falha) {
      setErroFoto(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar a foto.");
    }
  }, [idFoto, mostrar]);

  useEffect(() => {
    if (veiculo?.id) void carregarFoto(veiculo.id);
  }, [veiculo?.id, carregarFoto]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Foto" voltarPara="/veiculos" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  const galeria = `/veiculos/${veiculo.id}/fotos`;
  if (erroFoto || !foto) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Foto" voltarPara={galeria} />
        {erroFoto
          ? <ErroComNovaTentativa mensagem={erroFoto} aoTentar={() => void carregarFoto(veiculo.id)} />
          : <Carregando />}
      </main>
    );
  }

  async function executar(acao: () => Promise<void>) {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    setSucesso(null);
    try {
      await acao();
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível concluir a ação.");
    } finally {
      setOcupado(false);
      setConfirmando(false);
    }
  }

  async function aoSalvar(evento: FormEvent) {
    evento.preventDefault();
    setSucesso(null);
    if (!data || data > hoje) {
      setErrosCampo({ data_foto: data ? "A data da foto não pode ser no futuro." : "Informe a data da foto." });
      return;
    }
    await enviar(async () => {
      // O vínculo (manutenção ou diagnóstico) é mantido: aqui só mudam legenda e data.
      mostrar(await editarFoto(veiculo!.id, foto!.id, legenda, data, foto!.manutencao_id,
        foto!.diagnostico_id, foto!.projeto_id, foto!.momento));
      setSucesso("Alterações salvas.");
    });
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Foto" voltarPara={galeria} />
      {sucesso && <Alerta tipo="sucesso">{sucesso}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}

      <div className="foto-grande">
        <FotoProtegida veiculoId={veiculo.id} fotoId={foto.id}
          descricao={foto.legenda ?? `Foto de ${formatarDataIso(foto.data_foto)}`} />
        {foto.principal && <span className="etiqueta-foto">Capa</span>}
      </div>
      <p className="texto-suave">
        {formatarDataIso(foto.data_foto)} · {formatarTamanho(foto.tamanho_bytes)}
      </p>
      {foto.manutencao_id !== null && (
        <p className="foto-vinculo">
          <span className="texto-suave">Ligada a uma manutenção. </span>
          <Link to={`/veiculos/${veiculo.id}/manutencoes/${foto.manutencao_id}`} className="link">
            Ver manutenção
          </Link>
          {veiculo.ativo && (
            <button type="button" className="botao-link" disabled={ocupado}
              onClick={() => void executar(async () => {
                mostrar(await editarFoto(veiculo.id, foto.id, foto.legenda ?? "", foto.data_foto, null));
                setSucesso("A foto não está mais ligada à manutenção.");
              })}>
              Desligar
            </button>
          )}
        </p>
      )}
      {foto.projeto_id !== null && (
        <p className="foto-vinculo">
          <span className="texto-suave">
            {foto.momento === "antes" ? "Foto de antes de um projeto. " : foto.momento === "depois"
              ? "Foto de depois de um projeto. " : "Ligada a um projeto. "}
          </span>
          <Link to={`/veiculos/${veiculo.id}/projetos/${foto.projeto_id}`} className="link">Ver projeto</Link>
          {veiculo.ativo && (
            <button type="button" className="botao-link" disabled={ocupado}
              onClick={() => void executar(async () => {
                mostrar(await editarFoto(veiculo.id, foto.id, foto.legenda ?? "", foto.data_foto, null, null));
                setSucesso("A foto não está mais ligada ao projeto.");
              })}>
              Desligar
            </button>
          )}
        </p>
      )}
      {foto.diagnostico_id !== null && (
        <p className="foto-vinculo">
          <span className="texto-suave">Ligada a um diagnóstico. </span>
          <Link to={`/veiculos/${veiculo.id}/diagnosticos/${foto.diagnostico_id}`} className="link">
            Ver diagnóstico
          </Link>
          {veiculo.ativo && (
            <button type="button" className="botao-link" disabled={ocupado}
              onClick={() => void executar(async () => {
                mostrar(await editarFoto(veiculo.id, foto.id, foto.legenda ?? "", foto.data_foto, null, null));
                setSucesso("A foto não está mais ligada ao diagnóstico.");
              })}>
              Desligar
            </button>
          )}
        </p>
      )}

      {veiculo.ativo ? (
        <>
          {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
          <form onSubmit={aoSalvar} noValidate>
            <CampoTexto rotulo="Legenda" value={legenda} maxLength={150} placeholder="Opcional"
              onChange={(e) => setLegenda(e.target.value)} erro={errosCampo.legenda} />
            <CampoTexto rotulo="Data da foto" type="date" max={hoje} value={data}
              onChange={(e) => setData(e.target.value)} erro={errosCampo.data_foto} />
            <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">Salvar alterações</BotaoEnviar>
          </form>

          <button type="button" className="botao botao--secundario botao--espaco" disabled={ocupado}
            onClick={() => void executar(async () => {
              if (foto.principal) {
                await removerCapa(veiculo.id);
                mostrar({ ...foto, principal: false });
                setSucesso("O veículo ficou sem foto de capa.");
              } else {
                mostrar(await usarComoCapa(veiculo.id, foto.id));
                setSucesso("Esta foto agora é a capa do veículo.");
              }
              await recarregarLista();
            })}>
            {foto.principal ? "Deixar de usar como capa" : "Usar como capa"}
          </button>
          <button type="button" className="botao botao--texto-perigo" disabled={ocupado}
            onClick={() => setConfirmando(true)}>
            Apagar foto
          </button>
        </>
      ) : (
        <>
          {foto.legenda && <p>{foto.legenda}</p>}
          <Alerta tipo="info">Veículo inativo: as fotos podem ser vistas, mas não alteradas.</Alerta>
        </>
      )}

      {confirmando && (
        <DialogoConfirmacao titulo="Apagar esta foto?" textoConfirmar="Apagar" perigo ocupado={ocupado}
          aoCancelar={() => setConfirmando(false)}
          aoConfirmar={() => void executar(async () => {
            await apagarFoto(veiculo.id, foto.id);
            if (foto.principal) await recarregarLista();
            navegar(galeria, { replace: true, state: { mensagem: "Foto apagada." } });
          })}>
          <p>A foto é removida da galeria e do servidor. Não dá para desfazer.</p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
