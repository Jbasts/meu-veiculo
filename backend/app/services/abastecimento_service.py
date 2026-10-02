"""Regras dos abastecimentos, do consumo e da comparação etanol × gasolina.

Litros, preço e valor total (decisões da Paula, 01/10/2026)
- Basta informar dois dos três; o backend calcula o terceiro:
    valor total     = litros × preço por litro (centavos, meio para cima:
                      38,5 × 4,29 = 165,165 → R$ 165,17)
    litros          = valor total ÷ preço por litro (3 casas, meio para cima)
    preço por litro = valor total ÷ litros (3 casas, meio para cima)
  Quando os litros ou o preço são calculados, o valor total informado (o
  que a bomba mostrou) é gravado como veio.
- Se a pessoa informar o valor do cupom, ele é gravado quando a diferença
  para o calculado é de no máximo R$ 50,00 (era R$ 0,10 na 0008; ampliado a
  pedido dela na 0009); diferença maior é recusada como provável erro de
  digitação (o banco confere a mesma regra).

Tipo do combustível (tabela da Paula, migration 0010)
- Cada combustível tem os seus tipos (gasolina comum/comum aditivada/premium/
  premium aditivada; etanol comum/aditivado/premium/premium aditivado; diesel
  S10/S10 aditivado/S500/S500 aditivado; eletricidade AC/DC). GNV não tem tipo.
- Obrigatório nos abastecimentos novos. Abastecimento antigo sem tipo pode
  continuar sem ao ser editado: o tipo não é inventado.
- Não muda o consumo: gasolina comum e premium são o mesmo combustível.

Combustível
- Só os combustíveis do tipo do veículo: flex = gasolina ou etanol; diesel =
  diesel; elétrico = eletricidade; híbrido = gasolina ou eletricidade.
- Unidade: litro; m³ no GNV; kWh na eletricidade (a coluna é a mesma
  "litros"). Num híbrido, alternar gasolina e recarga entre dois "cheios" é
  mistura: aquele ciclo fica sem consumo.

Tanque (services/tanque.py)
- nivel_antes: o marcador antes de abastecer, opcional, só para gasolina,
  etanol e diesel. Com o tamanho do tanque, ele vira ponto do cálculo de
  consumo (services/consumo.py) e confere se os litros cabem no tanque.

Hodômetro
- A quilometragem é obrigatória e vira leitura: precisa combinar com as outras
  (o hodômetro só anda para a frente). Abastecimentos antigos válidos podem
  ser lançados depois; o consumo é recalculado a cada consulta.

Etanol ou gasolina? (decisão da Paula: último preço + simulação)
- O limite vem do consumo real do carro: média do etanol / média da gasolina
  (ex.: 7,9 / 11,3 = 70%). Nunca um percentual fixo.
- Os preços são os do último abastecimento de cada um, ou os digitados para
  simular (nada é gravado). Etanol compensa quando preço do etanol / preço da
  gasolina < limite (mesmo custo por km no limite).
- Sem média dos dois combustíveis ou sem preço dos dois, não há
  recomendação: a tela diz o que falta.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Protocol

from app.entities.abastecimento import (
    COMBUSTIVEIS_COM_MARCADOR,
    COMBUSTIVEIS_DO_VEICULO,
    ETANOL,
    GASOLINA,
    TIPOS_DO_COMBUSTIVEL,
    Abastecimento,
)
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br, numero_br
from app.services.consumo import Media, MesDeConsumo, Resultado, Situacao, calcular_tudo, medias, por_mes
from app.services.erros import DadosInvalidos, NaoEncontrado
from app.services.nivel_tanque import NivelDoTanque, nivel_do_tanque
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.tanque import combustivel_inicial, conferir_se_cabe, tanque_pendente, validar_nivel
from app.services.veiculo_service import validar_quilometragem

CENTAVO = Decimal("0.01")
MILESIMO = Decimal("0.001")
TOLERANCIA_DO_CUPOM = Decimal("50.00")
LITROS_MAXIMO = Decimal("9999.999")      # NUMERIC(7,3)
PRECO_MAXIMO = Decimal("999.999")        # NUMERIC(6,3)
TAMANHO_MAXIMO_POSTO = 80
NOMES = {"gasolina": "gasolina", "etanol": "etanol", "diesel": "diesel", "gnv": "GNV",
         "eletrica": "eletricidade"}
UNIDADES = {"gnv": "a quantidade de m³", "eletrica": "a energia em kWh"}

ETANOL_COMPENSA = "etanol"
GASOLINA_COMPENSA = "gasolina"
TANTO_FAZ = "tanto_faz"


class Transacional(Protocol):
    def transacao(self): ...


def calcular_total(litros: Decimal, preco: Decimal) -> Decimal:
    """Litros × preço por litro, em centavos, meio para cima."""
    return (litros * preco).quantize(CENTAVO, rounding=ROUND_HALF_UP)


def dividir(total: Decimal, divisor: Decimal) -> Decimal:
    """Valor total ÷ preço (= litros) ou ÷ litros (= preço), com 3 casas, meio para cima."""
    return (total / divisor).quantize(MILESIMO, rounding=ROUND_HALF_UP)


def percentual(valor: Decimal) -> int:
    return int((valor * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _decimal(valor: Decimal | None, campo: str, rotulo: str, maximo: Decimal, casas: Decimal) -> Decimal:
    if valor is None:
        raise DadosInvalidos(f"Informe {rotulo}.", campo=campo)
    if not valor.is_finite() or valor <= 0:
        raise DadosInvalidos(f"{rotulo[0].upper()}{rotulo[1:]} precisa ser maior que zero.", campo=campo)
    if valor != valor.quantize(casas):
        raise DadosInvalidos(f"Use no máximo {len(str(casas)) - 2} casas decimais.", campo=campo)
    if valor > maximo:
        raise DadosInvalidos(f"Valor alto demais para {rotulo}.", campo=campo)
    return valor.quantize(casas)


@dataclass(frozen=True)
class AbastecimentoDetalhe:
    abastecimento: Abastecimento
    situacao: Situacao


@dataclass(frozen=True)
class Comparacao:
    recomendacao: str | None        # etanol | gasolina | tanto_faz | None (sem dados)
    motivo: str | None              # o que falta, quando não há recomendação
    limite_percentual: int | None   # até quanto o etanol compensa (do consumo do carro)
    relacao_percentual: int | None  # preço do etanol / preço da gasolina
    preco_gasolina: Decimal | None
    preco_etanol: Decimal | None
    precos_simulados: bool


@dataclass(frozen=True)
class ResumoCombustivel:
    combustiveis: tuple[str, ...]   # os que o veículo aceita
    medias: list[Media]
    comparacao: Comparacao | None   # só para veículo flex
    postos_recentes: list[str]
    ultima_quilometragem: int
    capacidade_tanque: Decimal | None
    tanque_pendente: bool           # tem tanque, mas falta o tamanho no cadastro
    marcacao_do_mes_pendente: bool  # ainda não marcou o km e o nível neste mês
    meses: list[MesDeConsumo]       # do mais recente para o mais antigo (até 12)
    nivel_tanque: NivelDoTanque     # último nível conhecido e estimativa de agora


MESES_NO_RESUMO = 12


def calcular_do_veiculo(veiculo: Veiculo, abastecimentos: list, medicoes: list) -> Resultado:
    """O cálculo de consumo com tudo o que se sabe do veículo (tanque e marcações)."""
    return calcular_tudo(abastecimentos, medicoes, veiculo.capacidade_tanque,
                         combustivel_inicial(veiculo.tipo_combustivel))


class AbastecimentoService:
    def __init__(self, uow: Transacional, veiculos, abastecimentos, leituras, medicoes, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._abastecimentos = abastecimentos
        self._leituras = leituras
        self._medicoes = medicoes
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo_id: int, abastecimento_id: int) -> Abastecimento:
        a = self._abastecimentos.buscar(abastecimento_id)
        # O abastecimento precisa ser DESTE veículo, não basta existir.
        if a is None or a.veiculo_id != veiculo_id:
            raise NaoEncontrado("Abastecimento não encontrado.")
        return a

    def _situacoes(self, veiculo: Veiculo) -> tuple[list[Abastecimento], dict[int, Situacao], list]:
        todos = self._abastecimentos.todos(veiculo.id)
        r = calcular_do_veiculo(veiculo, todos, self._medicoes.todas(veiculo.id))
        return todos, r.situacoes, r.ciclos

    # ------------------------------------------------------------------ validação
    def _validar(self, veiculo: Veiculo, dados: dict, atual: Abastecimento | None) -> dict:
        aceitos = COMBUSTIVEIS_DO_VEICULO.get(veiculo.tipo_combustivel, ())
        combustivel = dados.get("combustivel")
        if combustivel not in aceitos:
            opcoes = " ou ".join(NOMES[c] for c in aceitos)
            raise DadosInvalidos(f"Este veículo usa {opcoes}.", campo="combustivel")
        tipo = dados.get("tipo")
        tipos = TIPOS_DO_COMBUSTIVEL[combustivel]
        if not tipos:
            if tipo is not None:
                raise DadosInvalidos("GNV não tem tipo.", campo="tipo")
        elif tipo is None:
            antigo_sem_tipo = atual is not None and atual.tipo is None
            if not antigo_sem_tipo:
                raise DadosInvalidos(f"Escolha o tipo de {NOMES[combustivel]}.", campo="tipo")
        elif tipo not in tipos:
            raise DadosInvalidos(f"Tipo inválido para {NOMES[combustivel]}.", campo="tipo")
        data = dados.get("data")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data")
        if data > self._hoje():
            raise DadosInvalidos("A data não pode ser no futuro.", campo="data")
        km = validar_quilometragem(dados.get("quilometragem"))
        litros, preco, total = self._litros_preco_e_total(combustivel, dados)
        nivel = validar_nivel(dados.get("nivel_antes"), "nivel_antes", obrigatorio=False)
        if nivel is not None and combustivel not in COMBUSTIVEIS_COM_MARCADOR:
            raise DadosInvalidos("O nível do marcador é só do tanque de combustível líquido, não de "
                                 f"{NOMES[combustivel]}.", campo="nivel_antes")
        if combustivel in COMBUSTIVEIS_COM_MARCADOR:
            conferir_se_cabe(veiculo.capacidade_tanque, litros, nivel)
        posto = " ".join((dados.get("posto") or "").split()) or None
        if posto and len(posto) > TAMANHO_MAXIMO_POSTO:
            raise DadosInvalidos(f"Nome do posto longo demais (máximo {TAMANHO_MAXIMO_POSTO} caracteres).",
                                 campo="posto")
        self._conferir_hodometro(veiculo, km, data, atual)
        return {"combustivel": combustivel, "tipo": tipo, "data": data, "quilometragem": km, "litros": litros,
                "valor_litro": preco, "valor_total": total, "tanque_cheio": bool(dados.get("tanque_cheio")),
                "nivel_antes": nivel, "posto": posto}

    @staticmethod
    def _litros_preco_e_total(combustivel: str, dados: dict) -> tuple[Decimal, Decimal, Decimal]:
        """Dois dos três bastam; o terceiro é calculado (veja o topo do arquivo)."""
        unidade = UNIDADES.get(combustivel, "os litros")
        informado = dados.get("valor_total")
        if informado is not None:
            if not informado.is_finite() or informado != informado.quantize(CENTAVO):
                raise DadosInvalidos("Use no máximo duas casas decimais (centavos).", campo="valor_total")
            if informado <= 0:
                raise DadosInvalidos("O valor total precisa ser maior que zero.", campo="valor_total")
        tem_litros = dados.get("litros") is not None
        tem_preco = dados.get("valor_litro") is not None
        if informado is not None and not (tem_litros and tem_preco):
            if not tem_litros and not tem_preco:
                raise DadosInvalidos(f"Informe o preço ou {unidade}.", campo="valor_litro")
            if tem_preco:
                preco = _decimal(dados.get("valor_litro"), "valor_litro", "o preço", PRECO_MAXIMO, MILESIMO)
                litros = dividir(informado, preco)
                if litros <= 0:
                    raise DadosInvalidos("Valor total baixo demais para este preço.", campo="valor_total")
                _decimal(litros, "litros", unidade, LITROS_MAXIMO, MILESIMO)
            else:
                litros = _decimal(dados.get("litros"), "litros", unidade, LITROS_MAXIMO, MILESIMO)
                preco = dividir(informado, litros)
                if preco <= 0:
                    raise DadosInvalidos("Valor total baixo demais para esta quantidade.", campo="valor_total")
                _decimal(preco, "valor_litro", "o preço", PRECO_MAXIMO, MILESIMO)
            return litros, preco, informado
        litros = _decimal(dados.get("litros"), "litros", unidade, LITROS_MAXIMO, MILESIMO)
        preco = _decimal(dados.get("valor_litro"), "valor_litro", "o preço", PRECO_MAXIMO, MILESIMO)
        calculado = calcular_total(litros, preco)
        if informado is None:
            return litros, preco, calculado
        if abs(informado - calculado) > TOLERANCIA_DO_CUPOM:
            raise DadosInvalidos(
                f"O valor do cupom difere mais de R$ 50,00 do calculado (R$ {calculado}). "
                "Confira os litros e o preço.", campo="valor_total")
        return litros, preco, informado

    def _conferir_hodometro(self, veiculo: Veiculo, km: int, data: date, atual: Abastecimento | None) -> None:
        conflitos = self._leituras.conflitos(
            veiculo.id, km, data, ignorar_origem=("abastecimento", atual.id) if atual else None)
        if conflitos:
            outra = conflitos[0]
            quando = f"em {data_br(outra.data_leitura)}" if outra.data_leitura else "numa leitura antiga sem data"
            raise DadosInvalidos(
                f"Esta quilometragem não combina com o histórico: {quando} o hodômetro marcava "
                f"{numero_br(outra.quilometragem)} km. Confira o valor e a data.", campo="quilometragem")

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, pagina: int = 1,
               por_pagina: int = 30) -> Pagina[AbastecimentoDetalhe]:
        """Do mais recente para o mais antigo, cada um com a situação no cálculo do consumo."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        todos, situacoes, _ = self._situacoes(veiculo)
        recentes = list(reversed(todos))[deslocamento:deslocamento + limite]
        return Pagina(itens=[AbastecimentoDetalhe(a, situacoes[a.id]) for a in recentes],
                      total=len(todos), pagina=pagina, por_pagina=por_pagina)

    def obter(self, usuario: Usuario, veiculo_id: int, abastecimento_id: int) -> AbastecimentoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        a = self._do_veiculo(veiculo.id, abastecimento_id)
        _, situacoes, _ = self._situacoes(veiculo)
        return AbastecimentoDetalhe(a, situacoes[a.id])

    def resumo(self, usuario: Usuario, veiculo_id: int, preco_gasolina: Decimal | None = None,
               preco_etanol: Decimal | None = None) -> ResumoCombustivel:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if (preco_gasolina is None) != (preco_etanol is None):
            raise DadosInvalidos("Para simular, informe os dois preços.", campo="preco_etanol")
        simulado = preco_gasolina is not None
        if simulado:
            preco_gasolina = _decimal(preco_gasolina, "preco_gasolina", "o preço da gasolina", PRECO_MAXIMO, MILESIMO)
            preco_etanol = _decimal(preco_etanol, "preco_etanol", "o preço do etanol", PRECO_MAXIMO, MILESIMO)
        todos, _, ciclos = self._situacoes(veiculo)
        por_combustivel = medias(ciclos)
        aceitos = COMBUSTIVEIS_DO_VEICULO.get(veiculo.tipo_combustivel, ())
        comparacao = None
        if set(aceitos) >= {GASOLINA, ETANOL}:
            if not simulado:
                ultimos = {a.combustivel: a.valor_litro for a in todos}  # o último de cada um fica
                preco_gasolina, preco_etanol = ultimos.get(GASOLINA), ultimos.get(ETANOL)
            comparacao = self._comparar(por_combustivel.get(GASOLINA), por_combustivel.get(ETANOL),
                                        preco_gasolina, preco_etanol, simulado)
        return ResumoCombustivel(
            combustiveis=aceitos,
            medias=sorted(por_combustivel.values(), key=lambda m: aceitos.index(m.combustivel)
                          if m.combustivel in aceitos else 99),
            comparacao=comparacao,
            postos_recentes=self._abastecimentos.postos_recentes(veiculo.id),
            ultima_quilometragem=veiculo.quilometragem,
            capacidade_tanque=veiculo.capacidade_tanque,
            tanque_pendente=tanque_pendente(veiculo),
            marcacao_do_mes_pendente=(
                veiculo.ativo and veiculo.capacidade_tanque is not None
                and not self._medicoes.existe_desde(veiculo.id, self._hoje().replace(day=1))),
            meses=por_mes(ciclos)[:MESES_NO_RESUMO],
            nivel_tanque=nivel_do_tanque(veiculo, todos, self._medicoes.todas(veiculo.id), por_combustivel),
        )

    @staticmethod
    def _comparar(gasolina: Media | None, etanol: Media | None, preco_gasolina: Decimal | None,
                  preco_etanol: Decimal | None, simulado: bool) -> Comparacao:
        faltam = [nome for nome, m in (("gasolina", gasolina), ("etanol", etanol)) if m is None]
        if faltam:
            return Comparacao(None, (
                "Ainda não dá para comparar: falta o consumo de " + " e de ".join(faltam)
                + ". Registre pelo menos dois abastecimentos de tanque cheio de cada combustível."),
                None, None, preco_gasolina, preco_etanol, simulado)
        limite = etanol.exata / gasolina.exata
        if preco_gasolina is None or preco_etanol is None:
            return Comparacao(None, "Ainda não há preço registrado dos dois combustíveis.",
                              percentual(limite), None, preco_gasolina, preco_etanol, simulado)
        relacao = preco_etanol / preco_gasolina
        recomendacao = (ETANOL_COMPENSA if relacao < limite
                        else GASOLINA_COMPENSA if relacao > limite else TANTO_FAZ)
        return Comparacao(recomendacao, None, percentual(limite), percentual(relacao),
                          preco_gasolina, preco_etanol, simulado)

    # ------------------------------------------------------------------ gravação
    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> AbastecimentoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            a = self._abastecimentos.criar(veiculo.id, self._validar(veiculo, dados, None))
            self._veiculos.recarregar(veiculo)  # a quilometragem pode ter mudado
            _, situacoes, _ = self._situacoes(veiculo)
        return AbastecimentoDetalhe(a, situacoes[a.id])

    def editar(self, usuario: Usuario, veiculo_id: int, abastecimento_id: int,
               dados: dict) -> AbastecimentoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            a = self._do_veiculo(veiculo.id, abastecimento_id)
            self._abastecimentos.atualizar(a, self._validar(veiculo, dados, a))
            self._veiculos.recarregar(veiculo)
            _, situacoes, _ = self._situacoes(veiculo)
        return AbastecimentoDetalhe(a, situacoes[a.id])

    def apagar(self, usuario: Usuario, veiculo_id: int, abastecimento_id: int) -> None:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            self._abastecimentos.apagar(self._do_veiculo(veiculo.id, abastecimento_id))
