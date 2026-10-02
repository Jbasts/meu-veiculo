"""Controller da área de administração.

Os e-mails (convite e link para nova senha) são enviados depois da resposta,
como na recuperação de senha; falha no envio fica registrada só pelo tipo do
erro, sem o link.
"""

from dataclasses import asdict

from fastapi import BackgroundTasks

from app.entities.sessao import SessaoAtual
from app.schemas.admin_schema import (
    AlterarUsuarioEntrada,
    ConviteEntrada,
    ConviteResposta,
    LinkEnviadoResposta,
    PaginaUsuariosAdmin,
    PaginaVeiculosAdmin,
    ResumoAdminResposta,
    UsuarioDetalheAdminResposta,
)
from app.services.admin_service import AdminService, LinkEnviado, UsuarioDetalheAdmin
from app.services.email_service import EnviadorEmail, enviar_sem_interromper


def _detalhe(d: UsuarioDetalheAdmin) -> UsuarioDetalheAdminResposta:
    return UsuarioDetalheAdminResposta(usuario=asdict(d.usuario),
                                       veiculos=[asdict(v) for v in d.veiculos])


def _texto_do_link(link: LinkEnviado) -> str:
    if link.tipo == "convite":
        return (f"Convite enviado para {link.mensagem.para}. A pessoa define a própria senha "
                "pelo link, que só pode ser usado uma vez.")
    return (f"Link para criar uma senha nova enviado para {link.mensagem.para}. "
            "A senha atual continua valendo até ser trocada.")


class AdminController:
    def __init__(self, service: AdminService, enviador: EnviadorEmail):
        self._service = service
        self._enviador = enviador

    def resumo(self, atual: SessaoAtual) -> ResumoAdminResposta:
        return ResumoAdminResposta(**asdict(self._service.resumo(atual.usuario)))

    def listar_usuarios(self, atual: SessaoAtual, busca: str | None, perfil: str | None,
                        pagina: int, por_pagina: int) -> PaginaUsuariosAdmin:
        return PaginaUsuariosAdmin(**asdict(
            self._service.listar_usuarios(atual.usuario, busca, perfil, pagina, por_pagina)))

    def obter_usuario(self, atual: SessaoAtual, usuario_id: int) -> UsuarioDetalheAdminResposta:
        return _detalhe(self._service.obter_usuario(atual.usuario, usuario_id))

    def alterar_usuario(self, atual: SessaoAtual, usuario_id: int,
                        dados: AlterarUsuarioEntrada) -> UsuarioDetalheAdminResposta:
        return _detalhe(self._service.alterar(atual.usuario, usuario_id, dados.perfil, dados.ativo))

    def enviar_link(self, atual: SessaoAtual, usuario_id: int,
                    tarefas: BackgroundTasks) -> LinkEnviadoResposta:
        link = self._service.enviar_link(atual.usuario, usuario_id)
        tarefas.add_task(enviar_sem_interromper, self._enviador, link.mensagem)
        return LinkEnviadoResposta(tipo=link.tipo, mensagem=_texto_do_link(link))

    def convidar(self, atual: SessaoAtual, dados: ConviteEntrada,
                 tarefas: BackgroundTasks) -> ConviteResposta:
        detalhe, link = self._service.convidar(atual.usuario, dados.nome, dados.email)
        tarefas.add_task(enviar_sem_interromper, self._enviador, link.mensagem)
        return ConviteResposta(detalhe=_detalhe(detalhe), mensagem=_texto_do_link(link))

    def listar_veiculos(self, atual: SessaoAtual, busca: str | None, pagina: int,
                        por_pagina: int) -> PaginaVeiculosAdmin:
        return PaginaVeiculosAdmin(**asdict(
            self._service.listar_veiculos(atual.usuario, busca, pagina, por_pagina)))
