// Aba "Combustível" das Finanças (PDF, página 11): consumo médio por
// combustível, "Etanol ou gasolina?", consumo por mês, marcações do tanque e
// a lista de abastecimentos. Todos os números vêm do backend; a tela só formata.

import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link } from "react-router";

import { ErroDaApi } from "../services/apiCliente";
import { listarAbastecimentos, listarMarcacoes, obterResumoCombustivel } from "../services/abastecimentoService";
import {
  nomeDoCombustivel,
  ROTULO_COMBUSTIVEL,
  rotuloDoNivel,
  unidade,
  type Abastecimento,
  type Comparacao,
  type MarcacaoTanque,
  type MediaConsumo,
  type ResumoCombustivel,
  type SituacaoConsumo,
} from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso, nomeDoMes } from "../utils/datas";
import { arredondarUmaCasa, formatarDecimal, formatarDinheiro, formatarKm, lerDecimal3 } from "../utils/formatos";
import CampoTexto from "./CampoTexto";
import { Carregando, ErroComNovaTentativa } from "./EstadoDaTela";
import { IconeBomba, IconeCheck, IconeSeta } from "./Icones";
import { faixaDoMarcador, NivelDoTanqueCartao, textoDoKmPorLitro } from "./PecasTanque";

const POR_PAGINA = 30;

function mensagemDe(falha: unknown, padrao: string): string {
  return falha instanceof ErroDaApi ? falha.message : padrao;
}

function primeiraMaiuscula(texto: string): string {
  return texto.charAt(0).toUpperCase() + texto.slice(1);
}

function preco(valor: string): string {
  return `R$ ${formatarDecimal(valor, 2)}`;
}

/** O que aparece à direita de cada abastecimento (ou marcação). */
function textoDoConsumo(consumo: SituacaoConsumo, combustivel: string): { texto: string; destaque: boolean } {
  switch (consumo.tipo) {
    case "consumo":
      return { texto: textoDoKmPorLitro(consumo, combustivel), destaque: true };
    case "parcial":
      return { texto: "Tanque parcial", destaque: false };
    case "primeiro_cheio":
      return { texto: "Primeiro tanque cheio", destaque: false };
    case "primeiro_nivel":
      return { texto: "Primeiro nível marcado", destaque: false };
    case "trecho_curto":
      return { texto: "Trecho curto", destaque: false };
    case "fora_do_calculo":
      return { texto: "Fora do cálculo", destaque: false };
    case "sem_tanque":
      return { texto: "Falta o tamanho do tanque", destaque: false };
    default:
      return { texto: "Sem consumo", destaque: false };
  }
}

/** "≈ 10,4" com a faixa, quando alguma ponta veio do marcador. */
function ValorDaMedia({ m }: { m: MediaConsumo }) {
  return (
    <>
      <p className="cartao-consumo__valor">
        {m.estimada && "≈ "}{formatarDecimal(m.km_por_litro, 1)} <span>{unidade(m.combustivel).consumo}</span>
      </p>
      {m.estimada && <p className="cartao-consumo__faixa">{faixaDoMarcador(m.km_por_litro_minimo, m.km_por_litro_maximo)}</p>}
    </>
  );
}

/** Tamanho do tanque que falta no cadastro e a marcação do início do mês. */
function AvisosDoTanque({ veiculo, resumo }: { veiculo: Veiculo; resumo: ResumoCombustivel }) {
  if (!veiculo.ativo) return null;
  return (
    <>
      {resumo.tanque_pendente && (
        <section className="cartao" aria-label="Tamanho do tanque">
          <p className="cartao__titulo">Falta o tamanho do tanque</p>
          <p className="texto-suave">
            Com ele, o app confere se os litros cabem no tanque e calcula o consumo pelo nível do marcador.
          </p>
          <Link to={`/veiculos/${veiculo.id}/editar`} className="botao botao--secundario">Informar o tamanho do tanque</Link>
        </section>
      )}
      {resumo.marcacao_do_mes_pendente && (
        <section className="cartao" aria-label="Marcação do mês">
          <p className="cartao__titulo">Marque o km e o nível do tanque deste mês</p>
          <p className="texto-suave">
            Uma vez no início do mês: com ela, o consumo do mês fecha certinho, mesmo sem encher o tanque.
          </p>
          <Link to={`/veiculos/${veiculo.id}/tanque/marcacoes/nova`} className="botao botao--secundario">
            Marcar km e nível
          </Link>
        </section>
      )}
    </>
  );
}

function Medias({ resumo }: { resumo: ResumoCombustivel }) {
  if (resumo.medias.length === 0) {
    return (
      <section className="cartao-consumo" aria-label="Consumo médio">
        <p className="cartao-consumo__vazio">Ainda não há consumo calculado.</p>
        <p className="cartao-consumo__nota">
          O consumo aparece depois de dois abastecimentos de tanque cheio (ou duas cargas completas)
          do mesmo combustível, ou entre dois registros com o nível do marcador.
        </p>
      </section>
    );
  }
  return (
    <section className="cartao-consumo" aria-label="Consumo médio">
      <div className="cartao-consumo__medias">
        {resumo.medias.map((m) => (
          <div key={m.combustivel} className="cartao-consumo__media">
            <p className="cartao-consumo__rotulo">{ROTULO_COMBUSTIVEL[m.combustivel]}</p>
            <ValorDaMedia m={m} />
          </div>
        ))}
      </div>
      <p className="cartao-consumo__nota">
        {resumo.medias.some((m) => m.estimada)
          ? "Média entre tanques cheios e níveis do marcador. O tanque cheio é exato; o marcador tem margem, "
            + "que fica menor quanto mais quilômetros você registra."
          : "Média calculada entre abastecimentos de tanque cheio."}
      </p>
    </section>
  );
}

/** "Consumo por mês": cada trecho conta no mês em que começou. */
function ConsumoPorMes({ resumo }: { resumo: ResumoCombustivel }) {
  if (resumo.meses.length === 0) return null;
  const varios = new Set(resumo.meses.map((m) => m.combustivel)).size > 1;
  return (
    <section aria-label="Consumo por mês">
      <h2 className="rotulo-secao">Consumo por mês</h2>
      <ul className="cartao lista-simples">
        {resumo.meses.map((m) => (
          <li key={`${m.ano}-${m.mes}-${m.combustivel}`} className="lista-simples__item consumo-mes">
            <span className="lista-simples__texto">
              <span className="lista-simples__titulo">
                {nomeDoMes({ ano: m.ano, mes: m.mes })}{varios ? `, ${ROTULO_COMBUSTIVEL[m.combustivel].toLowerCase()}` : ""}
              </span>
              <span className="texto-suave">
                {formatarKm(m.distancia)} com {formatarDecimal(arredondarUmaCasa(m.quantidade))} {unidade(m.combustivel).curta}
              </span>
            </span>
            <span className="consumo-mes__valor">
              <strong className="consumo-destaque">
                {m.estimada && "≈ "}{formatarDecimal(m.km_por_litro, 1)} {unidade(m.combustivel).consumo}
              </strong>
              {m.estimada && m.km_por_litro_minimo && m.km_por_litro_maximo && (
                <span className="texto-suave">
                  {" "}{formatarDecimal(m.km_por_litro_minimo, 1)} a {formatarDecimal(m.km_por_litro_maximo, 1)}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

/** Marcações do tanque (km e nível sem abastecer), da mais recente para a mais antiga. */
function ListaDeMarcacoes({ veiculo, resumo }: { veiculo: Veiculo; resumo: ResumoCombustivel }) {
  const [itens, setItens] = useState<MarcacaoTanque[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarMarcacoes(veiculo.id, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setTotal(r.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar as marcações do tanque."));
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return null;
  const podeMarcar = veiculo.ativo && resumo.capacidade_tanque !== null;
  if (total === 0 && (!podeMarcar || resumo.marcacao_do_mes_pendente)) return null;
  return (
    <section aria-label="Marcações do tanque">
      <h2 className="rotulo-secao">Marcações do tanque</h2>
      {total > 0 && (
        <ul className="cartao lista-simples">
          {itens.map((m) => {
            const consumo = textoDoConsumo(m.consumo, "gasolina");
            return (
              <li key={m.id}>
                <Link to={`/veiculos/${veiculo.id}/tanque/marcacoes/${m.id}`} className="lista-simples__item">
                  <span className="lista-simples__texto">
                    <span className="lista-simples__titulo">Marcador em {rotuloDoNivel(m.nivel)}</span>
                    <span className="texto-suave">{formatarDataIso(m.data)}, {formatarKm(m.quilometragem)}</span>
                  </span>
                  <span className={consumo.destaque ? "consumo-destaque" : "texto-suave"}>{consumo.texto}</span>
                  <IconeSeta tamanho={20} />
                </Link>
              </li>
            );
          })}
        </ul>
      )}
      {itens.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
      {podeMarcar && !resumo.marcacao_do_mes_pendente && (
        <Link to={`/veiculos/${veiculo.id}/tanque/marcacoes/nova`} className="botao botao--secundario botao--espaco">
          Marcar km e nível
        </Link>
      )}
    </section>
  );
}

const TITULO_DA_RECOMENDACAO = {
  etanol: "Hoje, o etanol compensa",
  gasolina: "Hoje, a gasolina compensa",
  tanto_faz: "Hoje, tanto faz",
};

function CartaoComparacao({ comparacao: c, aoSimular, simulando, erroSimulacao }: {
  comparacao: Comparacao;
  aoSimular: (precos: { gasolina: string; etanol: string } | null) => void;
  simulando: boolean;
  erroSimulacao: string | null;
}) {
  const [aberto, setAberto] = useState(false);
  const [gasolina, setGasolina] = useState("");
  const [etanol, setEtanol] = useState("");
  const [erros, setErros] = useState<Record<string, string>>({});

  function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const g = lerDecimal3(gasolina);
    const e = lerDecimal3(etanol);
    const novos: Record<string, string> = {};
    if (typeof g !== "string") novos.gasolina = g === null ? "Informe o preço da gasolina." : "Preço inválido. Exemplo: 6,29.";
    if (typeof e !== "string") novos.etanol = e === null ? "Informe o preço do etanol." : "Preço inválido. Exemplo: 4,39.";
    setErros(novos);
    if (typeof g === "string" && typeof e === "string") aoSimular({ gasolina: g, etanol: e });
  }

  return (
    <section className="cartao comparacao" aria-label="Etanol ou gasolina?">
      <p className="texto-suave comparacao__pergunta">Etanol ou gasolina?</p>
      {c.recomendacao ? (
        <>
          <p className="comparacao__titulo">
            <IconeCheck tamanho={22} /> {TITULO_DA_RECOMENDACAO[c.recomendacao]}
          </p>
          <p className="comparacao__texto">
            Com o seu consumo, o etanol vale a pena até {c.limite_percentual}% do preço da gasolina.{" "}
            {c.precos_simulados
              ? `Com os preços informados, ele custa ${c.relacao_percentual}%.`
              : `No último abastecimento, ele custou ${c.relacao_percentual}%.`}
          </p>
          <div className="comparacao__barra" aria-hidden="true"
            style={{ "--limite": `${Math.min(100, c.limite_percentual!)}%` } as CSSProperties}>
            <span className="comparacao__marca" style={{ left: `${Math.min(100, Math.max(0, c.relacao_percentual!))}%` }}>
              {c.relacao_percentual}%
            </span>
          </div>
          <p className="comparacao__legenda">
            <span>Etanol compensa</span>
            <strong>{c.limite_percentual}%</strong>
            <span>Gasolina compensa</span>
          </p>
          <p className="texto-suave comparacao__precos">
            Gasolina {preco(c.preco_gasolina!)} · Etanol {preco(c.preco_etanol!)}
            {c.precos_simulados ? " (simulação, nada foi gravado)" : " (últimos preços pagos)"}
          </p>
        </>
      ) : (
        <p className="comparacao__texto">
          {c.motivo}
          {c.limite_percentual !== null && ` Com o seu consumo, o etanol vale a pena até ${c.limite_percentual}% do preço da gasolina.`}
        </p>
      )}

      {c.limite_percentual !== null && (aberto ? (
        <form className="comparacao__simular" onSubmit={aoEnviar} noValidate aria-label="Simular com os preços de hoje">
          <div className="dupla">
            <CampoTexto rotulo="Gasolina hoje (R$)" inputMode="decimal" value={gasolina} placeholder="6,29"
              onChange={(e) => setGasolina(e.target.value)} erro={erros.gasolina} />
            <CampoTexto rotulo="Etanol hoje (R$)" inputMode="decimal" value={etanol} placeholder="4,39"
              onChange={(e) => setEtanol(e.target.value)} erro={erros.etanol} />
          </div>
          {erroSimulacao && <p className="campo__erro" role="alert">{erroSimulacao}</p>}
          <div className="dupla dupla--botoes">
            <button type="button" className="botao botao--secundario" onClick={() => {
              setAberto(false);
              aoSimular(null);
            }}>
              Usar o último preço
            </button>
            <button type="submit" className="botao botao--primario" disabled={simulando}>
              {simulando ? "Comparando…" : "Comparar"}
            </button>
          </div>
        </form>
      ) : (
        <button type="button" className="botao-link comparacao__abrir" onClick={() => setAberto(true)}>
          Simular com os preços de hoje
        </button>
      ))}
    </section>
  );
}

function ListaDeAbastecimentos({ veiculo }: { veiculo: Veiculo }) {
  const [itens, setItens] = useState<Abastecimento[]>([]);
  const [total, setTotal] = useState<number | null>(null);
  const [pagina, setPagina] = useState(0);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregando(true);
    try {
      const r = await listarAbastecimentos(veiculo.id, numero, POR_PAGINA);
      setItens((atuais) => (numero === 1 ? r.itens : [...atuais, ...r.itens]));
      setTotal(r.total);
      setPagina(numero);
      setErro(null);
    } catch (falha) {
      setErro(mensagemDe(falha, "Não foi possível carregar os abastecimentos."));
    } finally {
      setCarregando(false);
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar(1);
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar(Math.max(1, pagina))} />;
  if (total === null) return <Carregando />;
  if (total === 0) {
    return (
      <section className="cartao">
        <p className="cartao__titulo">Nenhum abastecimento</p>
        <p className="texto-suave">Registre os abastecimentos e recargas pelo botão +. Marque "Tanque cheio" (ou "Carga completa") quando completar: é assim que o consumo é calculado.</p>
      </section>
    );
  }
  return (
    <section aria-label="Abastecimentos">
      <h2 className="rotulo-secao">Abastecimentos</h2>
      <ul className="cartao lista-simples">
        {itens.map((a) => {
          const consumo = textoDoConsumo(a.consumo, a.combustivel);
          const u = unidade(a.combustivel);
          return (
            <li key={a.id}>
              <Link to={`/veiculos/${veiculo.id}/abastecimentos/${a.id}`} className="lista-simples__item">
                <span className="pendencia__icone pendencia__icone--aviso"><IconeBomba /></span>
                <span className="lista-simples__texto">
                  <span className="lista-simples__titulo">
                    {a.posto
                      ? `${a.posto}, ${nomeDoCombustivel(a.combustivel, a.tipo)}`
                      : primeiraMaiuscula(nomeDoCombustivel(a.combustivel, a.tipo))}
                  </span>
                  <span className="texto-suave">
                    {formatarDataIso(a.data)}, {formatarDecimal(a.litros)} {u.curta} a {preco(a.valor_litro)}
                  </span>
                </span>
                <span className="conta__valor">
                  <strong>{formatarDinheiro(a.valor_total)}</strong>
                  <span className={consumo.destaque ? "consumo-destaque" : "texto-suave"}>{consumo.texto}</span>
                </span>
              </Link>
            </li>
          );
        })}
      </ul>
      {itens.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregando}
          onClick={() => void carregar(pagina + 1)}>
          {carregando ? "Carregando…" : `Carregar mais (${total - itens.length} restantes)`}
        </button>
      )}
    </section>
  );
}

export default function AbaCombustivel({ veiculo }: { veiculo: Veiculo }) {
  const [resumo, setResumo] = useState<ResumoCombustivel | null>(null);
  const [erro, setErro] = useState<string | null>(null);
  const [simulando, setSimulando] = useState(false);
  const [erroSimulacao, setErroSimulacao] = useState<string | null>(null);

  const carregar = useCallback(async (simulacao?: { gasolina: string; etanol: string }) => {
    setSimulando(Boolean(simulacao));
    try {
      setResumo(await obterResumoCombustivel(veiculo.id, simulacao));
      setErro(null);
      setErroSimulacao(null);
    } catch (falha) {
      if (simulacao) setErroSimulacao(mensagemDe(falha, "Não foi possível comparar."));
      else setErro(mensagemDe(falha, "Não foi possível carregar o consumo."));
    } finally {
      setSimulando(false);
    }
  }, [veiculo.id]);

  useEffect(() => {
    void carregar();
  }, [carregar]);

  if (erro) return <ErroComNovaTentativa mensagem={erro} aoTentar={() => void carregar()} />;
  if (!resumo) return <Carregando />;
  return (
    <>
      <AvisosDoTanque veiculo={veiculo} resumo={resumo} />
      {veiculo.tipo_combustivel !== "eletrico" && (
        <NivelDoTanqueCartao veiculoId={veiculo.id} nivel={resumo.nivel_tanque} podeAtualizar={veiculo.ativo} />
      )}
      <Medias resumo={resumo} />
      {resumo.comparacao && (
        <CartaoComparacao comparacao={resumo.comparacao} simulando={simulando} erroSimulacao={erroSimulacao}
          aoSimular={(precos) => void carregar(precos ?? undefined)} />
      )}
      <ConsumoPorMes resumo={resumo} />
      <ListaDeMarcacoes veiculo={veiculo} resumo={resumo} />
      <ListaDeAbastecimentos veiculo={veiculo} />
    </>
  );
}
