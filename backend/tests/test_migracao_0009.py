"""Migration 0009: tipo do combustível (comum/aditivada) e tolerância do cupom de R$ 50,00."""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0007 import novo_abastecimento


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


def test_banco_na_0008_atualiza_sem_inventar_o_tipo(banco_vazio):
    subir(banco_vazio, "0008")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    antigo = novo_abastecimento(banco_vazio, veiculo, "165.17")
    subir(banco_vazio, "0009")
    assert linhas(banco_vazio, "SELECT id, tipo, valor_total::text FROM abastecimento") == [
        (antigo, None, "165.17")]


def test_tolerancia_do_cupom_de_50_reais(banco_migrado, veiculo):
    novo_abastecimento(banco_migrado, veiculo, "215.17")  # 165,17 + 50,00: aceito
    with pytest.raises(DBAPIError):
        novo_abastecimento(banco_migrado, veiculo, "215.18", km=85300)  # 50,01: recusado
    assert valor(banco_migrado, "SELECT count(*) FROM abastecimento") == 1


def test_na_0009_tipo_invalido_e_gnv_com_tipo_sao_recusados(banco_vazio):
    # A regra da 0009 (comum/aditivada); a 0010 a trocou pelos tipos de cada combustível.
    subir(banco_vazio, "0009")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    gid = novo_abastecimento(banco_vazio, veiculo, "165.17")
    executar(banco_vazio, "UPDATE abastecimento SET tipo = 'aditivada' WHERE id = :a", a=gid)
    with pytest.raises(DBAPIError):
        executar(banco_vazio, "UPDATE abastecimento SET tipo = 'premium' WHERE id = :a", a=gid)
    with pytest.raises(DBAPIError):
        executar(banco_vazio, "UPDATE abastecimento SET combustivel = 'gnv' WHERE id = :a", a=gid)
    assert valor(banco_vazio, "SELECT tipo FROM abastecimento") == "aditivada"


def test_desfazer_e_refazer_a_0009(banco_migrado, veiculo):
    novo_abastecimento(banco_migrado, veiculo, "190.00")  # 24,83 acima: só vale na regra nova
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0008")
    # O dado gravado com a regra nova continua (a regra antiga volta só para gravações novas).
    assert valor(banco_migrado, "SELECT valor_total::text FROM abastecimento") == "190.00"
    assert valor(banco_migrado, "SELECT count(*) FROM information_schema.columns "
                                "WHERE table_name = 'abastecimento' AND column_name = 'tipo'") == 0
    subir(banco_migrado, "0009")
    assert valor(banco_migrado, "SELECT count(*) FROM abastecimento") == 1
