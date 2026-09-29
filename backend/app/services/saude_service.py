"""Regras da verificação de saúde: o sistema está pronto para uso?"""

from typing import Protocol

from app.config import FUSO_HORARIO
from app.entities.situacao_sistema import EstadoMigracoes, RelogioBanco, SituacaoSistema
from app.repositories.erros import BancoIndisponivel

MENSAGEM_BANCO_FORA = (
    "A API está no ar, mas não conseguiu falar com o banco de dados. "
    "Confira se o PostgreSQL está rodando e os dados do backend/.env."
)
MENSAGEM_SEM_CONTROLE = (
    "O banco tem tabelas sem registro de migrations. "
    "Rode 'python gerenciar.py adotar-banco-existente'."
)
MENSAGEM_TUDO_CERTO = "Tudo certo: API, banco e migrations em dia."


class RepositorioDeSaude(Protocol):
    """O que o service precisa do repository (facilita testar sem banco)."""

    def ler_relogio(self) -> RelogioBanco: ...

    def ler_estado_migracoes(self) -> EstadoMigracoes: ...


class SaudeService:
    def __init__(self, repositorio: RepositorioDeSaude):
        self._repositorio = repositorio

    def verificar(self) -> SituacaoSistema:
        try:
            relogio = self._repositorio.ler_relogio()
            migracoes = self._repositorio.ler_estado_migracoes()
        except BancoIndisponivel:
            return SituacaoSistema(
                banco_disponivel=False,
                fuso_horario=FUSO_HORARIO,
                mensagem=MENSAGEM_BANCO_FORA,
                tudo_certo=False,
            )

        if migracoes.situacao == "sem_controle":
            mensagem = MENSAGEM_SEM_CONTROLE
        elif migracoes.pendentes:
            mensagem = (
                f"Há {len(migracoes.pendentes)} migration(s) pendente(s). "
                "Rode 'python gerenciar.py migrar'."
            )
        else:
            mensagem = MENSAGEM_TUDO_CERTO

        tudo_certo = migracoes.situacao == "controlado" and not migracoes.pendentes
        return SituacaoSistema(
            banco_disponivel=True,
            fuso_horario=relogio.fuso_horario,
            mensagem=mensagem,
            tudo_certo=tudo_certo,
            data_hoje=relogio.data_hoje,
            migracoes=migracoes,
        )
