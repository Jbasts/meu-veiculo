// Aba "Combustível" das Finanças (PDF, página 11): consumo médio por
// combustível, "Etanol ou gasolina?" e a lista de abastecimentos.
// Todos os números vêm do backend; a tela só formata.

import { useCallback, useEffect, useState, type CSSProperties, type FormEvent } from "react";
import { Link } from "react-router";

import { ErroDaApi } from "../services/apiCliente";
import { listarAbastecimentos, obterResumoCombustivel } from "../services/abastecimentoService";
import {
  nomeDoCombustivel,
  ROTULO_COMBUSTIVEL,
  unidade,
  type Abastecimento,
  type Comparacao,
  type ResumoCombustivel,
} from "../types/abastecimento";
import type { Veiculo } from "../types/veiculo";
import { formatarDataIso } from "../utils/datas";
import { formatarDecimal, formatarDinheiro, lerDecimal3 } from "../utils/formatos";
import CampoTexto from "./CampoTexto";
import { Carregando, ErroComNovaTentativa } from "./EstadoDaTela";
import { IconeBomba, IconeCheck } from "./Icones";

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

/** O que aparece à direita de cada abastecimento. */
function textoDoConsumo(a: Abastecimento): { texto: string; destaque: boolean } {
  switch (a.consumo.tipo) {
    case "consumo":
      return { texto: `${formatarDecimal(a.consumo.km_por_litro!, 1)} ${unidade(a.combustivel).consumo}`, destaque: true };
    case "parcial":
      return { texto: "Tanque parcial", destaque: false };
    case "primeiro_cheio":
      return { texto: "Primeiro tanque cheio", destaque: false };
    case "fora_do_calculo":
      return { texto: "Fora do cálculo", destaque: false };
    default:
      return { texto: "Sem consumo", destaque: false };
  }
}

function Medias({ resumo }: { resumo: ResumoCombustivel }) {
  if (resumo.medias.length === 0) {
    return (
      <section className="cartao-consumo" aria-label="Consumo médio">
        <p className="cartao-consumo__vazio">Ainda não há consumo calculado.</p>
        <p className="cartao-consumo__nota">
          O consumo aparece depois de dois abastecimentos de tanque cheio (ou duas cargas completas)
          do mesmo combustível.
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
            <p className="cartao-consumo__valor">
              {formatarDecimal(m.km_por_litro, 1)} <span>{unidade(m.combustivel).consumo}</span>
            </p>
          </div>
        ))}
      </div>
      <p className="cartao-consumo__nota">Média calculada entre abastecimentos de tanque cheio.</p>
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
          const consumo = textoDoConsumo(a);
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
      <Medias resumo={resumo} />
      {resumo.comparacao && (
        <CartaoComparacao comparacao={resumo.comparacao} simulando={simulando} erroSimulacao={erroSimulacao}
          aoSimular={(precos) => void carregar(precos ?? undefined)} />
      )}
      <ListaDeAbastecimentos veiculo={veiculo} />
    </>
  );
}
