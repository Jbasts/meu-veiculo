"""Regras do tanque de combustível líquido (pedido da Paula, 01/10/2026).

Tamanho do tanque
- Obrigatório no cadastro e na edição de veículos com combustível líquido
  (todos, menos o elétrico). Veículos antigos sem o tamanho continuam
  funcionando, mas as telas pedem para informar.
- Litros com uma casa decimal, até 2.000 L.

Nível do marcador
- Em oitavos do tanque: 0 = vazio, 2 = 1/4, 3 = "1,5/4", 4 = meio, 8 = cheio.

Quanto cabe ao abastecer (para não passar do limite do tanque)
- Sem o nível: até o tamanho do tanque + 10% (o tanque real costuma levar um
  pouco mais que o número do manual, contando o bocal).
- Com o nível: o espaço livre pelo marcador + 1/8 do tanque de folga (a
  leitura do marcador não é exata), sem passar do limite acima.
- Litros acima disso são recusados como provável erro de digitação.
"""

from decimal import ROUND_HALF_UP, Decimal

from app.entities.abastecimento import COMBUSTIVEIS_DO_VEICULO, COMBUSTIVEIS_COM_MARCADOR
from app.entities.medicao_tanque import OITAVOS_DO_TANQUE
from app.entities.veiculo import Veiculo
from app.services.erros import DadosInvalidos

CAPACIDADE_MAXIMA = Decimal("2000.0")
UM_DECIMO = Decimal("0.1")
FOLGA_SEM_NIVEL = Decimal("1.10")
NOMES_DO_NIVEL = {0: "vazio", 1: "0,5/4", 2: "1/4", 3: "1,5/4", 4: "2/4 (meio)", 5: "2,5/4", 6: "3/4",
                  7: "3,5/4", 8: "cheio"}


def tem_tanque(tipo_combustivel: str) -> bool:
    """Só o elétrico não tem tanque de combustível líquido."""
    return any(c in COMBUSTIVEIS_COM_MARCADOR for c in COMBUSTIVEIS_DO_VEICULO.get(tipo_combustivel, ()))


def tanque_pendente(veiculo: Veiculo) -> bool:
    """Veículo com tanque, mas sem o tamanho no cadastro (veículos antigos)."""
    return tem_tanque(veiculo.tipo_combustivel) and veiculo.capacidade_tanque is None


def combustivel_inicial(tipo_combustivel: str) -> str | None:
    """O combustível do tanque quando o veículo só usa um combustível líquido."""
    liquidos = [c for c in COMBUSTIVEIS_DO_VEICULO.get(tipo_combustivel, ()) if c in COMBUSTIVEIS_COM_MARCADOR]
    return liquidos[0] if len(liquidos) == 1 else None


def nivel_br(nivel: int) -> str:
    return NOMES_DO_NIVEL[nivel]


def litros_br(valor: Decimal) -> str:
    """37.5 -> "37,5"; 50.0 -> "50" (para mensagens)."""
    texto = f"{valor.quantize(UM_DECIMO, rounding=ROUND_HALF_UP):f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def validar_nivel(valor: int | None, campo: str, obrigatorio: bool) -> int | None:
    if valor is None:
        if obrigatorio:
            raise DadosInvalidos("Escolha o nível do marcador.", campo=campo)
        return None
    if not 0 <= valor <= OITAVOS_DO_TANQUE:
        raise DadosInvalidos("Nível inválido: use de vazio (0) a cheio (8 oitavos).", campo=campo)
    return valor


def validar_capacidade(valor: Decimal | None, tipo_combustivel: str) -> Decimal | None:
    if not tem_tanque(tipo_combustivel):
        return None  # elétrico: não tem tanque (o valor enviado é descartado)
    if valor is None:
        raise DadosInvalidos("Informe o tamanho do tanque em litros (está no manual do veículo).",
                             campo="capacidade_tanque")
    if not valor.is_finite() or valor <= 0:
        raise DadosInvalidos("O tamanho do tanque precisa ser maior que zero.", campo="capacidade_tanque")
    if valor != valor.quantize(UM_DECIMO):
        raise DadosInvalidos("Use no máximo uma casa decimal. Exemplo: 47,5.", campo="capacidade_tanque")
    if valor > CAPACIDADE_MAXIMA:
        raise DadosInvalidos("Tamanho do tanque alto demais (máximo 2.000 L).", campo="capacidade_tanque")
    return valor.quantize(UM_DECIMO)


def conferir_se_cabe(capacidade: Decimal | None, litros: Decimal, nivel: int | None) -> None:
    """Recusa litros que não cabem no tanque (veja as regras no topo)."""
    if capacidade is None:
        return
    limite = capacidade * FOLGA_SEM_NIVEL
    if nivel is not None:
        livre = capacidade * (OITAVOS_DO_TANQUE - nivel) / OITAVOS_DO_TANQUE
        limite = min(limite, livre + capacidade / OITAVOS_DO_TANQUE)
    if litros <= limite:
        return
    if nivel is None:
        raise DadosInvalidos(
            f"{litros_br(litros)} L não cabem no tanque de {litros_br(capacidade)} L deste veículo. "
            "Confira os litros (ou o valor total e o preço) ou o tamanho do tanque no cadastro.",
            campo="litros")
    raise DadosInvalidos(
        f"Com o marcador em {nivel_br(nivel)}, cabem cerca de {litros_br(livre)} L no tanque de "
        f"{litros_br(capacidade)} L; {litros_br(litros)} L não cabem. Confira os litros (ou o valor total "
        "e o preço), o nível ou o tamanho do tanque no cadastro.", campo="litros")
