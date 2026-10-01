"""Endpoints de diagnósticos: /api/veiculos/{veiculo_id}/diagnosticos.

Todos exigem login. O service confere se o veículo é de quem está logado (ou
se é admin) e se o diagnóstico, a anotação e a manutenção escolhida
pertencem àquele veículo.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.controllers.diagnostico_controller import DiagnosticoController
from app.dependencias import SessaoAtualDep, obter_diagnostico_controller
from app.schemas.diagnostico_schema import (
    AcompanhamentoEntrada,
    DescarteEntrada,
    DiagnosticoDetalheResposta,
    DiagnosticoEntrada,
    NotaEntrada,
    PaginaDiagnosticos,
    ResolucaoResposta,
    VinculoEntrada,
)
from app.schemas.erro_schema import ErroResposta
from app.schemas.manutencao_schema import ManutencaoEntrada

router = APIRouter(prefix="/veiculos/{veiculo_id}/diagnosticos", tags=["diagnósticos"])

ControllerDep = Annotated[DiagnosticoController, Depends(obter_diagnostico_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 404, 409, 422)}
Detalhe = DiagnosticoDetalheResposta


@router.get("", response_model=PaginaDiagnosticos, responses=ERROS,
            summary="Diagnósticos do veículo (filtro=abertos, resolvidos ou todos)")
def listar(veiculo_id: Id, atual: SessaoAtualDep, controller: ControllerDep,
           filtro: Annotated[str, Query(max_length=20)] = "abertos",
           pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar(atual, veiculo_id, filtro, pagina, por_pagina)


@router.post("", response_model=Detalhe, status_code=201, responses=ERROS,
             summary="Registrar um problema")
def criar(veiculo_id: Id, dados: DiagnosticoEntrada, atual: SessaoAtualDep,
          controller: ControllerDep):
    return controller.criar(atual, veiculo_id, dados)


@router.get("/{diagnostico_id}", response_model=Detalhe, responses=ERROS,
            summary="Dados do diagnóstico, anotações e aviso de garantia")
def obter(veiculo_id: Id, diagnostico_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.obter(atual, veiculo_id, diagnostico_id)


@router.put("/{diagnostico_id}", response_model=Detalhe, responses=ERROS,
            summary="Editar o que foi registrado (a situação muda pelas ações)")
def editar(veiculo_id: Id, diagnostico_id: Id, dados: DiagnosticoEntrada,
           atual: SessaoAtualDep, controller: ControllerDep):
    return controller.editar(atual, veiculo_id, diagnostico_id, dados)


@router.delete("/{diagnostico_id}", status_code=204, responses=ERROS,
               summary="Apagar diagnóstico (anotações e fotos dele saem junto)")
def apagar(veiculo_id: Id, diagnostico_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.apagar(atual, veiculo_id, diagnostico_id)


@router.post("/{diagnostico_id}/acompanhamento", response_model=Detalhe, responses=ERROS,
             summary="Marcar como aberto ou em observação")
def acompanhamento(veiculo_id: Id, diagnostico_id: Id, dados: AcompanhamentoEntrada,
                   atual: SessaoAtualDep, controller: ControllerDep):
    return controller.definir_acompanhamento(atual, veiculo_id, diagnostico_id, dados)


@router.post("/{diagnostico_id}/descartar", response_model=Detalhe, responses=ERROS,
             summary="Descartar (não era problema ou sumiu)")
def descartar(veiculo_id: Id, diagnostico_id: Id, dados: DescarteEntrada,
              atual: SessaoAtualDep, controller: ControllerDep):
    return controller.descartar(atual, veiculo_id, diagnostico_id, dados)


@router.post("/{diagnostico_id}/reabrir", response_model=Detalhe, responses=ERROS,
             summary="Reabrir diagnóstico resolvido ou descartado")
def reabrir(veiculo_id: Id, diagnostico_id: Id, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.reabrir(atual, veiculo_id, diagnostico_id)


@router.post("/{diagnostico_id}/resolver", response_model=ResolucaoResposta, status_code=201,
             responses=ERROS,
             summary="Registrar a manutenção que resolve (realizada) ou vai resolver (agendada)")
def resolver_com_nova(veiculo_id: Id, diagnostico_id: Id, dados: ManutencaoEntrada,
                      atual: SessaoAtualDep, controller: ControllerDep):
    return controller.resolver_com_nova(atual, veiculo_id, diagnostico_id, dados)


@router.post("/{diagnostico_id}/vincular", response_model=Detalhe, responses=ERROS,
             summary="Usar uma manutenção já registrada do mesmo veículo")
def resolver_com_existente(veiculo_id: Id, diagnostico_id: Id, dados: VinculoEntrada,
                           atual: SessaoAtualDep, controller: ControllerDep):
    return controller.resolver_com_existente(atual, veiculo_id, diagnostico_id, dados)


@router.post("/{diagnostico_id}/notas", response_model=Detalhe, status_code=201,
             responses=ERROS, summary="Adicionar anotação")
def anotar(veiculo_id: Id, diagnostico_id: Id, dados: NotaEntrada, atual: SessaoAtualDep,
           controller: ControllerDep):
    return controller.anotar(atual, veiculo_id, diagnostico_id, dados)


@router.delete("/{diagnostico_id}/notas/{nota_id}", response_model=Detalhe, responses=ERROS,
               summary="Apagar anotação")
def apagar_anotacao(veiculo_id: Id, diagnostico_id: Id, nota_id: Id, atual: SessaoAtualDep,
                    controller: ControllerDep):
    return controller.apagar_anotacao(atual, veiculo_id, diagnostico_id, nota_id)
