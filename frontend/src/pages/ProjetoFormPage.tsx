import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoArea, GrupoOpcoes } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { criarProjeto, editarProjeto, obterProjeto } from "../services/projetoService";
import {
  CATEGORIAS_PROJETO,
  type CategoriaProjeto,
  type DadosProjeto,
  type ProjetoDetalhe,
  type StatusProjeto,
} from "../types/projeto";
import type { Veiculo } from "../types/veiculo";
import { dinheiroParaCampo, lerDinheiro } from "../utils/formatos";
import { erroObrigatorio, soErros } from "../utils/validacao";

const COMECO: { valor: StatusProjeto; rotulo: string }[] = [
  { valor: "planejado", rotulo: "Planejado" },
  { valor: "em_andamento", rotulo: "Já começou" },
];

/** "Novo projeto" e edição (nome, descrição, categoria, orçamento e previsão). */
export default function ProjetoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { projetoId } = useParams();
  const id = projetoId ? Number(projetoId) : null;
  const [existente, setExistente] = useState<ProjetoDetalhe | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo || id === null) return;
    let cancelado = false;
    obterProjeto(veiculo.id, id)
      .then((p) => {
        if (!cancelado) setExistente(p);
      })
      .catch((falha) => {
        if (!cancelado) setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o projeto.");
      });
    return () => {
      cancelado = true;
    };
  }, [veiculo, id]);

  const titulo = id ? "Editar projeto" : "Novo projeto";
  if (carregando || (veiculo && id !== null && !existente && !erroDados)) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo={titulo} voltarPara="/projetos" />
          <ErroComNovaTentativa mensagem={erro ?? erroDados ?? "Veículo não encontrado."}
            aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
        </main>
      </div>
    );
  }
  return <Formulario key={existente?.id ?? "novo"} veiculo={veiculo} existente={existente} titulo={titulo} />;
}

function Formulario({ veiculo, existente, titulo }: { veiculo: Veiculo; existente: ProjetoDetalhe | null; titulo: string }) {
  const navegar = useNavigate();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const [nome, setNome] = useState(existente?.nome ?? "");
  const [descricao, setDescricao] = useState(existente?.descricao ?? "");
  const [categoria, setCategoria] = useState<CategoriaProjeto>(existente?.categoria ?? "exterior");
  const [orcamento, setOrcamento] = useState(dinheiroParaCampo(existente?.orcamento ?? null));
  const [prevista, setPrevista] = useState(existente?.data_prevista ?? "");
  const [status, setStatus] = useState<StatusProjeto>("planejado");

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const valor = lerDinheiro(orcamento);
    const erros = soErros({
      nome: erroObrigatorio(nome, "Dê um nome ao projeto."),
      orcamento: valor === undefined ? "Valor inválido. Exemplo: 4.500,00." : null,
    });
    if (Object.keys(erros).length || valor === undefined) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosProjeto = {
      nome: nome.trim(), descricao: descricao.trim() || null, categoria, orcamento: valor,
      data_prevista: prevista || null,
    };
    let destino = "";
    const deuCerto = await enviar(async () => {
      const salvo = existente
        ? await editarProjeto(veiculo.id, existente.id, dados)
        : await criarProjeto(veiculo.id, { ...dados, status });
      destino = `/veiculos/${veiculo.id}/projetos/${salvo.id}`;
    });
    if (deuCerto) {
      navegar(destino, { replace: true, state: { mensagem: existente ? "Alterações salvas." : "Projeto criado." } });
    }
  }

  const voltar = existente ? `/veiculos/${veiculo.id}/projetos/${existente.id}` : `/veiculos/${veiculo.id}/projetos`;
  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        <form onSubmit={aoEnviar} noValidate>
          <CampoTexto rotulo="Nome" value={nome} maxLength={120} placeholder="Ex.: Rodas de liga leve"
            onChange={(e) => setNome(e.target.value)} erro={errosCampo.nome} />
          <CampoArea rotulo="Descrição" value={descricao} maxLength={2000} placeholder="O que vai ser feito (opcional)"
            onChange={(e) => setDescricao(e.target.value)} erro={errosCampo.descricao} />
          <GrupoOpcoes rotulo="Categoria" opcoes={CATEGORIAS_PROJETO} valor={categoria} aoMudar={setCategoria}
            erro={errosCampo.categoria} />
          <div className="dupla">
            <CampoTexto rotulo="Orçamento (R$)" inputMode="decimal" value={orcamento} maxLength={20}
              placeholder="Opcional" onChange={(e) => setOrcamento(e.target.value)} erro={errosCampo.orcamento} />
            <CampoTexto rotulo="Previsão" type="date" value={prevista}
              onChange={(e) => setPrevista(e.target.value)} erro={errosCampo.data_prevista} dica="Opcional" />
          </div>
          {!existente && (
            <GrupoOpcoes rotulo="Situação" opcoes={COMECO} valor={status} aoMudar={setStatus} erro={errosCampo.status} />
          )}
          <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
            {existente ? "Salvar alterações" : "Criar projeto"}
          </BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
