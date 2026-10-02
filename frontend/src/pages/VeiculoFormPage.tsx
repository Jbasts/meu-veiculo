import { useRef, useState, type ChangeEvent, type FormEvent } from "react";
import { useNavigate } from "react-router";

import Alerta from "../components/Alerta";
import BotaoEnviar from "../components/BotaoEnviar";
import CampoTexto from "../components/CampoTexto";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { GrupoOpcoes } from "../components/Formulario";
import { IconeCamera } from "../components/Icones";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useEnvioFormulario } from "../hooks/useEnvioFormulario";
import { usePreviaDeArquivo } from "../hooks/usePreviaDeArquivo";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { enviarFoto, erroDoArquivo } from "../services/fotoService";
import { cadastrarVeiculo, editarVeiculo } from "../services/veiculoService";
import { COMBUSTIVEIS, type Combustivel, type DadosVeiculo, type Veiculo } from "../types/veiculo";
import { hojeIso } from "../utils/datas";
import {
  dinheiroParaCampo,
  formatarDecimal,
  formatarInteiro,
  formatarPlaca,
  lerDecimal3,
  lerDinheiro,
  lerInteiro,
  mascararInteiro,
  normalizarPlaca,
  placaValida,
} from "../utils/formatos";
import { erroObrigatorio, soErros } from "../utils/validacao";

interface Campos {
  marca: string;
  modelo: string;
  ano: string;
  placa: string;
  versao: string;
  cor: string;
  combustivel: Combustivel;
  quilometragem: string;
  dataAquisicao: string;
  valorAquisicao: string;
  kmAquisicao: string;
  tanque: string;
}

const VAZIO: Campos = {
  marca: "", modelo: "", ano: "", placa: "", versao: "", cor: "", combustivel: "flex",
  quilometragem: "", dataAquisicao: "", valorAquisicao: "", kmAquisicao: "", tanque: "",
};

function camposDe(veiculo: Veiculo): Campos {
  return {
    marca: veiculo.marca,
    modelo: veiculo.modelo,
    ano: String(veiculo.ano),
    placa: formatarPlaca(veiculo.placa),
    versao: veiculo.versao ?? "",
    cor: veiculo.cor ?? "",
    combustivel: veiculo.tipo_combustivel,
    quilometragem: formatarInteiro(veiculo.quilometragem),
    dataAquisicao: veiculo.data_aquisicao ?? "",
    valorAquisicao: dinheiroParaCampo(veiculo.valor_aquisicao),
    kmAquisicao: veiculo.km_aquisicao === null ? "" : formatarInteiro(veiculo.km_aquisicao),
    tanque: veiculo.capacidade_tanque === null ? "" : formatarDecimal(veiculo.capacidade_tanque),
  };
}

/** Cadastro de veículo (PDF, página 4). */
export function NovoVeiculoPage() {
  return <Formulario veiculo={null} />;
}

/** Edição: o mesmo formulário, sem a quilometragem (ela muda por leituras). */
export function EditarVeiculoPage() {
  const { veiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Editar veículo" voltarPara="/veiculos" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }
  return <Formulario veiculo={veiculo} />;
}

function Formulario({ veiculo }: { veiculo: Veiculo | null }) {
  const edicao = veiculo !== null;
  const navegar = useNavigate();
  const { recarregar: recarregarLista } = useVeiculos();
  const [campos, setCampos] = useState<Campos>(veiculo ? camposDe(veiculo) : VAZIO);
  const [capa, setCapa] = useState<File | null>(null);
  const previa = usePreviaDeArquivo(capa);
  const [erroCapa, setErroCapa] = useState<string | null>(null);
  const entradaCapa = useRef<HTMLInputElement>(null);
  const { enviando, erroGeral, errosCampo, setErrosCampo, enviar } = useEnvioFormulario();
  const hoje = hojeIso();


  function mudar<K extends keyof Campos>(campo: K, valor: Campos[K]) {
    setCampos((atual) => ({ ...atual, [campo]: valor }));
  }

  function aoEscolherCapa(evento: ChangeEvent<HTMLInputElement>) {
    const arquivo = evento.target.files?.[0] ?? null;
    const erro = arquivo ? erroDoArquivo(arquivo) : null;
    setErroCapa(erro);
    setCapa(erro ? null : arquivo);
  }

  function validar(): { erros: Record<string, string>; dados?: DadosVeiculo; km?: number } {
    const ano = lerInteiro(campos.ano);
    const km = lerInteiro(campos.quilometragem);
    const kmCompra = lerInteiro(campos.kmAquisicao);
    const valor = lerDinheiro(campos.valorAquisicao);
    const kmAtual = edicao ? veiculo.quilometragem : km;
    // Elétrico não tem tanque; os outros precisam do tamanho (em litros, até 1 casa).
    const temTanque = campos.combustivel !== "eletrico";
    const tanque = temTanque ? lerDecimal3(campos.tanque) : null;
    const placaInalterada = edicao && normalizarPlaca(campos.placa) === veiculo.placa;
    const erros = soErros({
      marca: erroObrigatorio(campos.marca, "Informe a marca."),
      modelo: erroObrigatorio(campos.modelo, "Informe o modelo."),
      ano: ano === null || ano < 1900 || ano > Number(hoje.slice(0, 4)) + 1
        ? `Informe um ano entre 1900 e ${Number(hoje.slice(0, 4)) + 1}.` : null,
      placa: !campos.placa.trim() ? "Informe a placa."
        : placaInalterada || placaValida(campos.placa) ? null
          : "Placa inválida. Use o formato ABC-1234 ou ABC1D23.",
      quilometragem: edicao ? null : km === null ? "Informe a quilometragem atual." : null,
      data_aquisicao: campos.dataAquisicao && campos.dataAquisicao > hoje
        ? "A data da compra não pode ser no futuro." : null,
      valor_aquisicao: valor === undefined ? "Valor inválido. Exemplo: 65.000,00." : null,
      km_aquisicao: kmCompra !== null && kmAtual !== null && kmCompra > kmAtual
        ? "A quilometragem na compra não pode ser maior que a atual." : null,
      capacidade_tanque: !temTanque ? null
        : tanque === null ? "Informe o tamanho do tanque em litros (está no manual do veículo)."
          : tanque === undefined || !/0{2}$/.test(tanque) ? "Tamanho inválido. Exemplo: 47 ou 47,5."
            : Number(tanque) <= 0 ? "O tamanho do tanque precisa ser maior que zero." : null,
    });
    if (Object.keys(erros).length || ano === null || valor === undefined || tanque === undefined) return { erros };
    return {
      erros,
      km: km ?? undefined,
      dados: {
        marca: campos.marca.trim(),
        modelo: campos.modelo.trim(),
        versao: campos.versao.trim() || null,
        ano,
        placa: campos.placa.trim(),
        cor: campos.cor.trim() || null,
        tipo_combustivel: campos.combustivel,
        data_aquisicao: campos.dataAquisicao || null,
        valor_aquisicao: valor,
        km_aquisicao: kmCompra,
        capacidade_tanque: tanque,
      },
    };
  }

  async function aoEnviar(evento: FormEvent) {
    evento.preventDefault();
    const { erros, dados, km } = validar();
    if (!dados) {
      setErrosCampo(erros);
      return;
    }
    let destino = "";
    let aviso: string | undefined;
    const deuCerto = await enviar(async () => {
      if (edicao) {
        await editarVeiculo(veiculo.id, dados);
        destino = `/veiculos/${veiculo.id}`;
      } else {
        const criado = await cadastrarVeiculo({ ...dados, quilometragem: km ?? 0 });
        destino = `/veiculos/${criado.id}`;
        if (capa) {
          try {
            await enviarFoto(criado.id, {
              arquivo: capa, legenda: "", dataFoto: hoje, principal: true,
            });
          } catch (falha) {
            // O veículo já foi salvo: avisa e segue, sem repetir o cadastro.
            const motivo = falha instanceof ErroDaApi ? falha.message : "erro inesperado";
            aviso = `Veículo salvo, mas a foto de capa não foi enviada: ${motivo} Tente de novo em "Adicionar capa".`;
          }
        }
      }
      await recarregarLista();
    });
    if (deuCerto) {
      navegar(destino, {
        replace: true,
        state: aviso ? { aviso } : { mensagem: edicao ? "Alterações salvas." : "Veículo cadastrado." },
      });
    }
  }

  return (
    <div className="pagina">
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo={edicao ? "Editar veículo" : "Cadastrar veículo"}
          voltarPara={edicao ? `/veiculos/${veiculo.id}` : "/veiculos"} />
        {erroGeral && <Alerta tipo="erro">{erroGeral}</Alerta>}

        <form onSubmit={aoEnviar} noValidate>
          {!edicao && (
            <div className="campo">
              <input ref={entradaCapa} type="file" className="oculto" aria-label="Foto de capa"
                accept="image/jpeg,image/png,image/webp,image/heic,image/heif"
                onChange={aoEscolherCapa} />
              <button type="button" className="area-foto" onClick={() => entradaCapa.current?.click()}>
                {previa
                  ? <img src={previa} alt="Foto de capa escolhida" className="area-foto__previa" />
                  : <IconeCamera tamanho={34} />}
                <span className="area-foto__titulo">
                  {capa ? "Trocar foto de capa" : "Adicionar foto de capa"}
                </span>
                <span className="texto-suave">
                  {capa ? capa.name : "Opcional. Dá para trocar depois."}
                </span>
              </button>
              {erroCapa && <p className="campo__erro" role="alert">{erroCapa}</p>}
            </div>
          )}

          <div className="dupla">
            <CampoTexto rotulo="Marca" value={campos.marca} maxLength={60} placeholder="Honda"
              onChange={(e) => mudar("marca", e.target.value)} erro={errosCampo.marca} />
            <CampoTexto rotulo="Modelo" value={campos.modelo} maxLength={80} placeholder="Civic"
              onChange={(e) => mudar("modelo", e.target.value)} erro={errosCampo.modelo} />
          </div>
          <div className="dupla">
            <CampoTexto rotulo="Ano" inputMode="numeric" value={campos.ano} maxLength={4}
              placeholder="2020" onChange={(e) => mudar("ano", e.target.value.replace(/\D/g, ""))}
              erro={errosCampo.ano} />
            <CampoTexto rotulo="Placa" value={campos.placa} maxLength={8} placeholder="ABC-1234"
              autoCapitalize="characters" autoComplete="off"
              onChange={(e) => mudar("placa", e.target.value.toUpperCase())} erro={errosCampo.placa} />
          </div>
          <div className="dupla">
            <CampoTexto rotulo="Versão" value={campos.versao} maxLength={80} placeholder="Opcional"
              onChange={(e) => mudar("versao", e.target.value)} erro={errosCampo.versao} />
            <CampoTexto rotulo="Cor" value={campos.cor} maxLength={40} placeholder="Opcional"
              onChange={(e) => mudar("cor", e.target.value)} erro={errosCampo.cor} />
          </div>

          <GrupoOpcoes rotulo="Combustível" opcoes={COMBUSTIVEIS} valor={campos.combustivel}
            aoMudar={(valor) => mudar("combustivel", valor)} erro={errosCampo.tipo_combustivel} />

          {campos.combustivel !== "eletrico" && (
            <>
              {edicao && veiculo.tanque_pendente && (
                <Alerta tipo="info">Informe o tamanho do tanque: ele passou a ser obrigatório.</Alerta>
              )}
              <CampoTexto rotulo="Tamanho do tanque (litros)" inputMode="decimal" placeholder="47"
                value={campos.tanque} maxLength={7} onChange={(e) => mudar("tanque", e.target.value)}
                erro={errosCampo.capacidade_tanque}
                dica="Está no manual. Serve para conferir os litros ao abastecer e usar o nível do marcador." />
            </>
          )}

          {edicao ? (
            <div className="caixa-info">
              <p>
                Quilometragem atual: <strong>{formatarInteiro(veiculo.quilometragem)} km</strong>.
                Para atualizar ou corrigir, use "Atualizar km" na tela do veículo.
              </p>
            </div>
          ) : (
            <CampoTexto rotulo="Quilometragem atual" inputMode="numeric" placeholder="85.000"
              value={campos.quilometragem} maxLength={9}
              onChange={(e) => mudar("quilometragem", mascararInteiro(e.target.value))}
              erro={errosCampo.quilometragem} dica="O que o hodômetro marca hoje." />
          )}

          <hr className="separador" />
          <h2 className="titulo-secao">Dados da compra</h2>
          <p className="texto-suave secao__dica">
            Opcional. Serve para calcular quanto o carro já custou e o custo por km.
          </p>
          <div className="dupla">
            <CampoTexto rotulo="Data da compra" type="date" max={hoje} value={campos.dataAquisicao}
              onChange={(e) => mudar("dataAquisicao", e.target.value)}
              erro={errosCampo.data_aquisicao} />
            <CampoTexto rotulo="Valor pago (R$)" inputMode="decimal" placeholder="65.000,00"
              value={campos.valorAquisicao} maxLength={20}
              onChange={(e) => mudar("valorAquisicao", e.target.value)}
              erro={errosCampo.valor_aquisicao} />
          </div>
          <CampoTexto rotulo="Quilometragem na compra" inputMode="numeric" placeholder="22.000"
            value={campos.kmAquisicao} maxLength={9}
            onChange={(e) => mudar("kmAquisicao", mascararInteiro(e.target.value))}
            erro={errosCampo.km_aquisicao} />

          <BotaoEnviar enviando={enviando} textoEnviando="Salvando…">
            {edicao ? "Salvar alterações" : "Salvar veículo"}
          </BotaoEnviar>
        </form>
      </main>
    </div>
  );
}
