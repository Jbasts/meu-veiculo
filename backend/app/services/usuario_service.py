"""Regras de gestão de contas usadas fora da API.

promover_a_admin é usado pelo comando "gerenciar.py promover-admin", que
só quem tem acesso ao banco consegue rodar. Não existe endpoint público
para virar administrador.
"""

from typing import Protocol

from app.entities.usuario import PERFIL_ADMIN
from app.services.erros import DadosInvalidos, NaoEncontrado
from app.services.validacao import normalizar_email


class Transacional(Protocol):
    def transacao(self): ...


class UsuarioService:
    def __init__(self, uow: Transacional, usuarios):
        self._uow = uow
        self._usuarios = usuarios

    def promover_a_admin(self, email: str) -> bool:
        """Devolve True se promoveu, False se a conta já era admin."""
        email = normalizar_email(email)
        usuario = self._usuarios.buscar_por_email(email)
        if usuario is None:
            raise NaoEncontrado(
                f"Não há conta com o e-mail {email}. Crie a conta pela tela 'Criar conta' antes."
            )
        if not usuario.ativo:
            raise DadosInvalidos("Esta conta está desativada; não pode virar administradora.")
        if usuario.eh_admin:
            return False
        with self._uow.transacao():
            self._usuarios.definir_perfil(usuario, PERFIL_ADMIN)
        return True
