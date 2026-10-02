"""Migration 0012: tamanho do tanque, nível antes de abastecer e marcação do tanque."""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, km_atual, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0007 import novo_abastecimento


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


def nova_marcacao(engine, veiculo_id: int, km: int, nivel: int, data: str = "2026-09-20") -> int:
    return executar(engine, "INSERT INTO medicao_tanque (veiculo_id, data, quilometragem, nivel) "
                            "VALUES (:v, :d, :km, :n) RETURNING id",
                    v=veiculo_id, d=data, km=km, n=nivel).scalar()


def test_banco_na_0011_ganha_as_colunas_vazias_sem_mudar_nada(banco_vazio):
    subir(banco_vazio, "0011")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    novo_abastecimento(banco_vazio, veiculo, "165.17")
    antes = linhas(banco_vazio, "SELECT * FROM abastecimento")
    subir(banco_vazio, "0012")
    assert valor(banco_vazio, "SELECT capacidade_tanque FROM veiculo") is None  # não é inventado
    assert linhas(banco_vazio, "SELECT * FROM abastecimento") == [antes[0] + (None,)]


@pytest.mark.parametrize("sql", [
    "UPDATE veiculo SET capacidade_tanque = 0",
    "UPDATE veiculo SET capacidade_tanque = 2000.1",
    "UPDATE veiculo SET tipo_combustivel = 'eletrico', capacidade_tanque = 50",
])
def test_banco_recusa_tamanho_do_tanque_invalido(banco_migrado, veiculo, sql):
    with pytest.raises(DBAPIError):
        executar(banco_migrado, sql)


@pytest.mark.parametrize("combustivel, nivel, aceita", [
    ("gasolina", 0, True), ("diesel", 8, True), ("etanol", 9, False), ("gasolina", -1, False),
    ("gnv", 4, False), ("eletrica", 4, False),
])
def test_nivel_antes_so_de_0_a_8_e_so_no_tanque_liquido(banco_migrado, veiculo, combustivel, nivel, aceita):
    a = novo_abastecimento(banco_migrado, veiculo, "165.17")
    tipo = {"diesel": "s10", "eletrica": "ac", "gnv": None}.get(combustivel, "comum")
    sql = "UPDATE abastecimento SET combustivel = :c, tipo = :t, nivel_antes = :n WHERE id = :a"
    if aceita:
        executar(banco_migrado, sql, c=combustivel, t=tipo, n=nivel, a=a)
    else:
        with pytest.raises(DBAPIError):
            executar(banco_migrado, sql, c=combustivel, t=tipo, n=nivel, a=a)


def test_marcacao_vira_leitura_do_hodometro(banco_migrado, veiculo):
    m = nova_marcacao(banco_migrado, veiculo, 86000, 4)
    assert km_atual(banco_migrado, veiculo)[0] == 86000
    assert linhas(banco_migrado, "SELECT origem, origem_id FROM leitura_km WHERE quilometragem = 86000") == [
        ("medicao_tanque", m)]
    executar(banco_migrado, "UPDATE medicao_tanque SET quilometragem = 86500 WHERE id = :m", m=m)
    assert km_atual(banco_migrado, veiculo)[0] == 86500
    executar(banco_migrado, "DELETE FROM medicao_tanque WHERE id = :m", m=m)
    assert km_atual(banco_migrado, veiculo)[0] == 85000


@pytest.mark.parametrize("nivel", [-1, 9])
def test_marcacao_com_nivel_fora_da_escala_e_recusada(banco_migrado, veiculo, nivel):
    with pytest.raises(DBAPIError):
        nova_marcacao(banco_migrado, veiculo, 86000, nivel)


def test_desfazer_e_refazer_a_0012_com_banco_sem_os_dados_novos(banco_migrado, veiculo):
    novo_abastecimento(banco_migrado, veiculo, "165.17")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0011")
    assert valor(banco_migrado, "SELECT count(*) FROM abastecimento") == 1
    subir(banco_migrado, "0012")
    assert valor(banco_migrado, "SELECT version_num FROM alembic_version") == "0012"


@pytest.mark.parametrize("dado", ["marcacao", "nivel", "tanque"])
def test_nao_volta_para_a_0011_com_dados_que_so_existem_na_0012(banco_migrado, veiculo, dado):
    if dado == "marcacao":
        nova_marcacao(banco_migrado, veiculo, 86000, 4)
    elif dado == "nivel":
        a = novo_abastecimento(banco_migrado, veiculo, "165.17")
        executar(banco_migrado, "UPDATE abastecimento SET nivel_antes = 2 WHERE id = :a", a=a)
    else:
        executar(banco_migrado, "UPDATE veiculo SET capacidade_tanque = 50")
    with pytest.raises(RuntimeError, match="Não dá para voltar"):
        command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0011")
    assert valor(banco_migrado, "SELECT version_num FROM alembic_version") == "0012"
