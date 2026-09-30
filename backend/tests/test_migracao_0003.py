"""Migration 0003: placas antigas, leituras de quilometragem e veículo em uso.

Os testes de trigger rodam direto no PostgreSQL de teste, sem passar pela API:
as regras valem também para quem mexer no banco por fora (pgAdmin).
"""

import logging

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.banco.migracoes import config_alembic


def subir(engine, versao: str) -> None:
    command.upgrade(config_alembic(engine, configurar_logs=False), versao)


def executar(engine, sql: str, **parametros):
    with engine.begin() as conexao:
        return conexao.execute(text(sql), parametros)


def valor(engine, sql: str, **parametros):
    with engine.connect() as conexao:
        return conexao.execute(text(sql), parametros).scalar()


def linhas(engine, sql: str, **parametros) -> list[tuple]:
    with engine.connect() as conexao:
        return [tuple(linha) for linha in conexao.execute(text(sql), parametros)]


def novo_usuario(engine, email: str = "ana@x.com") -> int:
    return executar(
        engine, "INSERT INTO usuario (nome, email, senha_hash) VALUES ('Ana', :e, 'h') RETURNING id",
        e=email,
    ).scalar()


def novo_veiculo(engine, usuario_id: int, placa: str = "ABC1234", km: int = 85000) -> int:
    return executar(
        engine,
        "INSERT INTO veiculo (usuario_id, marca, modelo, ano, placa, quilometragem) "
        "VALUES (:u, 'Honda', 'Civic', 2020, :p, :km) RETURNING id",
        u=usuario_id, p=placa, km=km,
    ).scalar()


def km_atual(engine, veiculo_id: int) -> tuple:
    return linhas(engine, "SELECT quilometragem, data_leitura_km FROM veiculo WHERE id = :v",
                  v=veiculo_id)[0]


# ----------------------------------------------------------- placas antigas

def test_normaliza_placas_antigas_sem_colisao(banco_vazio):
    subir(banco_vazio, "0002")
    usuario = novo_usuario(banco_vazio)
    novo_veiculo(banco_vazio, usuario, "abc-1234")
    novo_veiculo(banco_vazio, usuario, "bra 2e19")
    subir(banco_vazio, "0003")
    assert linhas(banco_vazio, "SELECT placa FROM veiculo ORDER BY id") == [("ABC1234",), ("BRA2E19",)]


def test_mesma_placa_em_donos_diferentes_continua_permitida(banco_vazio):
    """A unicidade é por dono; a migration não a transforma em global."""
    subir(banco_vazio, "0002")
    novo_veiculo(banco_vazio, novo_usuario(banco_vazio, "ana@x.com"), "ABC-1234")
    novo_veiculo(banco_vazio, novo_usuario(banco_vazio, "bia@x.com"), "abc1234")
    subir(banco_vazio, "0003")
    assert linhas(banco_vazio, "SELECT placa FROM veiculo ORDER BY id") == [("ABC1234",), ("ABC1234",)]


def test_para_sem_alterar_nada_quando_placas_do_mesmo_dono_colidem(banco_vazio):
    subir(banco_vazio, "0002")
    usuario = novo_usuario(banco_vazio)
    a = novo_veiculo(banco_vazio, usuario, "ABC-1234")
    b = novo_veiculo(banco_vazio, usuario, "abc1234")
    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0003")
    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem
    assert f"usuário {usuario}" in mensagem and "'ABC1234'" in mensagem
    assert f"{a} (ABC-1234)" in mensagem and f"{b} (abc1234)" in mensagem
    # Nenhum veículo foi apagado, unido ou alterado, e a versão continua a 0002.
    assert linhas(banco_vazio, "SELECT placa FROM veiculo ORDER BY id") == [("ABC-1234",), ("abc1234",)]
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0002"


def test_para_quando_ha_placa_com_caractere_invalido(banco_vazio):
    subir(banco_vazio, "0002")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio), "AB.1234")
    with pytest.raises(RuntimeError, match=f"veículo {veiculo}.*'AB.1234'"):
        subir(banco_vazio, "0003")
    assert valor(banco_vazio, "SELECT placa FROM veiculo") == "AB.1234"


def test_banco_recusa_placa_fora_do_padrao(banco_migrado):
    usuario = novo_usuario(banco_migrado)
    for placa in ("abc1234", "ABC-1234", "ABC 123"):
        with pytest.raises(IntegrityError):
            novo_veiculo(banco_migrado, usuario, placa)


# ------------------------------------------- leituras a partir de dados antigos

def test_registros_antigos_viram_leituras_com_as_datas_deles(banco_vazio):
    subir(banco_vazio, "0002")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio), km=80000)
    executar(banco_vazio,
             "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
             "valor_litro, valor_total) VALUES (:v, '2026-09-20', 85000, 'gasolina', 40, 6.25, 250)",
             v=veiculo)
    executar(banco_vazio,
             "INSERT INTO manutencao (veiculo_id, descricao, status, data, quilometragem) VALUES "
             "(:v, 'Pneus', 'realizada', '2026-09-02', 83900), "
             "(:v, 'Revisão', 'agendada', '2026-12-01', 90000)", v=veiculo)
    executar(banco_vazio,
             "INSERT INTO diagnostico (veiculo_id, titulo, data_identificacao, quilometragem) "
             "VALUES (:v, 'Barulho', '2026-09-10', 84300)", v=veiculo)
    subir(banco_vazio, "0003")

    leituras = linhas(banco_vazio,
                      "SELECT origem, quilometragem, data_leitura::text FROM leitura_km "
                      "ORDER BY quilometragem")
    assert leituras == [
        ("manutencao", 83900, "2026-09-02"),
        ("diagnostico", 84300, "2026-09-10"),
        ("abastecimento", 85000, "2026-09-20"),
    ]  # a manutenção agendada não vira leitura
    atual, data = km_atual(banco_vazio, veiculo)
    assert (atual, str(data)) == (85000, "2026-09-20")


def test_km_atual_sem_registro_vira_leitura_herdada_sem_data(banco_vazio):
    """A data do km antigo é desconhecida: fica NULL, não é inventada."""
    subir(banco_vazio, "0002")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio), km=85000)
    executar(banco_vazio,
             "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
             "valor_litro, valor_total) VALUES (:v, '2026-08-01', 82000, 'gasolina', 40, 6.25, 250)",
             v=veiculo)
    subir(banco_vazio, "0003")
    assert linhas(banco_vazio,
                  "SELECT origem, quilometragem, data_leitura::text FROM leitura_km "
                  "ORDER BY quilometragem") == [("abastecimento", 82000, "2026-08-01"),
                                                ("legado", 85000, None)]
    assert km_atual(banco_vazio, veiculo) == (85000, None)


def test_km_atual_menor_que_registro_e_corrigido_com_aviso(banco_vazio, caplog):
    """Caso deixado pelo trigger antigo: agendada que virou realizada sem atualizar o km."""
    subir(banco_vazio, "0002")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio), km=85000)
    manutencao = executar(
        banco_vazio,
        "INSERT INTO manutencao (veiculo_id, descricao, status, data, quilometragem) "
        "VALUES (:v, 'Revisão', 'agendada', '2026-09-25', 86000) RETURNING id", v=veiculo).scalar()
    executar(banco_vazio, "UPDATE manutencao SET status = 'realizada' WHERE id = :m", m=manutencao)
    assert valor(banco_vazio, "SELECT quilometragem FROM veiculo") == 85000  # o defeito do SQL original
    with caplog.at_level(logging.WARNING, logger="alembic.runtime.migration"):
        subir(banco_vazio, "0003")
    assert "o km atual era 85000, mas há registro com 86000 km" in caplog.text
    atual, data = km_atual(banco_vazio, veiculo)
    assert (atual, str(data)) == (86000, "2026-09-25")


def test_desfazer_e_refazer_a_0003(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0002")
    assert valor(banco_migrado, "SELECT to_regclass('public.leitura_km') IS NULL")
    subir(banco_migrado, "0003")
    assert km_atual(banco_migrado, veiculo) == (85000, None)  # voltou como leitura herdada


# ----------------------------------------------------- regras de quilometragem

INSERIR_ABASTECIMENTO = (
    "INSERT INTO abastecimento (veiculo_id, data, quilometragem, combustivel, litros, "
    "valor_litro, valor_total) VALUES (:v, :d, :km, 'gasolina', 40, 6.25, 250) RETURNING id"
)


@pytest.fixture
def veiculo(banco_migrado) -> int:
    return novo_veiculo(banco_migrado, novo_usuario(banco_migrado), km=85000)


def test_veiculo_novo_ganha_a_leitura_do_cadastro(banco_migrado, veiculo):
    assert linhas(banco_migrado,
                  "SELECT origem, quilometragem, data_leitura = current_date FROM leitura_km") == [
        ("cadastro", 85000, True)]
    assert valor(banco_migrado, "SELECT data_leitura_km = current_date FROM veiculo")


def test_registro_historico_nao_reduz_a_quilometragem_atual(banco_migrado, veiculo):
    executar(banco_migrado, INSERIR_ABASTECIMENTO, v=veiculo, d="2026-01-10", km=70000)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000
    assert valor(banco_migrado, "SELECT count(*) FROM leitura_km") == 2  # mas entra no histórico


def test_manutencao_agendada_nao_aumenta_a_quilometragem(banco_migrado, veiculo):
    executar(banco_migrado,
             "INSERT INTO manutencao (veiculo_id, descricao, status, data, quilometragem) "
             "VALUES (:v, 'Revisão', 'agendada', current_date, 90000)", v=veiculo)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000
    assert valor(banco_migrado, "SELECT count(*) FROM leitura_km WHERE origem = 'manutencao'") == 0


def test_mudar_so_o_status_para_realizada_atualiza_a_quilometragem(banco_migrado, veiculo):
    """O trigger original só disparava em INSERT ou UPDATE OF quilometragem."""
    manutencao = executar(
        banco_migrado,
        "INSERT INTO manutencao (veiculo_id, descricao, status, data, quilometragem) "
        "VALUES (:v, 'Revisão', 'agendada', '2026-09-25', 86500) RETURNING id", v=veiculo).scalar()
    executar(banco_migrado, "UPDATE manutencao SET status = 'realizada' WHERE id = :m", m=manutencao)
    atual, data = km_atual(banco_migrado, veiculo)
    assert (atual, str(data)) == (86500, "2026-09-25")
    # E o caminho de volta: reclassificar para agendada retira a leitura.
    executar(banco_migrado, "UPDATE manutencao SET status = 'agendada' WHERE id = :m", m=manutencao)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000


def test_manutencao_realizada_inserida_direto_atualiza_a_quilometragem(banco_migrado, veiculo):
    executar(banco_migrado,
             "INSERT INTO manutencao (veiculo_id, descricao, status, data, quilometragem) "
             "VALUES (:v, 'Óleo', 'realizada', '2026-09-26', 86000)", v=veiculo)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 86000


def test_corrigir_ou_apagar_registro_errado_recalcula_a_quilometragem(banco_migrado, veiculo):
    abastecimento = executar(banco_migrado, INSERIR_ABASTECIMENTO, v=veiculo, d="2026-09-27",
                             km=854500).scalar()  # digitou um zero a mais
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 854500
    executar(banco_migrado, "UPDATE abastecimento SET quilometragem = 85450 WHERE id = :a",
             a=abastecimento)
    atual, data = km_atual(banco_migrado, veiculo)
    assert (atual, str(data)) == (85450, "2026-09-27")
    executar(banco_migrado, "DELETE FROM abastecimento WHERE id = :a", a=abastecimento)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000
    assert valor(banco_migrado, "SELECT count(*) FROM leitura_km") == 1


def test_diagnostico_com_km_gera_leitura_na_data_de_identificacao(banco_migrado, veiculo):
    executar(banco_migrado,
             "INSERT INTO diagnostico (veiculo_id, titulo, data_identificacao, quilometragem) "
             "VALUES (:v, 'Barulho', '2026-09-28', 85200)", v=veiculo)
    atual, data = km_atual(banco_migrado, veiculo)
    assert (atual, str(data)) == (85200, "2026-09-28")


def test_leitura_anulada_deixa_de_contar(banco_migrado, veiculo):
    leitura = executar(
        banco_migrado,
        "INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem) "
        "VALUES (:v, 99000, current_date, 'manual') RETURNING id", v=veiculo).scalar()
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 99000
    executar(banco_migrado, "UPDATE leitura_km SET anulada_em = now() WHERE id = :i", i=leitura)
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000


def test_ninguem_altera_a_quilometragem_do_veiculo_direto(banco_migrado, veiculo):
    for comando in ("UPDATE veiculo SET quilometragem = 1",
                    "UPDATE veiculo SET data_leitura_km = '2020-01-01'"):
        with pytest.raises(DBAPIError, match="calculada a partir das leituras"):
            executar(banco_migrado, comando)
    executar(banco_migrado, "UPDATE veiculo SET cor = 'Prata'")  # outros campos, normalmente
    assert valor(banco_migrado, "SELECT quilometragem FROM veiculo") == 85000


def test_apagar_veiculo_apaga_as_leituras_sem_erro(banco_migrado, veiculo):
    executar(banco_migrado, INSERIR_ABASTECIMENTO, v=veiculo, d="2026-09-27", km=85450)
    executar(banco_migrado, "DELETE FROM veiculo WHERE id = :v", v=veiculo)
    assert valor(banco_migrado, "SELECT count(*) FROM leitura_km") == 0


# --------------------------------------------------------------- veículo em uso

def test_veiculo_em_uso_precisa_ser_do_proprio_usuario(banco_migrado):
    ana = novo_usuario(banco_migrado, "ana@x.com")
    bia = novo_usuario(banco_migrado, "bia@x.com")
    carro_da_ana = novo_veiculo(banco_migrado, ana)
    executar(banco_migrado, "UPDATE usuario SET veiculo_em_uso_id = :v WHERE id = :u",
             v=carro_da_ana, u=ana)
    with pytest.raises(IntegrityError):
        executar(banco_migrado, "UPDATE usuario SET veiculo_em_uso_id = :v WHERE id = :u",
                 v=carro_da_ana, u=bia)
    # Apagar o veículo só limpa a escolha; o usuário continua existindo.
    executar(banco_migrado, "DELETE FROM veiculo WHERE id = :v", v=carro_da_ana)
    assert linhas(banco_migrado, "SELECT id, veiculo_em_uso_id FROM usuario WHERE id = :u",
                  u=ana) == [(ana, None)]
