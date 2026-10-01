"""Migration 0008: total do abastecimento coerente com litros × preço (tolerância de R$ 0,10)."""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0007 import novo_abastecimento


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


def test_banco_na_0007_com_totais_coerentes_atualiza_sem_mudar_nada(banco_vazio):
    subir(banco_vazio, "0007")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    novo_abastecimento(banco_vazio, veiculo, "165.17")   # 38,5 × 4,29 = 165,165
    novo_abastecimento(banco_vazio, veiculo, "165.20", km=85200)  # cupom: 3 centavos a mais
    antes = linhas(banco_vazio, "SELECT * FROM abastecimento ORDER BY id")
    subir(banco_vazio, "0008")
    assert linhas(banco_vazio, "SELECT * FROM abastecimento ORDER BY id") == antes


def test_para_sem_alterar_nada_com_total_incoerente(banco_vazio):
    subir(banco_vazio, "0007")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    errado = novo_abastecimento(banco_vazio, veiculo, "16.52")  # vírgula no lugar errado
    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0008")
    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem and "15.6" in mensagem
    assert f"abastecimento {errado} (veículo {veiculo}" in mensagem and "R$ 165.17" in mensagem
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0007"


def test_na_0008_o_banco_recusa_total_fora_da_tolerancia(banco_vazio):
    # A regra da 0008 (R$ 0,10); a 0009 a trocou por R$ 50,00.
    subir(banco_vazio, "0008")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    novo_abastecimento(banco_vazio, veiculo, "165.27")  # 10 centavos: aceito
    with pytest.raises(DBAPIError):
        novo_abastecimento(banco_vazio, veiculo, "165.28", km=85300)  # 11 centavos: recusado
    assert valor(banco_vazio, "SELECT count(*) FROM abastecimento") == 1


def test_desfazer_e_refazer_a_0008(banco_migrado, veiculo):
    novo_abastecimento(banco_migrado, veiculo, "165.17")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0007")
    assert valor(banco_migrado, "SELECT count(*) FROM pg_constraint "
                                "WHERE conname = 'abastecimento_total_coerente'") == 0
    subir(banco_migrado, "0008")
    assert valor(banco_migrado, "SELECT count(*) FROM abastecimento") == 1
