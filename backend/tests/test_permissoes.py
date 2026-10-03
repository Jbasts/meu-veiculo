"""Proteções de acesso (usuário logado e admin) e criação do primeiro admin."""

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from app.banco.conexao import obter_engine
from app.controllers.erros_http import registrar_tratadores_de_erro
from app.dependencias import (
    AdminDep,
    SessaoAtualDep,
    obter_enviador_email,
    obter_senha_service,
    verificar_cabecalho_do_app,
)
from app.main import app as app_real
from app.routes import auth_routes
from gerenciar import main as gerenciar
from tests.auth_utils import (
    CABECALHOS_APP,
    SENHAS_RAPIDAS,
    CaixaDeEntrada,
    cadastrar,
    executar_sql,
    valor_sql,
)

# App de teste: as rotas reais de conta + duas rotas protegidas de exemplo,
# montadas exatamente como os módulos das próximas etapas vão fazer.
protegidas = APIRouter(prefix="/api/exemplo")


@protegidas.get("/meu")
def so_logado(atual: SessaoAtualDep):
    return {"usuario_id": atual.usuario.id}


@protegidas.get("/admin")
def so_admin(atual: AdminDep):
    return {"admin": atual.usuario.email}


def montar_app() -> FastAPI:
    app = FastAPI()
    registrar_tratadores_de_erro(app)
    app.include_router(auth_routes.router, prefix="/api",
                       dependencies=[Depends(verificar_cabecalho_do_app)])
    app.include_router(protegidas)
    return app


@pytest.fixture
def cliente(banco_migrado):
    app = montar_app()
    app.dependency_overrides[obter_engine] = lambda: banco_migrado
    app.dependency_overrides[obter_senha_service] = lambda: SENHAS_RAPIDAS
    caixa = CaixaDeEntrada()
    app.dependency_overrides[obter_enviador_email] = lambda: caixa
    return lambda: TestClient(app, headers=CABECALHOS_APP)


def test_rota_protegida_exige_login(cliente):
    anonimo = cliente()
    resposta = anonimo.get("/api/exemplo/meu")
    assert resposta.status_code == 401
    assert resposta.json()["mensagem"] == "Entre na sua conta para continuar."


def test_usuario_padrao_nao_acessa_area_admin(cliente, banco_migrado):
    paula = cliente()
    cadastrar(paula)
    assert paula.get("/api/exemplo/meu").status_code == 200
    resposta = paula.get("/api/exemplo/admin")
    assert resposta.status_code == 403
    assert resposta.json()["mensagem"] == "Área restrita a administradores."


def test_admin_acessa_area_admin(cliente, banco_migrado):
    paula = cliente()
    cadastrar(paula)
    executar_sql(banco_migrado, "UPDATE usuario SET perfil = 'admin'")
    assert paula.get("/api/exemplo/admin").json() == {"admin": "paula@email.com"}


def test_admin_desativado_perde_o_acesso(cliente, banco_migrado):
    paula = cliente()
    cadastrar(paula)
    rafael = cliente()
    cadastrar(rafael, email="rafael@email.com", nome="Rafael")
    executar_sql(banco_migrado, "UPDATE usuario SET perfil = 'admin'")  # dois admins
    executar_sql(banco_migrado, "UPDATE usuario SET ativo = FALSE WHERE email = 'rafael@email.com'")
    assert rafael.get("/api/exemplo/admin").status_code == 401


def test_nao_existe_endpoint_publico_para_virar_admin():
    """Mudar perfil pela API só existe em /api/admin/..., para quem JÁ é admin (cada
    endereço de lá é conferido em tests/test_admin_api.py). O primeiro admin vem do
    terminal (gerenciar.py promover-admin)."""
    enderecos = app_real.openapi()["paths"].keys()
    assert "/api/auth/cadastro" in enderecos
    fora_da_admin = [e for e in enderecos if not e.startswith("/api/admin/")]
    assert not [e for e in fora_da_admin if "admin" in e or "perfil" in e or "promover" in e]


# ------------------------------------------------- primeiro admin (terminal)

def test_promover_admin_pelo_terminal(cliente, banco_migrado, capsys):
    cadastrar(cliente())
    gerenciar(["promover-admin", " Paula@Email.com", "--teste"])
    assert "agora é administradora" in capsys.readouterr().out
    assert valor_sql(banco_migrado, "SELECT perfil FROM usuario") == "admin"
    gerenciar(["promover-admin", "paula@email.com", "--teste"])
    assert "já era administradora" in capsys.readouterr().out


def test_promover_admin_de_email_sem_conta_falha(banco_migrado, capsys):
    with pytest.raises(SystemExit) as saida:
        gerenciar(["promover-admin", "ninguem@email.com", "--teste"])
    assert saida.value.code == 1
    assert "Não há conta" in capsys.readouterr().err


def test_promover_admin_recusa_conta_desativada(cliente, banco_migrado, capsys):
    cadastrar(cliente())
    executar_sql(banco_migrado, "UPDATE usuario SET ativo = FALSE")
    with pytest.raises(SystemExit):
        gerenciar(["promover-admin", "paula@email.com", "--teste"])
    assert "desativada" in capsys.readouterr().err
    assert valor_sql(banco_migrado, "SELECT perfil FROM usuario") == "padrao"
