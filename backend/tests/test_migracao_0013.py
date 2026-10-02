"""Migration 0013: as imagens das fotos passam da pasta para o PostgreSQL."""

import logging

import pytest
from alembic import command

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor


def subir_com_pasta(engine, pasta, versao: str = "0013") -> None:
    cfg = config_alembic(engine, configurar_logs=False)
    cfg.attributes["pasta_fotos"] = pasta
    command.upgrade(cfg, versao)


def nova_foto(engine, veiculo_id: int, arquivo: str, tamanho: int = 3) -> int:
    return executar(engine, "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes) "
                            "VALUES (:v, :a, 'image/jpeg', :t) RETURNING id",
                    v=veiculo_id, a=arquivo, t=tamanho).scalar()


def test_banco_vazio_ganha_a_tabela_sem_ler_pasta_nenhuma(banco_vazio, tmp_path):
    subir_com_pasta(banco_vazio, tmp_path / "nao_existe")
    assert valor(banco_vazio, "SELECT count(*) FROM foto_conteudo") == 0


def test_copia_as_imagens_da_pasta_sem_apagar_nada(banco_vazio, tmp_path, caplog):
    subir(banco_vazio, "0012")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    pasta = tmp_path / "storage"
    (pasta / "veiculos" / str(veiculo)).mkdir(parents=True)
    (pasta / f"veiculos/{veiculo}/a.jpg").write_bytes(b"AAA")
    (pasta / f"veiculos/{veiculo}/vazia.jpg").write_bytes(b"")
    com_arquivo = nova_foto(banco_vazio, veiculo, f"veiculos/{veiculo}/a.jpg")
    sem_arquivo = nova_foto(banco_vazio, veiculo, f"veiculos/{veiculo}/sumiu.jpg")
    vazia = nova_foto(banco_vazio, veiculo, f"veiculos/{veiculo}/vazia.jpg")
    fora = nova_foto(banco_vazio, veiculo, "../fora.jpg")  # caminho que sai da pasta
    (tmp_path / "fora.jpg").write_bytes(b"NAO")
    antes = linhas(banco_vazio, "SELECT * FROM veiculo_foto ORDER BY id")

    with caplog.at_level(logging.INFO, logger="alembic.runtime.migration"):
        subir_com_pasta(banco_vazio, pasta)

    assert linhas(banco_vazio, "SELECT foto_id, dados FROM foto_conteudo") == [(com_arquivo, b"AAA")]
    assert linhas(banco_vazio, "SELECT * FROM veiculo_foto ORDER BY id") == antes  # nada mudou
    assert (pasta / f"veiculos/{veiculo}/a.jpg").exists()  # nada foi apagado
    log = caplog.text
    assert "1 de 4 fotos copiadas" in log
    assert f"foto {sem_arquivo} (veiculos/{veiculo}/sumiu.jpg)" in log
    assert f"foto {fora} (../fora.jpg)" in log
    assert f"foto {vazia}" in log and "vazio(s) ou acima de 10 MB" in log


def test_apagar_a_foto_apaga_a_imagem(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    foto = nova_foto(banco_migrado, veiculo, "x.jpg")
    executar(banco_migrado, "INSERT INTO foto_conteudo VALUES (:f, 'abc')", f=foto)
    executar(banco_migrado, "DELETE FROM veiculo_foto WHERE id = :f", f=foto)
    assert valor(banco_migrado, "SELECT count(*) FROM foto_conteudo") == 0


@pytest.mark.parametrize("tamanho", [0, 10_485_761])
def test_banco_recusa_imagem_vazia_ou_acima_de_10_mb(banco_migrado, tamanho):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    foto = nova_foto(banco_migrado, veiculo, "x.jpg")
    with pytest.raises(Exception):
        executar(banco_migrado, "INSERT INTO foto_conteudo VALUES (:f, :d)", f=foto, d=b"x" * tamanho)


def test_desfazer_a_0013_recusa_se_houver_imagens(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    foto = nova_foto(banco_migrado, veiculo, "x.jpg")
    executar(banco_migrado, "INSERT INTO foto_conteudo VALUES (:f, 'abc')", f=foto)
    with pytest.raises(RuntimeError, match="restaure um backup"):
        command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0012")
    assert valor(banco_migrado, "SELECT count(*) FROM foto_conteudo") == 1
    executar(banco_migrado, "DELETE FROM foto_conteudo")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0012")
    assert valor(banco_migrado, "SELECT to_regclass('public.foto_conteudo') IS NULL")
