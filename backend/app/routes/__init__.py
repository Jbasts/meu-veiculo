"""Routes: definem os endereços da API e entregam cada requisição ao controller.

Para um módulo novo, crie app/routes/<modulo>_routes.py e inclua o router abaixo.
Toda rota recebe a proteção contra requisições forjadas (verificar_cabecalho_do_app).
"""

from fastapi import APIRouter, Depends

from app.dependencias import verificar_cabecalho_do_app
from app.routes import auth_routes, saude_routes, veiculo_routes

api_router = APIRouter(prefix="/api", dependencies=[Depends(verificar_cabecalho_do_app)])
api_router.include_router(saude_routes.router)
api_router.include_router(auth_routes.router)
api_router.include_router(veiculo_routes.router)
