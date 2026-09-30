import { useEffect, useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate, useSearchParams } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { CampoSelecao, Chave, GrupoOpcoes } from "../components/Formulario";
import { IconeCamera, IconeImagem } from "../components/Icones";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { usePreviaDeArquivo } from "../hooks/usePreviaDeArquivo";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { enviarFoto, erroDoArquivo } from "../services/fotoService";
import { listarManutencoes } from "../services/manutencaoService";
import type { Manutencao } from "../types/manutencao";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarTamanho } from "../utils/formatos";

const TIPOS_ACEITOS = "image/jpeg,image/png,image/webp,image/heic,image/heif";
// Diagnóstico e projeto entram como opções nas etapas 5 e 8.
const VINCULOS: { valor: "nenhum" | "manutencao"; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "manutencao", rotulo: "Manutenção" },
];

// "Nova foto" (PDF, página 21), com "Ligar a um registro" para manutenção.
export default function FotoNovaPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { recarregar: recarregarLista } = useVeiculos();
  const [parametros] = useSearchParams();
  const navegar = useNavigate();
  const hoje = hojeIso();
  const [arquivo, setArquivo] = useState<File | null>(null);
  const previa = usePreviaDeArquivo(arquivo);
  const [previaFalhou, setPreviaFalhou] = useState(false);
  const [legenda, setLegenda] = useState("");
  const [data, setData] = useState(hoje);
  const [comoCapa, setComoCapa] = useState(parametros.get("capa") === "1");
  // ?manutencao=ID: a tela foi aberta a partir de uma manutenção.
  const manutencaoInicial = parametros.get("manutencao") ?? "";
  const [ligar, setLigar] = useState<"nenhum" | "manutencao">(manutencaoInicial ? "manutencao" : "nenhum");
  const [manutencaoId, setManutencaoId] = useState(manutencaoInicial);
  const [manutencoes, setManutencoes] = useState<Manutencao[] | null>(null);
  const [erroManutencoes, setErroManutencoes] = useState<string | null>(null);
  const entradaCamera = useRef<HTMLInputElement>(null);
  const entradaGaleria = useRef<HTMLInputElement>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  useEffect(() => setPreviaFalhou(false), [arquivo]);

  // A lista de manutenções só é buscada quando a pessoa escolhe ligar a foto a uma.
  const idVeiculo = veiculo?.id;
  useEffect(() => {
    if (ligar !== "manutencao" || !idVeiculo || manutencoes !== null) return;
    let cancelado = false;
    listarManutencoes(idVeiculo, { porPagina: 100 })
      .then((pagina) => {
        if (!cancelado) setManutencoes(pagina.itens);
      })
      .catch((falha) => {
        if (!cancelado) {
          setErroManutencoes(falha instanceof ErroDaApi ? falha.message
            : "Não foi possível carregar as manutenções.");
        }
      });
    return () => {
      cancelado = true;
    };
  }, [ligar, idVeiculo, manutencoes]);

  if (carregando) {
    return <div className="pagina"><main className="conteudo conteudo--topo"><Carregando /></main></div>;
  }
  if (erro || !veiculo) {
    return (
      <div className="pagina">
        <main className="conteudo conteudo--topo">
          <TopoComVoltar titulo="Nova foto" voltarPara="/veiculos" />
          <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
            aoTentar={() => void recarregar()} />
        </main>
      </div>
    );
  }
  const base = `/veiculos/${veiculo.id}`;

  function aoEscolher(evento: ChangeEvent<HTMLInputElement>) {
    const escolhido = evento.target.files?.[0] ?? null;
    evento.target.value = ""; // permite escolher o mesmo arquivo de novo
    if (!escolhido) return;
    const problema = erroDoArquivo(escolhido);
    setErrosCampo(problema ? { arquivo: problema } : {});
    setArquivo(problema ? null : escolhido);
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const erros: Record<string, string> = {};
    const problema = erroDoArquivo(arquivo);
    if (problema) erros.arquivo = problema;
    if (!data) erros.data_foto = "Informe a data da foto.";
    else if (data > hoje) erros.data_foto = "A data da foto não pode ser no futuro.";
    if (ligar === "manutencao" && !manutencaoId) erros.manutencao_id = "Escolha a manutenção.";
    if (Object.keys(erros).length || !arquivo) {
      setErrosCampo(erros);
      return;
    }
    const deuCerto = await enviar(async () => {
      await enviarFoto(veiculo!.id, {
        arquivo, legenda, dataFoto: data, principal: comoCapa,
        manutencaoId: ligar === "manutencao" ? Number(manutencaoId) : null,
      });
      if (comoCapa) await recarregarLista();
    });
    if (deuCerto) {
      navegar(manutencaoInicial ? `${base}/manutencoes/${manutencaoInicial}` : comoCapa ? base : `${base}/fotos`, {
        replace: true,
        state: { mensagem: comoCapa ? "Foto de capa atualizada." : "Foto adicionada." },
      });
    }
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Nova foto" voltarPara={manutencaoInicial
          ? `${base}/manutencoes/${manutencaoInicial}` : comoCapa ? base : `${base}/fotos`} />
        {!veiculo.ativo && (
          <Alerta tipo="erro">Este veículo está inativo e não aceita fotos novas.</Alerta>
        )}
        {erroGeral && !errosCampo.arquivo && <Alerta tipo="erro">{erroGeral}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          {/* Dois campos de arquivo: um abre a câmera do celular, o outro a galeria. */}
          <input ref={entradaCamera} type="file" className="oculto" accept="image/*"
            capture="environment" aria-label="Tirar foto com a câmera" onChange={aoEscolher} />
          <input ref={entradaGaleria} type="file" className="oculto" accept={TIPOS_ACEITOS}
            aria-label="Escolher foto da galeria" onChange={aoEscolher} />

          <div className={`previa-foto${arquivo ? "" : " previa-foto--vazia"}`}>
            {arquivo && previa && !previaFalhou ? (
              <img src={previa} alt="Foto escolhida" onError={() => setPreviaFalhou(true)} />
            ) : (
              <>
                <IconeImagem tamanho={36} />
                <span>
                  {!arquivo ? "Nenhuma foto escolhida"
                    : "Foto escolhida (pré-visualização indisponível para este formato)"}
                </span>
              </>
            )}
          </div>
          {arquivo && (
            <p className="texto-suave previa-foto__nome">
              {arquivo.name} · {formatarTamanho(arquivo.size)}
            </p>
          )}
          {errosCampo.arquivo && <p className="campo__erro" role="alert">{errosCampo.arquivo}</p>}

          <div className="dupla dupla--botoes">
            <button type="button" className="botao botao--secundario"
              onClick={() => entradaCamera.current?.click()}>
              <IconeCamera tamanho={20} /> {arquivo ? "Tirar outra" : "Tirar foto"}
            </button>
            <button type="button" className="botao botao--secundario"
              onClick={() => entradaGaleria.current?.click()}>
              <IconeImagem tamanho={20} /> Da galeria
            </button>
          </div>
          <p className="texto-suave secao__dica">
            JPEG, PNG, WebP ou HEIC, até 10 MB. A localização gravada pela câmera é removida.
          </p>

          <CampoTexto rotulo="Legenda" value={legenda} maxLength={150} placeholder="Opcional"
            onChange={(e) => setLegenda(e.target.value)} erro={errosCampo.legenda} />
          <CampoTexto rotulo="Data da foto" type="date" max={hoje} value={data}
            onChange={(e) => setData(e.target.value)} erro={errosCampo.data_foto}
            dica={data === hoje ? "Hoje. Toque para alterar." : undefined} />

          <GrupoOpcoes rotulo="Ligar a um registro" opcoes={VINCULOS} valor={ligar}
            aoMudar={setLigar} />
          {ligar === "manutencao" && (
            erroManutencoes ? <Alerta tipo="erro">{erroManutencoes}</Alerta>
              : manutencoes === null ? <Carregando texto="Carregando manutenções…" />
                : manutencoes.length === 0
                  ? <p className="campo__dica">Este veículo ainda não tem manutenções registradas.</p>
                  : (
                    <CampoSelecao rotulo="Manutenção" value={manutencaoId}
                      onChange={(e) => setManutencaoId(e.target.value)} erro={errosCampo.manutencao_id}
                      opcoes={[
                        { valor: "", rotulo: "Escolha…" },
                        ...manutencoes.map((m) => ({
                          valor: String(m.id), rotulo: `${m.descricao} (${formatarDataIso(m.data)})`,
                        })),
                      ]} />
                  )
          )}

          <Chave titulo="Usar como capa" ligada={comoCapa} aoMudar={setComoCapa}
            descricao="Substitui a foto de capa atual do veículo." />

          <BotaoEnviar enviando={enviando} textoEnviando="Enviando foto…">Salvar foto</BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
