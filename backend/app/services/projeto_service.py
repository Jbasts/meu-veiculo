"""Regras dos projetos de melhoria, dos gastos do projeto e do orçamento.

Situação
- planejado -> em andamento ("Iniciar") -> concluído ("Marcar como concluído",
  com data; padrão hoje). Planejado ou em andamento podem ser cancelados.
- Reabrir (concluído ou cancelado) volta para em andamento e apaga a data de
  conclusão; os gastos e as fotos (inclusive as de depois) continuam.
- Gastos só podem ser incluídos, editados ou apagados com o projeto planejado
  ou em andamento: para mexer num concluído ou cancelado, reabra. Assim o total
  de um projeto encerrado não muda sem querer.
- Cancelar não apaga os gastos: o que foi gasto continua nas despesas.
  Apagar o projeto apaga os gastos (saem das despesas) e as fotos dele.

Orçamento
- Gasto = soma dos itens (Decimal, somada pelo banco).
- Percentual = gasto / orçamento, inteiro meio para cima; sem orçamento ou
  orçamento zero não há percentual (sem divisão por zero).
- Diferença = orçamento − gasto: positiva é "restam", negativa é "excedido".
  Com orçamento zero, todo gasto é excedente; sem orçamento, não há diferença.

Fotos de antes e depois (decisões da Paula, 01/10/2026)
- Várias de cada; o cartão mostra a primeira (a mais antiga) de cada momento.
- A foto de depois pode ser enviada a qualquer momento ("Ao concluir" é dica).
"""

from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Callable, Protocol

from app.entities.projeto import (
    ANTES,
    CANCELADO,
    CATEGORIAS,
    CONCLUIDO,
    DEPOIS,
    EM_ANDAMENTO,
    PLANEJADO,
    STATUS,
    STATUS_ABERTOS,
    Projeto,
    ProjetoItem,
)
from app.entities.usuario import Usuario
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.veiculo_service import validar_dinheiro

FILTROS = ("todos", *STATUS)
TAMANHO_MAXIMO_NOME = 120
TAMANHO_MAXIMO_ITEM = 150
TAMANHO_MAXIMO_DESCRICAO = 2000
ZERO = Decimal("0.00")


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class Orcamento:
    gasto: Decimal
    orcamento: Decimal | None
    percentual: int | None      # gasto / orçamento; None sem orçamento ou com orçamento zero
    diferenca: Decimal | None   # orçamento − gasto (negativa = excedido); None sem orçamento


@dataclass(frozen=True)
class ProjetoResumo:
    projeto: Projeto
    orcamento: Orcamento
    quantidade_itens: int
    foto_antes_id: int | None
    foto_depois_id: int | None


@dataclass(frozen=True)
class ProjetoDetalhe(ProjetoResumo):
    itens: list[ProjetoItem] = field(default_factory=list)
    fotos_antes: list[int] = field(default_factory=list)
    fotos_depois: list[int] = field(default_factory=list)
    total_fotos: int = 0


def calcular_orcamento(gasto: Decimal, orcamento: Decimal | None) -> Orcamento:
    if orcamento is None:
        return Orcamento(gasto, None, None, None)
    percentual = None
    if orcamento > 0:
        percentual = int((gasto * 100 / orcamento).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    return Orcamento(gasto, orcamento, percentual, orcamento - gasto)


def _texto(valor: str | None, campo: str, maximo: int, obrigatorio: str | None = None) -> str | None:
    limpo = " ".join((valor or "").split())
    if not limpo:
        if obrigatorio:
            raise DadosInvalidos(obrigatorio, campo=campo)
        return None
    if len(limpo) > maximo:
        raise DadosInvalidos(f"Texto longo demais (máximo {maximo} caracteres).", campo=campo)
    return limpo


class ProjetoService:
    def __init__(self, uow: Transacional, veiculos, projetos, arquivos, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._projetos = projetos
        self._arquivos = arquivos
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo_id: int, projeto_id: int) -> Projeto:
        projeto = self._projetos.buscar(projeto_id)
        # O projeto precisa ser DESTE veículo, não basta existir.
        if projeto is None or projeto.veiculo_id != veiculo_id:
            raise NaoEncontrado("Projeto não encontrado.")
        return projeto

    def _item_do_projeto(self, projeto: Projeto, item_id: int) -> ProjetoItem:
        item = self._projetos.buscar_item(item_id)
        # O gasto precisa ser DESTE projeto.
        if item is None or item.projeto_id != projeto.id:
            raise NaoEncontrado("Gasto do projeto não encontrado.")
        return item

    def _resumos(self, projetos: list[Projeto]) -> list[ProjetoResumo]:
        ids = [p.id for p in projetos]
        totais = self._projetos.totais(ids)
        fotos = self._projetos.fotos_de_antes_e_depois(ids)
        resumos = []
        for p in projetos:
            gasto, n = totais.get(p.id, (ZERO, 0))
            f = fotos.get(p.id, {ANTES: [], DEPOIS: []})
            resumos.append(ProjetoResumo(p, calcular_orcamento(gasto, p.orcamento), n,
                                         (f[ANTES] or [None])[0], (f[DEPOIS] or [None])[0]))
        return resumos

    def _detalhar(self, projeto: Projeto) -> ProjetoDetalhe:
        itens = self._projetos.itens(projeto.id)
        gasto = sum((i.valor for i in itens), ZERO)
        f = self._projetos.fotos_de_antes_e_depois([projeto.id]).get(projeto.id, {ANTES: [], DEPOIS: []})
        return ProjetoDetalhe(
            projeto=projeto, orcamento=calcular_orcamento(gasto, projeto.orcamento),
            quantidade_itens=len(itens), foto_antes_id=(f[ANTES] or [None])[0],
            foto_depois_id=(f[DEPOIS] or [None])[0], itens=itens, fotos_antes=f[ANTES],
            fotos_depois=f[DEPOIS], total_fotos=self._projetos.contar_fotos(projeto.id))

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, filtro: str = "todos", pagina: int = 1,
               por_pagina: int = 20) -> tuple[Pagina[ProjetoResumo], dict[str, int]]:
        """A página pedida e a quantidade de projetos em cada situação (para os filtros)."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if filtro not in FILTROS:
            raise DadosInvalidos("Filtro de projetos inválido.", campo="filtro")
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        projetos = self._projetos.listar(veiculo.id, filtro, limite, deslocamento)
        contagem = self._projetos.contar_por_status(veiculo.id)
        return (Pagina(itens=self._resumos(projetos), total=self._projetos.contar(veiculo.id, filtro),
                       pagina=pagina, por_pagina=por_pagina),
                {s: contagem.get(s, 0) for s in STATUS})

    def obter(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> ProjetoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._detalhar(self._do_veiculo(veiculo.id, projeto_id))

    # ------------------------------------------------------------------ projetos
    def _validar(self, dados: dict) -> dict:
        categoria = dados.get("categoria")
        if categoria not in CATEGORIAS:
            raise DadosInvalidos("Escolha a categoria.", campo="categoria")
        descricao = (dados.get("descricao") or "").strip() or None  # mantém as quebras de linha
        if descricao and len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
            raise DadosInvalidos(f"Texto longo demais (máximo {TAMANHO_MAXIMO_DESCRICAO} caracteres).",
                                 campo="descricao")
        return {
            "nome": _texto(dados.get("nome"), "nome", TAMANHO_MAXIMO_NOME, "Dê um nome ao projeto."),
            "descricao": descricao,
            "categoria": categoria,
            "orcamento": validar_dinheiro(dados.get("orcamento"), "orcamento"),
            "data_prevista": dados.get("data_prevista"),
        }

    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> ProjetoDetalhe:
        status = dados.get("status") or PLANEJADO
        if status not in STATUS_ABERTOS:
            raise DadosInvalidos("Um projeto novo começa planejado ou em andamento.", campo="status")
        limpos = self._validar(dados)
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            projeto = self._projetos.criar(veiculo.id, {**limpos, "status": status})
        return self._detalhar(projeto)

    def editar(self, usuario: Usuario, veiculo_id: int, projeto_id: int, dados: dict) -> ProjetoDetalhe:
        """Nome, descrição, categoria, orçamento e previsão; a situação muda pelas ações."""
        limpos = self._validar(dados)
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            projeto = self._do_veiculo(veiculo.id, projeto_id)
            self._projetos.atualizar(projeto, limpos)
        return self._detalhar(projeto)

    def _mudar(self, usuario: Usuario, veiculo_id: int, projeto_id: int, de: tuple[str, ...],
               mensagem: str, novos: dict | Callable[[Projeto], dict]) -> ProjetoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            projeto = self._do_veiculo(veiculo.id, projeto_id)
            if projeto.status not in de:
                raise Conflito(mensagem)
            self._projetos.atualizar(projeto, novos(projeto) if callable(novos) else novos)
        return self._detalhar(projeto)

    def iniciar(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> ProjetoDetalhe:
        return self._mudar(usuario, veiculo_id, projeto_id, (PLANEJADO,),
                           "Só um projeto planejado pode ser iniciado.", {"status": EM_ANDAMENTO})

    def concluir(self, usuario: Usuario, veiculo_id: int, projeto_id: int,
                 data: date | None) -> ProjetoDetalhe:
        data = data or self._hoje()
        if data > self._hoje():
            raise DadosInvalidos("A data de conclusão não pode ser no futuro.", campo="data_conclusao")
        return self._mudar(usuario, veiculo_id, projeto_id, STATUS_ABERTOS,
                           "Este projeto já está concluído ou cancelado.",
                           {"status": CONCLUIDO, "data_conclusao": data})

    def cancelar(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> ProjetoDetalhe:
        return self._mudar(usuario, veiculo_id, projeto_id, STATUS_ABERTOS,
                           "Este projeto já está concluído ou cancelado.", {"status": CANCELADO})

    def reabrir(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> ProjetoDetalhe:
        return self._mudar(usuario, veiculo_id, projeto_id, (CONCLUIDO, CANCELADO),
                           "Este projeto já está aberto.",
                           {"status": EM_ANDAMENTO, "data_conclusao": None})

    def apagar(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> None:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            projeto = self._do_veiculo(veiculo.id, projeto_id)
            arquivos = self._projetos.arquivos_das_fotos(projeto.id)
            self._projetos.apagar(projeto)
        for caminho in arquivos:
            self._arquivos.apagar(caminho)

    # --------------------------------------------------------------------- itens
    def _validar_item(self, dados: dict) -> dict:
        data = dados.get("data")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data")
        if data > self._hoje():
            raise DadosInvalidos("A data do gasto não pode ser no futuro.", campo="data")
        valor = validar_dinheiro(dados.get("valor"), "valor")
        if valor is None:
            raise DadosInvalidos("Informe o valor.", campo="valor")
        if valor == 0:
            raise DadosInvalidos("O valor precisa ser maior que zero.", campo="valor")
        return {"descricao": _texto(dados.get("descricao"), "descricao", TAMANHO_MAXIMO_ITEM,
                                    "Informe o que foi comprado ou pago."),
                "data": data, "valor": valor}

    def _projeto_aberto(self, usuario: Usuario, veiculo_id: int, projeto_id: int) -> Projeto:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
        projeto = self._do_veiculo(veiculo.id, projeto_id)
        if projeto.status not in STATUS_ABERTOS:
            situacao = "concluído" if projeto.status == CONCLUIDO else "cancelado"
            raise Conflito(f"Este projeto está {situacao}. Reabra o projeto para alterar os gastos.")
        return projeto

    def adicionar_item(self, usuario: Usuario, veiculo_id: int, projeto_id: int, dados: dict) -> ProjetoDetalhe:
        limpos = self._validar_item(dados)
        with self._uow.transacao():
            projeto = self._projeto_aberto(usuario, veiculo_id, projeto_id)
            self._projetos.criar_item(projeto.id, limpos)
        return self._detalhar(projeto)

    def editar_item(self, usuario: Usuario, veiculo_id: int, projeto_id: int, item_id: int,
                    dados: dict) -> ProjetoDetalhe:
        limpos = self._validar_item(dados)
        with self._uow.transacao():
            projeto = self._projeto_aberto(usuario, veiculo_id, projeto_id)
            self._projetos.atualizar_item(self._item_do_projeto(projeto, item_id), limpos)
        return self._detalhar(projeto)

    def apagar_item(self, usuario: Usuario, veiculo_id: int, projeto_id: int, item_id: int) -> ProjetoDetalhe:
        with self._uow.transacao():
            projeto = self._projeto_aberto(usuario, veiculo_id, projeto_id)
            self._projetos.apagar_item(self._item_do_projeto(projeto, item_id))
        return self._detalhar(projeto)
