"""Migration 0005: itens da manutenção (peças e mão de obra) e o total conferido pelo banco.

Testes direto no PostgreSQL de teste: as regras valem também fora da API.
"""

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0004 import nova_manutencao


def novo_item(conexao, manutencao_id: int, tipo: str, nome: str, preco: str) -> None:
    conexao.execute(
        text("INSERT INTO manutencao_item (manutencao_id, tipo, nome, valor) "
             "VALUES (:m, :t, :n, CAST(:v AS numeric))"),
        {"m": manutencao_id, "t": tipo, "n": nome, "v": preco},
    )


def total(engine, manutencao_id: int) -> str:
    return str(valor(engine, "SELECT valor FROM manutencao WHERE id = :m", m=manutencao_id))


def manutencao_com_itens(engine, veiculo_id: int) -> int:
    """Filtro de óleo 70,00 + troca 20,00 = 90,00, gravados como o backend faz."""
    manutencao = nova_manutencao(engine, veiculo_id)
    with engine.begin() as conexao:
        novo_item(conexao, manutencao, "peca", "Filtro de óleo", "70.00")
        novo_item(conexao, manutencao, "mao_de_obra", "Troca do filtro de óleo", "20.00")
        conexao.execute(text("UPDATE manutencao SET valor = 90.00 WHERE id = :m"), {"m": manutencao})
    return manutencao


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


# ------------------------------------------------------------- instalação e atualização

def test_banco_vazio_ate_a_0005_tem_a_tabela_de_itens(banco_migrado):
    colunas = linhas(banco_migrado,
                     "SELECT column_name FROM information_schema.columns "
                     "WHERE table_name = 'manutencao_item' ORDER BY ordinal_position")
    assert [c for (c,) in colunas] == ["id", "manutencao_id", "tipo", "nome", "valor", "criado_em"]


def test_banco_na_0004_preserva_as_manutencoes_sem_inventar_divisao(banco_vazio):
    subir(banco_vazio, "0004")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    antiga = nova_manutencao(banco_vazio, veiculo, km=85000)
    executar(banco_vazio, "UPDATE manutencao SET valor = 350.00 WHERE id = :m", m=antiga)
    leitura_antes = linhas(banco_vazio, "SELECT id, quilometragem FROM leitura_km "
                                        "WHERE origem = 'manutencao'")

    subir(banco_vazio, "0005")

    assert total(banco_vazio, antiga) == "350.00"
    assert valor(banco_vazio, "SELECT count(*) FROM manutencao_item") == 0
    # A migration não tocou nas manutenções: a leitura do hodômetro é a mesma.
    assert linhas(banco_vazio, "SELECT id, quilometragem FROM leitura_km "
                               "WHERE origem = 'manutencao'") == leitura_antes


def test_desfazer_e_refazer_a_0005_mantem_o_total(banco_migrado, veiculo):
    manutencao = manutencao_com_itens(banco_migrado, veiculo)
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0004")
    assert valor(banco_migrado, "SELECT to_regclass('manutencao_item')") is None
    assert total(banco_migrado, manutencao) == "90.00"
    subir(banco_migrado, "0005")
    assert valor(banco_migrado, "SELECT count(*) FROM manutencao_item") == 0
    assert total(banco_migrado, manutencao) == "90.00"


# --------------------------------------------------------------------- total = soma

def test_com_itens_o_banco_troca_um_total_diferente_pela_soma(banco_migrado, veiculo):
    manutencao = manutencao_com_itens(banco_migrado, veiculo)
    executar(banco_migrado, "UPDATE manutencao SET valor = 5.00 WHERE id = :m", m=manutencao)
    assert total(banco_migrado, manutencao) == "90.00"


def test_banco_desfaz_a_transacao_se_o_total_nao_bate_com_os_itens(banco_migrado, veiculo):
    manutencao = nova_manutencao(banco_migrado, veiculo)
    with pytest.raises(DBAPIError) as erro:
        with banco_migrado.begin() as conexao:
            novo_item(conexao, manutencao, "peca", "Filtro de óleo", "70.00")
            # sem gravar o total: a conferência no fim da transação recusa
    assert "difere da soma dos itens" in str(erro.value)
    assert valor(banco_migrado, "SELECT count(*) FROM manutencao_item") == 0
    assert total(banco_migrado, manutencao) == "0.00"


def test_sem_itens_o_valor_manual_fica_como_informado(banco_migrado, veiculo):
    manutencao = nova_manutencao(banco_migrado, veiculo)
    executar(banco_migrado, "UPDATE manutencao SET valor = 50.00 WHERE id = :m", m=manutencao)
    assert total(banco_migrado, manutencao) == "50.00"


def test_centavos_somados_sem_erro_de_arredondamento(banco_migrado, veiculo):
    manutencao = nova_manutencao(banco_migrado, veiculo)
    with banco_migrado.begin() as conexao:
        for nome, preco in (("Arruela", "0.10"), ("Anel", "0.20"), ("Junta", "33.33")):
            novo_item(conexao, manutencao, "peca", nome, preco)
        conexao.execute(text("UPDATE manutencao SET valor = 0 WHERE id = :m"), {"m": manutencao})
    assert total(banco_migrado, manutencao) == "33.63"


@pytest.mark.parametrize("tipo, nome, preco", [
    ("acessorio", "Tapete", "10.00"),  # tipo fora da lista
    ("peca", "   ", "10.00"),           # nome só com espaços
    ("peca", "Filtro", "-1.00"),        # valor negativo (domínio dinheiro)
])
def test_banco_recusa_item_invalido(banco_migrado, veiculo, tipo, nome, preco):
    manutencao = nova_manutencao(banco_migrado, veiculo)
    with pytest.raises(DBAPIError):
        with banco_migrado.begin() as conexao:
            novo_item(conexao, manutencao, tipo, nome, preco)
    assert valor(banco_migrado, "SELECT count(*) FROM manutencao_item") == 0


# ------------------------------------------------------------------------ exclusão

def test_apagar_a_manutencao_apaga_os_itens(banco_migrado, veiculo):
    manutencao = manutencao_com_itens(banco_migrado, veiculo)
    outra = manutencao_com_itens(banco_migrado, veiculo)
    executar(banco_migrado, "DELETE FROM manutencao WHERE id = :m", m=manutencao)
    assert linhas(banco_migrado, "SELECT DISTINCT manutencao_id FROM manutencao_item") == [(outra,)]


def test_apagar_o_veiculo_apaga_manutencoes_e_itens(banco_migrado, veiculo):
    manutencao_com_itens(banco_migrado, veiculo)
    executar(banco_migrado, "DELETE FROM veiculo WHERE id = :v", v=veiculo)
    assert valor(banco_migrado, "SELECT count(*) FROM manutencao_item") == 0
