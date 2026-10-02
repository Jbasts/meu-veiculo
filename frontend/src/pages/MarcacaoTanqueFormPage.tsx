import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import { faixaDoMarcador, SeletorDeNivel } from "../components/PecasTanque";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { apagarMarcacao, criarMarcacao, editarMarcacao, obterMarcacao } from "../services/abastecimentoService";
import { rotuloDoNivel, type MarcacaoTanque } from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import {
  arredondarUmaCasa,
  formatarDecimal,
  formatarInteiro,
  formatarKm,
  lerInteiro,
  litrosQueFaltam,
  mascararInteiro,
} from "../utils/formatos";

/**
 * "Marcação do tanque" (/veiculos/:id/tanque/marcacoes/nova e /:marcacaoId):
 * quilometragem e nível do marcador sem abastecer. Ideia da Paula: uma vez no
 * início de cada mês, para o consumo do mês ficar mais exato.
 */
export default function MarcacaoTanqueFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { marcacaoId } = useParams();
  const id = marcacaoId && marcacaoId !== "nova" ? Number(marcacaoId) : null;
  const [existente, setExistente] = useState<MarcacaoTanque | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo || !id) return;
    let cancelado = false;
    obterMarcacao(veiculo.id, id).then((m) => {
      if (!cancelado) setExistente(m);
    }).catch((falha) => {
      if (!cancelado) setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar a marcação.");
    });
    return () => {
      cancelado = true;
    };
  }, [veiculo, id]);

  const titulo = id ? "Marcação do tanque" : "Marcar km e nível";
  const voltar = veiculo ? `/veiculos/${veiculo.id}/financas?aba=combustivel` : "/financas?aba=combustivel";
  if (carregando || (veiculo && id && !existente && !erroDados)) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo={titulo} voltarPara={voltar} />
          <ErroComNovaTentativa mensagem={erro ?? erroDados ?? "Veículo não encontrado."}
            aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
        </main>
      </div>
    );
  }
  return <Formulario key={existente?.id ?? "nova"} veiculo={veiculo} existente={existente}
    titulo={titulo} voltar={voltar} />;
}

function Formulario({ veiculo, existente, titulo, voltar }: {
  veiculo: Veiculo; existente: MarcacaoTanque | null; titulo: string; voltar: string;
}) {
  const navegar = useNavigate();
  const { recarregar: recarregarLista } = useVeiculos();
  const hoje = hojeIso();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const [data, setData] = useState(existente?.data ?? hoje);
  const [km, setKm] = useState(existente ? formatarInteiro(existente.quilometragem) : "");
  const [nivel, setNivel] = useState<number | null>(existente?.nivel ?? null);
  const [confirmando, setConfirmando] = useState(false);
  const [apagando, setApagando] = useState(false);
  const [erroApagar, setErroApagar] = useState<string | null>(null);
  const capacidade = veiculo.capacidade_tanque;
  const podeAlterar = veiculo.ativo && capacidade !== null;

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const quilometragem = lerInteiro(km);
    const erros: Record<string, string> = {};
    if (!data) erros.data = "Informe a data.";
    else if (data > hoje) erros.data = "A data não pode ser no futuro.";
    if (quilometragem === null) erros.quilometragem = "Informe a quilometragem.";
    if (nivel === null) erros.nivel = "Escolha o nível do marcador.";
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const dados = { data, quilometragem, nivel };
    const deuCerto = await enviar(async () => {
      if (existente) await editarMarcacao(veiculo.id, existente.id, dados);
      else await criarMarcacao(veiculo.id, dados);
      await recarregarLista(); // a quilometragem do veículo pode ter mudado
    });
    if (deuCerto) {
      navegar(voltar, { replace: true, state: { mensagem: existente ? "Alterações salvas." : "Marcação registrada." } });
    }
  }

  async function apagar() {
    if (!existente || apagando) return;
    setApagando(true);
    try {
      await apagarMarcacao(veiculo.id, existente.id);
      await recarregarLista();
      navegar(voltar, { replace: true, state: { mensagem: "Marcação apagada." } });
    } catch (falha) {
      setErroApagar(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setApagando(false);
      setConfirmando(false);
    }
  }

  const consumo = existente?.consumo;
  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {!veiculo.ativo && <Alerta tipo="info">Veículo inativo: a marcação pode ser consultada, mas não alterada.</Alerta>}
        {veiculo.ativo && capacidade === null && (
          <Alerta tipo="info">
            Para marcar o nível, informe antes o tamanho do tanque: é com ele que o nível vira litros.{" "}
            <Link to={`/veiculos/${veiculo.id}/editar`} className="link">Informar agora</Link>
          </Alerta>
        )}
        {consumo?.tipo === "consumo" && (
          <Alerta tipo="info">
            Consumo do trecho até aqui: ≈ {formatarDecimal(consumo.km_por_litro!, 1)} km/L.
            {" "}{faixaDoMarcador(consumo.km_por_litro_minimo, consumo.km_por_litro_maximo) ?? ""}
          </Alerta>
        )}
        {consumo?.motivo && <Alerta tipo="info">{consumo.motivo}</Alerta>}
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        {erroApagar && <Alerta tipo="erro">{erroApagar}</Alerta>}

        {!existente && (
          <p className="texto-suave secao__dica">
            Anote o que o painel mostra, sem abastecer. Uma vez no início de cada mês já deixa o consumo
            do mês mais exato; ao abastecer, marque também o nível no abastecimento.
          </p>
        )}

        <form onSubmit={aoEnviar} noValidate>
          <fieldset className="grupo-campos" disabled={!podeAlterar}>
            <div className="dupla">
              <CampoTexto rotulo="Data" type="date" max={hoje} value={data}
                onChange={(e) => setData(e.target.value)} erro={errosCampo.data}
                dica={data === hoje ? "Hoje" : undefined} />
              <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={km} maxLength={9}
                placeholder={formatarInteiro(veiculo.quilometragem)}
                onChange={(e) => setKm(mascararInteiro(e.target.value))} erro={errosCampo.quilometragem}
                dica={`Última: ${formatarKm(veiculo.quilometragem)}`} />
            </div>
            <SeletorDeNivel rotulo="Nível do marcador" valor={nivel} erro={errosCampo.nivel}
              aoMudar={(n) => {
                setNivel(n);
                setErrosCampo(({ nivel: _escolhido, ...outros }) => outros);
              }}
              dica={nivel !== null && capacidade
                ? `${rotuloDoNivel(nivel)}: faltam cerca de ${formatarDecimal(arredondarUmaCasa(litrosQueFaltam(capacidade, nivel)))} L `
                  + `para encher o tanque de ${formatarDecimal(capacidade)} L.`
                : "Em quartos do tanque, como no marcador do carro (1,5/4 fica entre 1/4 e 2/4)."} />

            {podeAlterar && (
              <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
                {existente ? "Salvar alterações" : "Salvar marcação"}
              </BotaoEnviar>
            )}
          </fieldset>
        </form>

        {existente && veiculo.ativo && (
          <button type="button" className="botao botao--texto-perigo" disabled={apagando}
            onClick={() => setConfirmando(true)}>
            Apagar marcação
          </button>
        )}
        {confirmando && (
          <DialogoConfirmacao titulo="Apagar esta marcação?" textoConfirmar="Apagar" perigo ocupado={apagando}
            aoCancelar={() => setConfirmando(false)} aoConfirmar={() => void apagar()}>
            <p>A leitura de quilometragem dela é retirada e o consumo é recalculado. Não dá para desfazer.</p>
          </DialogoConfirmacao>
        )}
      </main>
    </div>
  );
}
