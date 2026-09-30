"""Política de senha e hash com Argon2id.

Algoritmo: Argon2id (vencedor da Password Hashing Competition, recomendado
pela OWASP e pela RFC 9106). Parâmetros padrão da biblioteca argon2-cffi,
que seguem o perfil de "pouca memória" da RFC 9106: 3 passadas, 64 MiB de
memória e 4 linhas em paralelo. Cada hash tem um "sal" aleatório próprio,
então duas pessoas com a mesma senha têm hashes diferentes.

Política:
- de 8 a 128 caracteres (qualquer caractere, inclusive espaço e acento);
- não pode ser só espaços;
- não pode ser igual ao e-mail nem ao que vem antes do @;
- não pode estar na lista de senhas mais usadas.
Não exigimos "uma maiúscula, um número e um símbolo": essas regras levam a
senhas previsíveis (ex.: "Senha@123"). Frases longas são mais fortes.
"""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.services.erros import DadosInvalidos

TAMANHO_MINIMO = 8
TAMANHO_MAXIMO = 128

SENHAS_COMUNS = frozenset({
    "12345678", "123456789", "1234567890", "12341234", "11111111", "00000000",
    "87654321", "88888888", "99999999", "123123123", "abcd1234", "1q2w3e4r",
    "qwerty123", "qwertyuiop", "password", "password1", "passw0rd", "iloveyou",
    "senha123", "senha1234", "senha12345", "minhasenha", "mudar123", "trocar123",
    "brasil123", "flamengo", "corinthians", "palmeiras", "saopaulo", "vasco123",
    "meuveiculo", "meucarro", "carro123", "admin123", "administrador", "abc12345",
})


class SenhaService:
    def __init__(self, hasher: PasswordHasher | None = None):
        self._hasher = hasher or PasswordHasher()
        # Hash de mentira para o login com e-mail inexistente levar o mesmo
        # tempo que o de um e-mail existente (não revela quem tem conta).
        self._hash_ficticio = self._hasher.hash("senha-ficticia-so-para-igualar-o-tempo")

    def validar_nova_senha(self, senha: str, confirmacao: str, *, email: str | None = None,
                           campo: str = "senha") -> None:
        if len(senha) < TAMANHO_MINIMO:
            raise DadosInvalidos(f"A senha precisa ter pelo menos {TAMANHO_MINIMO} caracteres.",
                                 campo=campo)
        if len(senha) > TAMANHO_MAXIMO:
            raise DadosInvalidos(f"A senha pode ter no máximo {TAMANHO_MAXIMO} caracteres.",
                                 campo=campo)
        if not senha.strip():
            raise DadosInvalidos("A senha não pode ser só espaços.", campo=campo)
        simples = senha.strip().lower()
        proibidas = set(SENHAS_COMUNS)
        if email:
            proibidas |= {email.lower(), email.split("@")[0].lower()}
        if simples in proibidas:
            raise DadosInvalidos(
                "Essa senha é fácil de adivinhar. Tente uma frase, como 'meu carro azul de 2020'.",
                campo=campo,
            )
        if senha != confirmacao:
            raise DadosInvalidos("A confirmação não é igual à senha.", campo="confirmacao_senha")

    def gerar_hash(self, senha: str) -> str:
        return self._hasher.hash(senha)

    def verificar(self, senha_hash: str, senha: str) -> bool:
        try:
            return self._hasher.verify(senha_hash, senha)
        except (VerifyMismatchError, VerificationError, InvalidHashError, ValueError):
            # ValueError cobre um hash corrompido (ex.: com acentos): nunca confere.
            return False

    def gastar_tempo_de_verificacao(self, senha: str) -> None:
        self.verificar(self._hash_ficticio, senha)

    def precisa_atualizar(self, senha_hash: str) -> bool:
        """True se o hash foi feito com parâmetros antigos (atualizado no próximo login)."""
        try:
            return self._hasher.check_needs_rehash(senha_hash)
        except (InvalidHashError, ValueError):
            return False
