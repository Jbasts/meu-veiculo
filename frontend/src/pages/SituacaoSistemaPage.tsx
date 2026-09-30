import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";

import CabecalhoMarca from "../components/CabecalhoMarca";
import SeloStatus, { type TomStatus } from "../components/SeloStatus";
import { consultarSaude } from "../services/saudeService";
import type { ResultadoSaude } from "../types/saude";
import { formatarDataIso } from "../utils/datas";

interface Linha {
  rotulo: string;
  valor: string;
  tom: TomStatus;
}

function montarLinhas(resultado: ResultadoSaude): Linha[] {
  if (resultado.tipo === "api_fora") {
    return [
      { rotulo: "API (backend)", valor: "Sem resposta", tom: "alerta" },
      { rotulo: "Banco de dados", valor: "Não verificado", tom: "neutro" },
    ];
  }
  const { saude } = resultado;
  const linhas: Linha[] = [{ rotulo: "API (backend)", valor: "No ar", tom: "ok" }];
  if (saude.banco !== "ok") {
    linhas.push({ rotulo: "Banco de dados", valor: "Indisponível", tom: "alerta" });
    return linhas;
  }
  linhas.push({ rotulo: "Banco de dados", valor: "Conectado", tom: "ok" });
  if (saude.situacao_banco === "sem_controle") {
    linhas.push({ rotulo: "Migrations", valor: "Banco sem registro", tom: "aviso" });
  } else if (saude.migracoes_pendentes.length > 0) {
    linhas.push({
      rotulo: "Migrations",
      valor: `Pendente: ${saude.migracoes_pendentes.join(", ")}`,
      tom: "aviso",
    });
  } else {
    linhas.push({
      rotulo: "Migrations",
      valor: `Em dia (versão ${saude.versao_migracao ?? "?"})`,
      tom: "ok",
    });
  }
  linhas.push({ rotulo: "Fuso horário", valor: saude.fuso_horario, tom: "neutro" });
  if (saude.data_hoje) {
    linhas.push({
      rotulo: "Data de hoje no banco",
      valor: formatarDataIso(saude.data_hoje),
      tom: "neutro",
    });
  }
  return linhas;
}

export default function SituacaoSistemaPage() {
  const [resultado, setResultado] = useState<ResultadoSaude | null>(null);
  const [carregando, setCarregando] = useState(true);
  const montado = useRef(true);

  const verificar = useCallback(async () => {
    setCarregando(true);
    const novo = await consultarSaude();
    if (montado.current) {
      setResultado(novo);
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    montado.current = true;
    void verificar();
    return () => {
      montado.current = false;
    };
  }, [verificar]);

  const tudoCerto =
    resultado?.tipo === "resposta" &&
    resultado.saude.banco === "ok" &&
    resultado.saude.situacao_banco === "controlado" &&
    resultado.saude.migracoes_pendentes.length === 0;

  return (
    <div className="pagina">
      <CabecalhoMarca />

      <main className="conteudo">
        <h2 className="titulo-secao">Situação do sistema</h2>

        <section className="cartao" aria-live="polite" aria-busy={carregando}>
          {resultado === null ? (
            <p className="texto-suave">Verificando a API e o banco de dados…</p>
          ) : (
            <>
              <ul className="lista-status">
                {montarLinhas(resultado).map((linha) => (
                  <li key={linha.rotulo} className="lista-status__linha">
                    <span className="lista-status__rotulo">{linha.rotulo}</span>
                    <SeloStatus tom={linha.tom}>{linha.valor}</SeloStatus>
                  </li>
                ))}
              </ul>
              <p className={`aviso ${tudoCerto ? "aviso--ok" : "aviso--atencao"}`} role="status">
                {resultado.tipo === "resposta" ? resultado.saude.mensagem : resultado.detalhe}
              </p>
              {resultado.tipo === "api_fora" && (
                <p className="texto-suave">
                  Confira se o backend está rodando: na pasta <code>backend</code>, rode{" "}
                  <code>.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload</code>.
                </p>
              )}
            </>
          )}
        </section>

        <button
          type="button"
          className="botao botao--primario"
          onClick={() => void verificar()}
          disabled={carregando}
        >
          {carregando ? "Verificando…" : "Verificar novamente"}
        </button>

        <p className="rodape-link">
          <Link to="/" className="link">
            Ir para o início
          </Link>
        </p>
      </main>
    </div>
  );
}
