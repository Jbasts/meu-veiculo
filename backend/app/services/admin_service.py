"""Regras da área de administração (PDF, páginas 18 e 22).

Quem pode
- Só administradores. As routes já exigem AdminDep; o service confere de
  novo, para a regra valer mesmo se for chamado por outro caminho.

Usuários
- Lista com busca por nome ou e-mail, filtro por perfil e paginação estável.
- Alterar perfil e ativar/desativar. O admin não altera a própria conta por
  aqui (decisão da Paula, 01/10/2026): evita perder o acesso sem querer;
  outro admin faz a mudança. O banco ainda impede ficar sem admin ativo
  (trigger garantir_admin_ativo, migration 0002), inclusive com duas
  alterações ao mesmo tempo.
- Desativar encerra na hora todas as sessões da pessoa e cancela links de
  senha ainda não usados.
- "Enviar link para nova senha": o admin nunca vê nem define senha. Conta que
  nunca entrou (ultimo_acesso vazio, por exemplo um convite não aceito) recebe
  um convite novo (CONVITE_DIAS); as demais, um link de recuperação
  (RECUPERACAO_MINUTOS). Conta desativada não recebe link.
- Botão "+": cria a conta de outra pessoa com perfil padrão e uma senha
  aleatória que ninguém conhece; ela define a senha pelo convite.

Veículos
- Lista de todos os veículos com o dono, busca por marca, modelo, placa ou
  dono e paginação estável. O detalhe abre as mesmas telas do dono: as rotas
  de veículo já aceitam admin (services/acesso_veiculo.py).
"""

from dataclasses import dataclass
from typing import Protocol

from app.entities.usuario import PERFIL_ADMIN, PERFIL_PADRAO, Usuario, UsuarioResumo
from app.entities.veiculo import VeiculoComDono
from app.repositories.erros import EmailJaCadastrado, UltimoAdministrador
from app.services.email_service import MensagemEmail
from app.services.erros import AcessoNegado, Conflito, DadosInvalidos, NaoEncontrado
from app.services.paginacao import Pagina, limite_e_deslocamento
from app.services.senha_service import SenhaService
from app.services.tokens import gerar_token
from app.services.validacao import normalizar_email, normalizar_nome

PERFIS = (PERFIL_ADMIN, PERFIL_PADRAO)
TAMANHO_MAXIMO_BUSCA = 100
MAXIMO_DE_VEICULOS_NO_DETALHE = 100


class Transacional(Protocol):
    def transacao(self): ...


@dataclass(frozen=True)
class ResumoAdmin:
    usuarios: int
    veiculos: int


@dataclass(frozen=True)
class PaginaUsuarios:
    itens: list[UsuarioResumo]
    total: int
    pagina: int
    por_pagina: int
    por_perfil: dict[str, int]   # contagens para os botões Todos / Admin / Padrão


@dataclass(frozen=True)
class UsuarioDetalheAdmin:
    usuario: UsuarioResumo
    veiculos: list[VeiculoComDono]


@dataclass(frozen=True)
class LinkEnviado:
    tipo: str                    # convite | recuperacao
    mensagem: MensagemEmail


def _exigir_admin(usuario: Usuario) -> None:
    if not usuario.eh_admin:
        raise AcessoNegado("Área restrita a administradores.")


def _busca(texto: str | None) -> str | None:
    texto = " ".join((texto or "").split())
    return texto[:TAMANHO_MAXIMO_BUSCA] or None


class AdminService:
    def __init__(self, uow: Transacional, consultas, usuarios, sessoes, recuperacoes, links,
                 senhas: SenhaService):
        self._uow = uow
        self._consultas = consultas
        self._usuarios = usuarios
        self._sessoes = sessoes
        self._recuperacoes = recuperacoes
        self._links = links            # AutenticacaoService: monta os e-mails com link
        self._senhas = senhas

    # ------------------------------------------------------------------ consulta
    def resumo(self, admin: Usuario) -> ResumoAdmin:
        _exigir_admin(admin)
        return ResumoAdmin(usuarios=sum(self._consultas.contagem_por_perfil(None).values()),
                           veiculos=self._consultas.contar_veiculos(None, None))

    def listar_usuarios(self, admin: Usuario, busca: str | None = None, perfil: str | None = None,
                        pagina: int = 1, por_pagina: int = 30) -> PaginaUsuarios:
        _exigir_admin(admin)
        if perfil is not None and perfil not in PERFIS:
            raise DadosInvalidos("Perfil inválido.", campo="perfil")
        busca = _busca(busca)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        por_perfil = {p: 0 for p in PERFIS} | self._consultas.contagem_por_perfil(busca)
        return PaginaUsuarios(
            itens=self._consultas.usuarios(busca, perfil, limite, deslocamento),
            total=por_perfil.get(perfil, 0) if perfil else sum(por_perfil.values()),
            pagina=pagina, por_pagina=por_pagina, por_perfil=por_perfil,
        )

    def obter_usuario(self, admin: Usuario, usuario_id: int) -> UsuarioDetalheAdmin:
        _exigir_admin(admin)
        resumo = self._consultas.usuario(usuario_id)
        if resumo is None:
            raise NaoEncontrado("Usuário não encontrado.")
        return UsuarioDetalheAdmin(resumo, self._consultas.veiculos(
            None, usuario_id, MAXIMO_DE_VEICULOS_NO_DETALHE, 0))

    def listar_veiculos(self, admin: Usuario, busca: str | None = None, pagina: int = 1,
                        por_pagina: int = 30) -> Pagina[VeiculoComDono]:
        _exigir_admin(admin)
        busca = _busca(busca)
        pagina, por_pagina, limite, deslocamento = limite_e_deslocamento(pagina, por_pagina)
        return Pagina(itens=self._consultas.veiculos(busca, None, limite, deslocamento),
                      total=self._consultas.contar_veiculos(busca, None),
                      pagina=pagina, por_pagina=por_pagina)

    # ------------------------------------------------------------------ gravação
    def alterar(self, admin: Usuario, usuario_id: int, perfil: str | None,
                ativo: bool | None) -> UsuarioDetalheAdmin:
        _exigir_admin(admin)
        if usuario_id == admin.id:
            raise Conflito("Você não pode mudar o próprio perfil nem desativar a própria conta "
                           "por aqui. Peça a outro administrador.")
        if perfil not in PERFIS:
            raise DadosInvalidos("Escolha o perfil: padrão ou admin.", campo="perfil")
        if ativo is None:
            raise DadosInvalidos("Informe se a conta fica ativa.", campo="ativo")
        with self._uow.transacao():
            usuario = self._usuarios.bloquear(usuario_id)
            if usuario is None:
                raise NaoEncontrado("Usuário não encontrado.")
            desativando = usuario.ativo and not ativo
            try:
                self._usuarios.alterar_acesso(usuario, perfil, ativo)
            except UltimoAdministrador:
                raise Conflito("Não é possível desativar nem rebaixar o último administrador "
                               "ativo. Promova outra conta a admin antes.") from None
            if desativando:
                # A pessoa sai de todos os aparelhos na hora, e links pendentes deixam de valer.
                self._sessoes.revogar_do_usuario(usuario.id, "conta_desativada")
                self._recuperacoes.cancelar_pendentes(usuario.id)
        return self.obter_usuario(admin, usuario_id)

    def enviar_link(self, admin: Usuario, usuario_id: int) -> LinkEnviado:
        _exigir_admin(admin)
        with self._uow.transacao():
            usuario = self._usuarios.bloquear(usuario_id)
            if usuario is None:
                raise NaoEncontrado("Usuário não encontrado.")
            if not usuario.ativo:
                raise Conflito("Esta conta está desativada. Ative a conta antes de enviar o link.")
            if usuario.ultimo_acesso is None:
                return LinkEnviado("convite", self._links.link_de_convite(usuario, admin.nome))
            return LinkEnviado("recuperacao",
                               self._links.link_de_recuperacao(usuario, pedido_pelo_admin=True))

    def convidar(self, admin: Usuario, nome: str | None,
                 email: str | None) -> tuple[UsuarioDetalheAdmin, LinkEnviado]:
        """Cria a conta (perfil padrão) e prepara o convite para a pessoa definir a senha."""
        _exigir_admin(admin)
        if not (nome or "").strip():
            raise DadosInvalidos("Informe o nome da pessoa.", campo="nome")
        nome = normalizar_nome(nome)
        email = normalizar_email(email or "")
        # Senha aleatória que ninguém conhece (nem o admin): só o convite dá acesso.
        senha_hash = self._senhas.gerar_hash(gerar_token())
        with self._uow.transacao():
            try:
                usuario = self._usuarios.criar(nome, email, senha_hash)
            except EmailJaCadastrado:
                raise Conflito("Já existe uma conta com este e-mail.", campo="email") from None
            mensagem = self._links.link_de_convite(usuario, admin.nome)
        return self.obter_usuario(admin, usuario.id), LinkEnviado("convite", mensagem)
