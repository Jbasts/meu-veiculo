import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { Chave, DialogoConfirmacao, GrupoOpcoes } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { apagarGasto, criarGasto, editarGasto, obterGasto } from "../services/gastoService";
import { CATEGORIAS_GASTO, type CategoriaGasto, type DadosGasto, type Gasto } from "../types/gasto";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, hojeIso, mesDaData } from "../utils/datas";
import { dinheiroParaCampo, lerDinheiro } from "../utils/formatos";

interface Campos {
  valor: string;
  categoria: CategoriaGasto | "";
  descricao: string;
  data: string;
  pago: boolean;
  vencimento: string;
  pagamento: string;
  /** A data do pagamento acompanha a data do gasto até a pessoa mudar uma das duas à mão. */
  pagamentoTocado: boolean;
}

/** "Novo gasto" (PDF, página 12) e edição de um gasto (/veiculos/:id/gastos/:gastoId). */
export default function GastoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { gastoId } = useParams();
  const id = gastoId && gastoId !== "novo" ? Number(gastoId) : null;
  const [existente, setExistente] = useState<Gasto | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo || id === null) return;
    let cancelado = false;
    obterGasto(veiculo.id, id)
      .then((gasto) => {
        if (!cancelado) setExistente(gasto);
      })
      .catch((falha) => {
        if (!cancelado) setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o gasto.");
      });
    return () => {
      cancelado = true;
    };
  }, [veiculo, id]);

  const titulo = id ? "Gasto" : "Novo gasto";
  if (carregando || (veiculo && id !== null && !existente && !erroDados)) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo={titulo} voltarPara={veiculo ? `/veiculos/${veiculo.id}/financas` : "/financas"} />
          <ErroComNovaTentativa mensagem={erro ?? erroDados ?? "Veículo não encontrado."}
            aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
        </main>
      </div>
    );
  }
  return <Formulario key={existente?.id ?? "novo"} veiculo={veiculo} existente={existente} titulo={titulo} />;
}

function camposIniciais(existente: Gasto | null, hoje: string): Campos {
  if (!existente) {
    return { valor: "", categoria: "", descricao: "", data: hoje, pago: true, vencimento: "",
      pagamento: hoje, pagamentoTocado: false };
  }
  return {
    valor: dinheiroParaCampo(existente.valor), categoria: existente.categoria,
    descricao: existente.descricao ?? "", data: existente.data, pago: existente.pago,
    vencimento: existente.data_vencimento ?? "", pagamento: existente.data_pagamento ?? "",
    pagamentoTocado: true,
  };
}

/** Para onde voltar: Finanças no mês em que o gasto conta (pago) ou no mês atual (pendente). */
function financasDoGasto(veiculoId: number, gasto: Gasto): string {
  const data = gasto.pago ? gasto.data_pagamento ?? gasto.data : null;
  if (!data) return `/veiculos/${veiculoId}/financas`;
  const { ano, mes } = mesDaData(data);
  return `/veiculos/${veiculoId}/financas?ano=${ano}&mes=${mes}`;
}

function Formulario({ veiculo, existente, titulo }: { veiculo: Veiculo; existente: Gasto | null; titulo: string }) {
  const navegar = useNavigate();
  const hoje = hojeIso();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const [campos, setCampos] = useState<Campos>(() => camposIniciais(existente, hoje));
  const [confirmando, setConfirmando] = useState(false);
  const [apagando, setApagando] = useState(false);
  const [erroApagar, setErroApagar] = useState<string | null>(null);
  const podeAlterar = veiculo.ativo;
  // Gasto pago antigo (antes da migration 0007): a data do pagamento não foi informada.
  const antigoSemPagamento = existente !== null && existente.pago && existente.data_pagamento === null;

  function mudar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  function mudarData(data: string) {
    setCampos((atual) => ({ ...atual, data, pagamento: atual.pagamentoTocado ? atual.pagamento : data }));
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const valor = lerDinheiro(campos.valor);
    const erros: Record<string, string> = {};
    if (valor === null) erros.valor = "Informe o valor.";
    else if (valor === undefined) erros.valor = "Valor inválido. Exemplo: 2.400,00.";
    else if (/^0+\.00$/.test(valor)) erros.valor = "O valor precisa ser maior que zero.";
    if (!campos.categoria) erros.categoria = "Escolha a categoria.";
    if (!campos.data) erros.data = "Informe a data.";
    else if (campos.data > hoje) {
      erros.data = "A data do gasto não pode ser no futuro. Para uma conta que ainda vai vencer, desligue \"Já foi pago\" e informe o vencimento.";
    }
    if (campos.pago) {
      if (!campos.pagamento && !antigoSemPagamento) erros.data_pagamento = "Informe a data do pagamento.";
      else if (campos.pagamento > hoje) erros.data_pagamento = "A data do pagamento não pode ser no futuro.";
    } else if (!campos.vencimento) {
      erros.data_vencimento = "Informe o vencimento: ele faz a conta aparecer em \"A vencer\".";
    }
    if (Object.keys(erros).length || typeof valor !== "string" || !campos.categoria) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosGasto = {
      categoria: campos.categoria, valor, descricao: campos.descricao.trim() || null,
      data: campos.data, pago: campos.pago,
      data_vencimento: campos.vencimento || null,
      data_pagamento: campos.pago ? campos.pagamento || null : null,
    };
    let destino = "";
    const deuCerto = await enviar(async () => {
      const salvo = existente
        ? await editarGasto(veiculo.id, existente.id, dados)
        : await criarGasto(veiculo.id, dados);
      destino = financasDoGasto(veiculo.id, salvo);
    });
    if (deuCerto) {
      navegar(destino, {
        replace: true,
        state: { mensagem: existente ? "Alterações salvas." : campos.pago ? "Gasto registrado." : "Conta registrada em \"A vencer\"." },
      });
    }
  }

  async function apagar() {
    if (!existente || apagando) return;
    setApagando(true);
    try {
      await apagarGasto(veiculo.id, existente.id);
      navegar(financasDoGasto(veiculo.id, existente), { replace: true, state: { mensagem: "Gasto apagado." } });
    } catch (falha) {
      setErroApagar(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setApagando(false);
      setConfirmando(false);
    }
  }

  const voltar = existente ? financasDoGasto(veiculo.id, existente) : `/veiculos/${veiculo.id}/financas`;
  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {!podeAlterar && (
          <Alerta tipo="info">Veículo inativo: o gasto pode ser consultado, mas não alterado.</Alerta>
        )}
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        {erroApagar && <Alerta tipo="erro">{erroApagar}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          <fieldset className="grupo-campos" disabled={!podeAlterar}>
            <div className="valor-grande">
              <CampoTexto rotulo="Valor" inputMode="decimal" value={campos.valor} maxLength={20}
                placeholder="R$ 0,00" onChange={(e) => mudar("valor", e.target.value)} erro={errosCampo.valor} />
            </div>
            <GrupoOpcoes rotulo="Categoria" opcoes={CATEGORIAS_GASTO} valor={campos.categoria}
              aoMudar={(valor) => mudar("categoria", valor)} erro={errosCampo.categoria} />
            <CampoTexto rotulo="Descrição" value={campos.descricao} maxLength={150}
              placeholder="Ex.: Renovação do seguro (opcional)"
              onChange={(e) => mudar("descricao", e.target.value)} erro={errosCampo.descricao} />
            <CampoTexto rotulo="Data" type="date" max={hoje} value={campos.data}
              onChange={(e) => mudarData(e.target.value)} erro={errosCampo.data}
              dica={campos.data === hoje ? "Hoje. Toque para alterar." : undefined} />

            <Chave titulo="Já foi pago" ligada={campos.pago} aoMudar={(pago) => mudar("pago", pago)}
              descricao={campos.pago ? "Entra nas despesas do mês do pagamento."
                : "Vai aparecer em \"A vencer\" nas Finanças."} />

            {campos.pago ? (
              <CampoTexto rotulo="Data do pagamento" type="date" max={hoje} value={campos.pagamento}
                onChange={(e) => setCampos((atual) => ({ ...atual, pagamento: e.target.value, pagamentoTocado: true }))}
                erro={errosCampo.data_pagamento}
                dica={antigoSemPagamento && !campos.pagamento
                  ? `Não informada (gasto antigo): ele conta pela data do gasto, ${formatarDataIso(campos.data)}.`
                  : "O mês do pagamento é o mês em que o gasto entra nas despesas."} />
            ) : (
              <CampoTexto rotulo="Vencimento" type="date" value={campos.vencimento}
                onChange={(e) => mudar("vencimento", e.target.value)} erro={errosCampo.data_vencimento} />
            )}

            {podeAlterar && (
              <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
                {existente ? "Salvar alterações" : "Salvar gasto"}
              </BotaoEnviar>
            )}
          </fieldset>
        </form>

        {existente && podeAlterar && (
          <button type="button" className="botao botao--texto-perigo" disabled={apagando}
            onClick={() => setConfirmando(true)}>
            Apagar gasto
          </button>
        )}
        {confirmando && (
          <DialogoConfirmacao titulo="Apagar este gasto?" textoConfirmar="Apagar" perigo ocupado={apagando}
            aoCancelar={() => setConfirmando(false)} aoConfirmar={() => void apagar()}>
            <p>{existente?.pago ? "O valor sai das despesas do mês." : "A conta sai de \"A vencer\"."} Não dá para desfazer.</p>
          </DialogoConfirmacao>
        )}
      </main>
    </div>
  );
}
