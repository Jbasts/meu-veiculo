"""Endpoints de manutenção: /api/veiculos/{veiculo_id}/planos e /manutencoes.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se o plano ou a manutenção pertence àquele veículo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.manutencao_controller import ManutencaoController
from app.dependencias import SessaoAtualDep, obter_manutencao_controller
from app.schemas.erro_schema import ErroResposta
from app.schemas.manutencao_schema import (
    ManutencaoDetalheResposta,
    ManutencaoEntrada,
    PaginaManutencoes,
    PendentesResposta,
    PlanoEntrada,
    PlanoResposta,
)

router = APIRouter(prefix="/veiculos/{veiculo_id}", tags=["manutenção"])

ControllerDep = Annotated[ManutencaoController, Depends(obter_manutencao_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}


# ---------------------------------------------------------------------- planos

@router.get("/planos", response_model=list[PlanoResposta], responses=ERROS,
            summary="Planos do veículo, com a situação de cada um")
def listar_planos(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.listar_planos(atual, veiculo_id)


@router.post("/planos", response_model=PlanoResposta, status_code=201, responses=ERROS,
             summary="Criar plano recorrente (por km, por meses ou os dois)")
def criar_plano(veiculo_id: Id, dados: PlanoEntrada, atual: SessaoAtualDep,
                controller: ControllerDep):
    return controller.criar_plano(atual, veiculo_id, dados)


@router.get("/planos/{plano_id}", response_model=PlanoResposta, responses=ERROS,
            summary="Dados de um plano")
def obter_plano(veiculo_id: Id, plano_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter_plano(atual, veiculo_id, plano_id)


@router.put("/planos/{plano_id}", response_model=PlanoResposta, responses=ERROS,
            summary="Editar plano")
def editar_plano(veiculo_id: Id, plano_id: Id, dados: PlanoEntrada, atual: SessaoAtualDep,
                 controller: ControllerDep):
    return controller.editar_plano(atual, veiculo_id, plano_id, dados)


@router.post("/planos/{plano_id}/desativar", response_model=PlanoResposta, responses=ERROS,
             summary="Desativar plano (sai dos alertas; o histórico fica)")
def desativar_plano(veiculo_id: Id, plano_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.definir_plano_ativo(atual, veiculo_id, plano_id, False)


@router.post("/planos/{plano_id}/ativar", response_model=PlanoResposta, responses=ERROS,
             summary="Reativar plano")
def ativar_plano(veiculo_id: Id, plano_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.definir_plano_ativo(atual, veiculo_id, plano_id, True)


@router.delete("/planos/{plano_id}", status_code=204, responses=ERROS,
               summary="Apagar plano (as manutenções dele ficam como avulsas)")
def apagar_plano(veiculo_id: Id, plano_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar_plano(atual, veiculo_id, plano_id)


# ----------------------------------------------------------------- manutenções

@router.get("/manutencoes/pendentes", response_model=PendentesResposta, responses=ERROS,
            summary="Aba Pendentes: planos, agendadas e lembretes, sem alerta duplicado")
def pendentes(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.pendentes(atual, veiculo_id)


@router.get("/manutencoes", response_model=PaginaManutencoes, responses=ERROS,
            summary="Manutenções do veículo (status=realizada ou agendada para filtrar)")
def listar(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           status: Annotated[str | None, Query(max_length=20)] = None,
           pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar(atual, veiculo_id, status, pagina, por_pagina)


@router.post("/manutencoes", response_model=ManutencaoDetalheResposta, status_code=201,
             responses=ERROS, summary="Registrar manutenção realizada ou agendada")
def criar(veiculo_id: Id, dados: ManutencaoEntrada, atual: SessaoAtualDep,
          controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/manutencoes/{manutencao_id}", response_model=ManutencaoDetalheResposta,
            responses=ERROS, summary="Dados de uma manutenção, com a situação da garantia")
def obter(veiculo_id: Id, manutencao_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, manutencao_id)


@router.put("/manutencoes/{manutencao_id}", response_model=ManutencaoDetalheResposta,
            responses=ERROS, summary="Editar, concluir (agendada -> realizada) ou reclassificar")
def editar(veiculo_id: Id, manutencao_id: Id, dados: ManutencaoEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.editar(atual, veiculo_id, manutencao_id, dados)


@router.delete("/manutencoes/{manutencao_id}", status_code=204, responses=ERROS,
               summary="Apagar manutenção (e as fotos ligadas a ela)")
def apagar(veiculo_id: Id, manutencao_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, manutencao_id)
