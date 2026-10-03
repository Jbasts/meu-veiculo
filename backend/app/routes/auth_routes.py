"""Endpoints de conta: /api/auth/..."""

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Request, Response

from app.controllers.auth_controller import AuthController
from app.dependencias import SessaoAtualDep, obter_auth_controller
from app.schemas.auth_schema import (
    AlterarSenhaEntrada,
    CadastroEntrada,
    ConfirmarEmailEntrada,
    LoginEntrada,
    MensagemResposta,
    RecuperarSenhaEntrada,
    ReenviarConfirmacaoEntrada,
    RedefinirSenhaEntrada,
    UsuarioResposta,
)
from app.schemas.erro_schema import ErroResposta

router = APIRouter(prefix="/auth", tags=["conta"])

ControllerDep = Annotated[AuthController, Depends(obter_auth_controller)]
ERROS = {code: {"model": ErroResposta} for code in (401, 403, 409, 422, 429)}


@router.post("/cadastro", response_model=MensagemResposta, status_code=201, responses=ERROS,
             summary="Criar conta (perfil padrão); envia o link de confirmação do e-mail")
def cadastrar(dados: CadastroEntrada, tarefas: BackgroundTasks, controller: ControllerDep):
    return controller.cadastrar(dados, tarefas)


@router.post("/confirmar-email", response_model=MensagemResposta, responses=ERROS,
             summary="Confirmar o e-mail pelo link (libera a entrada)")
def confirmar_email(dados: ConfirmarEmailEntrada, controller: ControllerDep):
    return controller.confirmar_email(dados)


@router.post("/reenviar-confirmacao", response_model=MensagemResposta, status_code=202,
             responses={**ERROS, 404: {"model": ErroResposta}},
             summary="Enviar outro link de confirmação do e-mail")
def reenviar_confirmacao(dados: ReenviarConfirmacaoEntrada, tarefas: BackgroundTasks,
                         controller: ControllerDep):
    return controller.reenviar_confirmacao(dados, tarefas)


@router.post("/entrar", response_model=UsuarioResposta, responses=ERROS, summary="Entrar")
def entrar(dados: LoginEntrada, requisicao: Request, resposta: Response, controller: ControllerDep):
    return controller.entrar(dados, requisicao, resposta)


@router.post("/sair", status_code=204, summary="Sair (encerra a sessão deste aparelho)")
def sair(requisicao: Request, controller: ControllerDep):
    return controller.sair(requisicao)


@router.get("/eu", response_model=UsuarioResposta, responses=ERROS, summary="Quem está logado")
def eu(atual: SessaoAtualDep, controller: ControllerDep):
    return controller.eu(atual)


@router.post("/alterar-senha", response_model=MensagemResposta, responses=ERROS,
             summary="Trocar a senha (os outros aparelhos saem)")
def alterar_senha(dados: AlterarSenhaEntrada, atual: SessaoAtualDep, controller: ControllerDep):
    return controller.alterar_senha(atual, dados)


@router.post("/recuperar-senha", response_model=MensagemResposta, status_code=202,
             responses=ERROS, summary="Pedir link para criar senha nova")
def recuperar_senha(dados: RecuperarSenhaEntrada, tarefas: BackgroundTasks,
                    controller: ControllerDep):
    return controller.solicitar_recuperacao(dados, tarefas)


@router.post("/redefinir-senha", response_model=MensagemResposta, responses=ERROS,
             summary="Criar senha nova com o link recebido")
def redefinir_senha(dados: RedefinirSenhaEntrada, resposta: Response, controller: ControllerDep):
    return controller.redefinir_senha(dados, resposta)
