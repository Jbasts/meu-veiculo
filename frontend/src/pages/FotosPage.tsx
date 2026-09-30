import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeMaisSinal } from "../components/Icones";
import { FotoProtegida } from "../components/PecasVeiculo";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarFotos } from "../services/fotoService";
import type { Foto } from "../types/veiculo";
import { formatarDataIso, formatarMesAnoLongo } from "../utils/datas";

const POR_PAGINA = 30;

/** Agrupa por mês, mantendo a ordem recebida (mais recente primeiro). */
function porMes(fotos: Foto[]): { mes: string; fotos: Foto[] }[] {
  const grupos: { mes: string; fotos: Foto[] }[] = [];
  for (const foto of fotos) {
    const mes = formatarMesAnoLongo(foto.data_foto);
    const ultimo = grupos[grupos.length - 1];
    if (ultimo?.mes === mes) ultimo.fotos.push(foto);
    else grupos.push({ mes, fotos: [foto] });
  }
  return grupos;
}

// Galeria do veículo (PDF, página 20). Os filtros por projeto, diagnóstico e
// manutenção aparecem quando esses vínculos existirem (etapas 4, 5 e 8).
export default function FotosPage() {
  const { id, veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const [fotos, setFotos] = useState<Foto[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(0);
  const [carregandoFotos, setCarregandoFotos] = useState(true);
  const [erroFotos, setErroFotos] = useState<string | null>(null);

  const carregar = useCallback(async (numero: number) => {
    setCarregandoFotos(true);
    try {
      const resultado = await listarFotos(id, numero, POR_PAGINA);
      setFotos((atuais) => (numero === 1 ? resultado.itens : [...atuais, ...resultado.itens]));
      setTotal(resultado.total);
      setPagina(numero);
      setErroFotos(null);
    } catch (falha) {
      setErroFotos(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar as fotos.");
    } finally {
      setCarregandoFotos(false);
    }
  }, [id]);

  useEffect(() => {
    if (veiculo?.id) void carregar(1);
  }, [veiculo?.id, carregar]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Fotos" voltarPara="/veiculos" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }

  const base = `/veiculos/${veiculo.id}`;
  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo={`Fotos do ${veiculo.modelo}`} voltarPara={base} acao={
        veiculo.ativo ? (
          <Link to={`${base}/fotos/nova`} className="botao-redondo" aria-label="Adicionar foto">
            <IconeMaisSinal />
          </Link>
        ) : null
      } />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {erroFotos && (
        <ErroComNovaTentativa mensagem={erroFotos} aoTentar={() => void carregar(Math.max(1, pagina))} />
      )}
      {carregandoFotos && fotos.length === 0 && <Carregando texto="Carregando fotos…" />}

      {!carregandoFotos && !erroFotos && total === 0 && (
        <section className="cartao">
          <p className="cartao__titulo">Nenhuma foto ainda</p>
          <p className="texto-suave">
            {veiculo.ativo
              ? "Toque no + para tirar uma foto ou escolher uma da galeria do aparelho."
              : "Este veículo está inativo e não tem fotos."}
          </p>
        </section>
      )}

      {total > 0 && <p className="texto-suave">{total === 1 ? "1 foto" : `${total} fotos`}</p>}
      {porMes(fotos).map((grupo) => (
        <section key={grupo.mes}>
          <h2 className="titulo-secao">{grupo.mes}</h2>
          <div className="grade-fotos">
            {grupo.fotos.map((foto) => (
              <Link key={foto.id} to={`${base}/fotos/${foto.id}`} className="grade-fotos__item">
                <FotoProtegida veiculoId={veiculo.id} fotoId={foto.id}
                  descricao={foto.legenda ?? `Foto de ${formatarDataIso(foto.data_foto)}`} />
                {foto.principal && <span className="etiqueta-foto">Capa</span>}
              </Link>
            ))}
          </div>
        </section>
      ))}

      {fotos.length < total && (
        <button type="button" className="botao botao--secundario" disabled={carregandoFotos}
          onClick={() => void carregar(pagina + 1)}>
          {carregandoFotos ? "Carregando…" : "Carregar mais fotos"}
        </button>
      )}
    </main>
  );
}
