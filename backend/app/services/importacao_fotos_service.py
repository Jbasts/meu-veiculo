"""Copia para o banco as imagens que ainda estão na antiga pasta de fotos.

Usado pelo comando "gerenciar.py importar-fotos". A migration 0013 já copia
tudo o que encontra; este comando serve para o caso de um arquivo aparecer
depois (pasta errada no .env, arquivo restaurado de um backup...).

- Só preenche fotos que estão SEM imagem no banco; nunca troca uma imagem.
- Não apaga nada da pasta. Depois de conferir as fotos no app, a pessoa
  apaga a pasta se quiser.
- Arquivo vazio ou acima de 10 MB não é copiado (o banco recusaria).
"""

from dataclasses import dataclass
from typing import Protocol

from app.entities.veiculo_foto import TAMANHO_MAXIMO_BYTES


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class RelatorioDeImportacao:
    pasta: str
    importadas: list[str]            # foto copiada da pasta para o banco
    sem_arquivo: list[str]           # foto sem imagem no banco e sem arquivo na pasta
    invalidos: list[str]             # arquivo vazio ou grande demais
    arquivos_sem_foto: list[str]     # arquivo na pasta que não pertence a nenhuma foto


class ImportacaoFotosService:
    def __init__(self, uow: Transacional, fotos, arquivos):
        self._uow = uow
        self._fotos = fotos
        self._arquivos = arquivos

    def importar(self) -> RelatorioDeImportacao:
        importadas, sem_arquivo, invalidos = [], [], []
        with self._uow.transacao():
            for foto in self._fotos.sem_conteudo():
                descricao = f"foto {foto.id} ({foto.arquivo})"
                dados = self._arquivos.ler(foto.arquivo)
                if dados is None:
                    sem_arquivo.append(descricao)
                elif not 0 < len(dados) <= TAMANHO_MAXIMO_BYTES:
                    invalidos.append(descricao)
                else:
                    self._fotos.salvar_conteudo(foto.id, dados)
                    importadas.append(descricao)
            registrados = self._fotos.arquivos_registrados()
        sobrando = [c for c in self._arquivos.listar() if c not in registrados]
        return RelatorioDeImportacao(str(self._arquivos.pasta), importadas, sem_arquivo,
                                     invalidos, sobrando)
