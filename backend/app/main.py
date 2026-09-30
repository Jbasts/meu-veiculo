"""API do Meu Veículo: cria a aplicação e registra as routes.

Nenhuma regra fica aqui. O caminho de cada requisição é:
    Route → Controller → Service → Repository → PostgreSQL

Iniciar (na pasta backend):
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.controllers.erros_http import registrar_tratadores_de_erro
from app.controllers.limite_corpo import LimiteDeCorpo
from app.routes import api_router

app = FastAPI(title="Meu Veículo API", version="0.1.0")
registrar_tratadores_de_erro(app)
app.add_middleware(LimiteDeCorpo)
app.include_router(api_router)
