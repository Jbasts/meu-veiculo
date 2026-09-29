"""Montagem das camadas para cada requisição (injeção de dependências).

É aqui que cada peça recebe a de baixo:
    sessão do banco → repository → service → controller

As routes pedem o controller pronto com Depends(...). Nos testes, dá para
trocar só a engine (app.dependency_overrides[obter_engine]) e todo o resto
passa a usar o banco de teste.
"""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.banco.conexao import obter_engine
from app.banco.sessao import abrir_sessao
from app.controllers.saude_controller import SaudeController
from app.repositories.saude_repository import SaudeRepository
from app.services.saude_service import SaudeService


def obter_sessao(engine: Annotated[Engine, Depends(obter_engine)]) -> Iterator[Session]:
    """Uma sessão por requisição. Ao fechar, o que não foi confirmado é desfeito."""
    with abrir_sessao(engine) as sessao:
        yield sessao


SessaoDep = Annotated[Session, Depends(obter_sessao)]


def obter_saude_controller(sessao: SessaoDep) -> SaudeController:
    return SaudeController(SaudeService(SaudeRepository(sessao)))
