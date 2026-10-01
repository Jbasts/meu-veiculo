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
import { listarDiagnosticos } from "../services/diagnosticoService";
import { enviarFoto, erroDoArquivo } from "../services/fotoService";
import { listarManutencoes } from "../services/manutencaoService";
import { formatarDataIso, hojeIso } from "../utils/datas";
import { formatarTamanho } from "../utils/formatos";

const TIPOS_ACEITOS = "image/jpeg,image/png,image/webp,image/heic,image/heif";
type Vinculo = "nenhum" | "diagnostico" | "manutencao";
// Projeto entra como opção na etapa 8.
const VINCULOS: { valor: Vinculo; rotulo: string }[] = [
  { valor: "nenhum", rotulo: "Nenhum" },
  { valor: "diagnostico", rotulo: "Diagnóstico" },
  { valor: "manutencao", rotulo: "Manutenção" },
];
const TEXTOS_DO_VINCULO = {
  diagnostico: { rotulo: "Diagnóstico", carregando: "Carregando diagnósticos…",
    vazio: "Este veículo ainda não tem diagnósticos registrados.", escolha: "Escolha o diagnóstico.",
    erro: "Não foi possível carregar os diagnósticos.", campo: "diagnostico_id", caminho: "diagnosticos" },
  manutencao: { rotulo: "Manutenção", carregando: "Carregando manutenções…",
    vazio: "Este veículo ainda não tem manutenções registradas.", escolha: "Escolha a manutenção.",
    erro: "Não foi possível carregar as manutenções.", campo: "manutencao_id", caminho: "manutencoes" },
} as const;

interface Registro {
  id: number;
  rotulo: string;
}

// "Nova foto" (PDF, página 21), com "Ligar a um registro" (diagnóstico ou manutenção).
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
  // ?manutencao=ID ou ?diagnostico=ID: a tela foi aberta a partir desse registro.
  const origem: Vinculo = parametros.get("diagnostico") ? "diagnostico"
    : parametros.get("manutencao") ? "manutencao" : "nenhum";
  const idDeOrigem = origem === "nenhum" ? "" : parametros.get(origem) ?? "";
  const [ligar, setLigar] = useState<Vinculo>(origem);
  const [registroId, setRegistroId] = useState(idDeOrigem);
  const [registros, setRegistros] = useState<Partial<Record<Vinculo, Registro[]>>>({});
  const [erroRegistros, setErroRegistros] = useState<string | null>(null);
  const entradaCamera = useRef<HTMLInputElement>(null);
  const entradaGaleria = useRef<HTMLInputElement>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();

  useEffect(() => setPreviaFalhou(false), [arquivo]);

  // A lista de registros só é buscada quando a pessoa escolhe ligar a foto a um.
  const idVeiculo = veiculo?.id;
  const jaCarregados = ligar === "nenhum" ? undefined : registros[ligar];
  useEffect(() => {
    if (ligar === "nenhum" || !idVeiculo || jaCarregados !== undefined) return;
    let cancelado = false;
    const busca: Promise<Registro[]> = ligar === "manutencao"
      ? listarManutencoes(idVeiculo, { porPagina: 100 }).then((pagina) => pagina.itens.map((m) => ({
        id: m.id, rotulo: `${m.descricao} (${formatarDataIso(m.data)})` })))
      : listarDiagnosticos(idVeiculo, "todos", 1, 100).then((pagina) => pagina.itens.map((d) => ({
        id: d.id, rotulo: `${d.titulo} (${formatarDataIso(d.data_identificacao)})` })));
    setErroRegistros(null);
    busca
      .then((lista) => {
        if (!cancelado) setRegistros((atuais) => ({ ...atuais, [ligar]: lista }));
      })
      .catch((falha) => {
        if (!cancelado) {
          setErroRegistros(falha instanceof ErroDaApi ? falha.message : TEXTOS_DO_VINCULO[ligar].erro);
        }
      });
    return () => {
      cancelado = true;
    };
  }, [ligar, idVeiculo, jaCarregados]);

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
  const voltar = origem !== "nenhum" ? `${base}/${TEXTOS_DO_VINCULO[origem].caminho}/${idDeOrigem}`
    : comoCapa ? base : `${base}/fotos`;

  function aoMudarVinculo(valor: Vinculo) {
    setLigar(valor);
    setRegistroId(valor === origem ? idDeOrigem : "");
    setErrosCampo({});
  }

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
    if (ligar !== "nenhum" && !registroId) erros[TEXTOS_DO_VINCULO[ligar].campo] = TEXTOS_DO_VINCULO[ligar].escolha;
    if (Object.keys(erros).length || !arquivo) {
      setErrosCampo(erros);
      return;
    }
    const deuCerto = await enviar(async () => {
      await enviarFoto(veiculo!.id, {
        arquivo, legenda, dataFoto: data, principal: comoCapa,
        manutencaoId: ligar === "manutencao" ? Number(registroId) : null,
        diagnosticoId: ligar === "diagnostico" ? Number(registroId) : null,
      });
      if (comoCapa) await recarregarLista();
    });
    if (deuCerto) {
      navegar(voltar, {
        replace: true,
        state: { mensagem: comoCapa ? "Foto de capa atualizada." : "Foto adicionada." },
      });
    }
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Nova foto" voltarPara={voltar} />
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
            aoMudar={aoMudarVinculo} />
          {ligar !== "nenhum" && (
            erroRegistros ? <Alerta tipo="erro">{erroRegistros}</Alerta>
              : jaCarregados === undefined ? <Carregando texto={TEXTOS_DO_VINCULO[ligar].carregando} />
                : jaCarregados.length === 0
                  ? <p className="campo__dica">{TEXTOS_DO_VINCULO[ligar].vazio}</p>
                  : (
                    <CampoSelecao rotulo={TEXTOS_DO_VINCULO[ligar].rotulo} value={registroId}
                      onChange={(e) => setRegistroId(e.target.value)}
                      erro={errosCampo[TEXTOS_DO_VINCULO[ligar].campo]}
                      opcoes={[
                        { valor: "", rotulo: "Escolha…" },
                        ...jaCarregados.map((r) => ({ valor: String(r.id), rotulo: r.rotulo })),
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
