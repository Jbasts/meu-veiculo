"""Controller da tela Histórico."""

from dataclasses import asdict

from app.entities.sessao import SessaoAtual
from app.schemas.historico_schema import PaginaHistorico
from app.services.historico_service import HistoricoService


class HistoricoController:
    def __init__(self, historico: HistoricoService):
        self._historico = historico

    def listar(self, atual: SessaoAtual, veiculo_id: int, tipo: str | None, periodo: str,
               ano: int | None, pagina: int, por_pagina: int) -> PaginaHistorico:
        resultado = self._historico.listar(atual.usuario, veiculo_id, tipo, periodo, ano,
                                           pagina, por_pagina)
        return PaginaHistorico(**asdict(resultado))
