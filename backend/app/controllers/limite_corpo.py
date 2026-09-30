"""Limite de tamanho das requisições (proteção contra envios gigantes).

Nenhuma requisição à API pode ter corpo maior que o limite: a maior
necessidade legítima é uma foto de 10 MB. Quem passa disso recebe HTTP 413
antes de o servidor guardar o conteúdo.
"""

from fastapi.responses import JSONResponse

from app.entities.veiculo_foto import TAMANHO_MAXIMO_BYTES
from app.schemas.erro_schema import ErroResposta

# 10 MB da foto + folga para os outros campos do formulário.
CORPO_MAXIMO_BYTES = TAMANHO_MAXIMO_BYTES + 1024 * 1024
MENSAGEM = "Envio grande demais. O limite para fotos é 10 MB."


class LimiteDeCorpo:
    def __init__(self, app, maximo_bytes: int = CORPO_MAXIMO_BYTES):
        self._app = app
        self._maximo = maximo_bytes

    async def _recusar(self, scope, receive, send) -> None:
        corpo = ErroResposta(mensagem=MENSAGEM, campos={"arquivo": MENSAGEM})
        await JSONResponse(status_code=413, content=corpo.model_dump())(scope, receive, send)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return

        declarado = dict(scope["headers"]).get(b"content-length")
        if declarado is not None and (not declarado.isdigit() or int(declarado) > self._maximo):
            await self._recusar(scope, receive, send)
            return

        # Sem tamanho declarado (envio em pedaços): conta os bytes que chegam.
        recebido = 0
        excedeu = False

        async def receber():
            nonlocal recebido, excedeu
            mensagem = await receive()
            if mensagem["type"] == "http.request":
                recebido += len(mensagem.get("body", b""))
                if recebido > self._maximo:
                    excedeu = True
                    return {"type": "http.disconnect"}
            return mensagem

        async def enviar(mensagem):
            if not excedeu:
                await send(mensagem)

        try:
            await self._app(scope, receber, enviar)
        except Exception:
            if not excedeu:
                raise
        if excedeu:
            await self._recusar(scope, receive, send)
