"""Endpoints de indicadores e histórico de um veículo:
/api/veiculos/{veiculo_id}/painel, /custo e /historico.

Todos exigem login; o service confere se o veículo é de quem está logado (ou
se é admin). Só leitura: nada aqui grava no banco.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.historico_controller import HistoricoController
from app.controllers.painel_controller import PainelController
from app.dependencias import SessaoAtualDep, obter_historico_controller, obter_painel_controller
from app.schemas.erro_schema import ErroResposta
from app.schemas.historico_schema import PaginaHistorico
from app.schemas.painel_schema import CustoVeiculoResposta, PainelInicioResposta

router = APIRouter(prefix="/veiculos/{veiculo_id}", tags=["indicadores e histórico"])

PainelDep = Annotated[PainelController, Depends(obter_painel_controller)]
HistoricoDep = Annotated[HistoricoController, Depends(obter_historico_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
Tipo = Annotated[str | None, Query(max_length=20)]
Periodo = Annotated[str, Query(max_length=10)]
Ano = Annotated[int | None, Query(ge=1990, le=2100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 422)}


@router.get("/painel", response_model=PainelInicioResposta, responses=ERROS,
            summary="Tela inicial: gastos do mês, consumo médio, custo por km e contas vencidas")
def painel(veiculo_id: Id, atual: SessaoAtualDep, controller: PainelDep):
    return controller.inicio(atual, veiculo_id)


@router.get("/custo", response_model=CustoVeiculoResposta, responses=ERROS,
            summary="Quanto o veículo já custou (com a compra) e o custo por km (sem a compra)")
def custo(veiculo_id: Id, atual: SessaoAtualDep, controller: PainelDep):
    return controller.custo(atual, veiculo_id)


@router.get("/historico", response_model=PaginaHistorico, responses=ERROS,
            summary="Histórico: lançamentos efetivados e diagnósticos (sem valor), por período e tipo")
def historico(veiculo_id: Id, atual: SessaoAtualDep, controller: HistoricoDep, tipo: Tipo = None,
              periodo: Periodo = "12_meses", ano: Ano = None, pagina: Pagina = 1,
              por_pagina: PorPagina = 50):
    return controller.listar(atual, veiculo_id, tipo, periodo, ano, pagina, por_pagina)
