"""Controller de veículos e quilometragem.

Recebe os dados já validados no formato (schemas), chama o service com o
usuário da sessão e monta a resposta. O dono do veículo é sempre quem está
logado: nenhum usuario_id vem da requisição.
"""

from app.entities.sessao import SessaoAtual
from app.schemas.veiculo_schema import (
    AnulacaoLeituraEntrada,
    CorrecaoLeituraEntrada,
    LeituraEntrada,
    LeituraResposta,
    PaginaLeituras,
    VeiculoEdicaoEntrada,
    VeiculoEntrada,
    VeiculoResposta,
)
from app.services.quilometragem_service import QuilometragemService
from app.services.tanque import tanque_pendente
from app.services.veiculo_service import VeiculoDetalhe, VeiculoService


def resposta_de(detalhe: VeiculoDetalhe) -> VeiculoResposta:
    """Junta os dados do veículo com o que é calculado (em uso, capa, tanque sem tamanho)."""
    calculados = {"em_uso": detalhe.em_uso, "foto_capa_id": detalhe.foto_capa_id,
                  "tanque_pendente": tanque_pendente(detalhe.veiculo)}
    do_banco = {campo: getattr(detalhe.veiculo, campo)
                for campo in VeiculoResposta.model_fields if campo not in calculados}
    return VeiculoResposta(**do_banco, **calculados)


class VeiculoController:
    def __init__(self, veiculos: VeiculoService, quilometragem: QuilometragemService):
        self._veiculos = veiculos
        self._km = quilometragem

    def listar(self, atual: SessaoAtual) -> list[VeiculoResposta]:
        return [resposta_de(d) for d in self._veiculos.listar(atual.usuario)]

    def obter(self, atual: SessaoAtual, veiculo_id: int) -> VeiculoResposta:
        return resposta_de(self._veiculos.obter(atual.usuario, veiculo_id))

    def cadastrar(self, atual: SessaoAtual, dados: VeiculoEntrada) -> VeiculoResposta:
        return resposta_de(self._veiculos.cadastrar(atual.usuario, dados.model_dump()))

    def editar(self, atual: SessaoAtual, veiculo_id: int,
               dados: VeiculoEdicaoEntrada) -> VeiculoResposta:
        return resposta_de(
            self._veiculos.editar(atual.usuario, veiculo_id, dados.model_dump()))

    def selecionar(self, atual: SessaoAtual, veiculo_id: int) -> VeiculoResposta:
        return resposta_de(self._veiculos.selecionar(atual.usuario, veiculo_id))

    def inativar(self, atual: SessaoAtual, veiculo_id: int) -> VeiculoResposta:
        return resposta_de(self._veiculos.inativar(atual.usuario, veiculo_id))

    def reativar(self, atual: SessaoAtual, veiculo_id: int) -> VeiculoResposta:
        return resposta_de(self._veiculos.reativar(atual.usuario, veiculo_id))

    # ------------------------------------------------------------ quilometragem
    def listar_leituras(self, atual: SessaoAtual, veiculo_id: int, pagina: int,
                        por_pagina: int) -> PaginaLeituras:
        resultado = self._km.listar(atual.usuario, veiculo_id, pagina, por_pagina)
        return PaginaLeituras(
            itens=[LeituraResposta.model_validate(leitura) for leitura in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )

    def _veiculo_atualizado(self, atual: SessaoAtual, veiculo_id: int) -> VeiculoResposta:
        return resposta_de(self._veiculos.obter(atual.usuario, veiculo_id))

    def registrar_leitura(self, atual: SessaoAtual, veiculo_id: int,
                          dados: LeituraEntrada) -> VeiculoResposta:
        self._km.registrar(atual.usuario, veiculo_id, dados.quilometragem, dados.data_leitura)
        return self._veiculo_atualizado(atual, veiculo_id)

    def corrigir_leitura(self, atual: SessaoAtual, veiculo_id: int, leitura_id: int,
                         dados: CorrecaoLeituraEntrada) -> VeiculoResposta:
        self._km.corrigir(atual.usuario, veiculo_id, leitura_id, dados.quilometragem, dados.motivo)
        return self._veiculo_atualizado(atual, veiculo_id)

    def anular_leitura(self, atual: SessaoAtual, veiculo_id: int, leitura_id: int,
                       dados: AnulacaoLeituraEntrada) -> VeiculoResposta:
        self._km.anular(atual.usuario, veiculo_id, leitura_id, dados.motivo)
        return self._veiculo_atualizado(atual, veiculo_id)
