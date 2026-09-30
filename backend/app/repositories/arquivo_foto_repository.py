"""Arquivos das fotos, guardados numa pasta do backend (fora do PostgreSQL).

- Os nomes são gerados pelo backend (nunca o nome enviado pelo usuário).
- A pasta não é servida direto pelo servidor web: o único caminho até um
  arquivo é o endpoint da API, que confere a permissão antes.
"""

import os
import time
from pathlib import Path

from app.repositories.erros import ErroRepositorio


class CaminhoDeFotoInvalido(ErroRepositorio):
    """O caminho aponta para fora da pasta de fotos."""


class ArquivoFotoRepository:
    def __init__(self, pasta: Path):
        self._pasta = Path(pasta).resolve()

    def caminho(self, relativo: str) -> Path:
        destino = (self._pasta / relativo).resolve()
        if not destino.is_relative_to(self._pasta) or destino == self._pasta:
            raise CaminhoDeFotoInvalido(relativo)
        return destino

    def salvar(self, relativo: str, conteudo: bytes) -> None:
        """Grava num arquivo temporário e renomeia: nunca fica um arquivo pela metade."""
        destino = self.caminho(relativo)
        destino.parent.mkdir(parents=True, exist_ok=True)
        temporario = destino.with_name(destino.name + ".tmp")
        try:
            with open(temporario, "xb") as arquivo:
                arquivo.write(conteudo)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, destino)
        except BaseException:
            temporario.unlink(missing_ok=True)
            raise

    def existe(self, relativo: str) -> bool:
        return self.caminho(relativo).is_file()

    def apagar(self, relativo: str) -> bool:
        """Apaga o arquivo. Devolve False se ele não existia ou não pôde ser apagado."""
        try:
            self.caminho(relativo).unlink()
            return True
        except OSError:
            return False

    def listar(self, idade_minima_segundos: float = 0) -> list[str]:
        """Caminhos relativos de todos os arquivos, no formato gravado no banco."""
        if not self._pasta.is_dir():
            return []
        limite = time.time() - idade_minima_segundos
        encontrados = []
        for arquivo in self._pasta.rglob("*"):
            if arquivo.is_file() and arquivo.stat().st_mtime <= limite:
                encontrados.append(arquivo.relative_to(self._pasta).as_posix())
        return sorted(encontrados)
