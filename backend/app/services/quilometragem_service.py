"""Regras da quilometragem: leituras do hodômetro, histórico e correção.

Como funciona
- Cada atualização de km é uma LEITURA: o valor e o dia em que o hodômetro
  marcava esse valor (data_leitura). O banco guarda também quando ela foi
  digitada (criado_em).
- A quilometragem atual do veículo é a MAIOR leitura válida, e a "data de
  atualização" mostrada na tela é a data dessa leitura. Quem calcula é o
  banco (função recalcular_km_veiculo), a cada mudança nas leituras.
- Por isso, lançar uma leitura antiga (km menor, data anterior) nunca reduz
  a quilometragem atual.

Coerência
- O hodômetro só anda para a frente: uma leitura é recusada se contradiz
  outra (dia anterior com km maior, ou dia posterior com km menor). No mesmo
  dia, qualquer ordem vale.

Correção de leitura digitada errada
- corrigir(): a leitura errada é ANULADA (continua no histórico, com o motivo)
  e uma leitura nova, com a mesma data e o valor certo, entra no lugar.
- anular(): retira uma leitura que não deveria existir. Não é possível
  anular a única leitura válida do veículo.
- Só leituras digitadas nesta tela (cadastro, manual ou herdada) são
  corrigidas aqui. As que vieram de abastecimento, manutenção ou
  diagnóstico são corrigidas editando o registro de origem.
- Depois de qualquer correção, o banco recalcula a quilometragem atual; os
  indicadores (consumo, custo por km, planos) são sempre calculados na hora,
  a partir das leituras válidas, então refletem a correção sem outro passo.
"""

from datetime import date
from typing import Callable, Protocol

from app.entities.leitura_km import ORIGEM_MANUAL, LeituraKm
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br, numero_br
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.veiculo_service import validar_quilometragem

TAMANHO_MAXIMO_MOTIVO = 200
NOME_DA_ORIGEM = {"abastecimento": "abastecimento", "manutencao": "manutenção",
                  "diagnostico": "diagnóstico", "medicao_tanque": "marcação do tanque"}


class Transacional(Protocol):
    def transacao(self): ...


def _motivo(texto: str | None) -> str | None:
    limpo = " ".join((texto or "").split())
    if len(limpo) > TAMANHO_MAXIMO_MOTIVO:
        raise DadosInvalidos(f"Texto longo demais (máximo {TAMANHO_MAXIMO_MOTIVO} caracteres).",
                             campo="motivo")
    return limpo or None


def _descrever(leitura: LeituraKm) -> str:
    quando = (f"em {data_br(leitura.data_leitura)}" if leitura.data_leitura
              else "numa leitura antiga sem data")
    return f"{quando} o hodômetro marcava {numero_br(leitura.quilometragem)} km"


class QuilometragemService:
    def __init__(self, uow: Transacional, veiculos, leituras, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._leituras = leituras
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def listar(self, usuario: Usuario, veiculo_id: int, pagina: int = 1,
               por_pagina: int = 30) -> Pagina[LeituraKm]:
        """Histórico de leituras, incluindo as anuladas (para mostrar as correções)."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(
            itens=self._leituras.listar(veiculo.id, limite, deslocamento),
            total=self._leituras.contar(veiculo.id), pagina=pagina, por_pagina=por_pagina,
        )

    def _conferir_coerencia(self, veiculo_id: int, quilometragem: int, data_leitura: date | None,
                            digitada_em: date | None = None,
                            ignorar_id: int | None = None) -> None:
        conflitos = self._leituras.conflitos(veiculo_id, quilometragem, data_leitura,
                                             digitada_em=digitada_em, ignorar_id=ignorar_id)
        if conflitos:
            raise DadosInvalidos(
                f"Esta leitura não combina com o histórico: {_descrever(conflitos[0])}. "
                "Confira o valor e a data. Se a leitura antiga é que está errada, "
                "corrija-a no histórico de quilometragem.",
                campo="quilometragem",
            )

    def registrar(self, usuario: Usuario, veiculo_id: int, quilometragem: int | None,
                  data_leitura: date | None) -> Veiculo:
        """Nova leitura manual ("Atualizar km"). Sem data, vale o dia de hoje."""
        quilometragem = validar_quilometragem(quilometragem)
        hoje = self._hoje()
        data_leitura = data_leitura or hoje
        if data_leitura > hoje:
            raise DadosInvalidos("A data da leitura não pode ser no futuro.", campo="data_leitura")
        with self._uow.transacao():
            # Linha do veículo bloqueada: leituras simultâneas entram uma de cada vez.
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            # Envio repetido (dois toques): não cria a mesma leitura duas vezes.
            if self._leituras.buscar_igual(veiculo.id, quilometragem, data_leitura,
                                           ORIGEM_MANUAL) is None:
                self._conferir_coerencia(veiculo.id, quilometragem, data_leitura)
                self._leituras.criar(veiculo.id, quilometragem, data_leitura, ORIGEM_MANUAL)
            self._veiculos.recarregar(veiculo)
        return veiculo

    def _leitura_editavel(self, veiculo: Veiculo, leitura_id: int) -> LeituraKm:
        leitura = self._leituras.buscar(leitura_id)
        # A leitura precisa ser DESTE veículo, não basta existir.
        if leitura is None or leitura.veiculo_id != veiculo.id:
            raise NaoEncontrado("Leitura não encontrada.")
        if not leitura.valida:
            raise Conflito("Esta leitura já foi anulada.")
        if not leitura.editavel:
            origem = NOME_DA_ORIGEM.get(leitura.origem, leitura.origem)
            raise Conflito(
                f"Esta leitura veio de um registro de {origem}. "
                "Para corrigi-la, edite esse registro."
            )
        return leitura

    def _conferir_km_da_compra(self, veiculo: Veiculo) -> None:
        """Relê a quilometragem recalculada; ela não pode ficar abaixo do km da compra.

        O erro desfaz a transação inteira: nada da correção fica gravado.
        """
        self._veiculos.recarregar(veiculo)
        if veiculo.km_aquisicao is not None and veiculo.quilometragem < veiculo.km_aquisicao:
            raise DadosInvalidos(
                "A quilometragem atual ficaria menor que a da compra "
                f"({numero_br(veiculo.km_aquisicao)} km). Corrija antes os dados da compra.",
                campo="quilometragem")

    def corrigir(self, usuario: Usuario, veiculo_id: int, leitura_id: int,
                 quilometragem: int | None, motivo: str | None) -> Veiculo:
        """Substitui o valor de uma leitura digitada errada, preservando o histórico."""
        quilometragem = validar_quilometragem(quilometragem)
        motivo = _motivo(motivo)
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            leitura = self._leitura_editavel(veiculo, leitura_id)
            if leitura.quilometragem == quilometragem:
                raise DadosInvalidos("O valor informado é igual ao da leitura atual.",
                                     campo="quilometragem")
            self._conferir_coerencia(
                veiculo.id, quilometragem, leitura.data_leitura,
                digitada_em=leitura.criado_em.date() if leitura.data_leitura is None else None,
                ignorar_id=leitura.id,
            )
            # Primeiro entra a leitura certa; depois a errada é anulada.
            self._leituras.criar(veiculo.id, quilometragem, leitura.data_leitura, leitura.origem,
                                 corrige_id=leitura.id)
            self._leituras.anular(leitura, motivo or "Valor corrigido.")
            self._conferir_km_da_compra(veiculo)
        return veiculo

    def anular(self, usuario: Usuario, veiculo_id: int, leitura_id: int,
               motivo: str | None) -> Veiculo:
        """Retira uma leitura que não deveria existir (ela continua no histórico)."""
        motivo = _motivo(motivo)
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            leitura = self._leitura_editavel(veiculo, leitura_id)
            if self._leituras.contar_validas(veiculo.id) <= 1:
                raise Conflito(
                    "Esta é a única leitura válida do veículo. Em vez de anular, "
                    "corrija o valor dela."
                )
            self._leituras.anular(leitura, motivo or "Leitura anulada.")
            self._conferir_km_da_compra(veiculo)
        return veiculo
