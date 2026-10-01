"""Migration 0011: conclusão coerente, fotos de projeto do mesmo veículo e projeto nas despesas."""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor


def novo_projeto(engine, veiculo_id: int, status: str = "em_andamento", conclusao: str | None = None,
                 nome: str = "Rodas") -> int:
    return executar(engine, "INSERT INTO projeto (veiculo_id, nome, status, data_conclusao) "
                            "VALUES (:v, :n, :s, :c) RETURNING id",
                    v=veiculo_id, n=nome, s=status, c=conclusao).scalar()


def nova_foto(engine, veiculo_id: int, projeto_id: int | None, momento: str | None = None,
              arquivo: str = "a.jpg") -> int:
    return executar(engine, "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, "
                            "projeto_id, momento) VALUES (:v, :a, 'image/jpeg', 10, :p, :m) RETURNING id",
                    v=veiculo_id, a=arquivo, p=projeto_id, m=momento).scalar()


@pytest.fixture
def dois_veiculos(banco_migrado) -> tuple[int, int]:
    dono = novo_usuario(banco_migrado)
    return novo_veiculo(banco_migrado, dono, placa="ABC1234"), novo_veiculo(banco_migrado, dono, placa="XYZ9876")


def test_banco_na_0010_com_dados_coerentes_atualiza_sem_mudar_nada(banco_vazio):
    subir(banco_vazio, "0010")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    concluido = novo_projeto(banco_vazio, veiculo, "concluido", "2026-08-15")
    nova_foto(banco_vazio, veiculo, concluido, "depois")
    antes = linhas(banco_vazio, "SELECT * FROM projeto ORDER BY id")
    subir(banco_vazio, "0011")
    assert linhas(banco_vazio, "SELECT * FROM projeto ORDER BY id") == antes


def test_para_sem_alterar_nada_com_dados_incompativeis(banco_vazio):
    subir(banco_vazio, "0010")
    dono = novo_usuario(banco_vazio)
    civic = novo_veiculo(banco_vazio, dono, placa="ABC1234")
    moto = novo_veiculo(banco_vazio, dono, placa="XYZ9876")
    sem_data = novo_projeto(banco_vazio, civic, "concluido", None, nome="Insulfilm")
    com_data = novo_projeto(banco_vazio, civic, "em_andamento", "2026-08-01", nome="Som")
    cruzada = nova_foto(banco_vazio, moto, sem_data, "antes")
    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0011")
    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem and "16.6" in mensagem
    assert f'projeto {sem_data} (veículo {civic}, "Insulfilm") está concluído e sem data' in mensagem
    assert f'projeto {com_data} (veículo {civic}, "Som") tem data de conclusão, mas está em_andamento' in mensagem
    assert f"foto {cruzada} (veículo {moto}) está ligada ao projeto {sem_data}, que é do veículo {civic}" in mensagem
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0010"


@pytest.mark.parametrize("status, conclusao", [("concluido", None), ("em_andamento", "2026-08-01"),
                                               ("cancelado", "2026-08-01")])
def test_banco_recusa_conclusao_incoerente(banco_migrado, dois_veiculos, status, conclusao):
    with pytest.raises(DBAPIError):
        novo_projeto(banco_migrado, dois_veiculos[0], status, conclusao)


def test_banco_recusa_foto_de_projeto_de_outro_veiculo_e_momento_sem_projeto(banco_migrado, dois_veiculos):
    civic, moto = dois_veiculos
    projeto = novo_projeto(banco_migrado, civic)
    with pytest.raises(DBAPIError):
        nova_foto(banco_migrado, moto, projeto, "antes")
    with pytest.raises(DBAPIError):
        nova_foto(banco_migrado, civic, None, "depois", arquivo="b.jpg")
    assert valor(banco_migrado, "SELECT count(*) FROM veiculo_foto") == 0


def test_despesa_do_item_traz_o_projeto_e_continua_no_cancelado(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    projeto = novo_projeto(banco_migrado, civic, "cancelado")
    executar(banco_migrado, "INSERT INTO projeto_item (projeto_id, descricao, data, valor) "
                            "VALUES (:p, 'Jogo de rodas', '2026-07-20', 3400.00)", p=projeto)
    assert linhas(banco_migrado, "SELECT tipo, valor::text, projeto_id FROM vw_despesa") == [
        ("projeto", "3400.00", projeto)]


def test_apagar_o_projeto_apaga_itens_e_fotos(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    projeto = novo_projeto(banco_migrado, civic)
    executar(banco_migrado, "INSERT INTO projeto_item (projeto_id, descricao, valor) VALUES (:p, 'x', 1)", p=projeto)
    nova_foto(banco_migrado, civic, projeto, "antes")
    executar(banco_migrado, "DELETE FROM projeto WHERE id = :p", p=projeto)
    assert (valor(banco_migrado, "SELECT count(*) FROM projeto_item"),
            valor(banco_migrado, "SELECT count(*) FROM veiculo_foto")) == (0, 0)


def test_desfazer_e_refazer_a_0011(banco_migrado, dois_veiculos):
    novo_projeto(banco_migrado, dois_veiculos[0], "concluido", "2026-08-15")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0010")
    assert valor(banco_migrado, "SELECT count(*) FROM information_schema.columns "
                                "WHERE table_name = 'vw_despesa' AND column_name = 'projeto_id'") == 0
    subir(banco_migrado, "0011")
    assert valor(banco_migrado, "SELECT count(*) FROM projeto") == 1
