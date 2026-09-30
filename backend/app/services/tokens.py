"""Tokens aleatórios (sessão e links) e seus hashes.

O token vai para o navegador (cookie) ou para o link do e-mail; o banco
guarda só o SHA-256. Um token tem 256 bits aleatórios: impossível de adivinhar.
"""

import hashlib
import secrets

TAMANHO_MAXIMO_TOKEN = 128


def gerar_token() -> str:
    return secrets.token_urlsafe(32)


def hash_de(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def token_com_formato_valido(token: str | None) -> bool:
    return bool(token) and len(token) <= TAMANHO_MAXIMO_TOKEN
