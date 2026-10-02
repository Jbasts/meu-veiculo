"""Endpoints das marcações do tanque: /api/veiculos/{veiculo_id}/tanque/marcacoes.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se a marcação pertence àquele veículo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.medicao_tanque_controller import MedicaoTanqueController
from app.dependencias import SessaoAtualDep, obter_medicao_tanque_controller
from app.schemas.abastecimento_schema import MedicaoDetalheResposta, MedicaoEntrada, PaginaMedicoes
from app.schemas.erro_schema import ErroResposta

router = APIRouter(prefix="/veiculos/{veiculo_id}/tanque/marcacoes", tags=["combustível"])

ControllerDep = Annotated[MedicaoTanqueController, Depends(obter_medicao_tanque_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}


@router.get("", response_model=PaginaMedicoes, responses=ERROS,
            summary="Marcações do tanque (km e nível), da mais recente para a mais antiga")
def listar(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar(atual, veiculo_id, pagina, por_pagina)


@router.post("", response_model=MedicaoDetalheResposta, status_code=201, responses=ERROS,
             summary="Marcar o km e o nível do tanque (sem abastecer)")
def criar(veiculo_id: Id, dados: MedicaoEntrada, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/{medicao_id}", response_model=MedicaoDetalheResposta, responses=ERROS,
            summary="Dados de uma marcação do tanque")
def obter(veiculo_id: Id, medicao_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, medicao_id)


@router.put("/{medicao_id}", response_model=MedicaoDetalheResposta, responses=ERROS,
            summary="Corrigir uma marcação do tanque (o consumo é recalculado)")
def editar(veiculo_id: Id, medicao_id: Id, dados: MedicaoEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.editar(atual, veiculo_id, medicao_id, dados)


@router.delete("/{medicao_id}", status_code=204, responses=ERROS,
               summary="Apagar uma marcação do tanque (e a leitura de km dela)")
def apagar(veiculo_id: Id, medicao_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, medicao_id)
