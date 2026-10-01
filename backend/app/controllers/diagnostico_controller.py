"""Controller dos diagnósticos: traduz entre o JSON da API e o service."""

from fastapi import Response

from app.controllers.manutencao_controller import manutencao_resposta
from app.entities.sessao import SessaoAtual
from app.schemas.diagnostico_schema import (
    AcompanhamentoEntrada,
    DescarteEntrada,
    DiagnosticoDetalheResposta,
    DiagnosticoEntrada,
    DiagnosticoResposta,
    DiagnosticoResumoResposta,
    GarantiaResposta,
    ManutencaoLigadaResposta,
    NotaEntrada,
    NotaResposta,
    PaginaDiagnosticos,
    ResolucaoResposta,
    VinculoEntrada,
)
from app.schemas.manutencao_schema import ManutencaoEntrada
from app.services.diagnostico_service import DiagnosticoDetalhe, DiagnosticoService


def _ligada(manutencao) -> ManutencaoLigadaResposta | None:
    return ManutencaoLigadaResposta.model_validate(manutencao) if manutencao else None


def diagnostico_resposta(detalhe: DiagnosticoDetalhe) -> DiagnosticoDetalheResposta:
    base = DiagnosticoResposta.model_validate(detalhe.diagnostico).model_dump()
    return DiagnosticoDetalheResposta(
        **base,
        notas=[NotaResposta.model_validate(nota) for nota in detalhe.notas],
        manutencao=_ligada(detalhe.manutencao),
        garantias=[GarantiaResposta(manutencao_id=g.manutencao.id,
                                    descricao=g.manutencao.descricao, data=g.manutencao.data,
                                    explicacao=g.explicacao) for g in detalhe.garantias],
        total_fotos=detalhe.total_fotos,
    )


class DiagnosticoController:
    def __init__(self, service: DiagnosticoService):
        self._service = service

    def listar(self, atual: SessaoAtual, veiculo_id: int, filtro: str, pagina: int,
               por_pagina: int) -> PaginaDiagnosticos:
        resultado = self._service.listar(atual.usuario, veiculo_id, filtro, pagina, por_pagina)
        return PaginaDiagnosticos(
            itens=[DiagnosticoResumoResposta(
                **DiagnosticoResposta.model_validate(r.diagnostico).model_dump(),
                total_notas=r.total_notas, manutencao=_ligada(r.manutencao),
            ) for r in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )

    def obter(self, atual: SessaoAtual, veiculo_id: int,
              diagnostico_id: int) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.obter(atual.usuario, veiculo_id, diagnostico_id))

    def criar(self, atual: SessaoAtual, veiculo_id: int,
              dados: DiagnosticoEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(
            self._service.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
               dados: DiagnosticoEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.editar(
            atual.usuario, veiculo_id, diagnostico_id, dados.model_dump()))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int) -> Response:
        self._service.apagar(atual.usuario, veiculo_id, diagnostico_id)
        return Response(status_code=204)

    def definir_acompanhamento(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
                               dados: AcompanhamentoEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.definir_acompanhamento(
            atual.usuario, veiculo_id, diagnostico_id, dados.status))

    def descartar(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
                  dados: DescarteEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.descartar(
            atual.usuario, veiculo_id, diagnostico_id, dados.motivo, dados.data))

    def reabrir(self, atual: SessaoAtual, veiculo_id: int,
                diagnostico_id: int) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(
            self._service.reabrir(atual.usuario, veiculo_id, diagnostico_id))

    def resolver_com_nova(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
                          dados: ManutencaoEntrada) -> ResolucaoResposta:
        resultado = self._service.resolver_com_nova(atual.usuario, veiculo_id, diagnostico_id,
                                                    dados.model_dump())
        return ResolucaoResposta(diagnostico=diagnostico_resposta(resultado.diagnostico),
                                 manutencao=manutencao_resposta(resultado.manutencao))

    def resolver_com_existente(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
                               dados: VinculoEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.resolver_com_existente(
            atual.usuario, veiculo_id, diagnostico_id, dados.manutencao_id))

    def anotar(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
               dados: NotaEntrada) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.anotar(
            atual.usuario, veiculo_id, diagnostico_id, dados.texto, dados.data))

    def apagar_anotacao(self, atual: SessaoAtual, veiculo_id: int, diagnostico_id: int,
                        nota_id: int) -> DiagnosticoDetalheResposta:
        return diagnostico_resposta(self._service.apagar_anotacao(
            atual.usuario, veiculo_id, diagnostico_id, nota_id))
