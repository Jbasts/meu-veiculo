"""Controller de gastos e do resumo financeiro do mês."""

from dataclasses import asdict

from fastapi import Response

from app.entities.sessao import SessaoAtual
from app.schemas.gasto_schema import (
    CategoriaResposta,
    GastoEntrada,
    GastoResposta,
    LancamentoResposta,
    PagamentoEntrada,
    PaginaLancamentos,
    PaginaPendentes,
    PendenteResposta,
    ResumoMesResposta,
)
from app.services.gasto_service import FinancasService, GastoService


class GastoController:
    def __init__(self, gastos: GastoService, financas: FinancasService):
        self._gastos = gastos
        self._financas = financas

    # ---------------------------------------------------------------------- gastos
    def obter(self, atual: SessaoAtual, veiculo_id: int, gasto_id: int) -> GastoResposta:
        return GastoResposta.model_validate(self._gastos.obter(atual.usuario, veiculo_id, gasto_id))

    def pendentes(self, atual: SessaoAtual, veiculo_id: int, pagina: int,
                  por_pagina: int) -> PaginaPendentes:
        resultado = self._gastos.pendentes(atual.usuario, veiculo_id, pagina, por_pagina)
        return PaginaPendentes(
            itens=[PendenteResposta(**GastoResposta.model_validate(p.gasto).model_dump(),
                                    situacao=p.situacao, dias=p.dias) for p in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )

    def criar(self, atual: SessaoAtual, veiculo_id: int, dados: GastoEntrada) -> GastoResposta:
        return GastoResposta.model_validate(
            self._gastos.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, gasto_id: int,
               dados: GastoEntrada) -> GastoResposta:
        return GastoResposta.model_validate(
            self._gastos.editar(atual.usuario, veiculo_id, gasto_id, dados.model_dump()))

    def pagar(self, atual: SessaoAtual, veiculo_id: int, gasto_id: int,
              dados: PagamentoEntrada) -> GastoResposta:
        return GastoResposta.model_validate(
            self._gastos.pagar(atual.usuario, veiculo_id, gasto_id, dados.data_pagamento))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, gasto_id: int) -> Response:
        self._gastos.apagar(atual.usuario, veiculo_id, gasto_id)
        return Response(status_code=204)

    # -------------------------------------------------------------------- finanças
    def resumo(self, atual: SessaoAtual, veiculo_id: int, ano: int | None,
               mes: int | None) -> ResumoMesResposta:
        r = self._financas.resumo(atual.usuario, veiculo_id, ano, mes)
        dados = asdict(r)
        dados["categorias"] = [CategoriaResposta(**asdict(c)) for c in r.categorias]
        return ResumoMesResposta(**dados)

    def lancamentos(self, atual: SessaoAtual, veiculo_id: int, ano: int | None, mes: int | None,
                    pagina: int,
                    por_pagina: int) -> PaginaLancamentos:
        resultado = self._financas.lancamentos(atual.usuario, veiculo_id, ano, mes, pagina, por_pagina)
        return PaginaLancamentos(
            itens=[LancamentoResposta.model_validate(d) for d in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )
