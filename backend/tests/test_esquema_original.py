"""Comportamentos do SQL original que continuam valendo depois da 0001.

Cada teste roda numa transação desfeita no final, para um não afetar o outro.
Os problemas conhecidos do SQL (apontados na etapa 0) serão corrigidos e
testados nas etapas em que forem tratados.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.config import FUSO_HORARIO


@pytest.fixture
def conexao(banco_migrado):
    with banco_migrado.connect() as conexao:
        transacao = conexao.begin()
        yield conexao
        transacao.rollback()


def criar_usuario(conexao, email="ana@x.com") -> int:
    return conexao.execute(
        text("INSERT INTO usuario (nome, email, senha_hash) VALUES ('Ana', :e, 'h') RETURNING id"),
        {"e": email},
    ).scalar()


def criar_veiculo(conexao, usuario_id: int, km: int = 85000) -> int:
    return conexao.execute(
        text(
            "INSERT INTO veiculo (usuario_id, marca, modelo, ano, placa, quilometragem) "
            "VALUES (:u, 'Honda', 'Civic', 2020, 'ABC1234', :km) RETURNING id"
        ),
        {"u": usuario_id, "km": km},
    ).scalar()


def test_conexao_usa_fuso_de_sao_paulo(conexao):
    fuso, hoje = conexao.execute(text("SELECT current_setting('TimeZone'), current_date")).one()
    assert fuso == FUSO_HORARIO
    assert hoje == datetime.now(ZoneInfo(FUSO_HORARIO)).date()


def test_dominio_dinheiro_recusa_valor_negativo(conexao):
    veiculo = criar_veiculo(conexao, criar_usuario(conexao))
    with pytest.raises(IntegrityError):
        conexao.execute(
            text("INSERT INTO gasto (veiculo_id, categoria, valor) VALUES (:v, 'multa', -1)"),
            {"v": veiculo},
        )


def test_email_unico_sem_diferenciar_maiusculas(conexao):
    criar_usuario(conexao, "Paula@Email.com")
    with pytest.raises(IntegrityError):
        criar_usuario(conexao, "paula@email.com")


def test_abastecimento_aumenta_km_mas_nao_reduz(conexao):
    veiculo = criar_veiculo(conexao, criar_usuario(conexao), km=85000)
    inserir = text(
        "INSERT INTO abastecimento (veiculo_id, quilometragem, combustivel, litros, "
        "valor_litro, valor_total) VALUES (:v, :km, 'gasolina', 40, 6.25, 250)"
    )
    km_atual = text("SELECT quilometragem FROM veiculo WHERE id = :v")
    conexao.execute(inserir, {"v": veiculo, "km": 85450})
    assert conexao.execute(km_atual, {"v": veiculo}).scalar() == 85450
    conexao.execute(inserir, {"v": veiculo, "km": 84000})  # registro antigo
    assert conexao.execute(km_atual, {"v": veiculo}).scalar() == 85450


def test_no_maximo_uma_foto_de_capa_por_veiculo(conexao):
    veiculo = criar_veiculo(conexao, criar_usuario(conexao))
    inserir = text(
        "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, principal) "
        "VALUES (:v, :a, 'image/jpeg', 1000, TRUE)"
    )
    conexao.execute(inserir, {"v": veiculo, "a": "veiculos/1/a.jpg"})
    with pytest.raises(IntegrityError):
        conexao.execute(inserir, {"v": veiculo, "a": "veiculos/1/b.jpg"})


def test_foto_acima_de_10_mb_e_recusada(conexao):
    veiculo = criar_veiculo(conexao, criar_usuario(conexao))
    with pytest.raises(IntegrityError):
        conexao.execute(
            text(
                "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes) "
                "VALUES (:v, 'veiculos/1/c.jpg', 'image/jpeg', 10485761)"
            ),
            {"v": veiculo},
        )


@pytest.mark.parametrize(
    "view", ["vw_situacao_manutencao", "vw_projeto_resumo", "vw_historico", "vw_usuario_resumo"]
)
def test_views_do_sql_original_respondem(conexao, view):
    assert conexao.execute(text(f"SELECT count(*) FROM {view}")).scalar() == 0


def test_resumo_de_usuarios_nao_expoe_hash_da_senha(conexao):
    colunas = conexao.execute(text("SELECT * FROM vw_usuario_resumo LIMIT 0")).keys()
    assert "senha_hash" not in colunas
