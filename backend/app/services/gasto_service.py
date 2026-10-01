"""Regras dos gastos e do resumo financeiro do mês.

Gasto (decisões da Paula, 01/10/2026)
- Pago: entra nas despesas no mês da data do pagamento. Ao cadastrar já
  pago, a data do pagamento é obrigatória (a tela sugere a data do gasto).
  Gastos pagos antigos sem data do pagamento continuam sem ela (não se
  inventa data) e contam pela data do gasto.
- Pendente: vencimento obrigatório; não tem data de pagamento e não entra no
  total de despesas. Aparece em "Vencidas" ou "A vencer".
- O valor precisa ser maior que zero, com no máximo duas casas.

Resumo do período (mês, ano ou total desde o primeiro registro)
- Despesas efetivadas vêm da view vw_despesa: manutenções realizadas,
  abastecimentos, gastos pagos e itens de projeto (inclusive de projeto
  cancelado). Cada valor é contado uma vez, pela tabela de origem.
- Os totais são somados pelo PostgreSQL em numeric; o percentual de cada
  categoria é calculado aqui com Decimal, arredondado meio para cima para
  inteiro (por isso a soma dos percentuais pode dar 99 ou 101).
- Manutenções agendadas e gastos pendentes que vencem no período aparecem
  como "previsto", separados, e não entram no total.
"""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Protocol

from app.entities.gasto import CATEGORIAS_DE_GASTO, Despesa, Gasto
from app.entities.usuario import Usuario
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.veiculo_service import validar_dinheiro

TAMANHO_MAXIMO_DESCRICAO = 150
ANO_MINIMO, ANO_MAXIMO = 1990, 2100
CEM = Decimal(100)

VENCIDO = "vencido"
VENCE_HOJE = "vence_hoje"
A_VENCER = "a_vencer"


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class Pendente:
    gasto: Gasto
    situacao: str          # vencido | vence_hoje | a_vencer
    dias: int              # dias até o vencimento (negativo = dias de atraso)


@dataclass(frozen=True)
class TotalCategoria:
    categoria: str
    total: Decimal
    quantidade: int
    percentual: int        # do total do mês, arredondado meio para cima


PERIODO_MES = "mes"
PERIODO_ANO = "ano"
PERIODO_TOTAL = "total"


@dataclass(frozen=True)
class ResumoDoMes:
    periodo: str           # mes | ano | total
    ano: int | None
    mes: int | None
    total: Decimal
    quantidade: int
    categorias: list[TotalCategoria]
    previsto_manutencoes: Decimal
    quantidade_manutencoes_previstas: int
    previsto_gastos: Decimal
    quantidade_gastos_previstos: int


def percentual(parte: Decimal, total: Decimal) -> int:
    """Percentual inteiro, meio para cima. Total zero não tem percentual (sem divisão por zero)."""
    if total <= 0:
        return 0
    return int((parte * CEM / total).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def intervalo_do_mes(ano: int, mes: int) -> tuple[date, date]:
    """(primeiro dia, primeiro dia do mês seguinte)."""
    if not ANO_MINIMO <= ano <= ANO_MAXIMO:
        raise DadosInvalidos("Ano inválido.", campo="ano")
    if not 1 <= mes <= 12:
        raise DadosInvalidos("Mês inválido.", campo="mes")
    inicio = date(ano, mes, 1)
    fim = date(ano + 1, 1, 1) if mes == 12 else date(ano, mes + 1, 1)
    return inicio, fim


def intervalo_do_periodo(ano: int | None, mes: int | None) -> tuple[str, date | None, date | None]:
    """Sem ano nem mês: total (sem limites). Só o ano: o ano inteiro. Ano e mês: o mês."""
    if ano is None:
        if mes is not None:
            raise DadosInvalidos("Informe o ano junto com o mês.", campo="ano")
        return PERIODO_TOTAL, None, None
    if mes is None:
        if not ANO_MINIMO <= ano <= ANO_MAXIMO:
            raise DadosInvalidos("Ano inválido.", campo="ano")
        return PERIODO_ANO, date(ano, 1, 1), date(ano + 1, 1, 1)
    return (PERIODO_MES, *intervalo_do_mes(ano, mes))


class GastoService:
    def __init__(self, uow: Transacional, veiculos, gastos, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._gastos = gastos
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo_id: int, gasto_id: int) -> Gasto:
        gasto = self._gastos.buscar(gasto_id)
        # O gasto precisa ser DESTE veículo, não basta existir.
        if gasto is None or gasto.veiculo_id != veiculo_id:
            raise NaoEncontrado("Gasto não encontrado.")
        return gasto

    def _situacao(self, gasto: Gasto) -> Pendente:
        dias = (gasto.data_vencimento - self._hoje()).days
        situacao = VENCIDO if dias < 0 else VENCE_HOJE if dias == 0 else A_VENCER
        return Pendente(gasto, situacao, dias)

    # ------------------------------------------------------------------ validação
    def _validar(self, dados: dict, atual: Gasto | None) -> dict:
        hoje = self._hoje()
        categoria = dados.get("categoria")
        if categoria not in CATEGORIAS_DE_GASTO:
            raise DadosInvalidos("Escolha a categoria.", campo="categoria")
        valor = validar_dinheiro(dados.get("valor"), "valor")
        if valor is None:
            raise DadosInvalidos("Informe o valor.", campo="valor")
        if valor == 0:
            raise DadosInvalidos("O valor precisa ser maior que zero.", campo="valor")
        descricao = " ".join((dados.get("descricao") or "").split()) or None
        if descricao and len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
            raise DadosInvalidos(f"Descrição longa demais (máximo {TAMANHO_MAXIMO_DESCRICAO} caracteres).",
                                 campo="descricao")
        data = dados.get("data")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data")
        if data > hoje:
            raise DadosInvalidos("A data do gasto não pode ser no futuro. Para uma conta que ainda "
                                 "vai vencer, desligue \"Já foi pago\" e informe o vencimento.",
                                 campo="data")
        pago = bool(dados.get("pago"))
        vencimento = dados.get("data_vencimento")
        pagamento = dados.get("data_pagamento")
        if pago:
            # Gasto pago antigo, de antes da 0007, pode continuar sem a data do pagamento.
            antigo_sem_data = atual is not None and atual.pago and atual.data_pagamento is None
            if pagamento is None and not antigo_sem_data:
                raise DadosInvalidos("Informe a data do pagamento.", campo="data_pagamento")
            if pagamento is not None and pagamento > hoje:
                raise DadosInvalidos("A data do pagamento não pode ser no futuro.", campo="data_pagamento")
        else:
            if vencimento is None:
                raise DadosInvalidos("Informe o vencimento: ele faz a conta aparecer em \"A vencer\".",
                                     campo="data_vencimento")
            if pagamento is not None:
                raise DadosInvalidos("Gasto pendente não tem data de pagamento.", campo="data_pagamento")
        return {"categoria": categoria, "valor": valor, "descricao": descricao, "data": data,
                "pago": pago, "data_vencimento": vencimento, "data_pagamento": pagamento}

    # ------------------------------------------------------------------ consulta
    def obter(self, usuario: Usuario, veiculo_id: int, gasto_id: int) -> Gasto:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._do_veiculo(veiculo.id, gasto_id)

    def pendentes(self, usuario: Usuario, veiculo_id: int, pagina: int = 1,
                  por_pagina: int = 50) -> Pagina[Pendente]:
        """Gastos pendentes, do vencimento mais antigo para o mais distante."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(
            itens=[self._situacao(g) for g in self._gastos.pendentes(veiculo.id, limite, deslocamento)],
            total=self._gastos.contar_pendentes(veiculo.id), pagina=pagina, por_pagina=por_pagina,
        )

    # ------------------------------------------------------------------ gravação
    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> Gasto:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            return self._gastos.criar(veiculo.id, self._validar(dados, None))

    def editar(self, usuario: Usuario, veiculo_id: int, gasto_id: int, dados: dict) -> Gasto:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            gasto = self._do_veiculo(veiculo.id, gasto_id)
            self._gastos.atualizar(gasto, self._validar(dados, gasto))
            return gasto

    def pagar(self, usuario: Usuario, veiculo_id: int, gasto_id: int,
              data_pagamento: date | None) -> Gasto:
        """Marca um gasto pendente como pago (data padrão: hoje)."""
        data_pagamento = data_pagamento or self._hoje()
        if data_pagamento > self._hoje():
            raise DadosInvalidos("A data do pagamento não pode ser no futuro.", campo="data_pagamento")
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            gasto = self._do_veiculo(veiculo.id, gasto_id)
            if gasto.pago:
                raise Conflito("Este gasto já está pago.")
            self._gastos.atualizar(gasto, {"pago": True, "data_pagamento": data_pagamento})
            return gasto

    def apagar(self, usuario: Usuario, veiculo_id: int, gasto_id: int) -> None:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            self._gastos.apagar(self._do_veiculo(veiculo.id, gasto_id))


class FinancasService:
    def __init__(self, veiculos, financas):
        self._financas = financas
        self._acesso = AcessoVeiculo(veiculos)

    def resumo(self, usuario: Usuario, veiculo_id: int, ano: int | None = None,
               mes: int | None = None) -> ResumoDoMes:
        """Mês (ano e mês), ano (só o ano) ou total desde o primeiro registro (nenhum)."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        periodo, inicio, fim = intervalo_do_periodo(ano, mes)
        linhas = self._financas.totais_por_categoria(veiculo.id, inicio, fim)
        total = sum((t for _, t, _ in linhas), Decimal("0.00"))
        previsto = self._financas.previsto(veiculo.id, inicio, fim)
        return ResumoDoMes(
            periodo=periodo, ano=ano, mes=mes, total=total, quantidade=sum(q for _, _, q in linhas),
            categorias=[TotalCategoria(c, t, q, percentual(t, total)) for c, t, q in linhas],
            previsto_manutencoes=previsto["manutencoes"],
            quantidade_manutencoes_previstas=previsto["quantidade_manutencoes"],
            previsto_gastos=previsto["gastos"],
            quantidade_gastos_previstos=previsto["quantidade_gastos"],
        )

    def lancamentos(self, usuario: Usuario, veiculo_id: int, ano: int | None = None,
                    mes: int | None = None, pagina: int = 1,
                    por_pagina: int = 50) -> Pagina[Despesa]:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        _, inicio, fim = intervalo_do_periodo(ano, mes)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        total = sum(q for _, _, q in self._financas.totais_por_categoria(veiculo.id, inicio, fim))
        return Pagina(
            itens=self._financas.lancamentos(veiculo.id, inicio, fim, limite, deslocamento),
            total=total, pagina=pagina, por_pagina=por_pagina,
        )

