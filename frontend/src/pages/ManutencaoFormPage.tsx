import { useEffect, useRef, useState, type FormEvent } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoArea, CampoSelecao, GrupoOpcoes } from "../components/Formulario";
import TopoComVoltar from "../components/TopoComVoltar";
import { rotulosDosValores } from "../components/ValoresManutencao";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import {
  criarManutencao,
  editarManutencao,
  listarPlanos,
  obterManutencao,
} from "../services/manutencaoService";
import {
  SISTEMAS,
  textoIntervalo,
  type DadosManutencao,
  type ManutencaoDetalhe,
  type Plano,
  type StatusManutencao,
  type TipoItem,
} from "../types/manutencao";
import type { Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import {
  dinheiroParaCampo,
  formatarDinheiro,
  formatarInteiro,
  formatarKm,
  lerDinheiro,
  lerInteiro,
  mascararInteiro,
  somarDinheiro,
} from "../utils/formatos";
import { erroObrigatorio, soErros } from "../utils/validacao";

const STATUS: { valor: StatusManutencao; rotulo: string }[] = [
  { valor: "realizada", rotulo: "Já foi feita" },
  { valor: "agendada", rotulo: "Agendar" },
];

interface Campos {
  status: StatusManutencao;
  descricao: string;
  sistema: string;
  planoId: string;
  data: string;
  km: string;
  valor: string;
  oficina: string;
  garantiaAte: string;
  garantiaKm: string;
  proximaData: string;
  proximaKm: string;
  observacao: string;
}

/** Uma linha de peça ou de mão de obra no formulário. */
interface ItemNoFormulario {
  chave: number;
  tipo: TipoItem;
  nome: string;
  valor: string;
}

const AREAS: { tipo: TipoItem; titulo: string; rotulo: string; adicionar: string; exemplo: string }[] = [
  { tipo: "peca", titulo: "Peças", rotulo: "Peça", adicionar: "+ Adicionar peça",
    exemplo: "Ex.: Filtro de óleo" },
  { tipo: "mao_de_obra", titulo: "Mão de obra", rotulo: "Mão de obra", adicionar: "+ Adicionar mão de obra",
    exemplo: "Ex.: Troca do filtro de óleo" },
];

function km(valor: number | null): string {
  return valor === null ? "" : formatarInteiro(valor);
}

function camposDe(m: ManutencaoDetalhe): Campos {
  return {
    status: m.status, descricao: m.descricao, sistema: m.sistema,
    planoId: m.plano_id === null ? "" : String(m.plano_id),
    data: m.data, km: km(m.quilometragem),
    valor: m.itens.length ? "" : dinheiroParaCampo(m.valor),
    oficina: m.oficina ?? "", garantiaAte: m.garantia_ate ?? "", garantiaKm: km(m.garantia_km),
    proximaData: m.proxima_data ?? "", proximaKm: km(m.proxima_km), observacao: m.observacao ?? "",
  };
}

/** "Nova manutenção" (PDF, página 9) e edição. ?plano=ID já escolhe o plano;
 *  ?concluir=1 abre a agendada pronta para ser marcada como realizada. */
export default function ManutencaoFormPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { manutencaoId } = useParams();
  const idManutencao = manutencaoId ? Number(manutencaoId) : null;
  const [planos, setPlanos] = useState<Plano[] | null>(null);
  const [existente, setExistente] = useState<ManutencaoDetalhe | null>(null);
  const [erroDados, setErroDados] = useState<string | null>(null);

  useEffect(() => {
    if (!veiculo) return;
    let cancelado = false;
    Promise.all([
      listarPlanos(veiculo.id),
      idManutencao ? obterManutencao(veiculo.id, idManutencao) : Promise.resolve(null),
    ]).then(([lista, manutencao]) => {
      if (cancelado) return;
      setPlanos(lista);
      setExistente(manutencao);
      setErroDados(null);
    }).catch((falha) => {
      if (!cancelado) {
        setErroDados(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar os dados.");
      }
    });
    return () => {
      cancelado = true;
    };
  }, [veiculo, idManutencao]);

  const titulo = idManutencao ? "Editar manutenção" : "Nova manutenção";
  if (carregando || (veiculo && !erroDados && (planos === null || (idManutencao && !existente)))) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || erroDados || !veiculo || planos === null) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo={titulo} voltarPara={veiculo ? `/veiculos/${veiculo.id}/manutencoes` : "/manutencao"} />
          <ErroComNovaTentativa mensagem={erro ?? erroDados ?? "Veículo não encontrado."}
            aoTentar={() => (erro ? void recarregar() : window.location.reload())} />
        </main>
      </div>
    );
  }
  return <Formulario key={existente?.id ?? "nova"} veiculo={veiculo} planos={planos}
    existente={existente} titulo={titulo} />;
}

function Formulario({ veiculo, planos, existente, titulo }: {
  veiculo: Veiculo; planos: Plano[]; existente: ManutencaoDetalhe | null; titulo: string;
}) {
  const navegar = useNavigate();
  const [parametros] = useSearchParams();
  const { recarregar: recarregarLista } = useVeiculos();
  const hoje = hojeIso();
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  const [campos, setCampos] = useState<Campos>(() => {
    if (existente) {
      const atuais = camposDe(existente);
      // "Marcar como realizada": muda o status e sugere a data de hoje.
      if (parametros.get("concluir") === "1" && existente.status === "agendada") {
        return { ...atuais, status: "realizada", data: atuais.data > hoje ? hoje : atuais.data };
      }
      return atuais;
    }
    const plano = planos.find((p) => String(p.id) === parametros.get("plano") && p.ativo);
    return {
      status: parametros.get("status") === "agendada" ? "agendada" : "realizada",
      descricao: plano?.nome ?? "", sistema: plano?.sistema ?? "outros",
      planoId: plano ? String(plano.id) : "", data: hoje, km: "", valor: "", oficina: "",
      garantiaAte: "", garantiaKm: "", proximaData: "", proximaKm: "", observacao: "",
    };
  });

  function mudar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  // Peças e mão de obra: uma lista só, na ordem em que foram adicionadas. A
  // posição na lista é a mesma do erro que o servidor devolve ("itens.2.valor").
  const proximaChave = useRef(existente?.itens.length ?? 0);
  const [itens, setItens] = useState<ItemNoFormulario[]>(() => (existente?.itens ?? []).map(
    (item, indice) => ({ chave: indice, tipo: item.tipo, nome: item.nome,
      valor: dinheiroParaCampo(item.valor) })));

  function adicionarItem(tipo: TipoItem) {
    setItens((atual) => [...atual, { chave: proximaChave.current++, tipo, nome: "", valor: "" }]);
  }

  function mudarItem(chave: number, campo: "nome" | "valor", valor: string) {
    setItens((atual) => atual.map((item) => (item.chave === chave ? { ...item, [campo]: valor } : item)));
  }

  function removerItem(chave: number) {
    setItens((atual) => atual.filter((item) => item.chave !== chave));
    // As posições mudam: os erros dos itens deixam de apontar para a linha certa.
    setErrosCampo((atual) => Object.fromEntries(
      Object.entries(atual).filter(([campo]) => !campo.startsWith("itens."))));
  }

  /** Só para mostrar na tela: o total que vale é o que o backend calcula. */
  function subtotal(tipo?: TipoItem): string {
    return somarDinheiro(itens
      .filter((item) => tipo === undefined || item.tipo === tipo)
      .map((item) => lerDinheiro(item.valor))
      .filter((valor): valor is string => typeof valor === "string"));
  }

  const realizada = campos.status === "realizada";
  const avulsa = campos.planoId === "";
  const planoEscolhido = planos.find((p) => String(p.id) === campos.planoId) ?? null;
  const opcoesDePlano = [
    { valor: "", rotulo: "Nenhum, manutenção avulsa" },
    ...planos
      .filter((p) => p.ativo || p.id === existente?.plano_id)
      .map((p) => ({ valor: String(p.id), rotulo: `${p.nome} (${textoIntervalo(p).toLowerCase()})` })),
  ];

  function aoEscolherPlano(valor: string) {
    const plano = planos.find((p) => String(p.id) === valor);
    setCampos((atual) => ({
      ...atual,
      planoId: valor,
      // Campo vazio é preenchido com os dados do plano; o que já foi digitado fica.
      descricao: atual.descricao.trim() || plano?.nome || "",
      sistema: plano && !atual.descricao.trim() ? plano.sistema : atual.sistema,
      proximaData: valor ? "" : atual.proximaData,
      proximaKm: valor ? "" : atual.proximaKm,
    }));
  }

  function aoMudarStatus(status: StatusManutencao) {
    setCampos((atual) => (status === "agendada"
      ? { ...atual, status, garantiaAte: "", garantiaKm: "", proximaData: "", proximaKm: "" }
      : { ...atual, status, data: atual.data > hoje ? hoje : atual.data }));
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const quilometragem = lerInteiro(campos.km);
    // Com itens, o total não vai da tela: o backend calcula a soma.
    const valor = itens.length ? null : lerDinheiro(campos.valor);
    const errosDosItens: Record<string, string | null> = {};
    itens.forEach((item, indice) => {
      const valorDoItem = lerDinheiro(item.valor);
      errosDosItens[`itens.${indice}.nome`] = erroObrigatorio(item.nome, "Informe o nome.");
      errosDosItens[`itens.${indice}.valor`] = valorDoItem === null ? "Informe o valor."
        : valorDoItem === undefined ? "Valor inválido. Exemplo: 70,00." : null;
    });
    const garantiaKm = lerInteiro(campos.garantiaKm);
    const proximaKm = lerInteiro(campos.proximaKm);
    const erros = soErros({
      descricao: erroObrigatorio(campos.descricao, "Informe a descrição."),
      data: !campos.data ? "Informe a data."
        : realizada && campos.data > hoje
          ? "Uma manutenção já feita não pode ter data no futuro. Para marcar uma data futura, escolha \"Agendar\"."
          : null,
      quilometragem: realizada && planoEscolhido?.intervalo_km != null && quilometragem === null
        ? "Informe a quilometragem: o plano conta o prazo em quilômetros." : null,
      valor: valor === undefined ? "Valor inválido. Exemplo: 280,00." : null,
      garantia_ate: campos.garantiaAte && campos.garantiaAte < campos.data
        ? "A garantia não pode terminar antes da data da manutenção." : null,
      garantia_km: garantiaKm !== null && quilometragem !== null && garantiaKm < quilometragem
        ? "Informe a quilometragem limite da garantia (o que o hodômetro vai marcar), não a distância." : null,
      proxima_data: campos.proximaData && campos.proximaData <= campos.data
        ? "A próxima data precisa ser depois da data da manutenção." : null,
      proxima_km: proximaKm !== null && quilometragem !== null && proximaKm <= quilometragem
        ? "A próxima quilometragem precisa ser maior que a da manutenção." : null,
      ...errosDosItens,
    });
    if (Object.keys(erros).length || valor === undefined) {
      setErrosCampo(erros);
      return;
    }
    const dados: DadosManutencao = {
      descricao: campos.descricao.trim(), sistema: campos.sistema, status: campos.status,
      data: campos.data, quilometragem, valor, oficina: campos.oficina.trim() || null,
      plano_id: campos.planoId ? Number(campos.planoId) : null,
      garantia_ate: realizada ? campos.garantiaAte || null : null,
      garantia_km: realizada ? garantiaKm : null,
      proxima_data: realizada && avulsa ? campos.proximaData || null : null,
      proxima_km: realizada && avulsa ? proximaKm : null,
      observacao: campos.observacao.trim() || null,
      itens: itens.map((item) => ({
        tipo: item.tipo, nome: item.nome.trim(), valor: lerDinheiro(item.valor) as string,
      })),
    };
    let destino = "";
    const deuCerto = await enviar(async () => {
      const salva = existente
        ? await editarManutencao(veiculo.id, existente.id, dados)
        : await criarManutencao(veiculo.id, dados);
      destino = `/veiculos/${veiculo.id}/manutencoes/${salva.id}`;
      await recarregarLista(); // a quilometragem do veículo pode ter mudado
    });
    if (deuCerto) {
      navegar(destino, {
        replace: true,
        state: { mensagem: existente ? "Alterações salvas." : realizada ? "Manutenção registrada." : "Manutenção agendada." },
      });
    }
  }

  const voltar = existente
    ? `/veiculos/${veiculo.id}/manutencoes/${existente.id}`
    : `/veiculos/${veiculo.id}/manutencoes`;

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={titulo} voltarPara={voltar} />
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          <GrupoOpcoes rotulo="Situação" opcoes={STATUS} valor={campos.status}
            aoMudar={aoMudarStatus} erro={errosCampo.status} />
          <CampoTexto rotulo="Descrição" value={campos.descricao} maxLength={150}
            placeholder="Ex.: Troca das bieletas dianteiras"
            onChange={(e) => mudar("descricao", e.target.value)} erro={errosCampo.descricao} />
          <CampoSelecao rotulo="Sistema" opcoes={SISTEMAS} value={campos.sistema}
            onChange={(e) => mudar("sistema", e.target.value)} erro={errosCampo.sistema} />
          <CampoSelecao rotulo="Plano de manutenção" opcoes={opcoesDePlano} value={campos.planoId}
            onChange={(e) => aoEscolherPlano(e.target.value)} erro={errosCampo.plano_id}
            dica={planoEscolhido ? "Ao salvar como feita, o prazo do plano recomeça a contar."
              : undefined} />

          <div className="dupla">
            <CampoTexto rotulo="Data" type="date" max={realizada ? hoje : undefined} value={campos.data}
              onChange={(e) => mudar("data", e.target.value)} erro={errosCampo.data} />
            <CampoTexto rotulo="Quilometragem" inputMode="numeric" value={campos.km} maxLength={9}
              placeholder="Opcional" onChange={(e) => mudar("km", mascararInteiro(e.target.value))}
              erro={errosCampo.quilometragem}
              dica={realizada ? `Atual: ${formatarKm(veiculo.quilometragem)}` : "Prevista (opcional)"} />
          </div>

          {AREAS.map((area) => (
            <section key={area.tipo} className="itens" aria-label={area.titulo}>
              <h2 className="rotulo-secao">{area.titulo}</h2>
              {itens.map((item, indice) => ({ item, indice }))
                .filter(({ item }) => item.tipo === area.tipo)
                .map(({ item, indice }, posicao) => {
                  const nomeDaLinha = `${area.rotulo} ${posicao + 1}`;
                  return (
                    <div key={item.chave} className="item-linha">
                      <CampoTexto rotulo={nomeDaLinha} value={item.nome} maxLength={150}
                        placeholder={area.exemplo} erro={errosCampo[`itens.${indice}.nome`]}
                        onChange={(e) => mudarItem(item.chave, "nome", e.target.value)} />
                      <CampoTexto rotulo={`Valor da ${nomeDaLinha.toLowerCase()}`} inputMode="decimal"
                        value={item.valor} maxLength={20} placeholder="0,00"
                        erro={errosCampo[`itens.${indice}.valor`]}
                        onChange={(e) => mudarItem(item.chave, "valor", e.target.value)} />
                      <button type="button" className="botao-pequeno botao-pequeno--perigo item-linha__remover"
                        aria-label={`Remover ${nomeDaLinha.toLowerCase()}`}
                        onClick={() => removerItem(item.chave)}>
                        Remover
                      </button>
                    </div>
                  );
                })}
              <button type="button" className="botao botao--secundario botao--adicionar"
                onClick={() => adicionarItem(area.tipo)}>
                {area.adicionar}
              </button>
            </section>
          ))}

          {itens.length > 0 ? (
            <ul className="cartao lista-status" aria-label="Resumo dos valores">
              <li className="lista-status__linha">
                <span className="texto-suave">{rotulosDosValores(realizada).pecas}</span>
                <strong className="lista-status__valor">{formatarDinheiro(subtotal("peca"))}</strong>
              </li>
              <li className="lista-status__linha">
                <span className="texto-suave">{rotulosDosValores(realizada).maoDeObra}</span>
                <strong className="lista-status__valor">{formatarDinheiro(subtotal("mao_de_obra"))}</strong>
              </li>
              <li className="lista-status__linha">
                <span>{rotulosDosValores(realizada).total}</span>
                <strong className="lista-status__valor">{formatarDinheiro(subtotal())}</strong>
              </li>
            </ul>
          ) : (
            <CampoTexto rotulo={realizada ? "Valor total (R$)" : "Valor total estimado (R$)"}
              inputMode="decimal" value={campos.valor} maxLength={20} placeholder="0,00"
              onChange={(e) => mudar("valor", e.target.value)} erro={errosCampo.valor}
              dica={realizada ? "Sem peças e mão de obra detalhadas, informe só o total."
                : "Agendada não entra nas despesas até ser realizada."} />
          )}
          <CampoTexto rotulo="Oficina" value={campos.oficina} maxLength={120}
            placeholder="Onde o serviço foi feito (opcional)"
            onChange={(e) => mudar("oficina", e.target.value)} erro={errosCampo.oficina} />

          {realizada && (
            <div className="dupla">
              <CampoTexto rotulo="Garantia até" type="date" min={campos.data} value={campos.garantiaAte}
                onChange={(e) => mudar("garantiaAte", e.target.value)} erro={errosCampo.garantia_ate} />
              <CampoTexto rotulo="Ou até (km)" inputMode="numeric" value={campos.garantiaKm}
                maxLength={9} placeholder="Opcional"
                onChange={(e) => mudar("garantiaKm", mascararInteiro(e.target.value))}
                erro={errosCampo.garantia_km} dica="O que o hodômetro vai marcar, ex.: 95.000" />
            </div>
          )}

          {realizada && avulsa && (
            <>
              <h2 className="rotulo-secao">Lembrar da próxima (opcional)</h2>
              <div className="dupla">
                <CampoTexto rotulo="Próxima em" type="date" value={campos.proximaData}
                  onChange={(e) => mudar("proximaData", e.target.value)} erro={errosCampo.proxima_data} />
                <CampoTexto rotulo="Ou aos (km)" inputMode="numeric" value={campos.proximaKm}
                  maxLength={9} placeholder="Opcional"
                  onChange={(e) => mudar("proximaKm", mascararInteiro(e.target.value))}
                  erro={errosCampo.proxima_km} />
              </div>
            </>
          )}

          <CampoArea rotulo="Observação" value={campos.observacao} maxLength={2000}
            placeholder="Peças usadas, recomendações do mecânico..."
            onChange={(e) => mudar("observacao", e.target.value)} erro={errosCampo.observacao} />

          <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">Salvar manutenção</BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
