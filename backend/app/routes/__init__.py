"""Routes: definem os endereços da API e entregam cada requisição ao controller.

Para um módulo novo, crie app/routes/<modulo>_routes.py e inclua o router abaixo.
"""

from fastapi import APIRouter

from app.routes import saude_routes

api_router = APIRouter(prefix="/api")
api_router.include_router(saude_routes.router)
