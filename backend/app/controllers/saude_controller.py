"""Controller da verificação de saúde."""

from fastapi.responses import JSONResponse

from app.entities.situacao_sistema import SituacaoSistema
from app.schemas.saude_schema import SaudeResposta
from app.services.saude_service import SaudeService


def montar_resposta(situacao: SituacaoSistema) -> SaudeResposta:
    migracoes = situacao.migracoes
    return SaudeResposta(
        banco="ok" if situacao.banco_disponivel else "indisponivel",
        situacao_banco=migracoes.situacao if migracoes else None,
        versao_migracao=migracoes.versao_atual if migracoes else None,
        versao_mais_recente=migracoes.versao_mais_recente if migracoes else None,
        migracoes_pendentes=list(migracoes.pendentes) if migracoes else [],
        fuso_horario=situacao.fuso_horario,
        data_hoje=situacao.data_hoje,
        mensagem=situacao.mensagem,
    )


class SaudeController:
    def __init__(self, service: SaudeService):
        self._service = service

    def verificar(self) -> JSONResponse:
        situacao = self._service.verificar()
        corpo = montar_resposta(situacao)
        # 503 = a API está no ar, mas o banco não respondeu.
        status = 200 if situacao.banco_disponivel else 503
        return JSONResponse(status_code=status, content=corpo.model_dump(mode="json"))
