"""Endpoints de abastecimentos e consumo: /api/veiculos/{veiculo_id}/abastecimentos e /combustivel.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se o abastecimento pertence àquele veículo.
"""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.abastecimento_controller import AbastecimentoController
from app.dependencias import SessaoAtualDep, obter_abastecimento_controller
from app.schemas.abastecimento_schema import (
    AbastecimentoDetalheResposta,
    AbastecimentoEntrada,
    PaginaAbastecimentos,
    ResumoCombustivelResposta,
)
from app.schemas.erro_schema import ErroResposta

router = APIRouter(prefix="/veiculos/{veiculo_id}", tags=["combustível"])

ControllerDep = Annotated[AbastecimentoController, Depends(obter_abastecimento_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
# Na query string o preço chega como texto ("4.290") e vira Decimal sem passar por float.
Preco = Annotated[Decimal | None, Query(max_digits=7, decimal_places=3)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}


@router.get("/combustivel/resumo", response_model=ResumoCombustivelResposta, responses=ERROS,
            summary="Consumo médio por combustível e 'Etanol ou gasolina?' (simulação opcional)")
def resumo(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           preco_gasolina: Preco = None, preco_etanol: Preco = None):
    return controller.resumo(atual, veiculo_id, preco_gasolina, preco_etanol)


@router.get("/abastecimentos", response_model=PaginaAbastecimentos, responses=ERROS,
            summary="Abastecimentos do mais recente para o mais antigo, com o consumo de cada tanque")
def listar(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar(atual, veiculo_id, pagina, por_pagina)


@router.post("/abastecimentos", response_model=AbastecimentoDetalheResposta, status_code=201,
             responses=ERROS, summary="Registrar abastecimento (total calculado no backend)")
def criar(veiculo_id: Id, dados: AbastecimentoEntrada, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/abastecimentos/{abastecimento_id}", response_model=AbastecimentoDetalheResposta,
            responses=ERROS, summary="Dados de um abastecimento")
def obter(veiculo_id: Id, abastecimento_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, abastecimento_id)


@router.put("/abastecimentos/{abastecimento_id}", response_model=AbastecimentoDetalheResposta,
            responses=ERROS, summary="Editar abastecimento (o consumo é recalculado)")
def editar(veiculo_id: Id, abastecimento_id: Id, dados: AbastecimentoEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.editar(atual, veiculo_id, abastecimento_id, dados)


@router.delete("/abastecimentos/{abastecimento_id}", status_code=204, responses=ERROS,
               summary="Apagar abastecimento (e a leitura de km dele)")
def apagar(veiculo_id: Id, abastecimento_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, abastecimento_id)
