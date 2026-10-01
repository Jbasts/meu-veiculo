"""Controller dos projetos de melhoria."""

from fastapi import Response

from app.entities.sessao import SessaoAtual
from app.schemas.projeto_schema import (
    ConclusaoEntrada,
    ContagemPorStatus,
    ItemEntrada,
    ItemResposta,
    PaginaProjetos,
    ProjetoDetalheResposta,
    ProjetoEntrada,
    ProjetoNovoEntrada,
    ProjetoResposta,
    ProjetoResumoResposta,
)
from app.services.projeto_service import ProjetoDetalhe, ProjetoResumo, ProjetoService


def _resumo(r: ProjetoResumo) -> dict:
    return {**ProjetoResposta.model_validate(r.projeto).model_dump(), "gasto": r.orcamento.gasto,
            "percentual": r.orcamento.percentual, "diferenca": r.orcamento.diferenca,
            "quantidade_itens": r.quantidade_itens, "foto_antes_id": r.foto_antes_id,
            "foto_depois_id": r.foto_depois_id}


def projeto_resposta(d: ProjetoDetalhe) -> ProjetoDetalheResposta:
    return ProjetoDetalheResposta(**_resumo(d), itens=[ItemResposta.model_validate(i) for i in d.itens],
                                  fotos_antes=d.fotos_antes, fotos_depois=d.fotos_depois,
                                  total_fotos=d.total_fotos)


class ProjetoController:
    def __init__(self, service: ProjetoService):
        self._service = service

    def listar(self, atual: SessaoAtual, veiculo_id: int, filtro: str, pagina: int,
               por_pagina: int) -> PaginaProjetos:
        r, por_status = self._service.listar(atual.usuario, veiculo_id, filtro, pagina, por_pagina)
        return PaginaProjetos(itens=[ProjetoResumoResposta(**_resumo(p)) for p in r.itens], total=r.total,
                              pagina=r.pagina, por_pagina=r.por_pagina,
                              por_status=ContagemPorStatus(**por_status))

    def obter(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.obter(atual.usuario, veiculo_id, projeto_id))

    def criar(self, atual: SessaoAtual, veiculo_id: int, dados: ProjetoNovoEntrada) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int,
               dados: ProjetoEntrada) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.editar(atual.usuario, veiculo_id, projeto_id, dados.model_dump()))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int) -> Response:
        self._service.apagar(atual.usuario, veiculo_id, projeto_id)
        return Response(status_code=204)

    def iniciar(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.iniciar(atual.usuario, veiculo_id, projeto_id))

    def concluir(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int,
                 dados: ConclusaoEntrada) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.concluir(atual.usuario, veiculo_id, projeto_id, dados.data_conclusao))

    def cancelar(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.cancelar(atual.usuario, veiculo_id, projeto_id))

    def reabrir(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.reabrir(atual.usuario, veiculo_id, projeto_id))

    def adicionar_item(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int,
                       dados: ItemEntrada) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.adicionar_item(atual.usuario, veiculo_id, projeto_id, dados.model_dump()))

    def editar_item(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int, item_id: int,
                    dados: ItemEntrada) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.editar_item(atual.usuario, veiculo_id, projeto_id, item_id,
                                                          dados.model_dump()))

    def apagar_item(self, atual: SessaoAtual, veiculo_id: int, projeto_id: int,
                    item_id: int) -> ProjetoDetalheResposta:
        return projeto_resposta(self._service.apagar_item(atual.usuario, veiculo_id, projeto_id, item_id))
