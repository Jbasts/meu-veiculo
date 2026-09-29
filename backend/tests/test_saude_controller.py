"""SaudeController: transforma a situação em resposta HTTP (sem banco)."""

import json
from datetime import date

from app.controllers.saude_controller import SaudeController
from app.entities.situacao_sistema import EstadoMigracoes, SituacaoSistema


class ServiceFalso:
    def __init__(self, situacao: SituacaoSistema):
        self.situacao = situacao

    def verificar(self) -> SituacaoSistema:
        return self.situacao


def responder(situacao: SituacaoSistema):
    resposta = SaudeController(ServiceFalso(situacao)).verificar()
    return resposta.status_code, json.loads(resposta.body)


def test_banco_disponivel_responde_200_com_data_pura():
    situacao = SituacaoSistema(
        banco_disponivel=True,
        fuso_horario="America/Sao_Paulo",
        mensagem="Tudo certo: API, banco e migrations em dia.",
        tudo_certo=True,
        data_hoje=date(2026, 9, 1),
        migracoes=EstadoMigracoes("controlado", "0001", "0001", ()),
    )
    status, corpo = responder(situacao)
    assert status == 200
    assert corpo == {
        "api": "ok",
        "banco": "ok",
        "situacao_banco": "controlado",
        "versao_migracao": "0001",
        "versao_mais_recente": "0001",
        "migracoes_pendentes": [],
        "fuso_horario": "America/Sao_Paulo",
        "data_hoje": "2026-09-01",
        "mensagem": "Tudo certo: API, banco e migrations em dia.",
    }


def test_banco_indisponivel_responde_503():
    situacao = SituacaoSistema(
        banco_disponivel=False,
        fuso_horario="America/Sao_Paulo",
        mensagem="A API está no ar, mas não conseguiu falar com o banco de dados.",
        tudo_certo=False,
    )
    status, corpo = responder(situacao)
    assert status == 503
    assert corpo["banco"] == "indisponivel"
    assert corpo["versao_migracao"] is None
    assert corpo["data_hoje"] is None
