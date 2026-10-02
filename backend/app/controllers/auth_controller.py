"""Controller de conta: cadastro, entrada, saída, senha e recuperação.

A sessão vai num cookie:
- HttpOnly: o JavaScript da página não consegue ler (protege contra roubo por script);
- SameSite=Lax: outros sites não conseguem enviá-lo em formulários;
- Secure (COOKIE_SEGURO=true): só trafega em HTTPS;
- Path=/api: só é enviado para a API.
"""

from dataclasses import dataclass

from fastapi import BackgroundTasks, Request, Response

from app.entities.sessao import SessaoAtual
from app.schemas.auth_schema import (
    AlterarSenhaEntrada,
    CadastroEntrada,
    LoginEntrada,
    MensagemResposta,
    RecuperarSenhaEntrada,
    RedefinirSenhaEntrada,
    UsuarioResposta,
)
from app.services.autenticacao_service import AutenticacaoService
from app.services.email_service import EnviadorEmail, enviar_sem_interromper

NOME_COOKIE = "mv_sessao"
CAMINHO_COOKIE = "/api"

MENSAGEM_RECUPERACAO = (
    "Enviamos um link para criar uma senha nova. Confira a caixa de entrada e o spam."
)


@dataclass(frozen=True)
class ConfigCookie:
    seguro: bool
    duracao_segundos: int


def ler_token(requisicao: Request) -> str | None:
    return requisicao.cookies.get(NOME_COOKIE)


def ip_de(requisicao: Request) -> str | None:
    return requisicao.client.host if requisicao.client else None


class AuthController:
    def __init__(self, service: AutenticacaoService, enviador: EnviadorEmail, cookie: ConfigCookie):
        self._service = service
        self._enviador = enviador
        self._cookie = cookie

    def _gravar_cookie(self, resposta: Response, token: str) -> None:
        resposta.set_cookie(
            NOME_COOKIE, token, max_age=self._cookie.duracao_segundos, path=CAMINHO_COOKIE,
            httponly=True, samesite="lax", secure=self._cookie.seguro,
        )

    def _apagar_cookie(self, resposta: Response) -> None:
        resposta.delete_cookie(NOME_COOKIE, path=CAMINHO_COOKIE, httponly=True, samesite="lax",
                               secure=self._cookie.seguro)

    def cadastrar(self, dados: CadastroEntrada, resposta: Response) -> UsuarioResposta:
        resultado = self._service.cadastrar(dados.nome, dados.email, dados.senha,
                                            dados.confirmacao_senha)
        self._gravar_cookie(resposta, resultado.token_sessao)
        return UsuarioResposta.model_validate(resultado.usuario)

    def entrar(self, dados: LoginEntrada, requisicao: Request, resposta: Response) -> UsuarioResposta:
        resultado = self._service.entrar(dados.email, dados.senha, ip_de(requisicao))
        self._gravar_cookie(resposta, resultado.token_sessao)
        return UsuarioResposta.model_validate(resultado.usuario)

    def sair(self, requisicao: Request) -> Response:
        self._service.sair(ler_token(requisicao))
        resposta = Response(status_code=204)
        self._apagar_cookie(resposta)
        # Pede ao navegador que apague o que guardou deste endereço (por
        # exemplo, fotos já vistas), para nada da conta sobrar no aparelho.
        resposta.headers["Clear-Site-Data"] = '"cache"'
        return resposta

    def eu(self, atual: SessaoAtual) -> UsuarioResposta:
        return UsuarioResposta.model_validate(atual.usuario)

    def alterar_senha(self, atual: SessaoAtual, dados: AlterarSenhaEntrada) -> MensagemResposta:
        self._service.alterar_senha(atual, dados.senha_atual, dados.nova_senha,
                                    dados.confirmacao_senha)
        return MensagemResposta(
            mensagem="Senha alterada. Os outros aparelhos conectados precisarão entrar de novo."
        )

    def solicitar_recuperacao(self, dados: RecuperarSenhaEntrada,
                              tarefas: BackgroundTasks) -> MensagemResposta:
        mensagem = self._service.solicitar_recuperacao(dados.email)
        # Enviado depois da resposta: a tela não espera o servidor de e-mail.
        tarefas.add_task(enviar_sem_interromper, self._enviador, mensagem)
        return MensagemResposta(mensagem=MENSAGEM_RECUPERACAO)

    def redefinir_senha(self, dados: RedefinirSenhaEntrada, resposta: Response) -> MensagemResposta:
        self._service.redefinir_senha(dados.token, dados.nova_senha, dados.confirmacao_senha)
        self._apagar_cookie(resposta)
        return MensagemResposta(mensagem="Senha redefinida. Entre com a senha nova.")
