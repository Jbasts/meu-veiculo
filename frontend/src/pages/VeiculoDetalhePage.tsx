import { useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { DialogoConfirmacao } from "../components/Formulario";
import { IconeCamera, IconeLapis, IconeMaisSinal } from "../components/Icones";
import { FotoProtegida, Placa } from "../components/PecasVeiculo";
import TopoComVoltar from "../components/TopoComVoltar";
import { useAuth } from "../contexts/AuthContext";
import { useVeiculos } from "../contexts/VeiculosContext";
import { useVeiculoDaRota } from "../hooks/useVeiculoDaRota";
import { ErroDaApi } from "../services/apiCliente";
import { listarFotos } from "../services/fotoService";
import { inativarVeiculo, reativarVeiculo } from "../services/veiculoService";
import { rotuloCombustivel, type Foto } from "../types/veiculo";
import { formatarDataIso, formatarMesAnoCurto } from "../utils/datas";
import { formatarDinheiro, formatarKm, formatarPlaca } from "../utils/formatos";

function Linha({ rotulo, valor }: { rotulo: string; valor: string }) {
  return (
    <li className="lista-status__linha">
      <span className="texto-suave">{rotulo}</span>
      <strong>{valor}</strong>
    </li>
  );
}

// "Meu veículo" (PDF, página 15). Os cartões "Quanto esse carro já me custou"
// e "Custo por quilômetro" dependem de gastos, abastecimentos e manutenções:
// entram na etapa 9, calculados com registros reais.
export default function VeiculoDetalhePage() {
  const { id, veiculo, setVeiculo, carregando, erro, recarregar } = useVeiculoDaRota();
  const { usuario } = useAuth();
  const { recarregar: recarregarLista, selecionar } = useVeiculos();
  const local = useLocation();
  const estado = local.state as { mensagem?: string; aviso?: string } | null;
  const [fotos, setFotos] = useState<Foto[]>([]);
  const [totalFotos, setTotalFotos] = useState<number | null>(null);
  const [confirmando, setConfirmando] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erroAcao, setErroAcao] = useState<string | null>(null);

  const carregarFotos = useCallback(async () => {
    try {
      const pagina = await listarFotos(id, 1, 3);
      setFotos(pagina.itens);
      setTotalFotos(pagina.total);
    } catch {
      setTotalFotos(null); // a seção de fotos mostra o aviso; o resto da tela continua útil
    }
  }, [id]);

  useEffect(() => {
    if (veiculo) void carregarFotos();
  }, [veiculo, carregarFotos]);

  if (carregando) return <main className="conteudo conteudo--topo"><Carregando /></main>;
  if (erro || !veiculo) {
    return (
      <main className="conteudo conteudo--topo">
        <TopoComVoltar titulo="Meu veículo" voltarPara="/veiculos" />
        <ErroComNovaTentativa mensagem={erro ?? "Veículo não encontrado."}
          aoTentar={() => void recarregar()} />
      </main>
    );
  }

  const nome = `${veiculo.marca} ${veiculo.modelo} ${veiculo.ano}`;
  const ehDono = usuario?.id === veiculo.usuario_id;
  const base = `/veiculos/${veiculo.id}`;

  async function executar(acao: () => Promise<unknown>) {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    try {
      await acao();
      await recarregarLista();
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível concluir a ação.");
    } finally {
      setOcupado(false);
      setConfirmando(false);
    }
  }

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo={ehDono ? "Meu veículo" : "Veículo"} voltarPara="/veiculos" acao={
        veiculo.ativo ? (
          <Link to={`${base}/editar`} className="botao-icone" aria-label="Editar veículo">
            <IconeLapis />
          </Link>
        ) : null
      } />
      {estado?.mensagem && <Alerta tipo="sucesso">{estado.mensagem}</Alerta>}
      {estado?.aviso && <Alerta tipo="erro">{estado.aviso}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}
      {!veiculo.ativo && (
        <Alerta tipo="info">
          Veículo inativo: o histórico pode ser consultado, mas não alterado.
        </Alerta>
      )}

      <div className="capa-veiculo">
        <FotoProtegida veiculoId={veiculo.id} fotoId={veiculo.foto_capa_id}
          descricao={`Foto de capa: ${nome}`} vazio="capa" className="foto--capa" />
        {veiculo.ativo && (
          <Link to={`${base}/fotos/nova?capa=1`} className="capa-veiculo__botao">
            <IconeCamera tamanho={20} />
            {veiculo.foto_capa_id ? "Alterar capa" : "Adicionar capa"}
          </Link>
        )}
      </div>

      <h2 className="titulo-pagina titulo-pagina--veiculo">{nome}</h2>
      <p className="linha-selos">
        <Placa placa={veiculo.placa} />
        <span className="selo selo--neutro">{rotuloCombustivel(veiculo.tipo_combustivel)}</span>
        {veiculo.em_uso && <span className="selo selo--ok">Em uso</span>}
        {!veiculo.ativo && <span className="selo selo--aviso">Inativo</span>}
      </p>

      <section className="cartao cartao--linha" aria-label="Quilometragem">
        <div>
          <p className="texto-suave cartao__rotulo">Quilometragem atual</p>
          <p className="numero-destaque">{formatarKm(veiculo.quilometragem)}</p>
          <p className="texto-suave">
            {veiculo.data_leitura_km
              ? `Leitura de ${formatarDataIso(veiculo.data_leitura_km)}`
              : "Data da leitura desconhecida"}
          </p>
        </div>
        <Link to={`${base}/km`} className="botao-pequeno">
          {veiculo.ativo ? "Atualizar km" : "Ver histórico"}
        </Link>
      </section>

      <div className="cabecalho-secao">
        <h2 className="titulo-secao">Fotos</h2>
        <Link to={`${base}/fotos`} className="link">
          {totalFotos === null ? "Ver todas" : `Ver todas (${totalFotos})`}
        </Link>
      </div>
      <div className="tira-fotos">
        {veiculo.ativo && (
          <Link to={`${base}/fotos/nova`} className="tira-fotos__adicionar">
            <IconeMaisSinal />
            Adicionar
          </Link>
        )}
        {fotos.map((foto) => (
          <Link key={foto.id} to={`${base}/fotos/${foto.id}`} className="tira-fotos__item">
            <FotoProtegida veiculoId={veiculo.id} fotoId={foto.id}
              descricao={foto.legenda ?? `Foto de ${formatarDataIso(foto.data_foto)}`} />
            {foto.principal && <span className="etiqueta-foto">Capa</span>}
          </Link>
        ))}
        {totalFotos === 0 && !veiculo.ativo && <p className="texto-suave">Nenhuma foto.</p>}
      </div>

      <Link to={`${base}/manutencoes`} className="botao botao--secundario botao--abaixo">
        Manutenções e planos deste veículo
      </Link>

      <h2 className="titulo-secao">Dados</h2>
      <ul className="cartao lista-status">
        <Linha rotulo="Marca" valor={veiculo.marca} />
        <Linha rotulo="Modelo" valor={veiculo.modelo} />
        {veiculo.versao && <Linha rotulo="Versão" valor={veiculo.versao} />}
        <Linha rotulo="Ano" valor={String(veiculo.ano)} />
        <Linha rotulo="Placa" valor={formatarPlaca(veiculo.placa)} />
        {veiculo.cor && <Linha rotulo="Cor" valor={veiculo.cor} />}
        <Linha rotulo="Combustível" valor={rotuloCombustivel(veiculo.tipo_combustivel)} />
        <Linha rotulo="Quilometragem atual" valor={formatarKm(veiculo.quilometragem)} />
        <Linha rotulo="Comprado em"
          valor={veiculo.data_aquisicao ? formatarMesAnoCurto(veiculo.data_aquisicao) : "Não informado"} />
        <Linha rotulo="Valor pago"
          valor={veiculo.valor_aquisicao ? formatarDinheiro(veiculo.valor_aquisicao) : "Não informado"} />
        <Linha rotulo="Km na compra"
          valor={veiculo.km_aquisicao !== null ? formatarKm(veiculo.km_aquisicao) : "Não informado"} />
      </ul>

      {veiculo.ativo && ehDono && !veiculo.em_uso && (
        <button type="button" className="botao botao--primario botao--espaco" disabled={ocupado}
          onClick={() => void executar(async () => {
            await selecionar(veiculo.id);
            await recarregar();
          })}>
          Usar este veículo
        </button>
      )}
      {veiculo.ativo ? (
        <button type="button" className="botao botao--texto-perigo" disabled={ocupado}
          onClick={() => setConfirmando(true)}>
          Inativar veículo
        </button>
      ) : (
        <button type="button" className="botao botao--secundario" disabled={ocupado}
          onClick={() => void executar(async () => setVeiculo(await reativarVeiculo(veiculo.id)))}>
          {ocupado ? "Reativando…" : "Reativar veículo"}
        </button>
      )}

      {confirmando && (
        <DialogoConfirmacao titulo="Inativar este veículo?" textoConfirmar="Inativar" perigo
          ocupado={ocupado} aoCancelar={() => setConfirmando(false)}
          aoConfirmar={() => void executar(async () => setVeiculo(await inativarVeiculo(veiculo.id)))}>
          <p>
            Use quando vender ou deixar de usar o {veiculo.modelo}. Nada é apagado: leituras, fotos e
            registros continuam disponíveis para consulta, e você pode reativar depois.
          </p>
        </DialogoConfirmacao>
      )}
    </main>
  );
}
