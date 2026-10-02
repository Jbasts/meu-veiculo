import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { Chave, DialogoConfirmacao, GrupoOpcoes } from "../components/Formulario";
import { faixaDoMarcador, SeletorDeNivel, textoDoKmPorLitro, textoDoUltimoNivel } from "../components/PecasTanque";
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
  rotuloDoNivel,
  temMarcador,
  TIPOS_POR_COMBUSTIVEL,
  unidade,
  type Abastecimento,
  type Combustivel,
  type DadosAbastecimento,
  type NivelTanque,
  type ResumoCombustivel,
} from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import {
  arredondarUmaCasa,
  dividirParaMilesimos,
  formatarDecimal,
  formatarDinheiro,
  formatarInteiro,
  formatarKm,
  lerDecimal3,
  lerDinheiro,
  lerInteiro,
  limiteDeLitros,
  litrosQueFaltam,
  maiorQue,
  mascararInteiro,
  multiplicarParaCentavos,
} from "../utils/formatos";

/**
 * Qual dos três valores a tela calcula (os outros dois são digitados):
 * total = litros × preço; litros = total ÷ preço; preço = total ÷ litros.
 */
type Calculado = "total" | "litros" | "preco";

interface Campos {
  combustivel: Combustivel;
  /** "" = não informado (abastecimento antigo) ou GNV. */
  tipo: string;
  data: string;
  km: string;
  calcular: Calculado;
  preco: string;
  litros: string;
  /** Valor total digitado (quando a tela calcula os litros ou o preço). */
  total: string;
  cupom: string;
  usarCupom: boolean;
  tanqueCheio: boolean;
  /** Marcador antes de abastecer, em oitavos; null = não informado. */
  nivel: number | null;
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
      calcular: "total", preco: formatarDecimal(existente.valor_litro, 2), litros: formatarDecimal(existente.litros, 2), total: "",
      cupom: doCupom ? formatarDinheiro(existente.valor_total).replace("R$ ", "") : "", usarCupom: doCupom,
      tanqueCheio: existente.tanque_cheio, nivel: existente.nivel_antes, posto: existente.posto ?? "",
    };
  }
  const combustivel = resumo.combustiveis[0];
  return { combustivel, tipo: TIPOS_POR_COMBUSTIVEL[combustivel][0]?.valor ?? "", data: hoje, km: "",
    calcular: "total", preco: "", litros: "", total: "", cupom: "", usarCupom: false, tanqueCheio: true, nivel: null,
    posto: "" };
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

  // Prévia do valor calculado (o gravado é o que o backend calcula).
  const litros = campos.calcular === "litros" ? null : lerDecimal3(campos.litros);
  const preco = campos.calcular === "preco" ? null : lerDecimal3(campos.preco);
  const total = campos.calcular === "total" ? null : lerDinheiro(campos.total);
  let calculado: string | null = null;
  if (campos.calcular === "total" && typeof litros === "string" && typeof preco === "string") {
    calculado = multiplicarParaCentavos(litros, preco);
  } else if (campos.calcular === "litros" && typeof total === "string" && typeof preco === "string") {
    calculado = dividirParaMilesimos(total, preco);
  } else if (campos.calcular === "preco" && typeof total === "string" && typeof litros === "string") {
    calculado = dividirParaMilesimos(total, litros);
  }
  const litrosFinais = campos.calcular === "litros" ? calculado : typeof litros === "string" ? litros : null;
  const precoFinal = campos.calcular === "preco" ? calculado : typeof preco === "string" ? preco : null;

  // Tanque: quanto falta para encher pelo marcador e o limite que o backend aceita.
  const comMarcador = temMarcador(campos.combustivel);
  const capacidade = comMarcador ? resumo.capacidade_tanque : null;
  const falta = capacidade && campos.nivel !== null ? litrosQueFaltam(capacidade, campos.nivel) : null;
  const passou = capacidade && litrosFinais && maiorQue(litrosFinais, limiteDeLitros(capacidade, campos.nivel));
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
    if (campos.calcular !== "preco") {
      if (preco === null) erros.valor_litro = "Informe o preço.";
      else if (preco === undefined) erros.valor_litro = "Preço inválido. Exemplo: 6,25.";
    }
    if (campos.calcular !== "litros") {
      if (litros === null) erros.litros = `Informe ${campos.combustivel === "gnv" ? "os m³" : "os litros"}.`;
      else if (litros === undefined) erros.litros = "Quantidade inválida. Exemplo: 40,5.";
    }
    if (campos.calcular !== "total") {
      if (total === null) erros.valor_total = "Informe o valor total.";
      else if (total === undefined) erros.valor_total = "Valor inválido. Exemplo: 250,00.";
    } else if (campos.usarCupom && cupom === null) erros.valor_total = "Informe o valor do cupom.";
    else if (campos.usarCupom && cupom === undefined) erros.valor_total = "Valor inválido. Exemplo: 250,00.";
    if (Object.keys(erros).length) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosAbastecimento = {
      combustivel: campos.combustivel, tipo: temTipo && campos.tipo ? campos.tipo : null,
      data: campos.data, quilometragem: km,
      // Só o que foi digitado: o valor calculado vai vazio e o backend calcula.
      litros: campos.calcular === "litros" ? null : (litros as string),
      valor_litro: campos.calcular === "preco" ? null : (preco as string),
      valor_total: campos.calcular !== "total" ? (total as string) : campos.usarCupom ? (cupom as string) : null,
      tanque_cheio: campos.tanqueCheio, nivel_antes: comMarcador ? campos.nivel : null,
      posto: campos.posto.trim() || null,
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
            Consumo deste tanque: {textoDoKmPorLitro(existente.consumo, existente.combustivel)}.
            {existente.consumo.estimado && ` ${faixaDoMarcador(existente.consumo.km_por_litro_minimo,
              existente.consumo.km_por_litro_maximo) ?? ""}.`}
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
            {comMarcador && capacidade && (
              <>
                <SeletorDeNivel rotulo="Marcador antes de abastecer" opcional valor={campos.nivel}
                  aoMudar={(n) => mudar("nivel", n)} erro={errosCampo.nivel_antes}
                  dica={campos.nivel === null
                    ? `Opcional. Com ele, o consumo aparece mesmo sem completar o tanque.${dicaDoNivel(resumo.nivel_tanque)}`
                    : undefined} />
                {falta && (
                  <p className="texto-suave cabe-no-tanque">
                    Com o marcador em {rotuloDoNivel(campos.nivel!)}, cabem cerca de {formatarDecimal(arredondarUmaCasa(falta))} {u.curta}
                    {" "}no tanque de {formatarDecimal(capacidade)} {u.curta}
                    {precoFinal ? `: encher sai por cerca de ${formatarDinheiro(multiplicarParaCentavos(falta, precoFinal))}.` : "."}
                  </p>
                )}
              </>
            )}
            {comMarcador && resumo.tanque_pendente && (
              <p className="texto-suave cabe-no-tanque">
                Para usar o nível do marcador e conferir se os litros cabem,{" "}
                <Link to={`/veiculos/${veiculo.id}/editar`} className="link">informe o tamanho do tanque</Link>.
              </p>
            )}

            <GrupoOpcoes rotulo="Calcular automaticamente" valor={campos.calcular}
              aoMudar={(c) => setCampos((atual) => ({ ...atual, calcular: c, usarCupom: false, cupom: "" }))}
              opcoes={[
                { valor: "total", rotulo: "Valor total" },
                { valor: "litros", rotulo: u.curta === "L" ? "Litros" : u.curta },
                { valor: "preco", rotulo: "Preço" },
              ]} />
            <div className="dupla">
              {campos.calcular !== "preco" && (
                <CampoTexto rotulo={u.preco} inputMode="decimal" value={campos.preco} maxLength={12}
                  placeholder="R$ 6,25" onChange={(e) => mudar("preco", e.target.value)} erro={errosCampo.valor_litro} />
              )}
              {campos.calcular !== "litros" && (
                <CampoTexto rotulo={u.quantidade} inputMode="decimal"
                  value={campos.litros} maxLength={12} placeholder="40,00"
                  onChange={(e) => mudar("litros", e.target.value)} erro={errosCampo.litros} />
              )}
              {campos.calcular !== "total" && (
                <CampoTexto rotulo="Valor total (R$)" inputMode="decimal" value={campos.total} maxLength={20}
                  placeholder="250,00" onChange={(e) => mudar("total", e.target.value)} erro={errosCampo.valor_total}
                  dica="O que a bomba mostrou." />
              )}
            </div>

            <section className="total-abastecimento" aria-label={
              campos.calcular === "total" ? "Valor total" : campos.calcular === "litros" ? u.quantidade : u.preco}>
              <span className="total-abastecimento__rotulo">
                {campos.calcular === "total" ? "Valor total" : campos.calcular === "litros" ? u.quantidade : u.preco}
                <small>{campos.calcular === "total" ? "litros × preço"
                  : campos.calcular === "litros" ? "valor total ÷ preço" : "valor total ÷ litros"}</small>
              </span>
              <strong>
                {campos.calcular === "total" ? (calculado ? formatarDinheiro(calculado) : "R$ —")
                  : campos.calcular === "litros" ? (calculado ? `${formatarDecimal(calculado)} ${u.curta}` : `— ${u.curta}`)
                    : (calculado ? `R$ ${formatarDecimal(calculado, 2)}` : "R$ —")}
              </strong>
            </section>
            {campos.calcular === "litros" && errosCampo.litros && (
              <p className="campo__erro" role="alert">{errosCampo.litros}</p>
            )}
            {campos.calcular === "preco" && errosCampo.valor_litro && (
              <p className="campo__erro" role="alert">{errosCampo.valor_litro}</p>
            )}
            {passou && (
              <Alerta tipo="info">
                {formatarDecimal(litrosFinais!)} {u.curta} parece mais do que cabe no tanque de {formatarDecimal(capacidade!)} {u.curta}
                {campos.nivel !== null ? ` com o marcador em ${rotuloDoNivel(campos.nivel)}` : ""}. Confira os valores.
              </Alerta>
            )}
            {campos.calcular !== "total" ? null : campos.usarCupom ? (
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

/** " Último nível: 3/4 em 02/10/2026 (≈ 1/4 agora)." para ajudar a conferir o marcador. */
function dicaDoNivel(n: NivelTanque): string {
  if (!n.disponivel || n.nivel === null) return "";
  const agora = n.nivel_estimado !== null ? ` (≈ ${rotuloDoNivel(n.nivel_estimado)} agora)` : "";
  return ` Último nível: ${textoDoUltimoNivel(n)}${agora}.`;
}
