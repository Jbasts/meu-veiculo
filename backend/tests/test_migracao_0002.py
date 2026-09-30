"""Migration 0002: e-mails antigos, tabelas novas e proteção do último admin."""

import threading
import time

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.banco.migracoes import config_alembic
from tests.conftest import criar_com_sql_original_sem_controle


def banco_na_0001_com_usuarios(engine, emails: list[str]) -> None:
    command.upgrade(config_alembic(engine, configurar_logs=False), "0001")
    with engine.begin() as conexao:
        for i, email in enumerate(emails):
            conexao.execute(
                text("INSERT INTO usuario (nome, email, senha_hash) VALUES (:n, :e, 'h')"),
                {"n": f"Pessoa {i}", "e": email},
            )


def emails(engine) -> list[str]:
    with engine.connect() as conexao:
        return list(conexao.execute(text("SELECT email FROM usuario ORDER BY id")).scalars())


def test_normaliza_emails_antigos_sem_colisao(banco_vazio):
    banco_na_0001_com_usuarios(banco_vazio, ["  Paula@Email.com ", "rafael@email.com"])
    command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "0002")
    assert emails(banco_vazio) == ["paula@email.com", "rafael@email.com"]


def test_para_sem_alterar_nada_quando_emails_colidem(banco_vazio):
    # O índice lower(email) do SQL original aceita estes dois, porque um tem espaço.
    banco_na_0001_com_usuarios(banco_vazio, ["ana@email.com", " Ana@email.com"])
    with pytest.raises(RuntimeError) as erro:
        command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "0002")
    assert "ficariam iguais a 'ana@email.com'" in str(erro.value)
    assert "Nada foi alterado" in str(erro.value)
    assert emails(banco_vazio) == ["ana@email.com", " Ana@email.com"]
    with banco_vazio.connect() as conexao:
        versao = conexao.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert versao == "0001"


def test_para_quando_ha_email_sem_arroba(banco_vazio):
    banco_na_0001_com_usuarios(banco_vazio, ["sem-arroba"])
    with pytest.raises(RuntimeError, match="sem '@'"):
        command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "0002")
    assert emails(banco_vazio) == ["sem-arroba"]


def test_banco_adotado_recebe_a_0002(banco_vazio):
    criar_com_sql_original_sem_controle(banco_vazio)
    from app.banco.migracoes import adotar_banco_existente, migrar

    adotar_banco_existente(engine=banco_vazio, configurar_logs=False)
    estado, _ = migrar(engine=banco_vazio, backup=False, configurar_logs=False)
    assert estado.pendentes == []
    with banco_vazio.connect() as conexao:
        assert conexao.execute(text("SELECT to_regclass('public.sessao') IS NOT NULL")).scalar()


def test_banco_recusa_email_fora_do_padrao(banco_migrado):
    for email in ("Paula@email.com", " paula@email.com", "sem-arroba"):
        with banco_migrado.connect() as conexao:
            with pytest.raises(IntegrityError):
                conexao.execute(
                    text("INSERT INTO usuario (nome, email, senha_hash) VALUES ('P', :e, 'h')"),
                    {"e": email},
                )


# ------------------------------------------------------------- último admin

def criar_usuario(conexao, email: str, perfil: str = "padrao") -> int:
    return conexao.execute(
        text("INSERT INTO usuario (nome, email, senha_hash, perfil) "
             "VALUES ('X', :e, 'h', :p) RETURNING id"),
        {"e": email, "p": perfil},
    ).scalar()


def test_nao_deixa_desativar_nem_rebaixar_o_ultimo_admin(banco_migrado):
    with banco_migrado.begin() as conexao:
        admin = criar_usuario(conexao, "admin@email.com", "admin")
    for comando in ("UPDATE usuario SET ativo = FALSE WHERE id = :i",
                    "UPDATE usuario SET perfil = 'padrao' WHERE id = :i",
                    "DELETE FROM usuario WHERE id = :i"):
        with banco_migrado.connect() as conexao:
            with pytest.raises(DBAPIError, match="último administrador ativo"):
                conexao.execute(text(comando), {"i": admin})


def test_com_dois_admins_um_pode_sair(banco_migrado):
    with banco_migrado.begin() as conexao:
        a = criar_usuario(conexao, "a@email.com", "admin")
        criar_usuario(conexao, "b@email.com", "admin")
        conexao.execute(text("UPDATE usuario SET ativo = FALSE WHERE id = :i"), {"i": a})
    with banco_migrado.connect() as conexao:
        ativos = conexao.execute(
            text("SELECT count(*) FROM usuario WHERE perfil = 'admin' AND ativo")
        ).scalar()
    assert ativos == 1


def test_sistema_sem_admin_continua_funcionando(banco_migrado):
    """Antes do primeiro admin, usuários padrão podem ser alterados normalmente."""
    with banco_migrado.begin() as conexao:
        u = criar_usuario(conexao, "u@email.com")
        conexao.execute(text("UPDATE usuario SET ativo = FALSE WHERE id = :i"), {"i": u})


def test_dois_admins_desativados_ao_mesmo_tempo_um_e_recusado(banco_migrado):
    with banco_migrado.begin() as conexao:
        a = criar_usuario(conexao, "a@email.com", "admin")
        b = criar_usuario(conexao, "b@email.com", "admin")

    primeira_alterou = threading.Event()
    resultados: dict[str, str] = {}

    def primeira() -> None:
        # Desativa "a" e demora para confirmar: a transação fica aberta.
        with banco_migrado.begin() as conexao:
            conexao.execute(text("UPDATE usuario SET ativo = FALSE WHERE id = :i"), {"i": a})
            primeira_alterou.set()
            time.sleep(0.8)
        resultados["primeira"] = "ok"

    def segunda() -> None:
        # Enquanto a primeira não confirmou, "a" ainda parece ativo.
        # Sem a trava, esta também passaria e o sistema ficaria sem admin.
        primeira_alterou.wait(timeout=10)
        try:
            with banco_migrado.begin() as conexao:
                conexao.execute(text("UPDATE usuario SET ativo = FALSE WHERE id = :i"), {"i": b})
            resultados["segunda"] = "ok"
        except DBAPIError:
            resultados["segunda"] = "recusado"

    tarefas = [threading.Thread(target=primeira), threading.Thread(target=segunda)]
    for tarefa in tarefas:
        tarefa.start()
    for tarefa in tarefas:
        tarefa.join(timeout=30)

    assert resultados == {"primeira": "ok", "segunda": "recusado"}
    with banco_migrado.connect() as conexao:
        ativos = conexao.execute(
            text("SELECT count(*) FROM usuario WHERE perfil = 'admin' AND ativo")
        ).scalar()
    assert ativos == 1
