import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { Chave, DialogoConfirmacao, GrupoOpcoes } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  apagarAbastecimento,
  criarAbastecimento,
  editarAbastecimento,
  obterAbastecimento,
  obterResumoCombustivel,
} from "../services/abastecimentoService";
import {
  ROTULO_COMBUSTIVEL,
  TIPOS_POR_COMBUSTIVEL,
  unidade,
  type Abastecimento,
  type Combustivel,
  type DadosAbastecimento,
  type ResumoCombustivel,
} from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import {
  formatarDecimal,
  formatarDinheiro,
  formatarInteiro,
  formatarKm,
  lerDecimal3,
  lerDinheiro,
  lerInteiro,
  mascararInteiro,
  multiplicarParaCentavos,
} from "../utils/formatos";

interface Campos {
  combustivel: Combustivel;
  /** "" = não informado (abastecimento antigo) ou GNV. */
  tipo: string;
  data: string;
  km: string;
  preco: string;
  litros: string;
  cupom: string;
  usarCupom: boolean;
  tanqueCheio: boolean;
  posto: string;
}

/** "Novo abastecimento" (PDF, página 13) e edição (/veiculos/:id/abastecimentos/:abastecimentoId). */
export default function AbastecimentoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { abastecimentoId } = useParams();
  const id = abastecimentoId && abastecimentoId !== "novo" ? Number(abastecimentoId) : null;
  const [resumo, setResumo] = useState<ResumoCombustivel | null>(null);
  const [existente, setExistente] = useState<Abastecimento | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo) return;
    let cancelado = false;
    Promise.all([
      obterResumoCombustivel(veiculo.id),
      id ? obterAbastecimento(veiculo.id, id) : Promise.resolve(null),
    ]).then(([r, a]) => {
      if (cancelado) return;
      setResumo(r);
      setExistente(a);
    }).catch((falha) => {
      if (!cancelado) setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar os dados.");
    });
    return () => {
      cancelado = true;
    };
  }, [veiculo, id]);

  const titulo = id ? "Abastecimento" : "Novo abastecimento";
  const voltar = veiculo ? `/veiculos/${veiculo.id}/financas?aba=combustivel` : "/financas?aba=combustivel";
  if (carregando || (veiculo && !erroDados && (!resumo || (id && !existente)))) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo || !resumo) {
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
  return <Formulario key={existente?.id ?? "novo"} veiculo={veiculo} resumo={resumo} existente={existente}
    titulo={titulo} voltar={voltar} />;
}

function camposIniciais(existente: Abastecimento | null, resumo: ResumoCombustivel, hoje: string): Campos {
  if (existente) {
    const calculado = multiplicarParaCentavos(existente.litros, existente.valor_litro);
    const doCupom = existente.valor_total !== calculado;
    return {
      combustivel: existente.combustivel, tipo: existente.tipo ?? "", data: existente.data, km: formatarInteiro(existente.quilometragem),
      preco: formatarDecimal(existente.valor_litro, 2), litros: formatarDecimal(existente.litros, 2),
      cupom: doCupom ? formatarDinheiro(existente.valor_total).replace("R$ ", "") : "", usarCupom: doCupom,
      tanqueCheio: existente.tanque_cheio, posto: existente.posto ?? "",
    };
  }
  const combustivel = resumo.combustiveis[0];
  return { combustivel, tipo: TIPOS_POR_COMBUSTIVEL[combustivel][0]?.valor ?? "", data: hoje, km: "", preco: "", litros: "", cupom: "",
    usarCupom: false, tanqueCheio: true, posto: "" };
}

function Formulario({ veiculo, resumo, existente, titulo, voltar }: {
  veiculo: Veiculo; resumo: ResumoCombustivel; existente: Abastecimento | null; titulo: string; voltar: string;
}) {
  const navegar = useNavigate();
  const { recarregar: recarregarLista } = useVeiculos();
  const hoje = hojeIso();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const [campos, setCampos] = useState<Campos>(() => camposIniciais(existente, resumo, hoje));
  const [confirmando, setConfirmando] = useState(false);
  const [apagando, setApagando] = useState(false);
  const [erroApagar, setErroApagar] = useState<string | null>(null);
  const podeAlterar = veiculo.ativo;
  const u = unidade(campos.combustivel);

  function mudar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  /** Trocar de combustível volta o tipo para o primeiro da lista dele (cada um tem os seus). */
  function escolherCombustivel(combustivel: Combustivel) {
    setCampos((atual) => ({ ...atual, combustivel,
      tipo: combustivel === atual.combustivel ? atual.tipo : TIPOS_POR_COMBUSTIVEL[combustivel][0]?.valor ?? "" }));
  }

  // Prévia do total (o gravado é o que o backend calcula).
  const litros = lerDecimal3(campos.litros);
  const preco = lerDecimal3(campos.preco);
  const calculado = typeof litros === "string" && typeof preco === "string"
    ? multiplicarParaCentavos(litros, preco) : null;
  const opcoes = resumo.combustiveis.map((c) => ({ valor: c, rotulo: ROTULO_COMBUSTIVEL[c] }));
  const tipos = TIPOS_POR_COMBUSTIVEL[campos.combustivel];
  const temTipo = tipos.length > 0;
  // Abastecimento antigo sem tipo pode continuar sem: o tipo não é inventado.
  const antigoSemTipo = existente !== null && existente.tipo === null;

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const km = lerInteiro(campos.km);
    const cupom = campos.usarCupom ? lerDinheiro(campos.cupom) : null;
    const erros: Record<string, string> = {};
    if (temTipo && !campos.tipo && !antigoSemTipo) erros.tipo = "Escolha o tipo.";
    if (!campos.data) erros.data = "Informe a data.";
    else if (campos.data > hoje) erros.data = "A data não pode ser no futuro.";
    if (km === null) erros.quilometragem = "Informe a quilometragem.";
    if (preco === null) erros.valor_litro = "Informe o preço.";
    else if (preco === undefined) erros.valor_litro = "Preço inválido. Exemplo: 6,25.";
    if (litros === null) erros.litros = `Informe ${campos.combustivel === "gnv" ? "os m³" : "os litros"}.`;
    else if (litros === undefined) erros.litros = "Quantidade inválida. Exemplo: 40,5.";
    if (campos.usarCupom && cupom === null) erros.valor_total = "Informe o valor do cupom.";
    else if (campos.usarCupom && cupom === undefined) erros.valor_total = "Valor inválido. Exemplo: 250,00.";
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosAbastecimento = {
      combustivel: campos.combustivel, tipo: temTipo && campos.tipo ? campos.tipo : null,
      data: campos.data, quilometragem: km,
      litros: litros as string, valor_litro: preco as string,
      valor_total: campos.usarCupom ? (cupom as string) : null,
      tanque_cheio: campos.tanqueCheio, posto: campos.posto.trim() || null,
    };
    const deuCerto = await enviar(async () => {
      if (existente) await editarAbastecimento(veiculo.id, existente.id, dados);
      else await criarAbastecimento(veiculo.id, dados);
      await recarregarLista(); // a quilometragem do veículo pode ter mudado
    });
    if (deuCerto) {
      navegar(voltar, { replace: true, state: { mensagem: existente ? "Alterações salvas." : "Abastecimento registrado." } });
    }
  }

  async function apagar() {
    if (!existente || apagando) return;
    setApagando(true);
    try {
      await apagarAbastecimento(veiculo.id, existente.id);
      await recarregarLista();
      navegar(voltar, { replace: true, state: { mensagem: "Abastecimento apagado." } });
    } catch (falha) {
      setErroApagar(falha instanceof ErroDaApi ? falha.message : "Não foi possível apagar.");
      setApagando(false);
      setConfirmando(false);
    }
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {!podeAlterar && <Alerta tipo="info">Veículo inativo: o abastecimento pode ser consultado, mas não alterado.</Alerta>}
        {existente?.consumo.motivo && existente.consumo.tipo !== "primeiro_cheio" && (
          <Alerta tipo="info">{existente.consumo.motivo}</Alerta>
        )}
        {existente?.consumo.tipo === "consumo" && (
          <Alerta tipo="info">
            Consumo deste tanque: {formatarDecimal(existente.consumo.km_por_litro!, 1)} {unidade(existente.combustivel).consumo}.
          </Alerta>
        )}
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}
        {erroApagar && <Alerta tipo="erro">{erroApagar}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          <fieldset className="grupo-campos" disabled={!podeAlterar}>
            {opcoes.length > 1 && (
              <GrupoOpcoes rotulo="Combustível" opcoes={opcoes} valor={campos.combustivel}
                aoMudar={escolherCombustivel} erro={errosCampo.combustivel} />
            )}
            {opcoes.length === 1 && <p className="texto-suave">Combustível: {opcoes[0].rotulo}</p>}
            {temTipo && (
              <>
                <GrupoOpcoes rotulo="Tipo" opcoes={tipos} valor={campos.tipo}
                  aoMudar={(t) => mudar("tipo", t)} erro={errosCampo.tipo} />
                {antigoSemTipo && !campos.tipo && (
                  <p className="campo__dica tipo__dica">Não informado (abastecimento antigo). Escolha se souber.</p>
                )}
              </>
            )}

            <div className="dupla">
              <CampoTexto rotulo="Data" type="date" max={hoje} value={campos.data}
                onChange={(e) => mudar("data", e.target.value)} erro={errosCampo.data}
                dica={campos.data === hoje ? "Hoje" : undefined} />
              <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={campos.km} maxLength={9}
                placeholder={`Ex.: ${formatarInteiro(resumo.ultima_quilometragem + 450)}`}
                onChange={(e) => mudar("km", mascararInteiro(e.target.value))} erro={errosCampo.quilometragem}
                dica={`Última: ${formatarKm(resumo.ultima_quilometragem)}`} />
            </div>
            <div className="dupla">
              <CampoTexto rotulo={u.preco} inputMode="decimal" value={campos.preco} maxLength={12}
                placeholder="R$ 6,25" onChange={(e) => mudar("preco", e.target.value)} erro={errosCampo.valor_litro} />
              <CampoTexto rotulo={u.quantidade} inputMode="decimal"
                value={campos.litros} maxLength={12} placeholder="40,00"
                onChange={(e) => mudar("litros", e.target.value)} erro={errosCampo.litros} />
            </div>

            <section className="total-abastecimento" aria-label="Valor total">
              <span>Valor total</span>
              <strong>{calculado ? formatarDinheiro(calculado) : "R$ —"}</strong>
            </section>
            {campos.usarCupom ? (
              <CampoTexto rotulo="Valor do cupom (R$)" inputMode="decimal" value={campos.cupom} maxLength={20}
                placeholder="0,00" onChange={(e) => mudar("cupom", e.target.value)} erro={errosCampo.valor_total}
                dica={`Calculado: ${calculado ? formatarDinheiro(calculado) : "—"}. Vale o do cupom se a diferença for de até R$ 50,00.`} />
            ) : (
              <>
                {errosCampo.valor_total && <p className="campo__erro" role="alert">{errosCampo.valor_total}</p>}
                <button type="button" className="botao-link botao-link--neutro" onClick={() => mudar("usarCupom", true)}>
                  O cupom mostra outro valor? Corrigir pelo cupom
                </button>
              </>
            )}

            <Chave titulo={u.cheio} ligada={campos.tanqueCheio} aoMudar={(v) => mudar("tanqueCheio", v)}
              descricao={campos.tanqueCheio ? u.cheioDescricao
                : "Parcial: entra no cálculo quando você completar de novo."} />

            <CampoTexto rotulo="Posto" value={campos.posto} maxLength={80} placeholder="Opcional"
              onChange={(e) => mudar("posto", e.target.value)} erro={errosCampo.posto} />
            {resumo.postos_recentes.length > 0 && (
              <div className="recentes">
                <span className="texto-suave">Recentes</span>
                {resumo.postos_recentes.map((p) => (
                  <button key={p} type="button" className={`opcao${campos.posto === p ? " opcao--ativa" : ""}`}
                    onClick={() => mudar("posto", p)}>
                    {p}
                  </button>
                ))}
              </div>
            )}

            {podeAlterar && (
              <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
                {existente ? "Salvar alterações" : "Salvar abastecimento"}
              </BotaoEnviar>
            )}
          </fieldset>
        </form>

        {existente && podeAlterar && (
          <button type="button" className="botao botao--texto-perigo" disabled={apagando}
            onClick={() => setConfirmando(true)}>
            Apagar abastecimento
          </button>
        )}
        {confirmando && (
          <DialogoConfirmacao titulo="Apagar este abastecimento?" textoConfirmar="Apagar" perigo ocupado={apagando}
            aoCancelar={() => setConfirmando(false)} aoConfirmar={() => void apagar()}>
            <p>O valor sai das despesas, a leitura de quilometragem dele é retirada e o consumo é recalculado. Não dá para desfazer.</p>
          </DialogoConfirmacao>
        )}
      </main>
    </div>
  );
}
