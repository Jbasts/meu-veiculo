"""Controller das fotos: recebe o arquivo enviado e entrega a imagem.

A imagem nunca é servida como arquivo público: ela sai por um endpoint da
API, depois de o service conferir a sessão e a quem pertence o veículo.
"""

from datetime import date

from fastapi import Request, Response, UploadFile
from fastapi.responses import FileResponse

from app.entities.sessao import SessaoAtual
from app.entities.veiculo_foto import TAMANHO_MAXIMO_BYTES
from app.schemas.veiculo_schema import FotoEdicaoEntrada, FotoResposta, PaginaFotos
from app.services.foto_service import FotoService


class FotoController:
    def __init__(self, service: FotoService):
        self._service = service

    def listar(self, atual: SessaoAtual, veiculo_id: int, pagina: int, por_pagina: int,
               vinculo: str | None, manutencao_id: int | None,
               diagnostico_id: int | None = None) -> PaginaFotos:
        resultado = self._service.listar(atual.usuario, veiculo_id, pagina, por_pagina,
                                         vinculo, manutencao_id, diagnostico_id)
        return PaginaFotos(
            itens=[FotoResposta.model_validate(foto) for foto in resultado.itens],
            total=resultado.total, pagina=resultado.pagina, por_pagina=resultado.por_pagina,
        )

    def obter(self, atual: SessaoAtual, veiculo_id: int, foto_id: int) -> FotoResposta:
        return FotoResposta.model_validate(self._service.obter(atual.usuario, veiculo_id, foto_id))

    def adicionar(self, atual: SessaoAtual, veiculo_id: int, arquivo: UploadFile,
                  legenda: str | None, data_foto: date | None, principal: bool,
                  manutencao_id: int | None, diagnostico_id: int | None = None) -> FotoResposta:
        # Lê no máximo o limite + 1 byte: o suficiente para o service saber
        # que passou do limite, sem carregar um arquivo enorme na memória.
        conteudo = arquivo.file.read(TAMANHO_MAXIMO_BYTES + 1)
        foto = self._service.adicionar(atual.usuario, veiculo_id, conteudo, legenda, data_foto,
                                       principal, manutencao_id, diagnostico_id)
        return FotoResposta.model_validate(foto)

    def editar(self, atual: SessaoAtual, veiculo_id: int, foto_id: int,
               dados: FotoEdicaoEntrada) -> FotoResposta:
        foto = self._service.editar(atual.usuario, veiculo_id, foto_id, dados.legenda,
                                    dados.data_foto, dados.manutencao_id, dados.diagnostico_id)
        return FotoResposta.model_validate(foto)

    def definir_capa(self, atual: SessaoAtual, veiculo_id: int, foto_id: int) -> FotoResposta:
        return FotoResposta.model_validate(
            self._service.definir_capa(atual.usuario, veiculo_id, foto_id))

    def remover_capa(self, atual: SessaoAtual, veiculo_id: int) -> Response:
        self._service.remover_capa(atual.usuario, veiculo_id)
        return Response(status_code=204)

    def apagar(self, atual: SessaoAtual, veiculo_id: int, foto_id: int) -> Response:
        self._service.apagar(atual.usuario, veiculo_id, foto_id)
        return Response(status_code=204)

    def arquivo(self, atual: SessaoAtual, veiculo_id: int, foto_id: int,
                requisicao: Request) -> Response:
        item = self._service.arquivo(atual.usuario, veiculo_id, foto_id)
        etiqueta = f'"foto-{item.foto.id}-{item.foto.tamanho_bytes}"'
        cabecalhos = {
            # O navegador pode guardar a imagem, mas precisa perguntar ao
            # servidor antes de reutilizá-la: a permissão é conferida sempre.
            "Cache-Control": "private, no-cache",
            "ETag": etiqueta,
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        }
        if requisicao.headers.get("if-none-match") == etiqueta:
            return Response(status_code=304, headers=cabecalhos)
        return FileResponse(item.caminho, media_type=item.foto.tipo_mime, headers=cabecalhos)
