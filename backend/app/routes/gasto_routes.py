"""Endpoints de gastos e finanças: /api/veiculos/{veiculo_id}/gastos e /financas.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se o gasto pertence àquele veículo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.gasto_controller import GastoController
from app.dependencias import SessaoAtualDep, obter_gasto_controller
from app.schemas.erro_schema import ErroResposta
from app.schemas.gasto_schema import (
    GastoEntrada,
    GastoResposta,
    PagamentoEntrada,
    PaginaLancamentos,
    PaginaPendentes,
    ResumoMesResposta,
)

router = APIRouter(prefix="/veiculos/{veiculo_id}", tags=["finanças"])

ControllerDep = Annotated[GastoController, Depends(obter_gasto_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
# Período: ano e mês = o mês; só o ano = o ano inteiro; nenhum = total desde o primeiro registro.
Ano = Annotated[int | None, Query(ge=1990, le=2100)]
Mes = Annotated[int | None, Query(ge=1, le=12)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}


# -------------------------------------------------------------------- finanças

@router.get("/financas/resumo", response_model=ResumoMesResposta, responses=ERROS,
            summary="Total do mês, do ano ou geral, por categoria, e o previsto (fora do total)")
def resumo(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep, ano: Ano = None,
           mes: Mes = None):
    return controller.resumo(atual, veiculo_id, ano, mes)


@router.get("/financas/lancamentos", response_model=PaginaLancamentos, responses=ERROS,
            summary="Despesas efetivadas do período, da mais recente para a mais antiga")
def lancamentos(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
                ano: Ano = None, mes: Mes = None, pagina: Pagina = 1, por_pagina: PorPagina = 50):
    return controller.lancamentos(atual, veiculo_id, ano, mes, pagina, por_pagina)


# ---------------------------------------------------------------------- gastos

@router.get("/gastos/pendentes", response_model=PaginaPendentes, responses=ERROS,
            summary="Gastos pendentes (vencidos e a vencer), do vencimento mais antigo")
def pendentes(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
              pagina: Pagina = 1, por_pagina: PorPagina = 50):
    return controller.pendentes(atual, veiculo_id, pagina, por_pagina)


@router.post("/gastos", response_model=GastoResposta, status_code=201, responses=ERROS,
             summary="Registrar gasto pago ou pendente")
def criar(veiculo_id: Id, dados: GastoEntrada, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/gastos/{gasto_id}", response_model=GastoResposta, responses=ERROS,
            summary="Dados de um gasto")
def obter(veiculo_id: Id, gasto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, gasto_id)


@router.put("/gastos/{gasto_id}", response_model=GastoResposta, responses=ERROS,
            summary="Editar gasto (inclusive pago/pendente)")
def editar(veiculo_id: Id, gasto_id: Id, dados: GastoEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.editar(atual, veiculo_id, gasto_id, dados)


@router.post("/gastos/{gasto_id}/pagar", response_model=GastoResposta, responses=ERROS,
             summary="Marcar gasto pendente como pago (data padrão: hoje)")
def pagar(veiculo_id: Id, gasto_id: Id, dados: PagamentoEntrada, atual: SessaoAtualDep,
          controller: ControllerDep):
    return controller.pagar(atual, veiculo_id, gasto_id, dados)


@router.delete("/gastos/{gasto_id}", status_code=204, responses=ERROS, summary="Apagar gasto")
def apagar(veiculo_id: Id, gasto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, gasto_id)
