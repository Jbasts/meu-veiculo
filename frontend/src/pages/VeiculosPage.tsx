import { useState } from "react";
import { Link, useLocation } from "react-router";

import Alerta from "../components/Alerta";
import { Carregando, ErroComNovaTentativa } from "../components/EstadoDaTela";
import { IconeMaisSinal } from "../components/Icones";
import { FotoProtegida, Placa } from "../components/PecasVeiculo";
import TopoComVoltar from "../components/TopoComVoltar";
import { useVeiculos } from "../contexts/VeiculosContext";
import { ErroDaApi } from "../services/apiCliente";
import type { Veiculo } from "../types/veiculo";
import { formatarKm } from "../utils/formatos";

function CartaoVeiculo({ veiculo, ocupado, aoUsar }: {
  veiculo: Veiculo; ocupado: boolean; aoUsar: (veiculo: Veiculo) => void;
}) {
  const nome = `${veiculo.marca} ${veiculo.modelo} ${veiculo.ano}`;
  return (
    <li className="cartao cartao-veiculo">
      <Link to={`/veiculos/${veiculo.id}`} className="cartao-veiculo__principal">
        <FotoProtegida veiculoId={veiculo.id} fotoId={veiculo.foto_capa_id}
          descricao={`Foto de capa: ${nome}`} vazio="capa" className="foto--miniatura" />
        <span className="cartao-veiculo__texto">
          <span className="cartao__titulo">{nome}</span>
          <Placa placa={veiculo.placa} />
          <span className="texto-suave">{formatarKm(veiculo.quilometragem)}</span>
        </span>
      </Link>
      <div className="cartao-veiculo__acao">
        {!veiculo.ativo && <span className="selo selo--neutro">Inativo</span>}
        {veiculo.ativo && veiculo.em_uso && <span className="selo selo--ok">Em uso</span>}
        {veiculo.ativo && !veiculo.em_uso && (
          <button type="button" className="botao-pequeno" disabled={ocupado}
            onClick={() => aoUsar(veiculo)} aria-label={`Usar ${nome}`}>
            Usar este
          </button>
        )}
      </div>
    </li>
  );
}

// Lista de veículos da conta: trocar o veículo em uso, abrir ou cadastrar.
export default function VeiculosPage() {
  const { carregando, erro, veiculos, recarregar, selecionar } = useVeiculos();
  const local = useLocation();
  const mensagem = (local.state as { mensagem?: string } | null)?.mensagem;
  const [ocupado, setOcupado] = useState(false);
  const [erroAcao, setErroAcao] = useState<string | null>(null);

  async function usar(veiculo: Veiculo) {
    if (ocupado) return;
    setOcupado(true);
    setErroAcao(null);
    try {
      await selecionar(veiculo.id);
    } catch (falha) {
      setErroAcao(falha instanceof ErroDaApi ? falha.message : "Não foi possível trocar o veículo.");
    } finally {
      setOcupado(false);
    }
  }

  const ativos = veiculos.filter((v) => v.ativo);
  const inativos = veiculos.filter((v) => !v.ativo);

  return (
    <main className="conteudo conteudo--topo">
      <TopoComVoltar titulo="Meus veículos" voltarPara="/mais" acao={
        <Link to="/veiculos/novo" className="botao-redondo" aria-label="Cadastrar veículo">
          <IconeMaisSinal />
        </Link>
      } />
      {mensagem && <Alerta tipo="sucesso">{mensagem}</Alerta>}
      {erroAcao && <Alerta tipo="erro">{erroAcao}</Alerta>}

      {carregando && <Carregando />}
      {!carregando && erro && <ErroComNovaTentativa mensagem={erro} aoTentar={() => void recarregar()} />}

      {!carregando && !erro && veiculos.length === 0 && (
        <>
          <section className="cartao">
            <p className="cartao__titulo">Nenhum veículo cadastrado</p>
            <p className="texto-suave">Cadastre o primeiro para começar a usar o aplicativo.</p>
          </section>
          <Link to="/veiculos/novo" className="botao botao--primario">Cadastrar veículo</Link>
        </>
      )}

      {ativos.length > 0 && (
        <ul className="lista-cartoes" aria-label="Veículos ativos">
          {ativos.map((v) => (
            <CartaoVeiculo key={v.id} veiculo={v} ocupado={ocupado} aoUsar={(x) => void usar(x)} />
          ))}
        </ul>
      )}

      {inativos.length > 0 && (
        <>
          <h2 className="rotulo-secao">Inativos (histórico preservado)</h2>
          <ul className="lista-cartoes" aria-label="Veículos inativos">
            {inativos.map((v) => (
              <CartaoVeiculo key={v.id} veiculo={v} ocupado={ocupado} aoUsar={(x) => void usar(x)} />
            ))}
          </ul>
        </>
      )}
    </main>
  );
}
