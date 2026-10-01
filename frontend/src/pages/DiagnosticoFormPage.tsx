import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoArea, GrupoOpcoes } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { criarDiagnostico, editarDiagnostico, obterDiagnostico } from "../services/diagnosticoService";
import {
  GRAVIDADES,
  type DadosDiagnostico,
  type DiagnosticoDetalhe,
  type Gravidade,
} from "../types/diagnostico";
import { SISTEMAS } from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import { formatarInteiro, formatarKm, lerInteiro, mascararInteiro } from "../utils/formatos";
import { erroObrigatorio, soErros } from "../utils/validacao";

interface Campos {
  titulo: string;
  descricao: string;
  sistema: string;
  gravidade: Gravidade;
  data: string;
  km: string;
}

/** "Novo diagnóstico" (PDF, página 7) e a edição do que foi registrado. */
export default function DiagnosticoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { diagnosticoId } = useParams();
  const id = diagnosticoId ? Number(diagnosticoId) : null;
  const [existente, setExistente] = useState<DiagnosticoDetalhe | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo || id === null) return;
    let cancelado = false;
    obterDiagnostico(veiculo.id, id)
      .then((detalhe) => {
        if (!cancelado) setExistente(detalhe);
      })
      .catch((falha) => {
        if (!cancelado) {
          setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o diagnóstico.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [veiculo, id]);

  const titulo = id ? "Editar diagnóstico" : "Novo diagnóstico";
  if (carregando || (veiculo && id !== null && !existente && !erroDados)) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo={titulo} voltarPara={veiculo ? `/veiculos/${veiculo.id}/diagnosticos` : "/diagnostico"} />
          <ErroComNovaTentativa mensagem={erro ?? erroDados ?? "Veículo não encontrado."}
            aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
        </main>
      </div>
    );
  }
  return <Formulario key={existente?.id ?? "novo"} veiculo={veiculo} existente={existente} titulo={titulo} />;
}

function Formulario({ veiculo, existente, titulo }: {
  veiculo: Veiculo; existente: DiagnosticoDetalhe | null; titulo: string;
}) {
  const navegar = useNavigate();
  const { recarregar: recarregarLista } = useVeiculos();
  const hoje = hojeIso();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const [campos, setCampos] = useState<Campos>(() => (existente ? {
    titulo: existente.titulo, descricao: existente.descricao ?? "", sistema: existente.sistema,
    gravidade: existente.gravidade, data: existente.data_identificacao,
    km: existente.quilometragem === null ? "" : formatarInteiro(existente.quilometragem),
  } : { titulo: "", descricao: "", sistema: "outros", gravidade: "media", data: hoje, km: "" }));

  function mudar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros = soErros({
      titulo: erroObrigatorio(campos.titulo, "Conte em poucas palavras o que está acontecendo."),
      data_identificacao: !campos.data ? "Informe a data."
        : campos.data > hoje ? "A data não pode ser no futuro." : null,
    });
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosDiagnostico = {
      titulo: campos.titulo.trim(), descricao: campos.descricao.trim() || null,
      sistema: campos.sistema, gravidade: campos.gravidade, data_identificacao: campos.data,
      quilometragem: lerInteiro(campos.km),
    };
    let destino = "";
    const deuCerto = await enviar(async () => {
      const salvo = existente
        ? await editarDiagnostico(veiculo.id, existente.id, dados)
        : await criarDiagnostico(veiculo.id, dados);
      destino = `/veiculos/${veiculo.id}/diagnosticos/${salvo.id}`;
      if (dados.quilometragem !== null) await recarregarLista(); // a quilometragem pode ter mudado
    });
    if (deuCerto) {
      navegar(destino, {
        replace: true, state: { mensagem: existente ? "Alterações salvas." : "Problema registrado." },
      });
    }
  }

  const orientacao = GRAVIDADES.find((g) => g.valor === campos.gravidade)?.orientacao;
  const voltar = existente
    ? `/veiculos/${veiculo.id}/diagnosticos/${existente.id}`
    : `/veiculos/${veiculo.id}/diagnosticos`;

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          <CampoTexto rotulo="O que está acontecendo?" value={campos.titulo} maxLength={150}
            placeholder="Ex.: Barulho na suspensão dianteira"
            onChange={(e) => mudar("titulo", e.target.value)} erro={errosCampo.titulo} />
          <CampoArea rotulo="Detalhes" value={campos.descricao} maxLength={2000}
            placeholder="Quando acontece, de que lado, se piora com o motor frio..."
            onChange={(e) => mudar("descricao", e.target.value)} erro={errosCampo.descricao} />
          <GrupoOpcoes rotulo="Sistema" opcoes={SISTEMAS} valor={campos.sistema}
            aoMudar={(valor) => mudar("sistema", valor)} erro={errosCampo.sistema} />
          <GrupoOpcoes rotulo="Gravidade" opcoes={GRAVIDADES} valor={campos.gravidade}
            aoMudar={(valor) => mudar("gravidade", valor)} erro={errosCampo.gravidade} />
          {orientacao && <p className="campo__dica diagnostico__orientacao">{orientacao}</p>}

          <div className="dupla">
            <CampoTexto rotulo="Data" type="date" max={hoje} value={campos.data}
              onChange={(e) => mudar("data", e.target.value)} erro={errosCampo.data_identificacao}
              dica={campos.data === hoje ? "Hoje. Toque para alterar." : undefined} />
            <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={campos.km} maxLength={9}
              placeholder="Opcional" onChange={(e) => mudar("km", mascararInteiro(e.target.value))}
              erro={errosCampo.quilometragem} dica={`Atual: ${formatarKm(veiculo.quilometragem)}`} />
          </div>

          <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
            {existente ? "Salvar alterações" : "Registrar problema"}
          </BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
