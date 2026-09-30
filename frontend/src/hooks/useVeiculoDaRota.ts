import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router";

import { ErroDaApi } from "../services/apiCliente";
import { obterVeiculo } from "../services/veiculoService";
import type { Veiculo } from "../types/veiculo";

// Carrega o veículo cujo número está no endereço (/veiculos/:veiculoId/...).
// O backend confere a permissão: veículo de outra pessoa responde "não encontrado".
export function useVeiculoDaRota() {
  const { veiculoId } = useParams();
  const id = Number(veiculoId);
  const idValido = Number.isInteger(id) && id > 0;
  const [veiculo, setVeiculo] = useState<Veiculo | null>(null);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    if (!idValido) {
      setErro("Veículo não encontrado.");
      setCarregando(false);
      return;
    }
    try {
      setVeiculo(await obterVeiculo(id));
      setErro(null);
    } catch (falha) {
      setVeiculo(null);
      setErro(falha instanceof ErroDaApi ? falha.message : "Não foi possível carregar o veículo.");
    } finally {
      setCarregando(false);
    }
  }, [id, idValido]);

  useEffect(() => {
    setCarregando(true);
    void recarregar();
  }, [recarregar]);

  return { id, veiculo, setVeiculo, carregando, erro, recarregar };
}
