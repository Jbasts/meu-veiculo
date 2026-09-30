"""Regras das manutenções e dos planos de manutenção.

Planos (o que se repete)
- Intervalo por quilometragem, por meses ou pelos dois. Com os dois, vale o
  limite atingido primeiro.
- Base do plano (data_base / km_base): de onde o intervalo é contado enquanto
  não há manutenção realizada do plano. É informada no cadastro ("última vez
  feita", ou "a partir de hoje") e fica gravada: o prazo não anda sozinho.
- Referência = o mais recente entre a base e a última manutenção realizada.
  Próxima = referência + intervalo (meses de calendário: 31/01 + 1 mês = 28/02).

Situação (calculada pelo banco, função classificar_prazo)
- atrasada: km atual >= próxima km, OU hoje >= próxima data;
- próxima : faltam de 1 a 1.000 km, OU de 1 a 30 dias;
- em dia  : faltam mais de 1.000 km e mais de 30 dias;
- sem base: o plano não tem a base de algum intervalo e o que se conhece não
  está atrasado. Desconhecido não é "em dia".

Aba "Pendentes": cada obrigação aparece uma vez
- plano ativo: um item; se já houver manutenção agendada para ele, ela
  aparece dentro do mesmo item (não vira outro alerta). Cada plano aceita no
  máximo uma agendada;
- manutenção agendada sem plano ativo: um item; atrasa a partir do dia
  SEGUINTE ao marcado (ou quando o km previsto é atingido);
- lembrete: "próxima em..." informada numa manutenção avulsa realizada. Em
  manutenção de plano esse campo não é aceito: a próxima vem do plano.

Manutenções
- realizada: aconteceu (data até hoje); se tiver quilometragem, o banco gera a
  leitura do hodômetro. agendada: ainda vai acontecer; não gera leitura, não
  tem garantia e não entra nas despesas.
- Mudar de agendada para realizada (mesmo alterando só o status) gera a
  leitura; voltar para agendada ou apagar retira a leitura. A situação dos
  planos e os alertas são sempre calculados na consulta, então refletem a
  mudança sem outro passo.
- O plano da manutenção precisa ser do mesmo veículo (conferido aqui e por
  chave estrangeira composta no banco).

Valores: peças e mão de obra
- Cada item tem tipo (peça ou mão de obra), nome e valor (Decimal, até 2 casas).
- Sem nenhum item, o total é o valor informado à mão (ou 0,00).
- Com pelo menos um item, o total é SEMPRE a soma dos itens, calculada aqui e
  conferida pelo banco (migration 0005). Mandar um total junto com itens é
  recusado: a tela não escolhe o total.
- Manutenção sem itens não tem subtotal de peças nem de mão de obra
  (desconhecido, não zero): nada é inventado para registros antigos.
- A edição troca a lista inteira de itens, na mesma transação do resto.

Garantia
- garantia_ate: último dia de cobertura. garantia_km: LIMITE DO HODÔMETRO
  (ex.: "até os 95.000 km"), não uma distância.
- Com os dois limites, a garantia acaba no que for atingido primeiro.
- Sem nenhum limite informado, a resposta é "sem informação de garantia",
  nunca "em garantia".
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Protocol

from app.entities.manutencao import (
    ITEM_MAO_DE_OBRA,
    ITEM_PECA,
    SISTEMAS,
    SITUACAO_ATRASADA,
    SITUACAO_EM_DIA,
    SITUACAO_PROXIMA,
    SITUACAO_SEM_BASE,
    STATUS_AGENDADA,
    STATUS_REALIZADA,
    TIPOS_DE_ITEM,
    Manutencao,
    ManutencaoItem,
    Pendencia,
    PlanoManutencao,
    SituacaoPlano,
)
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br, numero_br
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.veiculo_service import validar_dinheiro, validar_quilometragem

INTERVALO_KM_MAXIMO = 1_000_000
INTERVALO_MESES_MAXIMO = 600
TAMANHO_MAXIMO_OBSERVACAO = 2000
MAXIMO_DE_ITENS = 50
ROTULO_DO_ITEM = {ITEM_PECA: "Peça", ITEM_MAO_DE_OBRA: "Mão de obra"}

GARANTIA_VIGENTE = "vigente"
GARANTIA_VENCIDA = "vencida"
GARANTIA_SEM_INFORMACAO = "sem_informacao"
GARANTIA_NAO_SE_APLICA = "nao_se_aplica"

ORDEM_DAS_SITUACOES = {SITUACAO_ATRASADA: 0, SITUACAO_PROXIMA: 1, SITUACAO_SEM_BASE: 2,
                       SITUACAO_EM_DIA: 3}


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class PlanoDetalhe:
    plano: PlanoManutencao
    situacao: SituacaoPlano | None  # None quando o plano está inativo


@dataclass(frozen=True)
class Garantia:
    situacao: str
    explicacao: str


@dataclass(frozen=True)
class ManutencaoDetalhe:
    manutencao: Manutencao
    plano_nome: str | None
    garantia: Garantia
    total_fotos: int
    itens: list[ManutencaoItem]
    # None quando a manutenção não tem itens (só o total, sem detalhamento).
    total_pecas: Decimal | None
    total_mao_de_obra: Decimal | None


def somar(valores) -> Decimal:
    """Soma em Decimal (nunca float), começando de 0,00."""
    return sum(valores, Decimal("0.00"))


@dataclass(frozen=True)
class Pendentes:
    km_atual: int
    itens: list[Pendencia]


def _texto(valor: str | None, campo: str, mensagem_vazio: str | None, maximo: int) -> str | None:
    limpo = " ".join((valor or "").split())
    if not limpo:
        if mensagem_vazio:
            raise DadosInvalidos(mensagem_vazio, campo=campo)
        return None
    if len(limpo) > maximo:
        raise DadosInvalidos(f"Texto longo demais (máximo {maximo} caracteres).", campo=campo)
    return limpo


def _sistema(valor: str | None) -> str:
    if valor not in SISTEMAS:
        raise DadosInvalidos("Escolha o sistema do veículo.", campo="sistema")
    return valor


def avaliar_garantia(manutencao: Manutencao, km_atual: int, hoje: date) -> Garantia:
    """Situação da garantia de uma manutenção. Vale o limite atingido primeiro."""
    if not manutencao.realizada:
        return Garantia(GARANTIA_NAO_SE_APLICA, "Manutenção ainda não realizada.")
    ate, km = manutencao.garantia_ate, manutencao.garantia_km
    if ate is None and km is None:
        return Garantia(GARANTIA_SEM_INFORMACAO, "Sem informação de garantia.")
    if ate is not None and hoje > ate:
        return Garantia(GARANTIA_VENCIDA, f"Garantia vencida em {data_br(ate)}.")
    if km is not None and km_atual > km:
        return Garantia(GARANTIA_VENCIDA,
                        f"Garantia vencida: o veículo passou dos {numero_br(km)} km.")
    limites = []
    if ate is not None:
        limites.append(f"até {data_br(ate)}")
    if km is not None:
        limites.append(f"até os {numero_br(km)} km")
    texto = " ou ".join(limites)
    if len(limites) == 2:
        texto += ", o que vier primeiro"
    return Garantia(GARANTIA_VIGENTE, f"Em garantia {texto}.")


# ======================================================================= planos

class PlanoService:
    def __init__(self, uow: Transacional, veiculos, planos, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._planos = planos
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo: Veiculo, plano_id: int) -> PlanoManutencao:
        plano = self._planos.buscar(plano_id)
        # O plano precisa ser DESTE veículo, não basta existir.
        if plano is None or plano.veiculo_id != veiculo.id:
            raise NaoEncontrado("Plano não encontrado.")
        return plano

    def listar(self, usuario: Usuario, veiculo_id: int) -> list[PlanoDetalhe]:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        situacoes = self._planos.situacoes(veiculo.id)
        return [PlanoDetalhe(p, situacoes.get(p.id)) for p in self._planos.listar(veiculo.id)]

    def obter(self, usuario: Usuario, veiculo_id: int, plano_id: int) -> PlanoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        plano = self._do_veiculo(veiculo, plano_id)
        return PlanoDetalhe(plano, self._planos.situacoes(veiculo.id).get(plano.id))

    def _validar(self, veiculo: Veiculo, dados: dict) -> dict:
        hoje = self._hoje()
        intervalo_km = dados.get("intervalo_km")
        intervalo_meses = dados.get("intervalo_meses")
        if intervalo_km is None and intervalo_meses is None:
            raise DadosInvalidos("Informe o intervalo em quilômetros, em meses ou os dois.",
                                 campo="intervalo_km")
        if intervalo_km is not None and not 1 <= intervalo_km <= INTERVALO_KM_MAXIMO:
            raise DadosInvalidos(
                f"O intervalo deve ficar entre 1 e {numero_br(INTERVALO_KM_MAXIMO)} km.",
                campo="intervalo_km")
        if intervalo_meses is not None and not 1 <= intervalo_meses <= INTERVALO_MESES_MAXIMO:
            raise DadosInvalidos(f"O intervalo deve ficar entre 1 e {INTERVALO_MESES_MAXIMO} meses.",
                                 campo="intervalo_meses")

        # A base só é guardada para o intervalo que o plano usa, e é obrigatória:
        # sem ela não há de onde contar o prazo.
        data_base = dados.get("data_base") if intervalo_meses is not None else None
        km_base = dados.get("km_base") if intervalo_km is not None else None
        if intervalo_meses is not None:
            if data_base is None:
                raise DadosInvalidos(
                    "Informe a data da última vez (ou a de hoje, para contar a partir de agora).",
                    campo="data_base")
            if data_base > hoje:
                raise DadosInvalidos("A data não pode ser no futuro.", campo="data_base")
        if intervalo_km is not None:
            if km_base is None:
                raise DadosInvalidos(
                    "Informe a quilometragem da última vez (ou a atual, para contar a partir de agora).",
                    campo="km_base")
            validar_quilometragem(km_base, "km_base")
            if km_base > veiculo.quilometragem:
                raise DadosInvalidos(
                    "A quilometragem da última vez não pode ser maior que a atual "
                    f"({numero_br(veiculo.quilometragem)} km).", campo="km_base")
        return {
            "nome": _texto(dados.get("nome"), "nome", "Informe o nome do plano.", 100),
            "sistema": _sistema(dados.get("sistema")),
            "intervalo_km": intervalo_km, "intervalo_meses": intervalo_meses,
            "data_base": data_base, "km_base": km_base,
        }

    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> PlanoDetalhe:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        limpos = self._validar(veiculo, dados)
        with self._uow.transacao():
            plano = self._planos.criar(veiculo.id, limpos)
        return PlanoDetalhe(plano, self._planos.situacoes(veiculo.id).get(plano.id))

    def editar(self, usuario: Usuario, veiculo_id: int, plano_id: int, dados: dict) -> PlanoDetalhe:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        plano = self._do_veiculo(veiculo, plano_id)
        limpos = self._validar(veiculo, dados)
        with self._uow.transacao():
            self._planos.atualizar(plano, limpos)
        return PlanoDetalhe(plano, self._planos.situacoes(veiculo.id).get(plano.id))

    def definir_ativo(self, usuario: Usuario, veiculo_id: int, plano_id: int,
                      ativo: bool) -> PlanoDetalhe:
        """Plano inativo sai dos alertas; as manutenções dele continuam no histórico."""
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        plano = self._do_veiculo(veiculo, plano_id)
        if plano.ativo != ativo:
            with self._uow.transacao():
                self._planos.atualizar(plano, {"ativo": ativo})
        return PlanoDetalhe(plano, self._planos.situacoes(veiculo.id).get(plano.id))

    def apagar(self, usuario: Usuario, veiculo_id: int, plano_id: int) -> None:
        """Apaga o plano. As manutenções já registradas ficam como avulsas."""
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        plano = self._do_veiculo(veiculo, plano_id)
        with self._uow.transacao():
            self._planos.apagar(plano)


# ================================================================== manutenções

class ManutencaoService:
    def __init__(self, uow: Transacional, veiculos, planos, manutencoes, leituras, fotos,
                 arquivos, *, hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._planos = planos
        self._manutencoes = manutencoes
        self._leituras = leituras
        self._fotos = fotos
        self._arquivos = arquivos
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo: Veiculo, manutencao_id: int) -> Manutencao:
        manutencao = self._manutencoes.buscar(manutencao_id)
        # A manutenção precisa ser DESTE veículo, não basta existir.
        if manutencao is None or manutencao.veiculo_id != veiculo.id:
            raise NaoEncontrado("Manutenção não encontrada.")
        return manutencao

    def _detalhar(self, veiculo: Veiculo, manutencao: Manutencao) -> ManutencaoDetalhe:
        plano = self._planos.buscar(manutencao.plano_id) if manutencao.plano_id else None
        itens = self._manutencoes.itens(manutencao.id)
        return ManutencaoDetalhe(
            manutencao=manutencao,
            plano_nome=plano.nome if plano else None,
            garantia=avaliar_garantia(manutencao, veiculo.quilometragem, self._hoje()),
            total_fotos=self._fotos.contar(veiculo.id, manutencao_id=manutencao.id),
            itens=itens,
            total_pecas=somar(i.valor for i in itens if i.tipo == ITEM_PECA) if itens else None,
            total_mao_de_obra=(somar(i.valor for i in itens if i.tipo == ITEM_MAO_DE_OBRA)
                               if itens else None),
        )

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, status: str | None, pagina: int = 1,
               por_pagina: int = 30) -> Pagina[Manutencao]:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if status not in (None, STATUS_REALIZADA, STATUS_AGENDADA):
            raise DadosInvalidos("Filtro de status inválido.", campo="status")
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(
            itens=self._manutencoes.listar(veiculo.id, status, limite, deslocamento),
            total=self._manutencoes.contar(veiculo.id, status), pagina=pagina, por_pagina=por_pagina,
        )

    def obter(self, usuario: Usuario, veiculo_id: int, manutencao_id: int) -> ManutencaoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._detalhar(veiculo, self._do_veiculo(veiculo, manutencao_id))

    def pendentes(self, usuario: Usuario, veiculo_id: int) -> Pendentes:
        """Obrigações do veículo, das mais urgentes para as menos urgentes."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        distante = 10**9
        itens = sorted(
            self._manutencoes.pendencias(veiculo.id),
            key=lambda p: (
                ORDEM_DAS_SITUACOES.get(p.situacao, 9),
                p.dias_restantes if p.dias_restantes is not None else distante,
                p.km_restantes if p.km_restantes is not None else distante,
                p.titulo.lower(), p.plano_id or 0, p.manutencao_id or 0,
            ),
        )
        return Pendentes(km_atual=veiculo.quilometragem, itens=itens)

    # ----------------------------------------------------------------- validação
    def _validar(self, veiculo: Veiculo, dados: dict,
                 atual: Manutencao | None) -> tuple[dict, list[dict]]:
        """Devolve (campos da manutenção, itens). Com itens, o valor é a soma deles."""
        hoje = self._hoje()
        status = dados.get("status")
        if status not in (STATUS_REALIZADA, STATUS_AGENDADA):
            raise DadosInvalidos("Informe se a manutenção foi realizada ou está agendada.",
                                 campo="status")
        realizada = status == STATUS_REALIZADA

        data = dados.get("data")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data")
        if realizada and data > hoje:
            raise DadosInvalidos(
                "Uma manutenção realizada não pode ter data no futuro. "
                "Se ela ainda vai acontecer, salve como agendada.", campo="data")

        km = dados.get("quilometragem")
        if km is not None:
            validar_quilometragem(km)

        itens = self._validar_itens(dados.get("itens") or [])
        valor = validar_dinheiro(dados.get("valor"), "valor")
        if itens and valor is not None:
            raise DadosInvalidos(
                "Com peças ou mão de obra detalhadas, o total é calculado automaticamente. "
                "Não informe o valor total.", campo="valor")
        if itens:
            valor = somar(item["valor"] for item in itens)
        limpos = {
            "descricao": _texto(dados.get("descricao"), "descricao", "Informe a descrição.", 150),
            "sistema": _sistema(dados.get("sistema")),
            "status": status, "data": data, "quilometragem": km,
            "valor": valor if valor is not None else Decimal("0.00"),
            "oficina": _texto(dados.get("oficina"), "oficina", None, 120),
        }

        observacao = (dados.get("observacao") or "").strip()
        if len(observacao) > TAMANHO_MAXIMO_OBSERVACAO:
            raise DadosInvalidos(
                f"Texto longo demais (máximo {TAMANHO_MAXIMO_OBSERVACAO} caracteres).",
                campo="observacao")
        limpos["observacao"] = observacao or None

        limpos["plano_id"] = self._validar_plano(veiculo, dados.get("plano_id"), status, km, atual)
        limpos.update(self._validar_garantia(dados, realizada, data, km))
        limpos.update(self._validar_lembrete(dados, realizada, limpos["plano_id"], data, km))

        if realizada and km is not None:
            self._conferir_hodometro(veiculo, km, data, atual)
        return limpos, itens

    @staticmethod
    def _validar_itens(itens: list[dict]) -> list[dict]:
        if len(itens) > MAXIMO_DE_ITENS:
            raise DadosInvalidos(f"No máximo {MAXIMO_DE_ITENS} itens por manutenção.",
                                 campo="itens")
        limpos = []
        for indice, item in enumerate(itens):
            tipo = item.get("tipo")
            if tipo not in TIPOS_DE_ITEM:
                raise DadosInvalidos("Tipo de item inválido.", campo=f"itens.{indice}.tipo")
            rotulo = ROTULO_DO_ITEM[tipo]
            nome = _texto(item.get("nome"), f"itens.{indice}.nome",
                          f"{rotulo}: informe o nome.", 150)
            if item.get("valor") is None:
                raise DadosInvalidos(f"{rotulo} \"{nome}\": informe o valor.",
                                     campo=f"itens.{indice}.valor")
            valor = validar_dinheiro(item["valor"], f"itens.{indice}.valor")
            limpos.append({"tipo": tipo, "nome": nome, "valor": valor})
        return limpos

    def _validar_plano(self, veiculo: Veiculo, plano_id: int | None, status: str, km: int | None,
                       atual: Manutencao | None) -> int | None:
        if plano_id is None:
            return None
        plano = self._planos.buscar(plano_id)
        # O plano precisa existir E ser do mesmo veículo (vale também para admin).
        if plano is None or plano.veiculo_id != veiculo.id:
            raise DadosInvalidos("Plano não encontrado neste veículo.", campo="plano_id")
        mudou_de_plano = atual is None or atual.plano_id != plano.id
        if mudou_de_plano and not plano.ativo:
            raise DadosInvalidos("Este plano está inativo. Reative-o ou escolha outro.",
                                 campo="plano_id")
        if status == STATUS_REALIZADA and plano.intervalo_km is not None and km is None:
            raise DadosInvalidos(
                "Informe a quilometragem: o plano conta o prazo em quilômetros.",
                campo="quilometragem")
        if status == STATUS_AGENDADA:
            outra = self._manutencoes.agendada_do_plano(plano.id,
                                                        ignorar_id=atual.id if atual else None)
            if outra is not None:
                raise Conflito(
                    f"Este plano já tem uma manutenção agendada para {data_br(outra.data)}. "
                    "Edite essa manutenção em vez de criar outra.", campo="plano_id")
        return plano.id

    @staticmethod
    def _validar_garantia(dados: dict, realizada: bool, data: date, km: int | None) -> dict:
        ate, limite_km = dados.get("garantia_ate"), dados.get("garantia_km")
        if not realizada:
            if ate is not None or limite_km is not None:
                raise DadosInvalidos("A garantia só é informada em manutenção realizada.",
                                     campo="garantia_ate" if ate is not None else "garantia_km")
            return {"garantia_ate": None, "garantia_km": None}
        if ate is not None and ate < data:
            raise DadosInvalidos("A garantia não pode terminar antes da data da manutenção.",
                                 campo="garantia_ate")
        if limite_km is not None:
            validar_quilometragem(limite_km, "garantia_km")
            if km is not None and limite_km < km:
                raise DadosInvalidos(
                    "Informe a quilometragem LIMITE da garantia (o que o hodômetro vai marcar "
                    f"quando ela acabar), não a distância. Ela não pode ser menor que {numero_br(km)} km.",
                    campo="garantia_km")
        return {"garantia_ate": ate, "garantia_km": limite_km}

    @staticmethod
    def _validar_lembrete(dados: dict, realizada: bool, plano_id: int | None, data: date,
                          km: int | None) -> dict:
        proxima_data, proxima_km = dados.get("proxima_data"), dados.get("proxima_km")
        if proxima_data is None and proxima_km is None:
            return {"proxima_data": None, "proxima_km": None}
        campo = "proxima_data" if proxima_data is not None else "proxima_km"
        if plano_id is not None:
            raise DadosInvalidos("Em manutenção de plano, a próxima é calculada pelo plano.",
                                 campo=campo)
        if not realizada:
            raise DadosInvalidos("O lembrete da próxima só vale para manutenção realizada.",
                                 campo=campo)
        if proxima_data is not None and proxima_data <= data:
            raise DadosInvalidos("A próxima data precisa ser depois da data da manutenção.",
                                 campo="proxima_data")
        if proxima_km is not None:
            validar_quilometragem(proxima_km, "proxima_km")
            if km is not None and proxima_km <= km:
                raise DadosInvalidos(
                    "A próxima quilometragem precisa ser maior que a da manutenção.",
                    campo="proxima_km")
        return {"proxima_data": proxima_data, "proxima_km": proxima_km}

    def _conferir_hodometro(self, veiculo: Veiculo, km: int, data: date,
                            atual: Manutencao | None) -> None:
        """A quilometragem de uma manutenção realizada vira leitura: precisa
        combinar com as outras (o hodômetro só anda para a frente)."""
        conflitos = self._leituras.conflitos(
            veiculo.id, km, data,
            ignorar_origem=("manutencao", atual.id) if atual is not None else None)
        if conflitos:
            outra = conflitos[0]
            quando = (f"em {data_br(outra.data_leitura)}" if outra.data_leitura
                      else "numa leitura antiga sem data")
            raise DadosInvalidos(
                f"Esta quilometragem não combina com o histórico: {quando} o hodômetro "
                f"marcava {numero_br(outra.quilometragem)} km. Confira o valor e a data.",
                campo="quilometragem")

    # ------------------------------------------------------------------ gravação
    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> ManutencaoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            limpos, itens = self._validar(veiculo, dados, None)
            manutencao = self._manutencoes.criar(veiculo.id, limpos)
            if itens:
                self._manutencoes.substituir_itens(manutencao.id, itens)
            self._veiculos.recarregar(veiculo)  # o banco pode ter atualizado a quilometragem
        return self._detalhar(veiculo, manutencao)

    def editar(self, usuario: Usuario, veiculo_id: int, manutencao_id: int,
               dados: dict) -> ManutencaoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            manutencao = self._do_veiculo(veiculo, manutencao_id)
            limpos, itens = self._validar(veiculo, dados, manutencao)
            # Primeiro os itens, depois o total: o banco confere que batem.
            self._manutencoes.substituir_itens(manutencao.id, itens)
            self._manutencoes.atualizar(manutencao, limpos)
            self._veiculos.recarregar(veiculo)
        return self._detalhar(veiculo, manutencao)

    def apagar(self, usuario: Usuario, veiculo_id: int, manutencao_id: int) -> None:
        """Apaga a manutenção, os itens dela e as fotos ligadas (linhas e arquivos)."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            manutencao = self._do_veiculo(veiculo, manutencao_id)
            # O banco apaga as linhas das fotos em cascata, mas não os arquivos.
            arquivos = self._fotos.arquivos_da_manutencao(manutencao.id)
            self._manutencoes.apagar(manutencao)
        for caminho in arquivos:
            self._arquivos.apagar(caminho)
