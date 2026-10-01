"""Endpoints de projetos de melhoria: /api/veiculos/{veiculo_id}/projetos.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se o projeto e o gasto pertencem àquele veículo e projeto.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.projeto_controller import ProjetoController
from app.dependencias import SessaoAtualDep, obter_projeto_controller
from app.schemas.erro_schema import ErroResposta
from app.schemas.projeto_schema import (
    ConclusaoEntrada,
    ItemEntrada,
    PaginaProjetos,
    ProjetoDetalheResposta,
    ProjetoEntrada,
    ProjetoNovoEntrada,
)

router = APIRouter(prefix="/veiculos/{veiculo_id}/projetos", tags=["projetos"])

ControllerDep = Annotated[ProjetoController, Depends(obter_projeto_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}
Detalhe = ProjetoDetalheResposta


@router.get("", response_model=PaginaProjetos, responses=ERROS,
            summary="Projetos (filtro=todos, planejado, em_andamento, concluido ou cancelado)")
def listar(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           filtro: Annotated[str, Query(max_length=20)] = "todos", pagina: Pagina = 1,
           por_pagina: PorPagina = 20):
    return controller.listar(atual, veiculo_id, filtro, pagina, por_pagina)


@router.post("", response_model=Detalhe, status_code=201, responses=ERROS, summary="Criar projeto")
def criar(veiculo_id: Id, dados: ProjetoNovoEntrada, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/{projeto_id}", response_model=Detalhe, responses=ERROS,
            summary="Projeto com gastos, orçamento e fotos de antes e depois")
def obter(veiculo_id: Id, projeto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, projeto_id)


@router.put("/{projeto_id}", response_model=Detalhe, responses=ERROS,
            summary="Editar nome, descrição, categoria, orçamento e previsão")
def editar(veiculo_id: Id, projeto_id: Id, dados: ProjetoEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.editar(atual, veiculo_id, projeto_id, dados)


@router.delete("/{projeto_id}", status_code=204, responses=ERROS,
               summary="Apagar projeto (os gastos saem das despesas; as fotos dele são apagadas)")
def apagar(veiculo_id: Id, projeto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, projeto_id)


@router.post("/{projeto_id}/iniciar", response_model=Detalhe, responses=ERROS, summary="Iniciar (planejado → em andamento)")
def iniciar(veiculo_id: Id, projeto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.iniciar(atual, veiculo_id, projeto_id)


@router.post("/{projeto_id}/concluir", response_model=Detalhe, responses=ERROS,
             summary="Marcar como concluído (data padrão: hoje)")
def concluir(veiculo_id: Id, projeto_id: Id, dados: ConclusaoEntrada, atual: SessaoAtualDep,
             controller: ControllerDep):
    return controller.concluir(atual, veiculo_id, projeto_id, dados)


@router.post("/{projeto_id}/cancelar", response_model=Detalhe, responses=ERROS,
             summary="Cancelar (os gastos continuam nas despesas)")
def cancelar(veiculo_id: Id, projeto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.cancelar(atual, veiculo_id, projeto_id)


@router.post("/{projeto_id}/reabrir", response_model=Detalhe, responses=ERROS,
             summary="Reabrir concluído ou cancelado (volta para em andamento)")
def reabrir(veiculo_id: Id, projeto_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.reabrir(atual, veiculo_id, projeto_id)


@router.post("/{projeto_id}/itens", response_model=Detalhe, status_code=201, responses=ERROS,
             summary="Adicionar gasto ao projeto")
def adicionar_item(veiculo_id: Id, projeto_id: Id, dados: ItemEntrada, atual: SessaoAtualDep,
                   controller: ControllerDep):
    return controller.adicionar_item(atual, veiculo_id, projeto_id, dados)


@router.put("/{projeto_id}/itens/{item_id}", response_model=Detalhe, responses=ERROS,
            summary="Editar gasto do projeto")
def editar_item(veiculo_id: Id, projeto_id: Id, item_id: Id, dados: ItemEntrada, atual: SessaoAtualDep,
                controller: ControllerDep):
    return controller.editar_item(atual, veiculo_id, projeto_id, item_id, dados)


@router.delete("/{projeto_id}/itens/{item_id}", response_model=Detalhe, responses=ERROS,
               summary="Apagar gasto do projeto")
def apagar_item(veiculo_id: Id, projeto_id: Id, item_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar_item(atual, veiculo_id, projeto_id, item_id)
