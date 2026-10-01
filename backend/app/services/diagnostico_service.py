"""Regras dos diagnósticos (problemas do dia a dia), anotações e resolução.

Situações
- aberto / em observação: o problema existe. "Em observação" é só um
  lembrete de que está sendo acompanhado; os dois aparecem em "Abertos".
- resolvido: resolvido por uma manutenção REALIZADA do mesmo veículo. A data
  de resolução é a data da manutenção.
- descartado: não era problema ou sumiu; motivo opcional (campo solucao).
- Reabrir volta para "aberto" e desfaz a ligação com a manutenção que tinha
  resolvido (a manutenção continua no histórico).

Resolver com uma manutenção
- Nova: a manutenção e a resolução são gravadas na MESMA transação. Se
  qualquer parte falhar, nada fica gravado.
- Salvar a manutenção nova como AGENDADA não resolve: ela fica ligada como a
  prevista; ao ser marcada como realizada, o banco resolve o diagnóstico.
- Já registrada: escolher uma manutenção do mesmo veículo (realizada resolve;
  agendada fica como prevista).
- Envio repetido: o veículo fica bloqueado durante a gravação e o diagnóstico
  é conferido depois do bloqueio; o segundo envio recebe "já foi resolvido"
  em vez de criar outra manutenção.

Aviso de garantia
- Manutenções realizadas do MESMO veículo e do MESMO sistema que estavam em
  garantia na data do problema (limite de data ou de km, o que vier primeiro).
  É um aviso: não garante que o problema novo tenha cobertura. Garantia com
  informação incompleta não é mostrada como vigente.

A coerência entre o diagnóstico e a manutenção ligada também é garantida por
trigger no banco (migration 0006).
"""

from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

from app.entities.diagnostico import (
    ABERTO,
    DESCARTADO,
    EM_OBSERVACAO,
    FILTRO_ABERTOS,
    FILTRO_RESOLVIDOS,
    FILTRO_TODOS,
    GRAVIDADES,
    RESOLVIDO,
    STATUS_EM_ABERTO,
    Diagnostico,
    DiagnosticoNota,
)
from app.entities.manutencao import SISTEMAS, STATUS_REALIZADA, Manutencao
from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.calendario import data_br, numero_br
from app.services.erros import Conflito, DadosInvalidos, NaoEncontrado
from app.services.manutencao_service import ManutencaoDetalhe, ManutencaoService
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.veiculo_service import validar_quilometragem

TAMANHO_MAXIMO_TEXTO = 2000


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class GarantiaPossivel:
    manutencao: Manutencao
    explicacao: str


@dataclass(frozen=True)
class DiagnosticoResumo:
    diagnostico: Diagnostico
    total_notas: int
    manutencao: object | None  # ManutencaoLigada (id, descricao, status, data, valor)


@dataclass(frozen=True)
class DiagnosticoDetalhe:
    diagnostico: Diagnostico
    notas: list[DiagnosticoNota]
    manutencao: object | None
    garantias: list[GarantiaPossivel]
    total_fotos: int


@dataclass(frozen=True)
class Resolucao:
    diagnostico: DiagnosticoDetalhe
    manutencao: ManutencaoDetalhe


def _texto(valor: str | None, campo: str, mensagem_vazio: str | None, maximo: int) -> str | None:
    limpo = " ".join((valor or "").split())
    if not limpo:
        if mensagem_vazio:
            raise DadosInvalidos(mensagem_vazio, campo=campo)
        return None
    if len(limpo) > maximo:
        raise DadosInvalidos(f"Texto longo demais (máximo {maximo} caracteres).", campo=campo)
    return limpo


def _texto_longo(valor: str | None, campo: str, mensagem_vazio: str | None = None) -> str | None:
    """Texto com quebras de linha (detalhes, anotação): só tira espaços das pontas."""
    limpo = (valor or "").strip()
    if not limpo:
        if mensagem_vazio:
            raise DadosInvalidos(mensagem_vazio, campo=campo)
        return None
    if len(limpo) > TAMANHO_MAXIMO_TEXTO:
        raise DadosInvalidos(f"Texto longo demais (máximo {TAMANHO_MAXIMO_TEXTO} caracteres).",
                             campo=campo)
    return limpo


def garantia_na_data(manutencao: Manutencao, data: date, km: int | None) -> str | None:
    """Explicação se a manutenção estava em garantia na data (e km) do problema.
    None quando não estava, ou quando não dá para saber."""
    ate, limite_km = manutencao.garantia_ate, manutencao.garantia_km
    if data < manutencao.data:
        return None  # o problema é anterior ao serviço
    if ate is not None and data > ate:
        return None  # venceu pela data
    if limite_km is not None and km is not None and km > limite_km:
        return None  # venceu pela quilometragem
    if ate is None and km is None:
        return None  # só há limite de km e o problema não tem km: não dá para saber
    limites = []
    if ate is not None:
        limites.append(f"até {data_br(ate)}")
    if limite_km is not None:
        limites.append(f"até os {numero_br(limite_km)} km")
    texto = (f"{manutencao.descricao} em {data_br(manutencao.data)}, com garantia "
             f"{' ou '.join(limites)}"
             + (" (o que vier primeiro)." if len(limites) == 2 else "."))
    if limite_km is not None and km is None:
        texto += " Informe a quilometragem do problema para conferir o limite de km."
    return texto


class DiagnosticoService:
    def __init__(self, uow: Transacional, veiculos, diagnosticos, manutencoes, leituras, fotos,
                 arquivos, manutencao_service: ManutencaoService, *,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._diagnosticos = diagnosticos
        self._manutencoes = manutencoes
        self._leituras = leituras
        self._fotos = fotos
        self._arquivos = arquivos
        self._servico_de_manutencao = manutencao_service
        self._acesso = AcessoVeiculo(veiculos)
        self._hoje = hoje

    def _do_veiculo(self, veiculo: Veiculo, diagnostico_id: int) -> Diagnostico:
        diagnostico = self._diagnosticos.buscar(diagnostico_id)
        # O diagnóstico precisa ser DESTE veículo, não basta existir.
        if diagnostico is None or diagnostico.veiculo_id != veiculo.id:
            raise NaoEncontrado("Diagnóstico não encontrado.")
        return diagnostico

    def _garantias(self, diagnostico: Diagnostico) -> list[GarantiaPossivel]:
        garantias = []
        for manutencao in self._manutencoes.com_garantia(diagnostico.veiculo_id,
                                                         diagnostico.sistema):
            if manutencao.id == diagnostico.manutencao_id:
                continue  # a própria manutenção que resolveu
            explicacao = garantia_na_data(manutencao, diagnostico.data_identificacao,
                                          diagnostico.quilometragem)
            if explicacao:
                garantias.append(GarantiaPossivel(manutencao, explicacao))
        return garantias

    def _detalhar(self, veiculo: Veiculo, diagnostico: Diagnostico) -> DiagnosticoDetalhe:
        ligadas = self._diagnosticos.manutencoes_ligadas(
            [diagnostico.manutencao_id] if diagnostico.manutencao_id else [])
        return DiagnosticoDetalhe(
            diagnostico=diagnostico,
            notas=self._diagnosticos.notas(diagnostico.id),
            manutencao=ligadas.get(diagnostico.manutencao_id),
            garantias=self._garantias(diagnostico) if diagnostico.em_aberto else [],
            total_fotos=self._fotos.contar(veiculo.id, diagnostico_id=diagnostico.id),
        )

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, filtro: str = FILTRO_ABERTOS,
               pagina: int = 1, por_pagina: int = 30) -> Pagina[DiagnosticoResumo]:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if filtro not in (FILTRO_ABERTOS, FILTRO_RESOLVIDOS, FILTRO_TODOS):
            raise DadosInvalidos("Filtro de diagnósticos inválido.", campo="filtro")
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        lista = self._diagnosticos.listar(veiculo.id, filtro, limite, deslocamento)
        notas = self._diagnosticos.contar_notas([d.id for d in lista])
        ligadas = self._diagnosticos.manutencoes_ligadas(
            [d.manutencao_id for d in lista if d.manutencao_id])
        return Pagina(
            itens=[DiagnosticoResumo(d, notas.get(d.id, 0), ligadas.get(d.manutencao_id))
                   for d in lista],
            total=self._diagnosticos.contar(veiculo.id, filtro), pagina=pagina,
            por_pagina=por_pagina,
        )

    def obter(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int) -> DiagnosticoDetalhe:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._detalhar(veiculo, self._do_veiculo(veiculo, diagnostico_id))

    # ----------------------------------------------------------------- validação
    def _validar(self, veiculo: Veiculo, dados: dict, atual: Diagnostico | None) -> dict:
        hoje = self._hoje()
        data = dados.get("data_identificacao")
        if data is None:
            raise DadosInvalidos("Informe a data.", campo="data_identificacao")
        if data > hoje:
            raise DadosInvalidos("A data não pode ser no futuro.", campo="data_identificacao")
        if atual is not None and atual.data_resolucao is not None and data > atual.data_resolucao:
            raise DadosInvalidos(
                f"O diagnóstico foi encerrado em {data_br(atual.data_resolucao)}; a data em que o "
                "problema apareceu não pode ser depois disso.", campo="data_identificacao")
        gravidade = dados.get("gravidade")
        if gravidade not in GRAVIDADES:
            raise DadosInvalidos("Escolha a gravidade.", campo="gravidade")
        sistema = dados.get("sistema")
        if sistema not in SISTEMAS:
            raise DadosInvalidos("Escolha o sistema do veículo.", campo="sistema")
        km = dados.get("quilometragem")
        if km is not None:
            validar_quilometragem(km)
            self._conferir_hodometro(veiculo, km, data, atual)
        return {
            "titulo": _texto(dados.get("titulo"), "titulo", "Conte em poucas palavras o que está "
                             "acontecendo.", 150),
            "descricao": _texto_longo(dados.get("descricao"), "descricao"),
            "sistema": sistema, "gravidade": gravidade, "data_identificacao": data,
            "quilometragem": km,
        }

    def _conferir_hodometro(self, veiculo: Veiculo, km: int, data: date,
                            atual: Diagnostico | None) -> None:
        """A quilometragem do diagnóstico vira leitura: precisa combinar com as outras."""
        conflitos = self._leituras.conflitos(
            veiculo.id, km, data,
            ignorar_origem=("diagnostico", atual.id) if atual is not None else None)
        if conflitos:
            outra = conflitos[0]
            quando = (f"em {data_br(outra.data_leitura)}" if outra.data_leitura
                      else "numa leitura antiga sem data")
            raise DadosInvalidos(
                f"Esta quilometragem não combina com o histórico: {quando} o hodômetro "
                f"marcava {numero_br(outra.quilometragem)} km. Confira o valor e a data.",
                campo="quilometragem")

    def _data_de_encerramento(self, diagnostico: Diagnostico, data: date | None) -> date:
        data = data or self._hoje()
        if data > self._hoje():
            raise DadosInvalidos("A data não pode ser no futuro.", campo="data")
        if data < diagnostico.data_identificacao:
            raise DadosInvalidos(
                f"A data não pode ser antes de {data_br(diagnostico.data_identificacao)}, quando "
                "o problema foi identificado.", campo="data")
        return data

    # ------------------------------------------------------------------ gravação
    def criar(self, usuario: Usuario, veiculo_id: int, dados: dict) -> DiagnosticoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._diagnosticos.criar(veiculo.id, self._validar(veiculo, dados, None))
            self._veiculos.recarregar(veiculo)  # a quilometragem pode ter mudado
        return self._detalhar(veiculo, diagnostico)

    def editar(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
               dados: dict) -> DiagnosticoDetalhe:
        """Edita o que foi registrado; a situação muda pelas ações (resolver, descartar...)."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            self._diagnosticos.atualizar(diagnostico, self._validar(veiculo, dados, diagnostico))
            self._veiculos.recarregar(veiculo)
        return self._detalhar(veiculo, diagnostico)

    def definir_acompanhamento(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
                               status: str) -> DiagnosticoDetalhe:
        """Alterna entre aberto e em observação (só para diagnóstico em aberto)."""
        if status not in STATUS_EM_ABERTO:
            raise DadosInvalidos("Situação inválida.", campo="status")
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            if not diagnostico.em_aberto:
                raise Conflito("Este diagnóstico já foi encerrado. Reabra-o antes.")
            self._diagnosticos.atualizar(diagnostico, {"status": status})
        return self._detalhar(veiculo, diagnostico)

    def descartar(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
                  motivo: str | None, data: date | None) -> DiagnosticoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            if not diagnostico.em_aberto:
                raise Conflito("Este diagnóstico já foi encerrado.")
            data = self._data_de_encerramento(diagnostico, data)
            motivo = _texto_longo(motivo, "motivo")
            # A manutenção agendada ligada (se houver) continua agendada, só sem vínculo.
            self._diagnosticos.atualizar(diagnostico, {
                "status": DESCARTADO, "data_resolucao": data, "solucao": motivo,
                "manutencao_id": None})
            self._diagnosticos.criar_nota(diagnostico.id, self._hoje(),
                                          "Descartado." + (f" Motivo: {motivo}" if motivo else ""))
        return self._detalhar(veiculo, diagnostico)

    def reabrir(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int) -> DiagnosticoDetalhe:
        """Volta para aberto. A manutenção que tinha resolvido continua no histórico."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            if diagnostico.em_aberto:
                raise Conflito("Este diagnóstico já está aberto.")
            self._diagnosticos.atualizar(diagnostico, {
                "status": ABERTO, "data_resolucao": None, "solucao": None, "manutencao_id": None})
            self._diagnosticos.criar_nota(diagnostico.id, self._hoje(), "Reaberto.")
        return self._detalhar(veiculo, diagnostico)

    def apagar(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int) -> None:
        """Apaga o diagnóstico, as anotações e as fotos dele (linhas e arquivos).
        A manutenção ligada, se houver, continua no histórico."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            arquivos = self._fotos.arquivos_do_diagnostico(diagnostico.id)
            self._diagnosticos.apagar(diagnostico)
        for caminho in arquivos:
            self._arquivos.apagar(caminho)

    # --------------------------------------------------------------- resolução
    def _em_aberto_e_livre(self, diagnostico: Diagnostico) -> None:
        if diagnostico.status == RESOLVIDO:
            raise Conflito("Este diagnóstico já foi resolvido.")
        if diagnostico.status == DESCARTADO:
            raise Conflito("Este diagnóstico foi descartado. Reabra-o para resolver.")
        if diagnostico.manutencao_id is not None:
            prevista = self._manutencoes.buscar(diagnostico.manutencao_id)
            raise Conflito(
                "Este diagnóstico já tem uma manutenção agendada"
                + (f" para {data_br(prevista.data)}" if prevista else "")
                + ". Marque essa manutenção como realizada para resolvê-lo.")

    def _ligar(self, veiculo: Veiculo, diagnostico: Diagnostico, manutencao: Manutencao) -> None:
        """Realizada resolve; agendada fica como a prevista (o banco resolve ao concluir)."""
        if manutencao.status == STATUS_REALIZADA:
            if manutencao.data < diagnostico.data_identificacao:
                raise DadosInvalidos(
                    f"O problema foi identificado em {data_br(diagnostico.data_identificacao)}; "
                    "a manutenção que o resolve não pode ser anterior.", campo="data")
            self._diagnosticos.atualizar(diagnostico, {
                "status": RESOLVIDO, "data_resolucao": manutencao.data, "solucao": None,
                "manutencao_id": manutencao.id})
            texto = f"Resolvido com a manutenção \"{manutencao.descricao}\"."
        else:
            self._diagnosticos.atualizar(diagnostico, {"manutencao_id": manutencao.id})
            texto = (f"Manutenção \"{manutencao.descricao}\" agendada para "
                     f"{data_br(manutencao.data)}. O diagnóstico será resolvido quando ela for "
                     "marcada como realizada.")
        self._diagnosticos.criar_nota(diagnostico.id, self._hoje(), texto)

    def resolver_com_nova(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
                          dados_manutencao: dict) -> Resolucao:
        """Cria a manutenção e resolve (ou liga, se agendada) na MESMA transação."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            self._em_aberto_e_livre(diagnostico)
            manutencao = self._servico_de_manutencao.registrar(veiculo, dados_manutencao)
            self._ligar(veiculo, diagnostico, manutencao)
            self._veiculos.recarregar(veiculo)
        return Resolucao(self._detalhar(veiculo, diagnostico),
                         self._servico_de_manutencao.detalhar(veiculo, manutencao))

    def resolver_com_existente(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
                               manutencao_id: int) -> DiagnosticoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            self._em_aberto_e_livre(diagnostico)
            manutencao = self._manutencoes.buscar(manutencao_id)
            # A manutenção precisa ser do MESMO veículo (vale também para admin).
            if manutencao is None or manutencao.veiculo_id != veiculo.id:
                raise DadosInvalidos("Manutenção não encontrada neste veículo.",
                                     campo="manutencao_id")
            self._ligar(veiculo, diagnostico, manutencao)
        return self._detalhar(veiculo, diagnostico)

    # ------------------------------------------------------------------ anotações
    def anotar(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int, texto: str | None,
               data: date | None) -> DiagnosticoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            data = data or self._hoje()
            if data > self._hoje():
                raise DadosInvalidos("A data não pode ser no futuro.", campo="data")
            self._diagnosticos.criar_nota(
                diagnostico.id, data, _texto_longo(texto, "texto", "Escreva a anotação."))
        return self._detalhar(veiculo, diagnostico)

    def apagar_anotacao(self, usuario: Usuario, veiculo_id: int, diagnostico_id: int,
                        nota_id: int) -> DiagnosticoDetalhe:
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
            diagnostico = self._do_veiculo(veiculo, diagnostico_id)
            nota = self._diagnosticos.buscar_nota(nota_id)
            # A anotação precisa ser DESTE diagnóstico.
            if nota is None or nota.diagnostico_id != diagnostico.id:
                raise NaoEncontrado("Anotação não encontrada.")
            self._diagnosticos.apagar_nota(nota)
        return self._detalhar(veiculo, diagnostico)
