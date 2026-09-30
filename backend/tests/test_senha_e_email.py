"""Política de senha, hash e envio de e-mail (sem banco)."""

import email
from email import policy

import pytest
from argon2 import PasswordHasher

from app.config import obter_configuracoes
from app.services.email_service import (
    EnviadorArquivo,
    EnviadorSmtp,
    MensagemEmail,
    criar_enviador,
    enviar_sem_interromper,
)
from app.services.erros import DadosInvalidos
from app.services.senha_service import SenhaService
from app.services.validacao import normalizar_email, normalizar_nome

SENHAS = SenhaService(PasswordHasher(time_cost=1, memory_cost=1024, parallelism=1))


def test_hash_confere_e_e_diferente_a_cada_vez():
    a = SENHAS.gerar_hash("meu carro azul 2020")
    b = SENHAS.gerar_hash("meu carro azul 2020")
    assert a != b  # sal aleatório
    assert SENHAS.verificar(a, "meu carro azul 2020")
    assert not SENHAS.verificar(a, "meu carro azul 2021")
    assert not SENHAS.verificar("não é um hash", "qualquer")


def test_hash_padrao_e_argon2id_com_parametros_da_rfc_9106():
    senha_hash = SenhaService().gerar_hash("meu carro azul 2020")
    assert senha_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")


def test_hash_com_parametros_antigos_precisa_ser_atualizado():
    antigo = SENHAS.gerar_hash("meu carro azul 2020")
    assert SenhaService().precisa_atualizar(antigo)


@pytest.mark.parametrize(
    ("senha", "trecho"),
    [
        ("1234567", "pelo menos 8"),
        ("x" * 129, "no máximo 128"),
        ("          ", "só espaços"),
        ("Senha123", "fácil de adivinhar"),
        ("ana.souza", "fácil de adivinhar"),
    ],
)
def test_politica_de_senha(senha, trecho):
    with pytest.raises(DadosInvalidos, match=trecho):
        SENHAS.validar_nova_senha(senha, senha, email="ana.souza@email.com")


def test_senha_com_acentos_e_espacos_e_aceita():
    SENHAS.validar_nova_senha("pão de queijo às 7h", "pão de queijo às 7h")


def test_normalizacoes():
    assert normalizar_email("  Ana.Souza@Email.COM ") == "ana.souza@email.com"
    assert normalizar_nome("  Ana   Souza ") == "Ana Souza"
    for invalido in ("", "ana", "ana@", "@email.com", "ana souza@email.com"):
        with pytest.raises(DadosInvalidos):
            normalizar_email(invalido)


def test_enviador_arquivo_grava_eml_legivel(tmp_path):
    enviador = EnviadorArquivo(tmp_path / "emails", "Meu Veículo <nao-responda@meuveiculo.local>")
    arquivo = enviador.enviar(MensagemEmail("ana@email.com", "Meu Veículo: teste", "Olá, Ana.\nLink: x"))
    lida = email.message_from_bytes(arquivo.read_bytes(), policy=policy.default)
    assert lida["To"] == "ana@email.com"
    assert lida["Subject"] == "Meu Veículo: teste"
    assert "Olá, Ana." in lida.get_content()


def test_link_aparece_inteiro_ao_abrir_o_arquivo_eml(tmp_path):
    """Com acentos no texto, a codificação padrão quebraria o link e trocaria "=" por "=3D"."""
    token = "Xy" * 21 + "z"  # 43 caracteres, como os tokens reais
    link = f"http://localhost:5173/redefinir-senha#token={token}"
    texto = f"Olá, Paula. Você pediu para redefinir a senha.\n\n{link}\n"
    arquivo = EnviadorArquivo(tmp_path, "Meu Veículo <x@meuveiculo.local>").enviar(
        MensagemEmail("paula@email.com", "Meu Veículo: redefinir sua senha", texto)
    )
    conteudo = arquivo.read_text(encoding="utf-8")
    assert link in conteudo
    assert "=3D" not in conteudo
    assert "Olá, Paula" in conteudo


def test_modo_do_enviador_vem_da_configuracao():
    cfg = obter_configuracoes()
    assert isinstance(criar_enviador(cfg.model_copy(update={"email_modo": "arquivo"})), EnviadorArquivo)
    assert isinstance(criar_enviador(cfg.model_copy(update={"email_modo": "smtp"})), EnviadorSmtp)


def test_falha_de_envio_so_registra_o_tipo_do_erro(caplog):
    class Quebrado:
        def enviar(self, mensagem):
            raise ConnectionRefusedError("smtp.exemplo:587 recusou ana@email.com")

    enviar_sem_interromper(Quebrado(), MensagemEmail("ana@email.com", "a", "b"))
    assert "ConnectionRefusedError" in caplog.text
    assert "ana@email.com" not in caplog.text
