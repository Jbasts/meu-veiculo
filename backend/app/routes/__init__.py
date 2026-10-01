"""Routes: definem os endereços da API e entregam cada requisição ao controller.

Para um módulo novo, crie app/routes/<modulo>_routes.py e inclua o router abaixo.
Toda rota recebe a proteção contra requisições forjadas (verificar_cabecalho_do_app).
Todas, menos a de saúde, exigem o banco na versão do código (exigir_banco_atualizado):
a tela "Situação do sistema" continua funcionando para mostrar o que falta.
"""

from fastapi import APIRouter, Depends

from app.dependencias import exigir_banco_atualizado, verificar_cabecalho_do_app
from app.routes import (
    auth_routes,
    diagnostico_routes,
    manutencao_routes,
    saude_routes,
    veiculo_routes,
)

api_router = APIRouter(prefix="/api", dependencies=[Depends(verificar_cabecalho_do_app)])
api_router.include_router(saude_routes.router)

BANCO_ATUALIZADO = [Depends(exigir_banco_atualizado)]
for modulo in (auth_routes, veiculo_routes, manutencao_routes, diagnostico_routes):
    api_router.include_router(modulo.router, dependencies=BANCO_ATUALIZADO)
