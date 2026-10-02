"""Regras das fotos do veículo: envio, galeria, capa e exclusão.

Tudo no banco (migration 0013)
- A imagem fica no PostgreSQL (tabela foto_conteudo) e os metadados em
  veiculo_foto (tipo, tamanho, legenda, data, capa, vínculo).
- O envio grava a foto e a imagem na MESMA transação: ou as duas ficam, ou
  nenhuma. Apagar a foto (ou o registro a que ela está ligada) apaga a imagem
  junto, por cascata. Não sobra arquivo em pasta nenhuma.
- veiculo_foto.arquivo recebe um nome gerado aqui (veiculos/<id>/<código>.jpg),
  só como referência; o nome enviado pelo usuário nunca é usado.

Acesso
- Toda operação confere o veículo (dono ou admin) E se a foto é daquele
  veículo. Conhecer o número ou o endereço de uma foto não dá acesso a ela.

Vínculo
- Uma foto pode ficar ligada a UM registro: uma manutenção (nota fiscal,
  peça trocada), um diagnóstico (o vazamento) ou um projeto (antes/depois).
  O registro precisa ser do mesmo veículo da foto: isso é conferido aqui
  e garantido por chave estrangeira composta no banco.
- "Antes" e "depois" só valem para foto ligada a projeto (CHECK do SQL
  original). Foto de projeto sem momento também é aceita.
- Ao apagar o registro, as fotos ligadas a ele são apagadas junto.

Capa
- No máximo uma por veículo (índice único no banco). A troca bloqueia a
  linha do veículo, então duas trocas simultâneas acontecem em sequência.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from typing import Callable, Protocol

from app.entities.usuario import Usuario
from app.entities.veiculo_foto import ImagemPronta, VeiculoFoto
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.erros import DadosInvalidos, NaoEncontrado
from app.services.imagem_service import preparar_imagem
from app.services.paginacao import Pagina, limite_e_deslocamento

TAMANHO_MAXIMO_LEGENDA = 150


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class ImagemDaFoto:
    foto: VeiculoFoto
    conteudo: bytes


def _legenda(texto: str | None) -> str | None:
    limpa = " ".join((texto or "").split())
    if len(limpa) > TAMANHO_MAXIMO_LEGENDA:
        raise DadosInvalidos(f"Legenda longa demais (máximo {TAMANHO_MAXIMO_LEGENDA} caracteres).",
                             campo="legenda")
    return limpa or None


class FotoService:
    def __init__(self, uow: Transacional, veiculos, fotos, manutencoes, diagnosticos,
                 projetos, *,
                 preparar: Callable[[bytes], ImagemPronta] = preparar_imagem,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._fotos = fotos
        self._manutencoes = manutencoes
        self._diagnosticos = diagnosticos
        self._projetos = projetos
        self._acesso = AcessoVeiculo(veiculos)
        self._preparar = preparar
        self._hoje = hoje

    def _data(self, data_foto: date | None) -> date:
        data_foto = data_foto or self._hoje()
        if data_foto > self._hoje():
            raise DadosInvalidos("A data da foto não pode ser no futuro.", campo="data_foto")
        return data_foto

    def _foto_do_veiculo(self, veiculo_id: int, foto_id: int) -> VeiculoFoto:
        foto = self._fotos.buscar(foto_id)
        # A foto precisa ser DESTE veículo, não basta existir.
        if foto is None or foto.veiculo_id != veiculo_id:
            raise NaoEncontrado("Foto não encontrada.")
        return foto

    def _manutencao_do_veiculo(self, veiculo_id: int, manutencao_id: int | None) -> int | None:
        """Confere o vínculo: a manutenção precisa existir e ser do MESMO veículo."""
        if manutencao_id is None:
            return None
        manutencao = self._manutencoes.buscar(manutencao_id)
        if manutencao is None or manutencao.veiculo_id != veiculo_id:
            raise DadosInvalidos("Manutenção não encontrada neste veículo.", campo="manutencao_id")
        return manutencao.id

    def _vinculo(self, veiculo_id: int, manutencao_id: int | None, diagnostico_id: int | None,
                 projeto_id: int | None = None, momento: str | None = None) -> dict:
        """Confere o vínculo: no máximo um registro, do MESMO veículo; antes/depois só com projeto."""
        informados = [c for c, v in (("manutencao_id", manutencao_id), ("diagnostico_id", diagnostico_id),
                                     ("projeto_id", projeto_id)) if v is not None]
        if len(informados) > 1:
            raise DadosInvalidos("A foto pode ficar ligada a um só registro: projeto, diagnóstico "
                                 "ou manutenção.", campo=informados[-1])
        if momento is not None:
            if momento not in ("antes", "depois"):
                raise DadosInvalidos("Momento inválido: use antes ou depois.", campo="momento")
            if projeto_id is None:
                raise DadosInvalidos("Fotos de antes e depois precisam estar ligadas a um projeto.",
                                     campo="momento")
        vinculo = {"manutencao_id": None, "diagnostico_id": None, "projeto_id": None, "momento": momento}
        if projeto_id is not None:
            projeto = self._projetos.buscar(projeto_id)
            if projeto is None or projeto.veiculo_id != veiculo_id:
                raise DadosInvalidos("Projeto não encontrado neste veículo.", campo="projeto_id")
            vinculo["projeto_id"] = projeto.id
        elif diagnostico_id is not None:
            diagnostico = self._diagnosticos.buscar(diagnostico_id)
            if diagnostico is None or diagnostico.veiculo_id != veiculo_id:
                raise DadosInvalidos("Diagnóstico não encontrado neste veículo.",
                                     campo="diagnostico_id")
            vinculo["diagnostico_id"] = diagnostico.id
        else:
            vinculo["manutencao_id"] = self._manutencao_do_veiculo(veiculo_id, manutencao_id)
        return vinculo

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, pagina: int = 1, por_pagina: int = 30,
               vinculo: str | None = None, manutencao_id: int | None = None,
               diagnostico_id: int | None = None, projeto_id: int | None = None,
               momento: str | None = None) -> Pagina[VeiculoFoto]:
        """vinculo: None (todas), "manutencao", "diagnostico", "projeto" ou "nenhum"."""
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        if vinculo not in (None, "manutencao", "diagnostico", "projeto", "nenhum"):
            raise DadosInvalidos("Filtro de fotos inválido.", campo="vinculo")
        if momento not in (None, "antes", "depois"):
            raise DadosInvalidos("Momento inválido: use antes ou depois.", campo="momento")
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(
            itens=self._fotos.listar(veiculo.id, limite, deslocamento, vinculo, manutencao_id,
                                     diagnostico_id, projeto_id, momento),
            total=self._fotos.contar(veiculo.id, vinculo, manutencao_id, diagnostico_id, projeto_id,
                                     momento),
            pagina=pagina, por_pagina=por_pagina,
        )

    def obter(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> VeiculoFoto:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._foto_do_veiculo(veiculo.id, foto_id)

    def imagem(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> ImagemDaFoto:
        """Os bytes da imagem, depois de conferida a permissão."""
        foto = self.obter(usuario, veiculo_id, foto_id)
        conteudo = self._fotos.conteudo(foto.id)
        if conteudo is None:
            raise NaoEncontrado("O arquivo desta foto não está mais disponível.")
        return ImagemDaFoto(foto, conteudo)

    # ------------------------------------------------------------------ gravação
    def adicionar(self, usuario: Usuario, veiculo_id: int, conteudo: bytes,
                  legenda: str | None, data_foto: date | None, principal: bool,
                  manutencao_id: int | None = None, diagnostico_id: int | None = None,
                  projeto_id: int | None = None, momento: str | None = None) -> VeiculoFoto:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        legenda = _legenda(legenda)
        data_foto = self._data(data_foto)
        vinculo = self._vinculo(veiculo.id, manutencao_id, diagnostico_id, projeto_id, momento)
        imagem = self._preparar(conteudo)

        nome = f"veiculos/{veiculo.id}/{uuid.uuid4().hex}.{imagem.extensao}"
        with self._uow.transacao():
            if principal:
                self._veiculos.bloquear(veiculo.id)
            foto = self._fotos.criar(veiculo.id, nome, imagem.tipo_mime,
                                     len(imagem.conteudo), legenda, data_foto, **vinculo)
            self._fotos.salvar_conteudo(foto.id, imagem.conteudo)
            if principal:
                self._fotos.definir_capa(veiculo.id, foto.id)
        return foto

    def editar(self, usuario: Usuario, veiculo_id: int, foto_id: int, legenda: str | None,
               data_foto: date | None, manutencao_id: int | None = None,
               diagnostico_id: int | None = None, projeto_id: int | None = None,
               momento: str | None = None) -> VeiculoFoto:
        """Atualiza legenda, data e vínculo (todos os ids vazios = sem vínculo)."""
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        foto = self._foto_do_veiculo(veiculo.id, foto_id)
        legenda = _legenda(legenda)
        data_foto = self._data(data_foto)
        vinculo = self._vinculo(veiculo.id, manutencao_id, diagnostico_id, projeto_id, momento)
        with self._uow.transacao():
            self._fotos.atualizar(foto, legenda, data_foto, **vinculo)
        return foto

    def definir_capa(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> VeiculoFoto:
        """Troca a capa do veículo por esta foto."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            foto = self._foto_do_veiculo(veiculo.id, foto_id)
            self._fotos.definir_capa(veiculo.id, foto.id)
        return foto

    def remover_capa(self, usuario: Usuario, veiculo_id: int) -> None:
        """Deixa o veículo sem capa (a foto continua na galeria)."""
        with self._uow.transacao():
            veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id, bloquear=True)
            self._fotos.definir_capa(veiculo.id, None)

    def apagar(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> None:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        foto = self._foto_do_veiculo(veiculo.id, foto_id)
        with self._uow.transacao():
            self._fotos.apagar(foto)  # a imagem sai junto (cascata)
