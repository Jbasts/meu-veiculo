"""SaudeRepository contra o PostgreSQL de teste."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.banco.conexao import criar_engine
from app.banco.sessao import abrir_sessao
from app.config import FUSO_HORARIO, obter_configuracoes
from app.repositories.erros import BancoIndisponivel
from app.repositories.saude_repository import SaudeRepository


def test_le_relogio_e_migracoes_do_banco(banco_migrado):
    with abrir_sessao(banco_migrado) as sessao:
        repositorio = SaudeRepository(sessao)
        relogio = repositorio.ler_relogio()
        estado = repositorio.ler_estado_migracoes()
    assert relogio.fuso_horario == FUSO_HORARIO
    assert relogio.data_hoje == datetime.now(ZoneInfo(FUSO_HORARIO)).date()
    assert estado.situacao == "controlado"
    assert estado.versao_atual == "0001"
    assert estado.pendentes == ()


def test_banco_vazio_mostra_pendencia(banco_vazio):
    with abrir_sessao(banco_vazio) as sessao:
        estado = SaudeRepository(sessao).ler_estado_migracoes()
    assert estado.situacao == "vazio"
    assert estado.pendentes == ("0001",)


def test_banco_fora_vira_erro_simples_sem_detalhes():
    cfg = obter_configuracoes().model_copy(update={"db_porta": 1})
    engine = criar_engine(cfg.db_nome_teste, cfg)
    try:
        with abrir_sessao(engine) as sessao:
            repositorio = SaudeRepository(sessao)
            with pytest.raises(BancoIndisponivel) as erro:
                repositorio.ler_relogio()
            with pytest.raises(BancoIndisponivel):
                repositorio.ler_estado_migracoes()
        assert str(erro.value) == ""
        assert erro.value.__cause__ is None
    finally:
        engine.dispose()
