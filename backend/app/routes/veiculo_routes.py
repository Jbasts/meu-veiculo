"""Endpoints de veículos, quilometragem e fotos: /api/veiculos/...

Todos exigem login (SessaoAtualDep). O service confere, em cada um, se o
veículo é de quem está logado (ou se é admin) e se a leitura ou a foto
pertence àquele veículo.
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Path, Query, Request, UploadFile

from app.controllers.foto_controller import FotoController
from app.controllers.veiculo_controller import VeiculoController
from app.dependencias import SessaoAtualDep, obter_foto_controller, obter_veiculo_controller
from app.schemas.erro_schema import ErroResposta
from app.schemas.veiculo_schema import (
    AnulacaoLeituraEntrada,
    CorrecaoLeituraEntrada,
    FotoEdicaoEntrada,
    FotoResposta,
    LeituraEntrada,
    PaginaFotos,
    PaginaLeituras,
    VeiculoEdicaoEntrada,
    VeiculoEntrada,
    VeiculoResposta,
)

router = APIRouter(prefix="/veiculos", tags=["veículos"])

VeiculoDep = Annotated[VeiculoController, Depends(obter_veiculo_controller)]
FotoDep = Annotated[FotoController, Depends(obter_foto_controller)]
# Identificadores do endereço: inteiros positivos dentro do limite do banco.
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
ERROS = {code: {"model": ErroResposta} for code in (401, 403, 404, 409, 413, 422)}


# ------------------------------------------------------------------- veículos

@router.get("", response_model=list[VeiculoResposta], responses=ERROS,
            summary="Meus veículos (ativos primeiro)")
def listar(atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.listar(atual)


@router.post("", response_model=VeiculoResposta, status_code=201, responses=ERROS,
             summary="Cadastrar veículo (vira o veículo em uso)")
def cadastrar(dados: VeiculoEntrada, atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.cadastrar(atual, dados)


@router.get("/{veiculo_id}", response_model=VeiculoResposta, responses=ERROS,
            summary="Dados de um veículo")
def obter(veiculo_id: Id, atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.obter(atual, veiculo_id)


@router.put("/{veiculo_id}", response_model=VeiculoResposta, responses=ERROS,
            summary="Editar veículo (a quilometragem muda por leituras)")
def editar(veiculo_id: Id, dados: VeiculoEdicaoEntrada, atual: SessaoAtualDep,
           controller: VeiculoDep):
    return controller.editar(atual, veiculo_id, dados)


@router.post("/{veiculo_id}/selecionar", response_model=VeiculoResposta, responses=ERROS,
             summary="Escolher como veículo em uso")
def selecionar(veiculo_id: Id, atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.selecionar(atual, veiculo_id)


@router.post("/{veiculo_id}/inativar", response_model=VeiculoResposta, responses=ERROS,
             summary="Inativar (o histórico é preservado)")
def inativar(veiculo_id: Id, atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.inativar(atual, veiculo_id)


@router.post("/{veiculo_id}/reativar", response_model=VeiculoResposta, responses=ERROS,
             summary="Reativar veículo inativo")
def reativar(veiculo_id: Id, atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.reativar(atual, veiculo_id)


# -------------------------------------------------------------- quilometragem

@router.get("/{veiculo_id}/leituras", response_model=PaginaLeituras, responses=ERROS,
            summary="Histórico de leituras de quilometragem")
def listar_leituras(veiculo_id: Id, atual: SessaoAtualDep, controller: VeiculoDep,
                    pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar_leituras(atual, veiculo_id, pagina, por_pagina)


@router.post("/{veiculo_id}/leituras", response_model=VeiculoResposta, status_code=201,
             responses=ERROS, summary="Atualizar km (nova leitura)")
def registrar_leitura(veiculo_id: Id, dados: LeituraEntrada, atual: SessaoAtualDep,
                      controller: VeiculoDep):
    return controller.registrar_leitura(atual, veiculo_id, dados)


@router.post("/{veiculo_id}/leituras/{leitura_id}/corrigir", response_model=VeiculoResposta,
             responses=ERROS, summary="Corrigir uma leitura digitada errada")
def corrigir_leitura(veiculo_id: Id, leitura_id: Id, dados: CorrecaoLeituraEntrada,
                     atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.corrigir_leitura(atual, veiculo_id, leitura_id, dados)


@router.post("/{veiculo_id}/leituras/{leitura_id}/anular", response_model=VeiculoResposta,
             responses=ERROS, summary="Anular uma leitura (continua no histórico)")
def anular_leitura(veiculo_id: Id, leitura_id: Id, dados: AnulacaoLeituraEntrada,
                   atual: SessaoAtualDep, controller: VeiculoDep):
    return controller.anular_leitura(atual, veiculo_id, leitura_id, dados)


# ---------------------------------------------------------------------- fotos

@router.get("/{veiculo_id}/fotos", response_model=PaginaFotos, responses=ERROS,
            summary="Galeria do veículo")
def listar_fotos(veiculo_id: Id, atual: SessaoAtualDep, controller: FotoDep,
                 pagina: Pagina = 1, por_pagina: PorPagina = 30,
                 vinculo: Annotated[str | None, Query(max_length=20)] = None,
                 manutencao_id: Annotated[int | None, Query(ge=1, le=2_147_483_647)] = None):
    return controller.listar(atual, veiculo_id, pagina, por_pagina, vinculo, manutencao_id)


@router.post("/{veiculo_id}/fotos", response_model=FotoResposta, status_code=201,
             responses=ERROS, summary="Enviar foto (JPEG, PNG, WebP ou HEIC, até 10 MB)")
def adicionar_foto(
    veiculo_id: Id, atual: SessaoAtualDep, controller: FotoDep,
    arquivo: Annotated[UploadFile, File()],
    legenda: Annotated[str | None, Form(max_length=1000)] = None,
    data_foto: Annotated[date | None, Form()] = None,
    principal: Annotated[bool, Form()] = False,
    manutencao_id: Annotated[int | None, Form(ge=1, le=2_147_483_647)] = None,
):
    return controller.adicionar(atual, veiculo_id, arquivo, legenda, data_foto, principal,
                                manutencao_id)


@router.delete("/{veiculo_id}/capa", status_code=204, responses=ERROS,
               summary="Deixar o veículo sem foto de capa")
def remover_capa(veiculo_id: Id, atual: SessaoAtualDep, controller: FotoDep):
    return controller.remover_capa(atual, veiculo_id)


@router.get("/{veiculo_id}/fotos/{foto_id}", response_model=FotoResposta, responses=ERROS,
            summary="Dados de uma foto")
def obter_foto(veiculo_id: Id, foto_id: Id, atual: SessaoAtualDep, controller: FotoDep):
    return controller.obter(atual, veiculo_id, foto_id)


@router.get("/{veiculo_id}/fotos/{foto_id}/arquivo", responses=ERROS,
            summary="A imagem em si (só para quem pode ver o veículo)")
def arquivo_da_foto(veiculo_id: Id, foto_id: Id, requisicao: Request, atual: SessaoAtualDep,
                    controller: FotoDep):
    return controller.arquivo(atual, veiculo_id, foto_id, requisicao)


@router.put("/{veiculo_id}/fotos/{foto_id}", response_model=FotoResposta, responses=ERROS,
            summary="Editar legenda e data da foto")
def editar_foto(veiculo_id: Id, foto_id: Id, dados: FotoEdicaoEntrada, atual: SessaoAtualDep,
                controller: FotoDep):
    return controller.editar(atual, veiculo_id, foto_id, dados)


@router.post("/{veiculo_id}/fotos/{foto_id}/capa", response_model=FotoResposta,
             responses=ERROS, summary="Usar esta foto como capa")
def definir_capa(veiculo_id: Id, foto_id: Id, atual: SessaoAtualDep, controller: FotoDep):
    return controller.definir_capa(atual, veiculo_id, foto_id)


@router.delete("/{veiculo_id}/fotos/{foto_id}", status_code=204, responses=ERROS,
               summary="Apagar foto")
def apagar_foto(veiculo_id: Id, foto_id: Id, atual: SessaoAtualDep, controller: FotoDep):
    return controller.apagar(atual, veiculo_id, foto_id)
