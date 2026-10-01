"""Controller de planos de manutenção, manutenções e pendências."""

from fastapi import Response

from app.entities.sessao import SessaoAtual
from app.schemas.manutencao_schema import (
    DiagnosticoLigadoResposta,
    ItemResposta,
    ManutencaoDetalheResposta,
    ManutencaoEntrada,
    ManutencaoResposta,
    PaginaManutencoes,
    PendenciaResposta,
    PendentesResposta,
    PlanoEntrada,
    PlanoResposta,
)
from app.services.manutencao_service import (
    ManutencaoDetalhe,
    ManutencaoService,
    PlanoDetalhe,
    PlanoService,
)

CAMPOS_DA_SITUACAO = ("situacao", "referencia_data", "referencia_km", "proxima_data", "proxima_km",
                      "dias_restantes", "km_restantes")


def plano_resposta(detalhe: PlanoDetalhe) -> PlanoResposta:
    calculados = {campo: getattr(detalhe.situacao, campo, None) for campo in CAMPOS_DA_SITUACAO}
    do_banco = {campo: getattr(detalhe.plano, campo)
                for campo in PlanoResposta.model_fields if campo not in calculados}
    return PlanoResposta(**do_banco, **calculados)


def manutencao_resposta(detalhe: ManutencaoDetalhe) -> ManutencaoDetalheResposta:
    base = ManutencaoResposta.model_validate(detalhe.manutencao).model_dump()
    return ManutencaoDetalheResposta(
        **base, plano_nome=detalhe.plano_nome, garantia_situacao=detalhe.garantia.situacao,
        garantia_explicacao=detalhe.garantia.explicacao, total_fotos=detalhe.total_fotos,
        itens=[ItemResposta.model_validate(item) for item in detalhe.itens],
        total_pecas=detalhe.total_pecas, total_mao_de_obra=detalhe.total_mao_de_obra,
        diagnosticos=[DiagnosticoLigadoResposta.model_validate(d) for d in detalhe.diagnosticos],
    )


class ManutencaoController:
    def __init__(self, planos: PlanoService, manutencoes: ManutencaoService):
        self._planos = planos
        self._manutencoes = manutencoes

    # --------------------------------------------------------------------- planos
    def listar_planos(self, atual: SessaoAtual, veiculo_id: int) -> list[PlanoResposta]:
        return [plano_resposta(d) for d in self._planos.listar(atual.usuario, veiculo_id)]

    def obter_plano(self, atual: SessaoAtual, veiculo_id: int, plano_id: int) -> PlanoResposta:
        return plano_resposta(self._planos.obter(atual.usuario, veiculo_id, plano_id))

    def criar_plano(self, atual: SessaoAtual, veiculo_id: int, dados: PlanoEntrada) -> PlanoResposta:
        return plano_resposta(self._planos.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar_plano(self, atual: SessaoAtual, veiculo_id: int, plano_id: int,
                     dados: PlanoEntrada) -> PlanoResposta:
        return plano_resposta(
            self._planos.editar(atual.usuario, veiculo_id, plano_id, dados.model_dump()))

    def definir_plano_ativo(self, atual: SessaoAtual, veiculo_id: int, plano_id: int,
                            ativo: bool) -> PlanoResposta:
        return plano_resposta(
            self._planos.definir_ativo(atual.usuario, veiculo_id, plano_id, ativo))

    def apagar_plano(self, atual: SessaoAtual, veiculo_id: int, plano_id: int) -> Response:
        self._planos.apagar(atual.usuario, veiculo_id, plano_id)
        return Response(status_code=204)

    # ---------------------------------------------------------------- manutenções
    def pendentes(self, atual: SessaoAtual, veiculo_id: int) -> PendentesResposta:
        resultado = self._manutencoes.pendentes(atual.usuario, veiculo_id)
        return PendentesResposta(
            km_atual=resultado.km_atual,
            itens=[PendenciaResposta.model_validate(item) for item in resultado.itens],
        )

    def listar(self, atual: SessaoAtual, veiculo_id: int, status: str | None, pagina: int,
               por_pagina: int) -> PaginaManutencoes:
        resultado = self._manutencoes.listar(atual.usuario, veiculo_id, status, pagina, por_pagina)
        return PaginaManutencoes(
            itens=[ManutencaoResposta.model_validate(m) for m in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )

    def obter(self, atual: SessaoAtual, veiculo_id: int,
              manutencao_id: int) -> ManutencaoDetalheResposta:
        return manutencao_resposta(self._manutencoes.obter(atual.usuario, veiculo_id, manutencao_id))

    def criar(self, atual: SessaoAtual, veiculo_id: int,
              dados: ManutencaoEntrada) -> ManutencaoDetalheResposta:
        return manutencao_resposta(
            self._manutencoes.criar(atual.usuario, veiculo_id, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int, manutencao_id: int,
               dados: ManutencaoEntrada) -> ManutencaoDetalheResposta:
        return manutencao_resposta(
            self._manutencoes.editar(atual.usuario, veiculo_id, manutencao_id, dados.model_dump()))

    def apagar(self, atual: SessaoAtual, veiculo_id: int, manutencao_id: int) -> Response:
        self._manutencoes.apagar(atual.usuario, veiculo_id, manutencao_id)
        return Response(status_code=204)
