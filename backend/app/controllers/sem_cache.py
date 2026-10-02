"""Respostas da API não ficam guardadas no navegador.

Os dados da API são da pessoa logada (veículos, gastos, quilometragem...).
Sem uma instrução explícita, o navegador do celular poderia guardar uma
resposta e mostrá-la de novo depois que a pessoa saísse ou que outra conta
entrasse no mesmo aparelho. Por isso toda resposta de /api sai com
"Cache-Control: no-store" (não guardar), a menos que o endpoint já tenha
escolhido outra regra. As fotos escolhem "private, no-cache": o navegador
guarda a imagem, mas pergunta ao servidor a cada uso, e o servidor confere a
permissão de novo (foto_controller.py).
"""

CABECALHO = b"cache-control"
NAO_GUARDAR = b"no-store"


class SemCacheNaApi:
    def __init__(self, app):
        self._app = app

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith("/api"):
            await self._app(scope, receive, send)
            return

        async def enviar(mensagem):
            if mensagem["type"] == "http.response.start":
                cabecalhos = list(mensagem.get("headers", []))
                if not any(nome.lower() == CABECALHO for nome, _ in cabecalhos):
                    cabecalhos.append((CABECALHO, NAO_GUARDAR))
                    mensagem = {**mensagem, "headers": cabecalhos}
            await send(mensagem)

        await self._app(scope, receive, enviar)
