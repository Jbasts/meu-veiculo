"""Migration 0007: data do pagamento, pendente com vencimento e despesas sem duplicar.

Testes direto no PostgreSQL de teste: as regras valem também fora da API.
"""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0004 import nova_manutencao


def novo_gasto(engine, veiculo_id: int, valor_: str = "30.00", pago: bool = True,
               data: str = "2026-09-18", vencimento: str | None = None,
               pagamento: str | None = None, categoria: str = "estacionamento",
               com_pagamento: bool = True) -> int:
    colunas = "veiculo_id, categoria, valor, data, pago, data_vencimento"
    valores = ":v, :c, CAST(:valor AS numeric), :d, :p, :venc"
    if com_pagamento:
        colunas += ", data_pagamento"
        valores += ", :pag"
    return executar(engine, f"INSERT INTO gasto ({colunas}) VALUES ({valores}) RETURNING id",
                    v=veiculo_id, c=categoria, valor=valor_, d=data, p=pago, venc=vencimento,
                    pag=pagamento).scalar()


def novo_abastecimento(engine, veiculo_id: int, valor_total: str, data: str = "2026-09-15",
                       km: int = 85100, posto: str | None = "Shell") -> int:
    return executar(
        engine,
        "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
        "valor_litro, valor_total, posto) VALUES (:v, :d, :km, 'gasolina', 38.5, 4.29, "
        "CAST(:t AS numeric), :posto) RETURNING id",
        v=veiculo_id, d=data, km=km, t=valor_total, posto=posto).scalar()


def novo_item_de_projeto(engine, veiculo_id: int, valor_: str, data: str = "2026-09-10",
                         status: str = "em_andamento") -> int:
    projeto = executar(engine, "INSERT INTO projeto (veiculo_id, nome, status) "
                               "VALUES (:v, 'Rodas', :s) RETURNING id", v=veiculo_id, s=status).scalar()
    return executar(engine, "INSERT INTO projeto_item (projeto_id, descricao, data, valor) "
                            "VALUES (:p, 'Jogo de rodas', :d, CAST(:valor AS numeric)) RETURNING id",
                    p=projeto, d=data, valor=valor_).scalar()


def despesas(engine, veiculo_id: int) -> list[tuple]:
    return linhas(engine, "SELECT tipo, categoria, data::text, valor::text FROM vw_despesa "
                          "WHERE veiculo_id = :v ORDER BY data, tipo", v=veiculo_id)


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado))


# ------------------------------------------------------------- instalação e atualização

def test_banco_na_0006_com_gastos_antigos_atualiza_sem_inventar_datas(banco_vazio):
    subir(banco_vazio, "0006")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    pago = novo_gasto(banco_vazio, veiculo, com_pagamento=False)
    pendente = novo_gasto(banco_vazio, veiculo, pago=False, vencimento="2026-11-10",
                          com_pagamento=False)

    subir(banco_vazio, "0007")

    assert linhas(banco_vazio, "SELECT id, pago, data_pagamento FROM gasto ORDER BY id") == [
        (pago, True, None), (pendente, False, None)]
    # O pago antigo conta pela data do gasto; o pendente não conta.
    assert despesas(banco_vazio, veiculo) == [("gasto", "estacionamento", "2026-09-18", "30.00")]


def test_para_sem_alterar_nada_quando_ha_pendente_sem_vencimento(banco_vazio):
    subir(banco_vazio, "0006")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    sem_vencimento = novo_gasto(banco_vazio, veiculo, pago=False, categoria="seguro",
                                valor_="2400.00", com_pagamento=False)

    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0007")

    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem and "14.6" in mensagem
    assert f"gasto {sem_vencimento} (veículo {veiculo}, seguro, R$ 2400.00, lançado em 18/09/2026)" in mensagem
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0006"
    assert valor(banco_vazio, "SELECT count(*) FROM information_schema.columns "
                              "WHERE table_name = 'gasto' AND column_name = 'data_pagamento'") == 0


def test_desfazer_e_refazer_a_0007(banco_migrado, veiculo):
    novo_gasto(banco_migrado, veiculo, pagamento="2026-09-20")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0006")
    assert valor(banco_migrado, "SELECT to_regclass('vw_despesa')") is None
    assert valor(banco_migrado, "SELECT data::text FROM vw_historico WHERE tipo = 'gasto'") == "2026-09-18"
    subir(banco_migrado, "0007")
    assert valor(banco_migrado, "SELECT count(*) FROM gasto") == 1


# ------------------------------------------------------------------------- regras

def test_banco_recusa_pendente_sem_vencimento_ou_com_pagamento(banco_migrado, veiculo):
    with pytest.raises(DBAPIError):
        novo_gasto(banco_migrado, veiculo, pago=False)
    with pytest.raises(DBAPIError):
        novo_gasto(banco_migrado, veiculo, pago=False, vencimento="2026-11-10", pagamento="2026-09-20")
    assert valor(banco_migrado, "SELECT count(*) FROM gasto") == 0


def test_gasto_pago_entra_no_mes_do_pagamento(banco_migrado, veiculo):
    # Lançado em setembro, pago em novembro: entra em novembro (despesa e histórico).
    gasto = novo_gasto(banco_migrado, veiculo, valor_="2400.00", categoria="seguro",
                       data="2026-09-24", pagamento="2026-11-08")
    assert despesas(banco_migrado, veiculo) == [("gasto", "seguro", "2026-11-08", "2400.00")]
    assert valor(banco_migrado, "SELECT data::text FROM vw_historico WHERE origem_id = :g "
                                "AND tipo = 'gasto'", g=gasto) == "2026-11-08"


def test_despesas_sem_agendada_sem_pendente_e_com_projeto_cancelado(banco_migrado, veiculo):
    realizada = nova_manutencao(banco_migrado, veiculo, data="2026-09-02")
    executar(banco_migrado, "UPDATE manutencao SET valor = 1800.00 WHERE id = :m", m=realizada)
    agendada = nova_manutencao(banco_migrado, veiculo, status="agendada", data="2026-09-28")
    executar(banco_migrado, "UPDATE manutencao SET valor = 350.00 WHERE id = :m", m=agendada)
    novo_abastecimento(banco_migrado, veiculo, "165.17")
    novo_gasto(banco_migrado, veiculo, pagamento="2026-09-18")
    novo_gasto(banco_migrado, veiculo, pago=False, vencimento="2026-09-30", valor_="99.00")
    novo_item_de_projeto(banco_migrado, veiculo, "500.00", status="cancelado")

    assert despesas(banco_migrado, veiculo) == [
        ("manutencao", "manutencao", "2026-09-02", "1800.00"),
        ("projeto", "projeto", "2026-09-10", "500.00"),
        ("abastecimento", "combustivel", "2026-09-15", "165.17"),
        ("gasto", "estacionamento", "2026-09-18", "30.00"),
    ]


def test_manutencao_com_itens_conta_uma_vez(banco_migrado, veiculo):
    from tests.test_migracao_0005 import manutencao_com_itens
    manutencao_com_itens(banco_migrado, veiculo)  # 70 + 20 = 90
    assert despesas(banco_migrado, veiculo) == [("manutencao", "manutencao", "2026-09-01", "90.00")]
