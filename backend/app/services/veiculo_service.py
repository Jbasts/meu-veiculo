"""Regras dos veículos: cadastro, edição, listagem, veículo em uso e inativação.

- Cada usuário pode ter vários veículos. A placa é única POR DONO (duas
  pessoas podem cadastrar a mesma placa; a mesma pessoa, não).
- A placa é guardada em maiúsculas, sem hífen e sem espaços.
- O dono do veículo é sempre quem está logado: o cadastro não aceita
  usuario_id vindo da tela.
- Um veículo nunca é apagado pela API: ele é inativado e todo o histórico
  continua consultável. Inativo fica somente para leitura até ser reativado.
- A quilometragem só entra no cadastro. Depois, muda por leituras
  (quilometragem_service.py), nunca pela edição do veículo.
- O tamanho do tanque é obrigatório no cadastro e na edição (menos no
  elétrico, que não tem tanque); veja services/tanque.py.
"""

import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Protocol

from app.entities.usuario import Usuario
from app.entities.veiculo import COMBUSTIVEIS, Veiculo
from app.repositories.erros import PlacaJaCadastrada
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import numero_br
from app.services.erros import Conflito, DadosInvalidos
from app.services.tanque import validar_capacidade

KM_MAXIMO = 9_999_999
VALOR_MAXIMO = Decimal("9999999999.99")
ANO_MINIMO = 1900
# Placa antiga (ABC1234) ou Mercosul (ABC1D23), já sem hífen.
FORMATO_PLACA = re.compile(r"^[A-Z]{3}[0-9][A-Z0-9][0-9]{2}$")


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class VeiculoDetalhe:
    veiculo: Veiculo
    em_uso: bool
    foto_capa_id: int | None


def normalizar_placa(texto: str) -> str:
    """ "abc-1234" e "ABC 1234" viram "ABC1234"."""
    return re.sub(r"[\s-]", "", texto or "").upper()


def _texto(valor: str | None, campo: str, rotulo: str, maximo: int, obrigatorio: bool) -> str | None:
    limpo = " ".join((valor or "").split())
    if not limpo:
        if obrigatorio:
            raise DadosInvalidos(f"Informe {rotulo}.", campo=campo)
        return None
    if len(limpo) > maximo:
        raise DadosInvalidos(f"Texto longo demais (máximo {maximo} caracteres).", campo=campo)
    return limpo


def validar_quilometragem(valor: int | None, campo: str = "quilometragem") -> int:
    if valor is None:
        raise DadosInvalidos("Informe a quilometragem.", campo=campo)
    if valor < 0:
        raise DadosInvalidos("A quilometragem não pode ser negativa.", campo=campo)
    if valor > KM_MAXIMO:
        raise DadosInvalidos(f"Quilometragem alta demais (máximo {numero_br(KM_MAXIMO)} km).",
                             campo=campo)
    return valor


def validar_dinheiro(valor: Decimal | None, campo: str) -> Decimal | None:
    """Dinheiro é Decimal com no máximo 2 casas. Nada é arredondado em silêncio."""
    if valor is None:
        return None
    if not valor.is_finite():
        raise DadosInvalidos("Valor inválido.", campo=campo)
    if valor < 0:
        raise DadosInvalidos("O valor não pode ser negativo.", campo=campo)
    if valor != valor.quantize(Decimal("0.01")):
        raise DadosInvalidos("Use no máximo duas casas decimais (centavos).", campo=campo)
    if valor > VALOR_MAXIMO:
        raise DadosInvalidos("Valor alto demais.", campo=campo)
    return valor.quantize(Decimal("0.01"))


class VeiculoService:
    def __init__(self, uow: Transacional, veiculos, fotos, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._fotos = fotos
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario) -> list[VeiculoDetalhe]:
        """Os veículos de quem está logado (ativos primeiro)."""
        veiculos = self._veiculos.listar_do_usuario(usuario.id)
        capas = self._fotos.capas([v.id for v in veiculos])
        em_uso = self._id_em_uso(usuario, veiculos)
        return [VeiculoDetalhe(v, v.id == em_uso, capas.get(v.id)) for v in veiculos]

    def obter(self, usuario: Usuario, veiculo_id: int) -> VeiculoDetalhe:
        return self._detalhar(usuario, self._acesso.exigir(usuario, veiculo_id))

    def _id_em_uso(self, usuario: Usuario, veiculos: list[Veiculo]) -> int | None:
        """O veículo escolhido, se ainda estiver ativo; senão, o ativo mais recente."""
        ativos = [v.id for v in veiculos if v.ativo]
        if usuario.veiculo_em_uso_id in ativos:
            return usuario.veiculo_em_uso_id
        return ativos[0] if ativos else None

    def _detalhar(self, usuario: Usuario, veiculo: Veiculo) -> VeiculoDetalhe:
        em_uso = False
        if veiculo.usuario_id == usuario.id:
            proprios = self._veiculos.listar_do_usuario(usuario.id)
            em_uso = self._id_em_uso(usuario, proprios) == veiculo.id
        return VeiculoDetalhe(veiculo, em_uso, self._fotos.capas([veiculo.id]).get(veiculo.id))

    # ----------------------------------------------------------------- validação
    def _validar(self, dados: dict, *, km_atual: int, placa_atual: str | None) -> dict:
        hoje = self._hoje()
        limpos = {
            "marca": _texto(dados.get("marca"), "marca", "a marca", 60, True),
            "modelo": _texto(dados.get("modelo"), "modelo", "o modelo", 80, True),
            "versao": _texto(dados.get("versao"), "versao", "a versão", 80, False),
            "cor": _texto(dados.get("cor"), "cor", "a cor", 40, False),
        }

        ano = dados.get("ano")
        if ano is None or not ANO_MINIMO <= ano <= hoje.year + 1:
            raise DadosInvalidos(f"Informe um ano entre {ANO_MINIMO} e {hoje.year + 1}.", campo="ano")
        limpos["ano"] = ano

        placa = normalizar_placa(dados.get("placa") or "")
        if not placa:
            raise DadosInvalidos("Informe a placa.", campo="placa")
        # Placa antiga que não foi alterada continua aceita como está.
        if placa != placa_atual and not FORMATO_PLACA.match(placa):
            raise DadosInvalidos("Placa inválida. Use o formato ABC-1234 ou ABC1D23.", campo="placa")
        limpos["placa"] = placa

        combustivel = dados.get("tipo_combustivel")
        if combustivel not in COMBUSTIVEIS:
            raise DadosInvalidos("Escolha o combustível.", campo="tipo_combustivel")
        limpos["tipo_combustivel"] = combustivel
        limpos["capacidade_tanque"] = validar_capacidade(dados.get("capacidade_tanque"), combustivel)

        data_aquisicao = dados.get("data_aquisicao")
        if data_aquisicao is not None and data_aquisicao > hoje:
            raise DadosInvalidos("A data da compra não pode ser no futuro.", campo="data_aquisicao")
        limpos["data_aquisicao"] = data_aquisicao

        limpos["valor_aquisicao"] = validar_dinheiro(dados.get("valor_aquisicao"), "valor_aquisicao")

        km_aquisicao = dados.get("km_aquisicao")
        if km_aquisicao is not None:
            validar_quilometragem(km_aquisicao, "km_aquisicao")
            if km_aquisicao > km_atual:
                raise DadosInvalidos(
                    "A quilometragem na compra não pode ser maior que a atual "
                    f"({numero_br(km_atual)} km).", campo="km_aquisicao")
        limpos["km_aquisicao"] = km_aquisicao
        return limpos

    # ------------------------------------------------------------------ gravação
    def cadastrar(self, usuario: Usuario, dados: dict) -> VeiculoDetalhe:
        """Cria o veículo para quem está logado e já o deixa como veículo em uso."""
        km = validar_quilometragem(dados.get("quilometragem"))
        limpos = self._validar(dados, km_atual=km, placa_atual=None)
        limpos["quilometragem"] = km
        with self._uow.transacao():
            try:
                veiculo = self._veiculos.criar(usuario.id, limpos)
            except PlacaJaCadastrada:
                raise self._placa_repetida() from None
            self._veiculos.definir_em_uso(usuario, veiculo.id)
        return VeiculoDetalhe(veiculo, True, None)

    def editar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> VeiculoDetalhe:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        limpos = self._validar(dados, km_atual=veiculo.quilometragem, placa_atual=veiculo.placa)
        with self._uow.transacao():
            try:
                self._veiculos.atualizar(veiculo, limpos)
            except PlacaJaCadastrada:
                raise self._placa_repetida() from None
        return self._detalhar(usuario, veiculo)

    @staticmethod
    def _placa_repetida() -> Conflito:
        return Conflito("Já existe um veículo com esta placa nesta conta.", campo="placa")

    def selecionar(self, usuario: Usuario, veiculo_id: int) -> VeiculoDetalhe:
        """Define o veículo em uso. Só vale para veículo próprio e ativo."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if veiculo.usuario_id != usuario.id:
            raise Conflito("Só o dono pode escolher este veículo como veículo em uso.")
        if not veiculo.ativo:
            raise Conflito("Este veículo está inativo. Reative-o para usá-lo.")
        with self._uow.transacao():
            self._veiculos.definir_em_uso(usuario, veiculo.id)
        return VeiculoDetalhe(veiculo, True, self._fotos.capas([veiculo.id]).get(veiculo.id))

    def inativar(self, usuario: Usuario, veiculo_id: int) -> VeiculoDetalhe:
        """Tira o veículo de uso (vendido, por exemplo). Nada é apagado."""
        return self._definir_ativo(usuario, veiculo_id, False)

    def reativar(self, usuario: Usuario, veiculo_id: int) -> VeiculoDetalhe:
        return self._definir_ativo(usuario, veiculo_id, True)

    def _definir_ativo(self, usuario: Usuario, veiculo_id: int, ativo: bool) -> VeiculoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if veiculo.ativo != ativo:
            with self._uow.transacao():
                self._veiculos.definir_ativo(veiculo, ativo)
        return self._detalhar(usuario, veiculo)
