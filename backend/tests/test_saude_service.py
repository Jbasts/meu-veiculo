"""Regras do SaudeService, com um repository falso (sem banco)."""

from datetime import date

from app.config import FUSO_HORARIO
from app.entities.situacao_sistema import EstadoMigracoes, RelogioBanco
from app.repositories.erros import BancoIndisponivel
from app.services.saude_service import (
    MENSAGEM_BANCO_FORA,
    MENSAGEM_SEM_CONTROLE,
    MENSAGEM_TUDO_CERTO,
    SaudeService,
)

HOJE = date(2026, 9, 29)


class RepositorioFalso:
    def __init__(self, estado: EstadoMigracoes | None = None, fora: bool = False):
        self.estado = estado
        self.fora = fora

    def ler_relogio(self) -> RelogioBanco:
        if self.fora:
            raise BancoIndisponivel()
        return RelogioBanco(data_hoje=HOJE, fuso_horario=FUSO_HORARIO)

    def ler_estado_migracoes(self) -> EstadoMigracoes:
        assert self.estado is not None
        return self.estado


def test_tudo_certo_quando_controlado_e_sem_pendencias():
    estado = EstadoMigracoes("controlado", "0001", "0001", ())
    situacao = SaudeService(RepositorioFalso(estado)).verificar()
    assert situacao.banco_disponivel
    assert situacao.tudo_certo
    assert situacao.mensagem == MENSAGEM_TUDO_CERTO
    assert situacao.data_hoje == HOJE
    assert situacao.migracoes == estado


def test_banco_vazio_tem_migration_pendente():
    estado = EstadoMigracoes("vazio", None, "0001", ("0001",))
    situacao = SaudeService(RepositorioFalso(estado)).verificar()
    assert situacao.banco_disponivel
    assert not situacao.tudo_certo
    assert situacao.mensagem == "Há 1 migration(s) pendente(s). Rode 'python gerenciar.py migrar'."


def test_banco_sem_controle_orienta_a_adotar():
    estado = EstadoMigracoes("sem_controle", None, "0001", ())
    situacao = SaudeService(RepositorioFalso(estado)).verificar()
    assert not situacao.tudo_certo
    assert situacao.mensagem == MENSAGEM_SEM_CONTROLE


def test_banco_fora_do_ar():
    situacao = SaudeService(RepositorioFalso(fora=True)).verificar()
    assert not situacao.banco_disponivel
    assert not situacao.tudo_certo
    assert situacao.mensagem == MENSAGEM_BANCO_FORA
    assert situacao.migracoes is None
    assert situacao.data_hoje is None
    assert situacao.fuso_horario == FUSO_HORARIO
