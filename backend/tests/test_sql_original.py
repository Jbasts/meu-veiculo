"""Leitura e proteção do SQL original (não precisam do banco)."""

import pytest

from app.banco.sql_original import (
    CAMINHO_SQL_ORIGINAL,
    SqlOriginalAlterado,
    ler_sql_original,
    remover_transacao,
    sql_original_para_executar,
)


def test_sql_original_confere_com_a_impressao_digital():
    texto = ler_sql_original()
    assert "CREATE TABLE usuario" in texto
    assert "CREATE VIEW vw_historico" in texto


def test_quebras_de_linha_do_windows_nao_mudam_a_impressao_digital(tmp_path):
    copia = tmp_path / "original_crlf.sql"
    conteudo = CAMINHO_SQL_ORIGINAL.read_bytes().replace(b"\r\n", b"\n")
    copia.write_bytes(conteudo.replace(b"\n", b"\r\n"))
    assert ler_sql_original(copia) == ler_sql_original()


def test_arquivo_alterado_e_recusado(tmp_path):
    copia = tmp_path / "alterado.sql"
    texto = CAMINHO_SQL_ORIGINAL.read_text(encoding="utf-8")
    copia.write_text(texto.replace("NUMERIC(12,2)", "NUMERIC(14,2)"), encoding="utf-8")
    with pytest.raises(SqlOriginalAlterado):
        ler_sql_original(copia)


def test_remove_apenas_begin_e_commit():
    texto = ler_sql_original()
    sem = sql_original_para_executar()
    linhas_removidas = set(texto.split("\n")) - set(sem.split("\n"))
    assert linhas_removidas == {"BEGIN;", "COMMIT;"}
    assert len(texto.split("\n")) - len(sem.split("\n")) == 2


def test_script_sem_commit_e_recusado():
    with pytest.raises(SqlOriginalAlterado):
        remover_transacao("BEGIN;\nCREATE TABLE x (id int);\n")
