"""Migration 0014: confirmação do e-mail."""

import logging

import pytest
from alembic import command
from sqlalchemy.exc import IntegrityError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, novo_usuario, subir, valor


def test_contas_que_ja_existiam_continuam_entrando(banco_vazio):
    subir(banco_vazio, "0013")
    antiga = novo_usuario(banco_vazio, "antiga@x.com")
    subir(banco_vazio, "0014")
    assert valor(banco_vazio, "SELECT email_confirmado FROM usuario WHERE id = :i", i=antiga)
    # A data da confirmação não é inventada.
    assert valor(banco_vazio, "SELECT email_confirmado_em FROM usuario WHERE id = :i",
                 i=antiga) is None
    nova = novo_usuario(banco_vazio, "nova@x.com")
    assert valor(banco_vazio, "SELECT email_confirmado FROM usuario WHERE id = :i", i=nova) is False


def test_banco_recusa_data_de_confirmacao_sem_estar_confirmado(banco_migrado):
    usuario = novo_usuario(banco_migrado)
    with pytest.raises(IntegrityError, match="usuario_confirmacao_coerente_check"):
        executar(banco_migrado, "UPDATE usuario SET email_confirmado_em = now() WHERE id = :i",
                 i=usuario)


def test_finalidade_confirmacao_aceita_e_outra_recusada(banco_migrado):
    usuario = novo_usuario(banco_migrado)
    sql = ("INSERT INTO recuperacao_senha (usuario_id, token_hash, finalidade, expira_em) "
           "VALUES (:u, :h, :f, now() + interval '1 hour')")
    executar(banco_migrado, sql, u=usuario, h="a" * 64, f="confirmacao")
    with pytest.raises(IntegrityError):
        executar(banco_migrado, sql, u=usuario, h="b" * 64, f="outra")


def test_desfazer_a_0014_avisa_quem_ainda_nao_confirmou_sem_apagar_contas(banco_migrado, caplog):
    novo_usuario(banco_migrado, "pendente@x.com")
    confirmada = novo_usuario(banco_migrado, "confirmada@x.com")
    executar(banco_migrado, "UPDATE usuario SET email_confirmado = TRUE WHERE id = :i", i=confirmada)
    caplog.set_level(logging.WARNING, logger="alembic.runtime.migration")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0013")
    assert "pendente@x.com" in caplog.text and "confirmada@x.com" not in caplog.text
    assert valor(banco_migrado, "SELECT count(*) FROM usuario") == 2
    assert valor(banco_migrado, "SELECT count(*) FROM information_schema.columns "
                                "WHERE table_name = 'usuario' AND column_name LIKE 'email_conf%'") == 0
    subir(banco_migrado, "0014")  # refazer funciona
