"""Migration 0010: tipos de cada combustível (tabela da Paula) e eletricidade."""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0007 import novo_abastecimento


def com_tipo(engine, abastecimento_id: int, combustivel: str, tipo: str | None) -> None:
    executar(engine, "UPDATE abastecimento SET combustivel = :c, tipo = :t WHERE id = :a",
             c=combustivel, t=tipo, a=abastecimento_id)


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


def test_banco_na_0009_converte_os_tipos_sem_perder_informacao(banco_vazio):
    subir(banco_vazio, "0009")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    ids = [novo_abastecimento(banco_vazio, veiculo, "165.17", km=85000 + i * 100) for i in range(5)]
    com_tipo(banco_vazio, ids[0], "gasolina", "comum")
    com_tipo(banco_vazio, ids[1], "gasolina", "aditivada")
    com_tipo(banco_vazio, ids[2], "etanol", "comum")
    com_tipo(banco_vazio, ids[3], "etanol", "aditivada")
    com_tipo(banco_vazio, ids[4], "gasolina", None)  # não informado
    subir(banco_vazio, "0010")
    assert linhas(banco_vazio, "SELECT combustivel, tipo FROM abastecimento ORDER BY id") == [
        ("gasolina", "comum"), ("gasolina", "comum_aditivada"), ("etanol", "comum"),
        ("etanol", "aditivado"), ("gasolina", None)]


def test_para_sem_alterar_nada_com_diesel_comum_ou_aditivada(banco_vazio):
    subir(banco_vazio, "0009")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    diesel = novo_abastecimento(banco_vazio, veiculo, "165.17")
    com_tipo(banco_vazio, diesel, "diesel", "aditivada")
    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0010")
    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem and "15.6" in mensagem
    assert f"abastecimento {diesel} (veículo {veiculo}" in mensagem and 'diesel "aditivada"' in mensagem
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0009"
    assert valor(banco_vazio, "SELECT tipo FROM abastecimento") == "aditivada"


@pytest.mark.parametrize("combustivel, tipo", [
    ("gasolina", "premium_aditivada"), ("etanol", "premium_aditivado"), ("diesel", "s500_aditivado"),
    ("eletrica", "dc"), ("gnv", None),
])
def test_banco_aceita_os_tipos_da_tabela(banco_migrado, veiculo, combustivel, tipo):
    a = novo_abastecimento(banco_migrado, veiculo, "165.17")
    com_tipo(banco_migrado, a, combustivel, tipo)
    assert valor(banco_migrado, "SELECT tipo FROM abastecimento") == tipo


@pytest.mark.parametrize("combustivel, tipo", [
    ("gasolina", "aditivado"), ("etanol", "comum_aditivada"), ("diesel", "comum"), ("eletrica", "comum"),
    ("gnv", "comum"), ("hidrogenio", None),
])
def test_banco_recusa_tipo_de_outro_combustivel(banco_migrado, veiculo, combustivel, tipo):
    a = novo_abastecimento(banco_migrado, veiculo, "165.17")
    with pytest.raises(DBAPIError):
        com_tipo(banco_migrado, a, combustivel, tipo)


def test_desfazer_e_refazer_a_0010(banco_migrado, veiculo):
    a = novo_abastecimento(banco_migrado, veiculo, "165.17")
    com_tipo(banco_migrado, a, "gasolina", "comum_aditivada")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0009")
    assert valor(banco_migrado, "SELECT tipo FROM abastecimento") == "aditivada"
    subir(banco_migrado, "0010")
    assert valor(banco_migrado, "SELECT tipo FROM abastecimento") == "comum_aditivada"


def test_nao_volta_para_a_0009_com_tipos_que_so_existem_na_0010(banco_migrado, veiculo):
    a = novo_abastecimento(banco_migrado, veiculo, "165.17")
    com_tipo(banco_migrado, a, "eletrica", "ac")
    with pytest.raises(RuntimeError, match="Não dá para voltar"):
        command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0009")
    assert valor(banco_migrado, "SELECT version_num FROM alembic_version") == "0010"
