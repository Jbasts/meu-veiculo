// Peças pequenas usadas nas telas de veículo: placa, hodômetro e foto protegida.

import { useState } from "react";

import { urlDaFoto } from "../services/fotoService";
import { formatarPlaca } from "../utils/formatos";
import { IconeCarro, IconeImagem } from "./Icones";

/** Placa com a faixa azul, como no PDF. */
export function Placa({ placa }: { placa: string }) {
  return <span className="placa">{formatarPlaca(placa)}</span>;
}

/** Hodômetro do PDF: seis casas, com os zeros à esquerda apagados. */
export function Hodometro({ km }: { km: number }) {
  const texto = String(km);
  const casas = texto.padStart(Math.max(6, texto.length), "0").split("");
  const zerosAEsquerda = casas.length - texto.length;
  return (
    <p className="hodometro" aria-label={`${km} quilômetros`}>
      {casas.map((digito, indice) => (
        <span key={indice} aria-hidden="true"
          className={`hodometro__casa${indice < zerosAEsquerda ? " hodometro__casa--vazia" : ""}`}>
          {digito}
        </span>
      ))}
      <span className="hodometro__unidade" aria-hidden="true">km</span>
    </p>
  );
}

interface PropsFoto {
  veiculoId: number;
  fotoId: number | null;
  descricao: string;
  /** "capa" mostra o carro no lugar vazio; "foto", o ícone de imagem. */
  vazio?: "capa" | "foto";
  className?: string;
}

/**
 * Imagem buscada no backend (que confere a permissão). Sem foto, ou se a
 * imagem não carregar, mostra o quadro listrado do PDF.
 */
export function FotoProtegida({ veiculoId, fotoId, descricao, vazio = "foto", className = "" }: PropsFoto) {
  const [falhou, setFalhou] = useState<number | null>(null);
  if (fotoId === null || falhou === fotoId) {
    return (
      <div className={`foto foto--vazia ${className}`}>
        {vazio === "capa" ? <IconeCarro tamanho={36} /> : <IconeImagem tamanho={28} />}
        {fotoId !== null && <span className="foto__aviso">Imagem indisponível</span>}
      </div>
    );
  }
  return (
    <img className={`foto ${className}`} src={urlDaFoto(veiculoId, fotoId)} alt={descricao}
      loading="lazy" onError={() => setFalhou(fotoId)} />
  );
}
