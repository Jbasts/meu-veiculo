"""Marcação do tanque: quilometragem e nível do marcador sem abastecer.

Ideia da Paula (01/10/2026): no início de cada mês, anotar a quilometragem e
o nível do tanque (1/4, "1,5/4"...). Cada marcação é um ponto do cálculo de
consumo (services/consumo.py): com ela, o consumo aparece mesmo sem tanque
cheio, e o mês fecha certinho no "Consumo por mês".

- Exige o tamanho do tanque no cadastro do veículo (sem ele, o nível não vira
  litros). Veículo elétrico não tem tanque.
- A quilometragem vira leitura do hodômetro (trigger da 0012) e precisa
  combinar com as outras leituras, como no abastecimento.
- Nível em oitavos do tanque (services/tanque.py).
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

from app.entities.medicao_tanque import MedicaoTanque
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services import calendario
from app.services.abastecimento_service import calcular_do_veiculo
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br, numero_br
from app.services.consumo import Situacao
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.tanque import tem_tanque, validar_nivel
from app.services.veiculo_service import validar_quilometragem

ORIGEM = "medicao_tanque"


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class MedicaoDetalhe:
    medicao: MedicaoTanque
    situacao: Situacao


class MedicaoTanqueService:
    def __init__(self, uow: Transacional, veiculos, abastecimentos, leituras, medicoes, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._abastecimentos = abastecimentos
        self._leituras = leituras
        self._medicoes = medicoes
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _da_veiculo(self, veiculo_id: int, medicao_id: int) -> MedicaoTanque:
        m = self._medicoes.buscar(medicao_id)
        # A marcação precisa ser DESTE veículo, não basta existir.
        if m is None or m.veiculo_id != veiculo_id:
            raise NaoEncontrado("Marcação do tanque não encontrada.")
        return m

    def _situacoes(self, veiculo: Veiculo) -> tuple[list[MedicaoTanque], dict[int, Situacao]]:
        todas = self._medicoes.todas(veiculo.id)
        r = calcular_do_veiculo(veiculo, self._abastecimentos.todos(veiculo.id), todas)
        return todas, r.situacoes_medicao

    # ------------------------------------------------------------------ validação
    def _validar(self, veiculo: Veiculo, dados: dict, atual: MedicaoTanque | None) -> dict:
        if not tem_tanque(veiculo.tipo_combustivel):
            raise Conflito("Veículo elétrico não tem tanque de combustível para marcar.")
        if veiculo.capacidade_tanque is None:
            raise Conflito("Informe o tamanho do tanque no cadastro do veículo antes de marcar o nível: "
                           "é com ele que o nível vira litros.")
        data = dados.get("data")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data")
        if data > self._hoje():
            raise DadosInvalidos("A data não pode ser no futuro.", campo="data")
        km = validar_quilometragem(dados.get("quilometragem"))
        nivel = validar_nivel(dados.get("nivel"), "nivel", obrigatorio=True)
        conflitos = self._leituras.conflitos(
            veiculo.id, km, data, ignorar_origem=(ORIGEM, atual.id) if atual else None)
        if conflitos:
            outra = conflitos[0]
            quando = f"em {data_br(outra.data_leitura)}" if outra.data_leitura else "numa leitura antiga sem data"
            raise DadosInvalidos(
                f"Esta quilometragem não combina com o histórico: {quando} o hodômetro marcava "
                f"{numero_br(outra.quilometragem)} km. Confira o valor e a data.", campo="quilometragem")
        return {"data": data, "quilometragem": km, "nivel": nivel}

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, pagina: int = 1,
               por_pagina: int = 30) -> Pagina[MedicaoDetalhe]:
        """Da mais recente para a mais antiga, cada uma com o consumo do trecho que ela fecha."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        todas, situacoes = self._situacoes(veiculo)
        recentes = list(reversed(todas))[deslocamento:deslocamento + limite]
        return Pagina(itens=[MedicaoDetalhe(m, situacoes[m.id]) for m in recentes],
                      total=len(todas), pagina=pagina, por_pagina=por_pagina)

    def obter(self, usuario: Usuario, veiculo_id: int, medicao_id: int) -> MedicaoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        m = self._da_veiculo(veiculo.id, medicao_id)
        _, situacoes = self._situacoes(veiculo)
        return MedicaoDetalhe(m, situacoes[m.id])

    # ------------------------------------------------------------------ gravação
    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> MedicaoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            m = self._medicoes.criar(veiculo.id, self._validar(veiculo, dados, None))
            self._veiculos.recarregar(veiculo)  # a quilometragem pode ter mudado
            _, situacoes = self._situacoes(veiculo)
        return MedicaoDetalhe(m, situacoes[m.id])

    def editar(self, usuario: Usuario, veiculo_id: int, medicao_id: int, dados: dict) -> MedicaoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            m = self._da_veiculo(veiculo.id, medicao_id)
            self._medicoes.atualizar(m, self._validar(veiculo, dados, m))
            self._veiculos.recarregar(veiculo)
            _, situacoes = self._situacoes(veiculo)
        return MedicaoDetalhe(m, situacoes[m.id])

    def apagar(self, usuario: Usuario, veiculo_id: int, medicao_id: int) -> None:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            self._medicoes.apagar(self._da_veiculo(veiculo.id, medicao_id))
            self._veiculos.recarregar(veiculo)
