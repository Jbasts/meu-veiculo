"""Regras de conta: cadastro, entrada, sessão, troca e recuperação de senha.

Sessões:
- duram SESSAO_DIAS (padrão 30) a partir do login; não são renovadas;
- terminam no logout, na troca de senha (as outras sessões) e na
  redefinição por link (todas);
- conta desativada perde o acesso na próxima requisição, mesmo com sessão.

Limites de tentativas (contados no banco, valem mesmo reiniciando a API):
- login: 5 erros por e-mail ou 20 erros por endereço de rede em 15 minutos;
- recuperação: 3 pedidos por e-mail (silencioso, sem revelar nada) ou
  10 por endereço de rede (resposta 429) em 1 hora.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.entities.sessao import Sessao, SessaoAtual
from app.entities.tentativa_acesso import TIPO_LOGIN, TIPO_RECUPERACAO
from app.entities.usuario import Usuario
from app.repositories.erros import EmailJaCadastrado
from app.services.email_service import MensagemEmail
from app.services.erros import (
    AcessoNegado,
    Conflito,
    DadosInvalidos,
    MuitasTentativas,
    NaoAutenticado,
)
from app.services.senha_service import SenhaService
from app.services.tokens import gerar_token, hash_de, token_com_formato_valido
from app.services.validacao import normalizar_email, normalizar_nome

LIMITE_LOGIN_POR_EMAIL = 5
LIMITE_LOGIN_POR_IP = 20
JANELA_LOGIN = timedelta(minutes=15)

LIMITE_RECUPERACAO_POR_EMAIL = 3
LIMITE_RECUPERACAO_POR_IP = 10
JANELA_RECUPERACAO = timedelta(hours=1)

MENSAGEM_LOGIN_INVALIDO = "E-mail ou senha incorretos."
MENSAGEM_LINK_INVALIDO = (
    "Este link é inválido, expirou ou já foi usado. Peça um novo em 'Esqueci minha senha'."
)


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class ResultadoEntrada:
    usuario: Usuario
    token_sessao: str


def _ip_curto(ip: str | None) -> str | None:
    return ip[:45] if ip else None


class AutenticacaoService:
    def __init__(self, uow: Transacional, usuarios, sessoes, recuperacoes, tentativas,
                 senhas: SenhaService, *, validade_sessao: timedelta,
                 validade_link: timedelta, url_frontend: str):
        self._uow = uow
        self._usuarios = usuarios
        self._sessoes = sessoes
        self._recuperacoes = recuperacoes
        self._tentativas = tentativas
        self._senhas = senhas
        self._validade_sessao = validade_sessao
        self._validade_link = validade_link
        self._url_frontend = url_frontend.rstrip("/")

    # ------------------------------------------------------------------ cadastro
    def cadastrar(self, nome: str, email: str, senha: str, confirmacao: str) -> ResultadoEntrada:
        """Cria a conta com perfil padrão (nunca admin) e já abre a sessão."""
        nome = normalizar_nome(nome)
        email = normalizar_email(email)
        self._senhas.validar_nova_senha(senha, confirmacao, email=email)
        senha_hash = self._senhas.gerar_hash(senha)
        with self._uow.transacao():
            try:
                usuario = self._usuarios.criar(nome, email, senha_hash)
            except EmailJaCadastrado:
                raise Conflito(
                    "Este e-mail já está cadastrado. Entre na sua conta ou use 'Esqueci minha senha'.",
                    campo="email",
                ) from None
            token = self._abrir_sessao(usuario)
        return ResultadoEntrada(usuario, token)

    # ------------------------------------------------------------------- entrada
    def entrar(self, email: str, senha: str, ip: str | None) -> ResultadoEntrada:
        email_normalizado = (email or "").strip().lower()
        chave = hash_de(email_normalizado)
        ip = _ip_curto(ip)

        falhas_email = self._tentativas.contar(TIPO_LOGIN, JANELA_LOGIN, chave_email=chave,
                                               somente_falhas=True)
        falhas_ip = self._tentativas.contar(TIPO_LOGIN, JANELA_LOGIN, ip=ip,
                                            somente_falhas=True) if ip else 0
        if falhas_email >= LIMITE_LOGIN_POR_EMAIL or falhas_ip >= LIMITE_LOGIN_POR_IP:
            raise MuitasTentativas(
                "Muitas tentativas de entrada. Aguarde 15 minutos e tente de novo, "
                "ou use 'Esqueci minha senha'."
            )

        usuario = self._usuarios.buscar_por_email(email_normalizado) if email_normalizado else None
        if usuario is None:
            self._senhas.gastar_tempo_de_verificacao(senha)
            senha_confere = False
        else:
            senha_confere = self._senhas.verificar(usuario.senha_hash, senha)

        if not senha_confere:
            with self._uow.transacao():
                self._tentativas.registrar(TIPO_LOGIN, chave, ip, sucesso=False)
            raise NaoAutenticado(MENSAGEM_LOGIN_INVALIDO)

        with self._uow.transacao():
            self._tentativas.registrar(TIPO_LOGIN, chave, ip, sucesso=True)
        if not usuario.ativo:
            raise AcessoNegado("Esta conta está desativada. Fale com o administrador do sistema.")

        with self._uow.transacao():
            if self._senhas.precisa_atualizar(usuario.senha_hash):
                self._usuarios.atualizar_senha(usuario, self._senhas.gerar_hash(senha))
            token = self._abrir_sessao(usuario)
        return ResultadoEntrada(usuario, token)

    def _abrir_sessao(self, usuario: Usuario) -> str:
        """Precisa rodar dentro de uma transação."""
        token = gerar_token()
        self._sessoes.criar(usuario.id, hash_de(token), self._validade_sessao)
        self._sessoes.registrar_acesso(usuario.id)
        return token

    # -------------------------------------------------------------------- sessão
    def sessao_atual(self, token: str | None) -> SessaoAtual:
        if not token_com_formato_valido(token):
            raise NaoAutenticado("Entre na sua conta para continuar.")
        encontrada: tuple[Sessao, Usuario] | None = self._sessoes.buscar_valida(hash_de(token))
        if encontrada is None:
            raise NaoAutenticado("Sua sessão terminou. Entre de novo.")
        sessao, usuario = encontrada
        if not usuario.ativo:
            with self._uow.transacao():
                self._sessoes.revogar(sessao.id, "conta_desativada")
            raise NaoAutenticado("Esta conta está desativada. Fale com o administrador do sistema.")
        with self._uow.transacao():
            self._sessoes.registrar_uso(sessao.id, usuario.id)
        return SessaoAtual(usuario=usuario, sessao_id=sessao.id)

    def sair(self, token: str | None) -> None:
        """Encerra a sessão do token, se existir. Sem sessão, não faz nada."""
        if not token_com_formato_valido(token):
            return
        encontrada = self._sessoes.buscar_valida(hash_de(token))
        if encontrada is not None:
            with self._uow.transacao():
                self._sessoes.revogar(encontrada[0].id, "logout")

    # ------------------------------------------------------------- troca de senha
    def alterar_senha(self, atual: SessaoAtual, senha_atual: str, nova_senha: str,
                      confirmacao: str) -> None:
        usuario = atual.usuario
        if not self._senhas.verificar(usuario.senha_hash, senha_atual):
            raise DadosInvalidos("A senha atual está incorreta.", campo="senha_atual")
        self._senhas.validar_nova_senha(nova_senha, confirmacao, email=usuario.email,
                                        campo="nova_senha")
        if self._senhas.verificar(usuario.senha_hash, nova_senha):
            raise DadosInvalidos("A nova senha precisa ser diferente da atual.", campo="nova_senha")
        novo_hash = self._senhas.gerar_hash(nova_senha)
        with self._uow.transacao():
            self._usuarios.atualizar_senha(usuario, novo_hash)
            # Outros aparelhos saem; este continua conectado.
            self._sessoes.revogar_do_usuario(usuario.id, "senha_alterada",
                                             exceto_sessao_id=atual.sessao_id)
            self._recuperacoes.cancelar_pendentes(usuario.id)

    # --------------------------------------------------------------- recuperação
    def solicitar_recuperacao(self, email: str, ip: str | None) -> MensagemEmail | None:
        """Devolve o e-mail a enviar, ou None. A resposta da API é a mesma nos
        dois casos, para não revelar se o e-mail tem conta."""
        ip = _ip_curto(ip)
        if ip and self._tentativas.contar(TIPO_RECUPERACAO, JANELA_RECUPERACAO,
                                          ip=ip) >= LIMITE_RECUPERACAO_POR_IP:
            raise MuitasTentativas("Muitos pedidos de recuperação. Aguarde uma hora e tente de novo.")
        email = normalizar_email(email)
        chave = hash_de(email)
        excedeu = self._tentativas.contar(TIPO_RECUPERACAO, JANELA_RECUPERACAO,
                                          chave_email=chave) >= LIMITE_RECUPERACAO_POR_EMAIL
        with self._uow.transacao():
            self._tentativas.registrar(TIPO_RECUPERACAO, chave, ip, sucesso=True)
        if excedeu:
            return None
        usuario = self._usuarios.buscar_por_email(email)
        if usuario is None or not usuario.ativo:
            return None
        token = gerar_token()
        with self._uow.transacao():
            self._recuperacoes.cancelar_pendentes(usuario.id)
            self._recuperacoes.criar(usuario.id, hash_de(token), self._validade_link)
        return self._email_de_recuperacao(usuario, token)

    def _email_de_recuperacao(self, usuario: Usuario, token: str) -> MensagemEmail:
        # O token vai depois do "#": essa parte do endereço não é enviada a
        # nenhum servidor, nem aparece em logs.
        link = f"{self._url_frontend}/redefinir-senha#token={token}"
        minutos = int(self._validade_link.total_seconds() // 60)
        texto = (
            f"Olá, {usuario.nome}.\n\n"
            "Recebemos um pedido para redefinir a senha da sua conta no Meu Veículo.\n\n"
            f"Para criar uma senha nova, abra o link abaixo. Ele vale por {minutos} minutos "
            "e só pode ser usado uma vez:\n\n"
            f"{link}\n\n"
            "Se não foi você, ignore esta mensagem: sua senha atual continua valendo.\n"
        )
        return MensagemEmail(para=usuario.email, assunto="Meu Veículo: redefinir sua senha",
                             texto=texto)

    def redefinir_senha(self, token: str, nova_senha: str, confirmacao: str) -> None:
        """Consome o link e troca a senha na MESMA transação.

        Se a troca falhar, o link continua válido; se o link já tiver sido
        usado (inclusive por outra requisição simultânea), nada muda.
        Depois da troca, todas as sessões do usuário são encerradas.
        """
        if not token_com_formato_valido(token):
            raise DadosInvalidos(MENSAGEM_LINK_INVALIDO, campo="token")
        self._senhas.validar_nova_senha(nova_senha, confirmacao, campo="nova_senha")
        with self._uow.transacao():
            usuario_id = self._recuperacoes.consumir(hash_de(token))
            usuario = self._usuarios.buscar_por_id(usuario_id) if usuario_id else None
            if usuario is None or not usuario.ativo:
                raise DadosInvalidos(MENSAGEM_LINK_INVALIDO, campo="token")
            self._senhas.validar_nova_senha(nova_senha, confirmacao, email=usuario.email,
                                            campo="nova_senha")
            self._usuarios.atualizar_senha(usuario, self._senhas.gerar_hash(nova_senha))
            self._sessoes.revogar_do_usuario(usuario.id, "senha_redefinida")
            self._recuperacoes.cancelar_pendentes(usuario.id)
