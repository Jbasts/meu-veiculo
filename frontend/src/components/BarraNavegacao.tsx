import { NavLink, Outlet, useLocation } from "react-router";

import { IconeDiagnostico, IconeFinancas, IconeInicio, IconeMais, IconeManutencao } from "./Icones";

// "prefixos": endereços que pertencem a cada aba (veículos e conta ficam em "Mais").
const ITENS = [
  { para: "/", rotulo: "Início", Icone: IconeInicio, prefixos: [] as string[] },
  { para: "/manutencao", rotulo: "Manutenção", Icone: IconeManutencao, prefixos: ["/manutencao"] },
  { para: "/diagnostico", rotulo: "Diagnóstico", Icone: IconeDiagnostico, prefixos: ["/diagnostico"] },
  { para: "/financas", rotulo: "Finanças", Icone: IconeFinancas, prefixos: ["/financas"] },
  { para: "/mais", rotulo: "Mais", Icone: IconeMais, prefixos: ["/mais", "/veiculos", "/conta"] },
];

// Navegação inferior do PDF: Início, Manutenção, Diagnóstico, Finanças e Mais.
export default function BarraNavegacao() {
  const { pathname } = useLocation();
  return (
    <nav className="barra" aria-label="Navegação principal">
      {ITENS.map(({ para, rotulo, Icone, prefixos }) => {
        // /veiculos/7/manutencoes e /veiculos/7/planos pertencem à aba Manutenção;
        // /veiculos/7/diagnosticos, à aba Diagnóstico; /veiculos/7/financas e /gastos, a Finanças.
        const deManutencao = /^\/veiculos\/\d+\/(manutencoes|planos)/.test(pathname);
        const deDiagnostico = /^\/veiculos\/\d+\/diagnosticos/.test(pathname);
        const deFinancas = /^\/veiculos\/\d+\/(financas|gastos)/.test(pathname);
        const ativo = para === "/" ? pathname === "/"
          : para === "/manutencao" ? deManutencao || pathname.startsWith("/manutencao")
            : para === "/diagnostico" ? deDiagnostico || pathname.startsWith("/diagnostico")
              : para === "/financas" ? deFinancas || pathname.startsWith("/financas")
                : !deManutencao && !deDiagnostico && !deFinancas && prefixos.some((p) => pathname.startsWith(p));
        return (
          <NavLink key={para} to={para} end
            className={`barra__item${ativo ? " barra__item--ativo" : ""}`}
            aria-current={ativo ? "page" : undefined}>
            <span className="barra__icone"><Icone /></span>
            <span className="barra__rotulo">{rotulo}</span>
          </NavLink>
        );
      })}
    </nav>
  );
}

/** Moldura das telas que mostram a barra inferior. */
export function ComBarra() {
  return (
    <div className="pagina pagina--com-barra">
      <Outlet />
      <BarraNavegacao />
    </div>
  );
}
