"""API do Meu Veículo: cria a aplicação e registra as routes.

Nenhuma regra fica aqui. O caminho de cada requisição é:
    Route → Controller → Service → Repository → PostgreSQL

Iniciar (na pasta backend):
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.controllers.erros_http import registrar_tratadores_de_erro
from app.controllers.limite_corpo import LimiteDeCorpo
from app.controllers.sem_cache import SemCacheNaApi
from app.dependencias import avisar_se_banco_desatualizado
from app.routes import api_router


@asynccontextmanager
async def ao_iniciar(_app: FastAPI):
    avisar_se_banco_desatualizado()
    yield


app = FastAPI(title="Meu Veículo API", version="0.1.0", lifespan=ao_iniciar)
registrar_tratadores_de_erro(app)
app.add_middleware(LimiteDeCorpo)
app.add_middleware(SemCacheNaApi)
app.include_router(api_router)
