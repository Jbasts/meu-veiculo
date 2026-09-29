"""UnidadeDeTrabalho: tudo ou nada dentro de uma transação."""

import pytest
from sqlalchemy import text

from app.banco.sessao import UnidadeDeTrabalho, abrir_sessao


@pytest.fixture
def tabela_rascunho(banco_vazio):
    with banco_vazio.begin() as conexao:
        conexao.execute(text("CREATE TABLE rascunho (valor INT NOT NULL)"))
    return banco_vazio


def contar(engine) -> int:
    with engine.connect() as conexao:
        return conexao.execute(text("SELECT count(*) FROM rascunho")).scalar()


def test_transacao_grava_tudo_quando_nada_falha(tabela_rascunho):
    with abrir_sessao(tabela_rascunho) as sessao:
        with UnidadeDeTrabalho(sessao).transacao():
            sessao.execute(text("INSERT INTO rascunho VALUES (1)"))
            sessao.execute(text("INSERT INTO rascunho VALUES (2)"))
    assert contar(tabela_rascunho) == 2


def test_transacao_desfaz_tudo_quando_uma_parte_falha(tabela_rascunho):
    with abrir_sessao(tabela_rascunho) as sessao:
        with pytest.raises(RuntimeError):
            with UnidadeDeTrabalho(sessao).transacao():
                sessao.execute(text("INSERT INTO rascunho VALUES (1)"))
                raise RuntimeError("falha forçada depois da primeira gravação")
    assert contar(tabela_rascunho) == 0


def test_sessao_fechada_sem_confirmar_nao_grava(tabela_rascunho):
    with abrir_sessao(tabela_rascunho) as sessao:
        sessao.execute(text("INSERT INTO rascunho VALUES (1)"))
    assert contar(tabela_rascunho) == 0
