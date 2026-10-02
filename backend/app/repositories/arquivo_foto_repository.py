"""Leitura da antiga pasta de fotos (PASTA_FOTOS), só para importar para o banco.

Desde a migration 0013 as imagens ficam no PostgreSQL (tabela foto_conteudo).
Esta classe só LÊ a pasta: é usada pelo comando "gerenciar.py importar-fotos",
que copia para o banco os arquivos que ainda estiverem lá. Nada é gravado
nem apagado na pasta.
"""

from pathlib import Path

from app.repositories.erros import ErroRepositorio


class CaminhoDeFotoInvalido(ErroRepositorio):
    """O caminho aponta para fora da pasta de fotos."""


class ArquivoFotoRepository:
    def __init__(self, pasta: Path):
        self._pasta = Path(pasta).resolve()

    @property
    def pasta(self) -> Path:
        return self._pasta

    def caminho(self, relativo: str) -> Path:
        destino = (self._pasta / relativo).resolve()
        if not destino.is_relative_to(self._pasta) or destino == self._pasta:
            raise CaminhoDeFotoInvalido(relativo)
        return destino

    def ler(self, relativo: str) -> bytes | None:
        """Conteúdo do arquivo, ou None se ele não existe (ou o caminho sai da pasta)."""
        try:
            caminho = self.caminho(relativo)
        except CaminhoDeFotoInvalido:
            return None
        return caminho.read_bytes() if caminho.is_file() else None

    def listar(self) -> list[str]:
        """Caminhos relativos de todos os arquivos, no formato gravado no banco."""
        if not self._pasta.is_dir():
            return []
        return sorted(arquivo.relative_to(self._pasta).as_posix()
                      for arquivo in self._pasta.rglob("*") if arquivo.is_file())
