// Guarda os veículos de quem está logado e qual deles está em uso.
//
// Fica só na memória da página (nada em localStorage) e existe apenas dentro
// da área logada: ao sair, a lista some junto.

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import * as veiculoService from "../services/veiculoService";
import type { Veiculo } from "../types/veiculo";

interface EstadoVeiculos {
  carregando: boolean;
  erro: string | null;
  veiculos: Veiculo[];
  /** Veículo selecionado nas telas; null quando a pessoa não tem veículo ativo. */
  emUso: Veiculo | null;
  recarregar: () => Promise<void>;
  selecionar: (id: number) => Promise<void>;
}

const ContextoVeiculos = createContext<EstadoVeiculos | null>(null);

export function VeiculosProvider({ children }: { children: ReactNode }) {
  const [veiculos, setVeiculos] = useState<Veiculo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);

  const recarregar = useCallback(async () => {
    try {
      setVeiculos(await veiculoService.listarVeiculos());
      setErro(null);
    } catch (falha) {
      setErro(falha instanceof Error ? falha.message : "Não foi possível carregar seus veículos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    void recarregar();
  }, [recarregar]);

  const selecionar = useCallback(async (id: number) => {
    await veiculoService.selecionarVeiculo(id);
    await recarregar();
  }, [recarregar]);

  const valor = useMemo<EstadoVeiculos>(
    () => ({
      carregando,
      erro,
      veiculos,
      emUso: veiculos.find((v) => v.em_uso) ?? null,
      recarregar,
      selecionar,
    }),
    [carregando, erro, veiculos, recarregar, selecionar],
  );

  return <ContextoVeiculos.Provider value={valor}>{children}</ContextoVeiculos.Provider>;
}

export function useVeiculos(): EstadoVeiculos {
  const contexto = useContext(ContextoVeiculos);
  if (!contexto) {
    throw new Error("useVeiculos precisa estar dentro de <VeiculosProvider>.");
  }
  return contexto;
}
