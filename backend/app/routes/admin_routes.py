"""Endpoints da administração: /api/admin/...

Todos exigem perfil admin (AdminDep): quem tem perfil padrão recebe 403,
mesmo digitando o endereço. Esconder o menu na tela não é a proteção; esta é.
"""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Query

from app.controllers.admin_controller import AdminController
from app.dependencias import AdminDep, obter_admin_controller
from app.schemas.admin_schema import (
    AlterarUsuarioEntrada,
    ConviteEntrada,
    ConviteResposta,
    LinkEnviadoResposta,
    PaginaUsuariosAdmin,
    PaginaVeiculosAdmin,
    ResumoAdminResposta,
    UsuarioDetalheAdminResposta,
)
from app.schemas.erro_schema import ErroResposta

router = APIRouter(prefix="/admin", tags=["administração"])

ControllerDep = Annotated[AdminController, Depends(obter_admin_controller)]
Id = Annotated[int, Path(ge=1, le=2_147_483_647)]
Pagina = Annotated[int, Query(ge=1, le=100_000)]
PorPagina = Annotated[int, Query(ge=1, le=100)]
Busca = Annotated[str | None, Query(max_length=200)]
Perfil = Annotated[str | None, Query(max_length=10)]
ERROS = {code: {"model": ErroResposta} for code in (401, 403, 404, 409, 422)}


@router.get("/resumo", response_model=ResumoAdminResposta, responses=ERROS,
            summary="Quantos usuários e veículos existem (menu Mais)")
def resumo(atual: AdminDep, controller: ControllerDep):
    return controller.resumo(atual)


@router.get("/usuarios", response_model=PaginaUsuariosAdmin, responses=ERROS,
            summary="Usuários, com busca por nome ou e-mail e filtro por perfil")
def listar_usuarios(atual: AdminDep, controller: ControllerDep, busca: Busca = None,
                    perfil: Perfil = None, pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar_usuarios(atual, busca, perfil, pagina, por_pagina)


@router.post("/usuarios", response_model=ConviteResposta, status_code=201, responses=ERROS,
             summary="Criar a conta de outra pessoa e enviar o convite para ela definir a senha")
def convidar(dados: ConviteEntrada, atual: AdminDep, controller: ControllerDep,
             tarefas: BackgroundTasks):
    return controller.convidar(atual, dados, tarefas)


@router.get("/usuarios/{usuario_id}", response_model=UsuarioDetalheAdminResposta, responses=ERROS,
            summary="Dados de um usuário e os veículos dele")
def obter_usuario(usuario_id: Id, atual: AdminDep, controller: ControllerDep):
    return controller.obter_usuario(atual, usuario_id)


@router.put("/usuarios/{usuario_id}", response_model=UsuarioDetalheAdminResposta, responses=ERROS,
            summary="Alterar perfil e conta ativa (não vale para a própria conta)")
def alterar_usuario(usuario_id: Id, dados: AlterarUsuarioEntrada, atual: AdminDep,
                    controller: ControllerDep):
    return controller.alterar_usuario(atual, usuario_id, dados)


@router.post("/usuarios/{usuario_id}/enviar-link", response_model=LinkEnviadoResposta,
             responses=ERROS, summary="Enviar link para a pessoa criar uma senha nova")
def enviar_link(usuario_id: Id, atual: AdminDep, controller: ControllerDep,
                tarefas: BackgroundTasks):
    return controller.enviar_link(atual, usuario_id, tarefas)


@router.get("/veiculos", response_model=PaginaVeiculosAdmin, responses=ERROS,
            summary="Veículos de todos os usuários, com o dono")
def listar_veiculos(atual: AdminDep, controller: ControllerDep, busca: Busca = None,
                    pagina: Pagina = 1, por_pagina: PorPagina = 30):
    return controller.listar_veiculos(atual, busca, pagina, por_pagina)
