"""Banco numa versão diferente da que o código espera: 503 com explicação, não erro 500.

Reproduz o problema real: o código já tinha a migration nova e o banco de
desenvolvimento não ("coluna ... não existe" no meio do uso).
"""

import pytest
from alembic import command

from app.banco.migracoes import config_alembic, versao_mais_recente
from app.banco.versao import esquecer_conferencias
from tests.auth_utils import executar_sql, valor_sql
from tests.test_migracoes import TODAS
from tests.veiculo_utils import banco, dados_veiculo, pasta_fotos, paula  # noqa: F401  (fixtures)


@pytest.fixture
def conferencia_limpa():
    esquecer_conferencias()
    yield
    esquecer_conferencias()


def voltar_para(banco, versao: str) -> None:
    command.downgrade(config_alembic(banco, configurar_logs=False), versao)
    esquecer_conferencias()  # como reiniciar o backend


def test_banco_atrasado_responde_503_explicando_o_que_fazer(banco, paula, conferencia_limpa):
    assert paula.get("/api/veiculos").status_code == 200
    ultima = versao_mais_recente()
    voltar_para(banco, "0004")

    for resposta in (
        paula.get("/api/veiculos"),
        paula.post("/api/veiculos", json=dados_veiculo()),
        paula.get("/api/auth/eu"),
    ):
        assert resposta.status_code == 503, resposta.request.url
        mensagem = resposta.json()["mensagem"]
        assert f"está na versão 0004 e o sistema precisa da {ultima}" in mensagem
        assert "gerenciar.py migrar" in mensagem
    assert valor_sql(banco, "SELECT count(*) FROM veiculo") == 0  # nada foi gravado

    # A tela "Situação do sistema" continua mostrando o que falta.
    saude = paula.get("/api/saude")
    assert saude.status_code == 200
    # Todas as que vêm depois da 0004 (não só a última).
    assert saude.json()["migracoes_pendentes"] == TODAS[TODAS.index("0004") + 1:]


def test_migrar_com_o_backend_ligado_volta_a_funcionar_sem_reiniciar(banco, paula, conferencia_limpa):
    voltar_para(banco, "0004")
    assert paula.get("/api/veiculos").status_code == 503
    command.upgrade(config_alembic(banco, configurar_logs=False), "head")
    assert paula.get("/api/veiculos").status_code == 200


def test_banco_em_versao_que_o_codigo_nao_conhece(banco, paula, conferencia_limpa):
    atual = valor_sql(banco, "SELECT version_num FROM alembic_version")
    executar_sql(banco, "UPDATE alembic_version SET version_num = '9999'")
    try:
        resposta = paula.get("/api/veiculos")
        assert resposta.status_code == 503
        assert "versão que este código não conhece" in resposta.json()["mensagem"]
    finally:
        executar_sql(banco, "UPDATE alembic_version SET version_num = :v", v=atual)


def test_banco_em_dia_nao_confere_a_cada_requisicao(banco, paula, conferencia_limpa, monkeypatch):
    assert paula.get("/api/veiculos").status_code == 200
    chamadas = []
    import app.banco.versao as versao
    monkeypatch.setattr(versao, "ler_estado", lambda engine: chamadas.append(engine))
    for _ in range(3):
        assert paula.get("/api/veiculos").status_code == 200
    assert chamadas == []
