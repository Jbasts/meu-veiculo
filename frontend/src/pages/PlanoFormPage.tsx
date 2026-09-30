import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoSelecao, DialogoConfirmacao } from "../components/Formulario";
import { TOM_DA_SITUACAO } from "../components/PecasManutencao";
import SeloStatus from "../components/SeloStatus";
import TopoComVoltar from "../components/TopoComVoltar";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  apagarPlano,
  criarPlano,
  definirPlanoAtivo,
  editarPlano,
  obterPlano,
} from "../services/manutencaoService";
import {
  resumoDoPrazo,
  ROTULO_SITUACAO,
  SISTEMAS,
  textoPrevisao,
  type DadosPlano,
  type Plano,
} from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarInteiro, formatarKm, lerInteiro, mascararInteiro } from "../utils/formatos";
import { erroObrigatorio, soErros } from "../utils/validacao";

/** Criar e editar um plano recorrente (aba Planos do PDF, página 5). */
export default function PlanoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { planoId } = useParams();
  const idPlano = planoId ? Number(planoId) : null;
  const [plano, setPlano] = useState<Plano | null>(null);
  const [erroPlano, setErroPlano] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo || !idPlano) return;
    let cancelado = false;
    obterPlano(veiculo.id, idPlano)
      .then((dados) => {
        if (!cancelado) setPlano(dados);
      })
      .catch((falha) => {
        if (!cancelado) {
          setErroPlano(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o plano.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [veiculo, idPlano]);

  const titulo = idPlano ? "Plano de manutenção" : "Novo plano";
  const lista = veiculo ? `/veiculos/${veiculo.id}/manutencoes?aba=planos` : "/manutencao?aba=planos";
  if (carregando || (veiculo && idPlano && !plano && !erroPlano)) {
    return <main className="conteudo conteudo--topo"><Carregando /></main>;
  }
  if (erro || erroPlano || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={lista} />
        <ErroComNovaTentativa mensagem={erro ?? erroPlano ?? "Veículo não encontrado."}
          aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
      </main>
    );
  }
  return <Formulario key={plano?.id ?? "novo"} veiculo={veiculo} plano={plano} titulo={titulo}
    lista={lista} aoMudar={setPlano} />;
}

function Formulario({ veiculo, plano, titulo, lista, aoMudar }: {
  veiculo: Veiculo; plano: Plano | null; titulo: string; lista: string;
  aoMudar: (plano: Plano) => void;
}) {
  const navegar = useNavigate();
  const hoje = hojeIso();
  const [nome, setNome] = useState(plano?.nome ?? "");
  const [sistema, setSistema] = useState(plano?.sistema ?? "outros");
  const [intervaloKm, setIntervaloKm] = useState(
    plano?.intervalo_km != null ? formatarInteiro(plano.intervalo_km) : "");
  const [intervaloMeses, setIntervaloMeses] = useState(
    plano?.intervalo_meses != null ? String(plano.intervalo_meses) : "");
  // Plano novo: a base sugerida é "a partir de hoje, com a quilometragem atual".
  const [dataBase, setDataBase] = useState(plano ? plano.data_base ?? "" : hoje);
  const [kmBase, setKmBase] = useState(
    plano ? (plano.km_base != null ? formatarInteiro(plano.km_base) : "") : formatarInteiro(veiculo.quilometragem));
  const [sucesso, setSucesso] = useState<string | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  const km = lerInteiro(intervaloKm);
  const meses = lerInteiro(intervaloMeses);
  const somenteLeitura = !veiculo.ativo;

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    setSucesso(null);
    const base = lerInteiro(kmBase);
    const erros = soErros({
      nome: erroObrigatorio(nome, "Informe o nome do plano."),
      intervalo_km: km === null && meses === null
        ? "Informe o intervalo em quilômetros, em meses ou os dois." : km === 0 ? "Informe um valor maior que zero." : null,
      intervalo_meses: meses === 0 ? "Informe um valor maior que zero." : null,
      km_base: km !== null && base === null ? "Informe a quilometragem da última vez (ou a atual)."
        : km !== null && base !== null && base > veiculo.quilometragem
          ? `Não pode ser maior que a quilometragem atual (${formatarKm(veiculo.quilometragem)}).` : null,
      data_base: meses !== null && !dataBase ? "Informe a data da última vez (ou a de hoje)."
        : meses !== null && dataBase > hoje ? "A data não pode ser no futuro." : null,
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosPlano = {
      nome: nome.trim(), sistema, intervalo_km: km, intervalo_meses: meses,
      data_base: meses !== null ? dataBase : null, km_base: km !== null ? base : null,
    };
    const deuCerto = await enviar(async () => {
      if (plano) {
        aoMudar(await editarPlano(veiculo.id, plano.id, dados));
        setSucesso("Alterações salvas.");
      } else {
        await criarPlano(veiculo.id, dados);
      }
    });
    if (deuCerto && !plano) {
      navegar(lista, { replace: true, state: { mensagem: "Plano criado." } });
    }
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

  const resumo = plano?.situacao ? resumoDoPrazo(plano) : null;

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo={titulo} voltarPara={lista} />
      {sucesso && <Alerta tipo="sucesso">{sucesso}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}
      {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
      {somenteLeitura && (
        <Alerta tipo="info">Veículo inativo: o plano pode ser consultado, mas não alterado.</Alerta>
      )}

      {plano && (
        <section className="cartao" aria-label="Situação do plano">
          <p className="cartao__titulo">
            {plano.nome}{" "}
            {plano.situacao
              ? <SeloStatus tom={TOM_DA_SITUACAO[plano.situacao]}>{ROTULO_SITUACAO[plano.situacao]}</SeloStatus>
              : <SeloStatus tom="neutro">Inativo</SeloStatus>}
          </p>
          {plano.situacao === "sem_base" && (
            <p className="texto-suave">
              Falta informar quando foi feita pela última vez. Sem isso não dá para calcular o prazo.
            </p>
          )}
          {plano.situacao && plano.situacao !== "sem_base" && resumo && (
            <p className="texto-suave">
              Próxima {textoPrevisao(plano)}: {resumo.valor} ({resumo.rotulo}).
              {plano.referencia_data && ` Contando desde ${formatarDataIso(plano.referencia_data)}`}
              {plano.referencia_km !== null && `${plano.referencia_data ? " e" : " Contando desde"} ${formatarKm(plano.referencia_km)}`}
              .
            </p>
          )}
          {!plano.ativo && <p className="texto-suave">Plano inativo não gera alertas.</p>}
          {plano.ativo && veiculo.ativo && (
            <Link to={`/veiculos/${veiculo.id}/manutencoes/nova?plano=${plano.id}`}
              className="botao-pequeno">
              Registrar manutenção deste plano
            </Link>
          )}
        </section>
      )}

      <form onSubmit={aoEnviar} noValidate>
        <fieldset disabled={somenteLeitura} className="grupo-campos">
          <CampoTexto rotulo="Nome" value={nome} maxLength={100} placeholder="Ex.: Troca de óleo"
            onChange={(e) => setNome(e.target.value)} erro={errosCampo.nome} />
          <CampoSelecao rotulo="Sistema" opcoes={SISTEMAS} value={sistema}
            onChange={(e) => setSistema(e.target.value)} erro={errosCampo.sistema} />

          <h2 className="rotulo-secao">Repetir a cada</h2>
          <div className="dupla">
            <CampoTexto rotulo="Quilômetros" inputMode="numeric" value={intervaloKm} maxLength={9}
              placeholder="Ex.: 10.000" onChange={(e) => setIntervaloKm(mascararInteiro(e.target.value))}
              erro={errosCampo.intervalo_km} />
            <CampoTexto rotulo="Meses" inputMode="numeric" value={intervaloMeses} maxLength={3}
              placeholder="Ex.: 12"
              onChange={(e) => setIntervaloMeses(e.target.value.replace(/\D/g, ""))}
              erro={errosCampo.intervalo_meses} />
          </div>
          <p className="texto-suave secao__dica">
            Preencha um dos dois ou os dois. Com os dois, vale o que chegar primeiro.
          </p>

          {(km !== null || meses !== null) && (
            <>
              <h2 className="rotulo-secao">Última vez que foi feita</h2>
              <div className="dupla">
                {meses !== null && (
                  <CampoTexto rotulo="Data" type="date" max={hoje} value={dataBase}
                    onChange={(e) => setDataBase(e.target.value)} erro={errosCampo.data_base} />
                )}
                {km !== null && (
                  <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={kmBase} maxLength={9}
                    onChange={(e) => setKmBase(mascararInteiro(e.target.value))}
                    erro={errosCampo.km_base} />
                )}
              </div>
              <p className="texto-suave secao__dica">
                É daqui que o prazo é contado até você registrar uma manutenção deste plano. Se não
                souber, use a data de hoje e a quilometragem atual ({formatarKm(veiculo.quilometragem)}):
                o prazo conta a partir de agora.
              </p>
            </>
          )}

          {!somenteLeitura && (
            <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
              {plano ? "Salvar alterações" : "Criar plano"}
            </BotaoEnviar>
          )}
        </fieldset>
      </form>

      {plano && !somenteLeitura && (
        <>
          <button type="button" className="botao botao--secundario botao--espaco" disabled={ocupado}
            onClick={() => void executar(async () => {
              aoMudar(await definirPlanoAtivo(veiculo.id, plano.id, !plano.ativo));
              setSucesso(plano.ativo ? "Plano desativado." : "Plano reativado.");
            })}>
            {plano.ativo ? "Desativar plano" : "Reativar plano"}
          </button>
          <button type="button" className="botao botao--texto-perigo" disabled={ocupado}
            onClick={() => setConfirmando(true)}>
            Apagar plano
          </button>
        </>
      )}

      {confirmando && plano && (
        <DialogoConfirmacao titulo="Apagar este plano?" textoConfirmar="Apagar" perigo ocupado={ocupado}
          aoCancelar={() => setConfirmando(false)}
          aoConfirmar={() => void executar(async () => {
            await apagarPlano(veiculo.id, plano.id);
            navegar(lista, { replace: true, state: { mensagem: "Plano apagado." } });
          })}>
          <p>
            Os alertas deste plano deixam de existir. As manutenções já registradas continuam no
            histórico, como avulsas. Se quiser só pausar os alertas, use "Desativar plano".
          </p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
