"""Regra única de acesso a veículos, usada por todos os módulos.

Um veículo (e tudo o que está ligado a ele) é visível para o dono e para
administradores. Para os demais, a resposta é a mesma de um veículo que não
existe ("não encontrado"): assim ninguém descobre, testando números, quais
veículos existem.

O id vem do endereço da requisição, mas nunca é aceito sem esta conferência.
"""

from app.entities.usuario import Usuario
from app.entities.veiculo import Veiculo
from app.services.erros import Conflito, NaoEncontrado

MENSAGEM_NAO_ENCONTRADO = "Veículo não encontrado."
MENSAGEM_INATIVO = (
    "Este veículo está inativo: o histórico pode ser consultado, mas não alterado. "
    "Reative o veículo para registrar novos dados."
)


def pode_acessar(usuario: Usuario, veiculo: Veiculo) -> bool:
    return usuario.eh_admin or veiculo.usuario_id == usuario.id


class AcessoVeiculo:
    def __init__(self, veiculos):
        self._veiculos = veiculos

    def exigir(self, usuario: Usuario, veiculo_id: int, *, bloquear: bool = False) -> Veiculo:
        """Devolve o veículo se o usuário puder vê-lo; senão, NaoEncontrado.

        bloquear=True segura a linha do veículo até o fim da transação.
        """
        veiculo = (self._veiculos.bloquear(veiculo_id) if bloquear
                   else self._veiculos.buscar(veiculo_id))
        if veiculo is None or not pode_acessar(usuario, veiculo):
            raise NaoEncontrado(MENSAGEM_NAO_ENCONTRADO)
        return veiculo

    def exigir_para_alterar(self, usuario: Usuario, veiculo_id: int, *,
                            bloquear: bool = False) -> Veiculo:
        """Como exigir(), mas recusa veículo inativo (só leitura)."""
        veiculo = self.exigir(usuario, veiculo_id, bloquear=bloquear)
        if not veiculo.ativo:
            raise Conflito(MENSAGEM_INATIVO)
        return veiculo
