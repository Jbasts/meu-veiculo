"""Controller das marcações do tanque (km e nível sem abastecer)."""

from dataclasses import asdict

from fastapi import Response

from app.entities.sessao import SessaoAtual
from app.schemas.abastecimento_schema import (
    MedicaoDetalheResposta,
    MedicaoEntrada,
    MedicaoResposta,
    PaginaMedicoes,
    SituacaoResposta,
)
from app.services.medicao_tanque_service import MedicaoDetalhe, MedicaoTanqueService


def medicao_resposta(detalhe: MedicaoDetalhe) -> MedicaoDetalheResposta:
    base = MedicaoResposta.model_validate(detalhe.medicao).model_dump()
    return MedicaoDetalheResposta(**base, consumo=SituacaoResposta(**asdict(detalhe.situacao)))


class MedicaoTanqueController:
    def __init__(self, service: MedicaoTanqueService):
        self._service = service

    def listar(self, atual: SessaoAtual, veiculo_id: int, pagina: int, por_pagina: int) -> PaginaMedicoes:
        r = self._service.listar(atual.usuario, veiculo_id, pagina, por_pagina)
        return PaginaMedicoes(itens=[medicao_resposta(d) for d in r.itens],
                              total=r.total, pagina=r.pagina, por_pagina=r.por_pagina)

    def obter(self, atual: SessaoAtual, veiculo_id: int, medicao_id: int) -> MedicaoDetalheResposta:
        return medicao_resposta(self._service.obter(atual.usuario, veiculo_id, medicao_id))

    def criar(self, atual: SessaoAtual, veiculo_id: int, dados: MedicaoEntrada) -> MedicaoDetalheResposta:
        return medicao_resposta(self._service.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, medicao_id: int,
               dados: MedicaoEntrada) -> MedicaoDetalheResposta:
        return medicao_resposta(self._service.editar(atual.usuario, veiculo_id, medicao_id, dados.model_dump()))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, medicao_id: int) -> Response:
        self._service.apagar(atual.usuario, veiculo_id, medicao_id)
        return Response(status_code=204)
