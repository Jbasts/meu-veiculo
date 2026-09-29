"""Endereço /api/saude."""

from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.banco.conexao import criar_engine, obter_engine
from app.config import FUSO_HORARIO, obter_configuracoes
from app.main import app


@pytest.fixture
def cliente_com(request):
    def fabricar(engine):
        app.dependency_overrides[obter_engine] = lambda: engine
        return TestClient(app)

    yield fabricar
    app.dependency_overrides.clear()


def test_saude_com_banco_migrado(banco_migrado, cliente_com):
    resposta = cliente_com(banco_migrado).get("/api/saude")
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["api"] == "ok"
    assert corpo["banco"] == "ok"
    assert corpo["situacao_banco"] == "controlado"
    assert corpo["versao_migracao"] == "0001"
    assert corpo["versao_mais_recente"] == "0001"
    assert corpo["migracoes_pendentes"] == []
    assert corpo["fuso_horario"] == FUSO_HORARIO
    assert date.fromisoformat(corpo["data_hoje"]) == datetime.now(ZoneInfo(FUSO_HORARIO)).date()


def test_saude_avisa_migration_pendente(banco_vazio, cliente_com):
    corpo = cliente_com(banco_vazio).get("/api/saude").json()
    assert corpo["banco"] == "ok"
    assert corpo["situacao_banco"] == "vazio"
    assert corpo["migracoes_pendentes"] == ["0001"]
    assert "gerenciar.py migrar" in corpo["mensagem"]


def test_saude_sem_banco_responde_503_sem_expor_dados_da_conexao(cliente_com):
    cfg = obter_configuracoes().model_copy(update={"db_porta": 1})
    engine_quebrada = criar_engine(cfg.db_nome_teste, cfg)
    resposta = cliente_com(engine_quebrada).get("/api/saude")
    assert resposta.status_code == 503
    corpo = resposta.json()
    assert corpo["banco"] == "indisponivel"
    assert corpo["versao_migracao"] is None
    texto = resposta.text
    assert cfg.db_senha.get_secret_value() not in texto
    assert cfg.db_usuario not in texto
    engine_quebrada.dispose()
