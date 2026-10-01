"""Controller dos abastecimentos e do resumo de combustível."""

from dataclasses import asdict
from decimal import Decimal

from fastapi import Response

from app.entities.sessao import SessaoAtual
from app.schemas.abastecimento_schema import (
    AbastecimentoDetalheResposta,
    AbastecimentoEntrada,
    AbastecimentoResposta,
    ComparacaoResposta,
    MediaResposta,
    PaginaAbastecimentos,
    ResumoCombustivelResposta,
    SituacaoResposta,
)
from app.services.abastecimento_service import AbastecimentoDetalhe, AbastecimentoService


def abastecimento_resposta(detalhe: AbastecimentoDetalhe) -> AbastecimentoDetalheResposta:
    base = AbastecimentoResposta.model_validate(detalhe.abastecimento).model_dump()
    return AbastecimentoDetalheResposta(**base, consumo=SituacaoResposta(**asdict(detalhe.situacao)))


class AbastecimentoController:
    def __init__(self, service: AbastecimentoService):
        self._service = service

    def listar(self, atual: SessaoAtual, veiculo_id: int, pagina: int, por_pagina: int) -> PaginaAbastecimentos:
        r = self._service.listar(atual.usuario, veiculo_id, pagina, por_pagina)
        return PaginaAbastecimentos(itens=[abastecimento_resposta(d) for d in r.itens],
                                    total=r.total, pagina=r.pagina, por_pagina=r.por_pagina)

    def obter(self, atual: SessaoAtual, veiculo_id: int, abastecimento_id: int) -> AbastecimentoDetalheResposta:
        return abastecimento_resposta(self._service.obter(atual.usuario, veiculo_id, abastecimento_id))

    def criar(self, atual: SessaoAtual, veiculo_id: int,
              dados: AbastecimentoEntrada) -> AbastecimentoDetalheResposta:
        return abastecimento_resposta(self._service.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, abastecimento_id: int,
               dados: AbastecimentoEntrada) -> AbastecimentoDetalheResposta:
        return abastecimento_resposta(
            self._service.editar(atual.usuario, veiculo_id, abastecimento_id, dados.model_dump()))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, abastecimento_id: int) -> Response:
        self._service.apagar(atual.usuario, veiculo_id, abastecimento_id)
        return Response(status_code=204)

    def resumo(self, atual: SessaoAtual, veiculo_id: int, preco_gasolina: Decimal | None,
               preco_etanol: Decimal | None) -> ResumoCombustivelResposta:
        r = self._service.resumo(atual.usuario, veiculo_id, preco_gasolina, preco_etanol)
        return ResumoCombustivelResposta(
            combustiveis=list(r.combustiveis),
            medias=[MediaResposta(combustivel=m.combustivel, km_por_litro=m.km_por_litro,
                                  distancia=m.distancia, quantidade=m.quantidade, ciclos=m.ciclos)
                    for m in r.medias],
            comparacao=ComparacaoResposta(**asdict(r.comparacao)) if r.comparacao else None,
            postos_recentes=r.postos_recentes, ultima_quilometragem=r.ultima_quilometragem,
        )
