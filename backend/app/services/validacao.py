"""Normalização e validação de dados de cadastro."""

from email_validator import EmailNotValidError, validate_email

from app.services.erros import DadosInvalidos

TAMANHO_MAXIMO_EMAIL = 160
TAMANHO_MAXIMO_NOME = 120


def normalizar_email(texto: str) -> str:
    """Tira os espaços das pontas e passa para minúsculas.

    " Paula@Email.com " e "paula@email.com" são o mesmo e-mail.
    """
    email = (texto or "").strip().lower()
    if not email:
        raise DadosInvalidos("Informe o e-mail.", campo="email")
    if len(email) > TAMANHO_MAXIMO_EMAIL:
        raise DadosInvalidos("E-mail muito longo.", campo="email")
    try:
        validate_email(email, check_deliverability=False)
    except EmailNotValidError:
        raise DadosInvalidos("E-mail inválido. Confira se está no formato nome@email.com.",
                             campo="email") from None
    return email


def normalizar_nome(texto: str) -> str:
    nome = " ".join((texto or "").split())
    if not nome:
        raise DadosInvalidos("Informe seu nome.", campo="nome")
    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise DadosInvalidos(f"Nome muito longo (máximo {TAMANHO_MAXIMO_NOME} caracteres).",
                             campo="nome")
    return nome
