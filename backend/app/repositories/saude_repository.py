"""Acesso ao banco para a verificação de saúde."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.banco.migracoes import ler_estado
from app.entities.situacao_sistema import EstadoMigracoes, RelogioBanco
from app.repositories.erros import BancoIndisponivel

log = logging.getLogger("meu_veiculo")


class SaudeRepository:
    def __init__(self, sessao: Session):
        self._sessao = sessao

    def ler_relogio(self) -> RelogioBanco:
        try:
            hoje, fuso = self._sessao.execute(
                text("SELECT current_date, current_setting('TimeZone')")
            ).one()
        except SQLAlchemyError as erro:
            self._registrar_falha(erro)
            raise BancoIndisponivel() from None
        return RelogioBanco(data_hoje=hoje, fuso_horario=fuso)

    def ler_estado_migracoes(self) -> EstadoMigracoes:
        try:
            estado = ler_estado(self._sessao.get_bind())
        except SQLAlchemyError as erro:
            self._registrar_falha(erro)
            raise BancoIndisponivel() from None
        return EstadoMigracoes(
            situacao=estado.situacao,
            versao_atual=estado.versao_atual,
            versao_mais_recente=estado.versao_mais_recente,
            pendentes=tuple(estado.pendentes),
        )

    @staticmethod
    def _registrar_falha(erro: SQLAlchemyError) -> None:
        # Só o tipo do erro: a mensagem do driver pode conter usuário e host.
        log.error("Banco indisponível na verificação de saúde (%s)", type(erro).__name__)
