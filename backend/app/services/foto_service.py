"""Regras das fotos do veículo: envio, galeria, capa e exclusão.

Arquivo e banco
- Os arquivos ficam numa pasta do backend (PASTA_FOTOS); o PostgreSQL guarda
  só os metadados (caminho, tipo, tamanho, legenda, data, capa).
- O nome do arquivo é gerado aqui (veiculos/<id do veículo>/<código>.jpg);
  o nome enviado pelo usuário nunca é usado.
- Ordem no envio: 1) grava o arquivo; 2) grava a linha no banco. Se o banco
  falhar, o arquivo é apagado. Se o servidor cair entre os dois passos, sobra
  um arquivo sem linha ("órfão"), que ninguém consegue acessar; o comando
  "gerenciar.py limpar-fotos" encontra e apaga esses arquivos.
- Ordem na exclusão: 1) apaga a linha no banco; 2) apaga o arquivo. Se o
  passo 2 falhar, o arquivo vira órfão e sai na próxima limpeza.

Acesso
- Toda operação confere o veículo (dono ou admin) E se a foto é daquele
  veículo. Conhecer o número ou o endereço de uma foto não dá acesso a ela.

Capa
- No máximo uma por veículo (índice único no banco). A troca bloqueia a
  linha do veículo, então duas trocas simultâneas acontecem em sequência.
"""

import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Callable, Protocol

from app.entities.usuario import Usuario
from app.entities.veiculo_foto import ImagemPronta, VeiculoFoto
from app.services import calendario
from app.services.acesso_veiculo import AcessoVeiculo
from app.services.erros import DadosInvalidos, NaoEncontrado
from app.services.imagem_service import preparar_imagem
from app.services.paginacao import Pagina, limite_e_deslocamento

TAMANHO_MAXIMO_LEGENDA = 150
# Arquivo recém-gravado pode ser de um envio ainda em andamento: a limpeza
# só considera órfão o arquivo com mais de uma hora.
IDADE_MINIMA_ORFAO_SEGUNDOS = 3600


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class ArquivoDaFoto:
    foto: VeiculoFoto
    caminho: Path


@dataclass(frozen=True)
class RelatorioDeLimpeza:
    arquivos_orfaos: list[str]      # arquivo na pasta, sem linha no banco
    fotos_sem_arquivo: list[str]    # linha no banco, sem arquivo na pasta
    apagados: int


def _legenda(texto: str | None) -> str | None:
    limpa = " ".join((texto or "").split())
    if len(limpa) > TAMANHO_MAXIMO_LEGENDA:
        raise DadosInvalidos(f"Legenda longa demais (máximo {TAMANHO_MAXIMO_LEGENDA} caracteres).",
                             campo="legenda")
    return limpa or None


class FotoService:
    def __init__(self, uow: Transacional, veiculos, fotos, arquivos, *,
                 preparar: Callable[[bytes], ImagemPronta] = preparar_imagem,
                 hoje: Callable[[], date] = calendario.hoje):
        self._uow = uow
        self._veiculos = veiculos
        self._fotos = fotos
        self._arquivos = arquivos
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

    # ------------------------------------------------------------------ consulta
    def listar(self, usuario: Usuario, veiculo_id: int, pagina: int = 1,
               por_pagina: int = 30) -> Pagina[VeiculoFoto]:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(
            itens=self._fotos.listar(veiculo.id, limite, deslocamento),
            total=self._fotos.contar(veiculo.id), pagina=pagina, por_pagina=por_pagina,
        )

    def obter(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> VeiculoFoto:
        veiculo = self._acesso.exigir(usuario, veiculo_id)
        return self._foto_do_veiculo(veiculo.id, foto_id)

    def arquivo(self, usuario: Usuario, veiculo_id: int, foto_id: int) -> ArquivoDaFoto:
        """Onde está o arquivo da foto, depois de conferida a permissão."""
        foto = self.obter(usuario, veiculo_id, foto_id)
        if not self._arquivos.existe(foto.arquivo):
            raise NaoEncontrado("O arquivo desta foto não está mais disponível.")
        return ArquivoDaFoto(foto, self._arquivos.caminho(foto.arquivo))

    # ------------------------------------------------------------------ gravação
    def adicionar(self, usuario: Usuario, veiculo_id: int, conteudo: bytes,
                  legenda: str | None, data_foto: date | None, principal: bool) -> VeiculoFoto:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        legenda = _legenda(legenda)
        data_foto = self._data(data_foto)
        imagem = self._preparar(conteudo)

        caminho = f"veiculos/{veiculo.id}/{uuid.uuid4().hex}.{imagem.extensao}"
        self._arquivos.salvar(caminho, imagem.conteudo)
        try:
            with self._uow.transacao():
                if principal:
                    self._veiculos.bloquear(veiculo.id)
                foto = self._fotos.criar(veiculo.id, caminho, imagem.tipo_mime,
                                         len(imagem.conteudo), legenda, data_foto)
                if principal:
                    self._fotos.definir_capa(veiculo.id, foto.id)
        except BaseException:
            # O banco não gravou: o arquivo não pode ficar sobrando.
            self._arquivos.apagar(caminho)
            raise
        return foto

    def editar(self, usuario: Usuario, veiculo_id: int, foto_id: int, legenda: str | None,
               data_foto: date | None) -> VeiculoFoto:
        veiculo = self._acesso.exigir_para_alterar(usuario, veiculo_id)
        foto = self._foto_do_veiculo(veiculo.id, foto_id)
        legenda = _legenda(legenda)
        data_foto = self._data(data_foto)
        with self._uow.transacao():
            self._fotos.atualizar(foto, legenda, data_foto)
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
        caminho = foto.arquivo
        with self._uow.transacao():
            self._fotos.apagar(foto)
        # Só depois de confirmado no banco. Se falhar, a limpeza de órfãos resolve.
        self._arquivos.apagar(caminho)

    # ------------------------------------------------------------- manutenção
    def limpar_orfaos(self, apagar: bool) -> RelatorioDeLimpeza:
        """Compara a pasta de fotos com o banco (comando gerenciar.py limpar-fotos)."""
        registrados = self._fotos.arquivos_registrados()
        antigos = self._arquivos.listar(idade_minima_segundos=IDADE_MINIMA_ORFAO_SEGUNDOS)
        orfaos = [caminho for caminho in antigos if caminho not in registrados]
        sem_arquivo = sorted(c for c in registrados if not self._arquivos.existe(c))
        apagados = sum(1 for caminho in orfaos if self._arquivos.apagar(caminho)) if apagar else 0
        return RelatorioDeLimpeza(orfaos, sem_arquivo, apagados)
