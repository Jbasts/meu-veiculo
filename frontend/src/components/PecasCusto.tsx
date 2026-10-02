// Peças dos indicadores de custo: barra em partes com legenda, "Quanto esse carro
// já me custou" e "Custo por quilômetro" (PDF, páginas 2 e 15). Todos os valores
// vêm calculados do backend; aqui só se formata.

import { rotuloDoGrupo, type CustoPorKm, type CustoTotal, type Parcela } from "../types/painel";
import { formatarDataIso } from "../utils/datas";
import { formatarDinheiro, formatarInteiro } from "../utils/formatos";

/** Barra única dividida pelos grupos, com a legenda e o valor de cada um. */
export function BarraEmPartes({ parcelas, singular = false, rotulo }: {
  parcelas: Parcela[]; singular?: boolean; rotulo: string;
}) {
  return (
    <>
      <span className="barra-partes" aria-hidden="true">
        {parcelas.map((p) => (
          <span key={p.grupo} className={`barra-partes__parte parte--${p.grupo}`}
            style={{ flexGrow: Math.max(p.percentual, 1) }} />
        ))}
      </span>
      <ul className="legenda-partes" aria-label={rotulo}>
        {parcelas.map((p) => (
          <li key={p.grupo} className="legenda-partes__linha">
            <span className={`legenda-partes__marca parte--${p.grupo}`} aria-hidden="true" />
            <span className="legenda-partes__nome">{rotuloDoGrupo(p.grupo, singular)}</span>
            <strong>{formatarDinheiro(p.total)}</strong>
          </li>
        ))}
      </ul>
    </>
  );
}

/** "Desde a compra" ou "Desde 12/03/2025" (curto, para o Início). */
export function periodoCurtoDoCustoPorKm(c: CustoPorKm): string {
  if (c.base === "compra") return "Desde a compra";
  return c.inicio ? `Desde ${formatarDataIso(c.inicio)}` : "";
}

/** "63.000 km rodados desde a compra (15/03/2022 a 20/09/2026), sem contar o valor de aquisição." */
export function periodoDoCustoPorKm(c: CustoPorKm): string {
  if (c.distancia === null || c.inicio === null || c.fim === null) return "";
  const km = `${formatarInteiro(c.distancia)} km rodados`;
  const datas = `${formatarDataIso(c.inicio)} a ${formatarDataIso(c.fim)}`;
  const desde = c.base === "compra"
    ? `desde a compra (${datas})`
    : `de ${datas}, desde a primeira leitura de quilometragem registrada`;
  return `${km} ${desde}, sem contar o valor de aquisição.`;
}

export function CartaoCustoTotal({ custo }: { custo: CustoTotal }) {
  return (
    <section className="cartao custo" aria-label="Quanto esse carro já me custou">
      <p className="texto-suave">Quanto esse carro já me custou</p>
      <p className="custo__valor">{formatarDinheiro(custo.total)}</p>
      {custo.parcelas.length > 0
        ? <BarraEmPartes parcelas={custo.parcelas} rotulo="Composição do custo" />
        : <p className="texto-suave">Nenhuma despesa registrada e valor da compra não informado.</p>}
      {custo.valor_aquisicao === null && (
        <p className="custo__nota">
          Valor da compra não informado: o total mostra só as despesas registradas. Informe-o em
          Editar veículo.
        </p>
      )}
    </section>
  );
}

export function CartaoCustoPorKm({ custo }: { custo: CustoPorKm }) {
  return (
    <section className="cartao custo" aria-label="Custo por quilômetro">
      <p className="texto-suave">Custo por quilômetro</p>
      {custo.disponivel && custo.valor !== null ? (
        <>
          <p className="custo__valor">
            {formatarDinheiro(custo.valor)} <span className="custo__unidade">/km</span>
          </p>
          <p className="texto-suave">{periodoDoCustoPorKm(custo)}</p>
          {custo.aviso_base && <p className="custo__nota">{custo.aviso_base}</p>}
          {custo.parcelas.length > 0 ? (
            <ul className="lista-status custo__linhas" aria-label="Custo por km de cada grupo">
              {custo.parcelas.map((p) => (
                <li key={p.grupo} className="lista-status__linha">
                  <span>{rotuloDoGrupo(p.grupo, true)}</span>
                  {/* Grupo com gasto, mas abaixo de 1 centavo por km: não é zero. */}
                  <strong>{p.por_km === "0.00" ? "menos de R$ 0,01" : formatarDinheiro(p.por_km)}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="custo__nota">Nenhuma despesa registrada nesse período.</p>
          )}
          <p className="custo__nota">
            Despesas depois da última leitura de quilometragem entram quando você atualizar o km.
          </p>
        </>
      ) : (
        <>
          <p className="custo__indisponivel">Dados insuficientes</p>
          <p className="texto-suave">{custo.motivo}</p>
          {custo.aviso_base && <p className="custo__nota">{custo.aviso_base}</p>}
        </>
      )}
    </section>
  );
}
