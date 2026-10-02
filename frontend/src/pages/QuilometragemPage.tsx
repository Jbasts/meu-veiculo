import { useCallback, useEffect, useState, type FormEvent } from "react";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  anularLeitura,
  corrigirLeitura,
  listarLeituras,
  registrarLeitura,
} from "../services/veiculoService";
import type { LeituraKm, OrigemLeitura, Veiculo } from "../types/veiculo";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarKm, lerInteiro, mascararInteiro } from "../utils/formatos";

const POR_PAGINA = 20;

const ORIGEM: Record<OrigemLeitura, string> = {
  cadastro: "Cadastro do veículo",
  manual: "Atualização manual",
  abastecimento: "Abastecimento",
  manutencao: "Manutenção",
  diagnostico: "Diagnóstico",
  legado: "Leitura anterior ao histórico",
  medicao_tanque: "Marcação do tanque",
};

function FormularioCorrecao({ veiculo, leitura, aoConcluir, aoCancelar }: {
  veiculo: Veiculo;
  leitura: LeituraKm;
  aoConcluir: (atualizado: Veiculo) => void;
  aoCancelar: () => void;
}) {
  const [km, setKm] = useState("");
  const [motivo, setMotivo] = useState("");
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const valor = lerInteiro(km);
    if (valor === null) {
      setErrosCampo({ quilometragem: "Informe a quilometragem correta." });
      return;
    }
    await enviar(async () => {
      aoConcluir(await corrigirLeitura(veiculo.id, leitura.id, valor, motivo.trim() || null));
    });
  }

  return (
    <form onSubmit={aoEnviar} noValidate className="correcao">
      {erroGeral && !errosCampo.quilometragem && <Alerta tipo="erro">{erroGeral}</Alerta>}
      <CampoTexto rotulo="Quilometragem correta" inputMode="numeric" value={km} maxLength={9}
        onChange={(e) => setKm(mascararInteiro(e.target.value))} erro={errosCampo.quilometragem}
        dica={`Substitui ${formatarKm(leitura.quilometragem)}. A leitura errada continua no histórico, marcada como corrigida.`} />
      <CampoTexto rotulo="Motivo (opcional)" value={motivo} maxLength={200}
        placeholder="Ex.: digitei um zero a mais" onChange={(e) => setMotivo(e.target.value)}
        erro={errosCampo.motivo} />
      <div className="dupla">
        <button type="button" className="botao botao--secundario" onClick={aoCancelar}
          disabled={enviando}>
          Cancelar
        </button>
        <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">Salvar correção</BotaoEnviar>
      </div>
    </form>
  );
}

// Atualizar km e histórico de leituras (tela complementar ao PDF).
export default function QuilometragemPage() {
  const { id, veiculo, setVeiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { recarregar: recarregarLista } = useVeiculos();
  const hoje = hojeIso();
  const [km, setKm] = useState("");
  const [data, setData] = useState(hoje);
  const [sucesso, setSucesso] = useState<string | null>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  const [leituras, setLeituras] = useState<LeituraKm[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [carregandoLista, setCarregandoLista] = useState(true);
  const [erroLista, setErroLista] = useState<string | null>(null);
  const [corrigindo, setCorrigindo] = useState<number | null>(null);
  const [anulando, setAnulando] = useState<LeituraKm | null>(null);
  const [ocupado, setOcupado] = useState(false);

  const carregarLeituras = useCallback(async (ate: number) => {
    setCarregandoLista(true);
    try {
      // Recarrega da primeira página até a atual: a lista fica coerente
      // mesmo depois de uma leitura nova ou de uma correção.
      const paginas = await Promise.all(
        Array.from({ length: ate }, (_, i) => listarLeituras(id, i + 1, POR_PAGINA)));
      setLeituras(paginas.flatMap((p) => p.itens));
      setTotal(paginas[0]?.total ?? 0);
      setPagina(ate);
      setErroLista(null);
    } catch (falha) {
      setErroLista(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o histórico.");
    } finally {
      setCarregandoLista(false);
    }
  }, [id]);

  useEffect(() => {
    if (veiculo?.id) void carregarLeituras(1);
  }, [veiculo?.id, carregarLeituras]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Quilometragem" voltarPara="/" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }

  async function depoisDeMudar(atualizado: Veiculo, mensagem: string) {
    setVeiculo(atualizado);
    setSucesso(mensagem);
    setCorrigindo(null);
    await Promise.all([carregarLeituras(pagina), recarregarLista()]);
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setSucesso(null);
    const valor = lerInteiro(km);
    const erros: Record<string, string> = {};
    if (valor === null) erros.quilometragem = "Informe a quilometragem.";
    if (!data) erros.data_leitura = "Informe a data da leitura.";
    else if (data > hoje) erros.data_leitura = "A data da leitura não pode ser no futuro.";
    if (Object.keys(erros).length || valor === null) {
      setErrosCampo(erros);
      return;
    }
    await enviar(async () => {
      const atualizado = await registrarLeitura(veiculo!.id, valor, data);
      setKm("");
      await depoisDeMudar(atualizado, atualizado.quilometragem === valor
        ? "Quilometragem atualizada."
        : "Leitura guardada no histórico. A quilometragem atual não mudou, porque já existe uma leitura maior.");
    });
  }

  async function confirmarAnulacao() {
    if (!anulando || ocupado) return;
    setOcupado(true);
    setSucesso(null);
    try {
      await depoisDeMudar(await anularLeitura(veiculo!.id, anulando.id, null), "Leitura anulada.");
      setErroLista(null);
    } catch (falha) {
      setErroLista(falha instanceof ErroDaApi ? falha.message : "Não foi possível anular a leitura.");
    } finally {
      setOcupado(false);
      setAnulando(null);
    }
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Quilometragem" voltarPara={`/veiculos/${veiculo.id}`} />

      <section className="cartao" aria-label="Quilometragem atual">
        <p className="texto-suave cartao__rotulo">{veiculo.modelo} {veiculo.ano}, quilometragem atual</p>
        <p className="numero-destaque">{formatarKm(veiculo.quilometragem)}</p>
        <p className="texto-suave">
          {veiculo.data_leitura_km
            ? `Leitura de ${formatarDataIso(veiculo.data_leitura_km)}`
            : "Data da leitura desconhecida (registro anterior ao histórico)"}
        </p>
      </section>

      {sucesso && <Alerta tipo="sucesso">{sucesso}</Alerta>}

      {veiculo.ativo ? (
        <>
          <h2 className="titulo-secao">Nova leitura</h2>
          {erroGeral && !errosCampo.quilometragem && !errosCampo.data_leitura
            && <Alerta tipo="erro">{erroGeral}</Alerta>}
          <form onSubmit={aoEnviar} noValidate>
            <div className="dupla">
              <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={km} maxLength={9}
                placeholder="Ex.: 85.450" onChange={(e) => setKm(mascararInteiro(e.target.value))}
                erro={errosCampo.quilometragem} />
              <CampoTexto rotulo="Data da leitura" type="date" max={hoje} value={data}
                onChange={(e) => setData(e.target.value)} erro={errosCampo.data_leitura}
                dica={data === hoje ? "Hoje. Toque para alterar." : undefined} />
            </div>
            <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">Salvar leitura</BotaoEnviar>
          </form>
        </>
      ) : (
        <Alerta tipo="info">Veículo inativo: o histórico pode ser consultado, mas não alterado.</Alerta>
      )}

      <h2 className="titulo-secao titulo-secao--espaco">Histórico de leituras</h2>
      {erroLista && <Alerta tipo="erro">{erroLista}</Alerta>}
      {carregandoLista && leituras.length === 0 && <Carregando />}
      <ul className="lista-leituras">
        {leituras.map((leitura) => (
          <li key={leitura.id} className={`cartao leitura${leitura.valida ? "" : " leitura--anulada"}`}>
            <div className="leitura__linha">
              <div>
                <p className="leitura__km">{formatarKm(leitura.quilometragem)}</p>
                <p className="texto-suave">
                  {leitura.data_leitura ? formatarDataIso(leitura.data_leitura) : "Data desconhecida"}
                  {" · "}{ORIGEM[leitura.origem]}
                </p>
              </div>
              {!leitura.valida && <span className="selo selo--neutro">Anulada</span>}
              {leitura.valida && leitura.quilometragem === veiculo.quilometragem
                && leitura.data_leitura === veiculo.data_leitura_km
                && <span className="selo selo--ok">Atual</span>}
            </div>
            {!leitura.valida && leitura.motivo_anulacao && (
              <p className="texto-suave leitura__motivo">Motivo: {leitura.motivo_anulacao}</p>
            )}
            {leitura.valida && !leitura.editavel && (
              <p className="texto-suave leitura__motivo">
                Para corrigir, edite o registro de {ORIGEM[leitura.origem].toLowerCase()}.
              </p>
            )}
            {veiculo.ativo && leitura.editavel && corrigindo !== leitura.id && (
              <div className="leitura__acoes">
                <button type="button" className="botao-pequeno"
                  onClick={() => setCorrigindo(leitura.id)}>
                  Corrigir
                </button>
                <button type="button" className="botao-pequeno botao-pequeno--perigo"
                  onClick={() => setAnulando(leitura)}>
                  Anular
                </button>
              </div>
            )}
            {corrigindo === leitura.id && (
              <FormularioCorrecao veiculo={veiculo} leitura={leitura}
                aoCancelar={() => setCorrigindo(null)}
                aoConcluir={(atualizado) => void depoisDeMudar(atualizado, "Leitura corrigida.")} />
            )}
          </li>
        ))}
      </ul>
      {leituras.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregandoLista}
          onClick={() => void carregarLeituras(pagina + 1)}>
          {carregandoLista ? "Carregando…" : `Carregar mais (${total - leituras.length} restantes)`}
        </button>
      )}

      {anulando && (
        <DialogoConfirmacao titulo="Anular esta leitura?" textoConfirmar="Anular" perigo
          ocupado={ocupado} aoCancelar={() => setAnulando(null)}
          aoConfirmar={() => void confirmarAnulacao()}>
          <p>
            A leitura de {formatarKm(anulando.quilometragem)} deixa de contar e fica no histórico
            como anulada. Se o valor só foi digitado errado, prefira "Corrigir".
          </p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
