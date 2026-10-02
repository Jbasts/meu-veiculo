"""Controller dos indicadores: tela inicial e custo do veículo."""

from dataclasses import asdict

from app.entities.sessao import SessaoAtual
from app.schemas.painel_schema import CustoVeiculoResposta, PainelInicioResposta
from app.services.custo_service import CustoService
from app.services.painel_service import PainelService


class PainelController:
    def __init__(self, painel: PainelService, custo: CustoService):
        self._painel = painel
        self._custo = custo

    def inicio(self, atual: SessaoAtual, veiculo_id: int) -> PainelInicioResposta:
        return PainelInicioResposta(**asdict(self._painel.inicio(atual.usuario, veiculo_id)))

    def custo(self, atual: SessaoAtual, veiculo_id: int) -> CustoVeiculoResposta:
        total = self._custo.custo_total(atual.usuario, veiculo_id)
        por_km = self._custo.custo_por_km(atual.usuario, veiculo_id)
        return CustoVeiculoResposta(custo_total=asdict(total), custo_por_km=asdict(por_km))
