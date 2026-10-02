"""Instalação em banco vazio, adoção de banco existente e backup.

Todos rodam no PostgreSQL de teste.
"""

import pytest
from alembic import command
from sqlalchemy import text

from app.banco.backup import BackupFalhou, fazer_backup
from app.banco.conexao import conectar_psycopg
from app.banco.migracoes import (
    ErroMigracao,
    EstruturaDiferente,
    adotar_banco_existente,
    config_alembic,
    ler_estado,
    migrar,
    versao_mais_recente,
)
from app.banco.sql_original import comparar_com_original
from app.config import obter_configuracoes
from tests.conftest import criar_com_sql_original_sem_controle

TODAS = ["0001", "0002", "0003", "0004", "0005", "0006", "0007", "0008", "0009", "0010", "0011", "0012", "0013"]


def tem_tabela(engine, nome: str) -> bool:
    with engine.connect() as conexao:
        return conexao.execute(text("SELECT to_regclass(:n) IS NOT NULL"), {"n": nome}).scalar()


def test_banco_vazio_tem_todas_as_migrations_pendentes(banco_vazio):
    estado = ler_estado(banco_vazio)
    assert estado.situacao == "vazio"
    assert estado.versao_atual is None
    assert estado.pendentes == TODAS
    assert estado.pendentes[0] == "0001"


def test_migrar_banco_vazio_aplica_tudo_sem_backup(banco_vazio):
    estado, backup = migrar(engine=banco_vazio, configurar_logs=False)
    assert backup is None  # banco vazio não tem o que salvar
    assert estado.situacao == "controlado"
    assert estado.versao_atual == versao_mais_recente()
    assert estado.pendentes == []
    assert tem_tabela(banco_vazio, "public.usuario")


def test_0001_cria_estrutura_identica_ao_sql_original(banco_vazio):
    command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "0001")
    with conectar_psycopg(banco_vazio.url.database) as conexao:
        diferencas = comparar_com_original(conexao)
        conexao.rollback()
    assert diferencas.iguais, diferencas.descrever()
    # A comparação não deixa o esquema temporário para trás.
    assert not tem_tabela(banco_vazio, "mv_referencia_original.usuario")


def test_migrar_de_novo_nao_faz_nada(banco_migrado):
    estado, backup = migrar(engine=banco_migrado, configurar_logs=False)
    assert backup is None
    assert estado.versao_atual == versao_mais_recente()
    assert estado.pendentes == []


def test_migrar_banco_com_dados_faz_backup_antes(banco_vazio, tmp_path):
    command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "0001")
    cfg = obter_configuracoes().model_copy(update={"pasta_backups": tmp_path})
    estado, backup = migrar(engine=banco_vazio, configurar_logs=False, cfg=cfg)
    assert backup is not None and backup.parent == tmp_path
    assert backup.read_bytes()[:5] == b"PGDMP"
    assert "antes_de_migrar" in backup.name
    assert estado.pendentes == []


def test_migrar_recusa_banco_existente_sem_controle(banco_vazio):
    criar_com_sql_original_sem_controle(banco_vazio)
    with banco_vazio.begin() as conexao:
        conexao.execute(text(
            "INSERT INTO usuario (nome, email, senha_hash) VALUES ('Ana', 'ana@x.com', 'h')"
        ))
    assert ler_estado(banco_vazio).situacao == "sem_controle"
    with pytest.raises(ErroMigracao, match="adotar-banco-existente"):
        migrar(engine=banco_vazio, configurar_logs=False)
    assert not tem_tabela(banco_vazio, "public.alembic_version")
    with banco_vazio.connect() as conexao:
        assert conexao.execute(text("SELECT count(*) FROM usuario")).scalar() == 1


def test_a_propria_0001_recusa_rodar_sobre_tabelas_existentes(banco_vazio):
    """Mesmo chamando o Alembic direto (sem o gerenciar.py), o SQL não roda duas vezes."""
    criar_com_sql_original_sem_controle(banco_vazio)
    with pytest.raises(RuntimeError, match="adotar-banco-existente"):
        command.upgrade(config_alembic(banco_vazio, configurar_logs=False), "head")
    assert not tem_tabela(banco_vazio, "public.alembic_version")


def test_adotar_banco_criado_com_sql_original_preserva_dados(banco_vazio):
    criar_com_sql_original_sem_controle(banco_vazio)
    with banco_vazio.begin() as conexao:
        conexao.execute(text(
            "INSERT INTO usuario (nome, email, senha_hash) VALUES ('Ana', 'ana@x.com', 'h')"
        ))
    estado = adotar_banco_existente(engine=banco_vazio, configurar_logs=False)
    assert estado.situacao == "controlado"
    assert estado.versao_atual == "0001"
    assert estado.pendentes == TODAS[1:]  # as migrations novas ficam para o "migrar"
    with banco_vazio.connect() as conexao:
        assert conexao.execute(text("SELECT nome FROM usuario")).scalar() == "Ana"


def test_adotar_recusa_estrutura_diferente_e_lista_as_diferencas(banco_vazio):
    criar_com_sql_original_sem_controle(banco_vazio)
    with banco_vazio.begin() as conexao:
        conexao.execute(text("DROP VIEW vw_historico"))
        conexao.execute(text("ALTER TABLE veiculo ADD COLUMN apelido VARCHAR(30)"))
    with pytest.raises(EstruturaDiferente) as erro:
        adotar_banco_existente(engine=banco_vazio, configurar_logs=False)
    faltando = {(tipo, item[0]) for tipo, item in erro.value.diferencas.faltando}
    sobrando = {(tipo, item[0], item[1]) for tipo, item in erro.value.diferencas.sobrando}
    assert ("view", "vw_historico") in faltando
    assert ("coluna", "veiculo", "apelido") in sobrando
    assert "vw_historico" in str(erro.value)
    assert not tem_tabela(banco_vazio, "public.alembic_version")


def test_adotar_recusa_banco_vazio_e_banco_ja_controlado(banco_vazio):
    with pytest.raises(ErroMigracao, match="vazio"):
        adotar_banco_existente(engine=banco_vazio, configurar_logs=False)
    migrar(engine=banco_vazio, backup=False, configurar_logs=False)
    with pytest.raises(ErroMigracao, match="já tem controle"):
        adotar_banco_existente(engine=banco_vazio, configurar_logs=False)


def test_0001_nao_e_desfeita_automaticamente(banco_migrado):
    with pytest.raises(RuntimeError, match="restaure um backup"):
        command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "base")
    assert tem_tabela(banco_migrado, "public.usuario")


def test_backup_gera_arquivo_restauravel(banco_migrado, tmp_path):
    cfg = obter_configuracoes().model_copy(update={"pasta_backups": tmp_path})
    arquivo = fazer_backup(banco_migrado.url.database, motivo="teste", cfg=cfg)
    assert arquivo.parent == tmp_path
    assert arquivo.stat().st_size > 0
    # Formato custom do pg_dump começa com "PGDMP".
    assert arquivo.read_bytes()[:5] == b"PGDMP"


def test_backup_com_falha_nao_deixa_arquivo_pela_metade(tmp_path):
    cfg = obter_configuracoes().model_copy(update={"pasta_backups": tmp_path})
    with pytest.raises(BackupFalhou):
        fazer_backup("banco_que_nao_existe_teste", motivo="teste", cfg=cfg)
    assert list(tmp_path.iterdir()) == []
