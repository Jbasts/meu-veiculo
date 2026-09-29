"""Endpoints de saúde do sistema."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.controllers.saude_controller import SaudeController
from app.dependencias import obter_saude_controller
from app.schemas.saude_schema import SaudeResposta

router = APIRouter(tags=["saúde"])


@router.get(
    "/saude",
    response_model=SaudeResposta,
    responses={503: {"model": SaudeResposta, "description": "Banco de dados indisponível"}},
    summary="Situação da API, do banco e das migrations",
)
def saude(controller: Annotated[SaudeController, Depends(obter_saude_controller)]):
    return controller.verificar()
