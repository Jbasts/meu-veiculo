"""Migration 0004: base dos planos, situação recalculada e vínculos do mesmo veículo.

Testes direto no PostgreSQL de teste: as regras valem também fora da API.
"""

import pytest
from alembic import command
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor


def novo_plano(engine, veiculo_id: int, nome: str = "Troca de óleo", **colunas) -> int:
    colunas = {"intervalo_km": 10000, **colunas}
    nomes = ", ".join(colunas)
    marcadores = ", ".join(f":{c}" for c in colunas)
    return executar(
        engine,
        f"INSERT INTO plano_manutencao (veiculo_id, nome, {nomes}) "
        f"VALUES (:v, :n, {marcadores}) RETURNING id",
        v=veiculo_id, n=nome, **colunas,
    ).scalar()


def nova_manutencao(engine, veiculo_id: int, plano_id: int | None = None, status: str = "realizada",
                    data: str = "2026-09-01", km: int | None = None) -> int:
    return executar(
        engine,
        "INSERT INTO manutencao (veiculo_id, plano_id, descricao, status, data, quilometragem) "
        "VALUES (:v, :p, 'Serviço', :s, :d, :km) RETURNING id",
        v=veiculo_id, p=plano_id, s=status, d=data, km=km,
    ).scalar()


def nova_foto(engine, veiculo_id: int, manutencao_id: int | None, arquivo: str = "a.jpg") -> int:
    return executar(
        engine,
        "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, manutencao_id) "
        "VALUES (:v, :a, 'image/jpeg', 100, :m) RETURNING id",
        v=veiculo_id, a=arquivo, m=manutencao_id,
    ).scalar()


def situacao(engine, plano_id: int) -> dict:
    with engine.connect() as conexao:
        linha = conexao.execute(
            text("SELECT * FROM vw_situacao_manutencao WHERE plano_id = :p"), {"p": plano_id}
        ).mappings().one()
    return dict(linha)


@pytest.fixture
def dois_veiculos(banco_migrado) -> tuple[int, int]:
    """Dois veículos do MESMO dono."""
    dono = novo_usuario(banco_migrado)
    return (novo_veiculo(banco_migrado, dono, "ABC1234"),
            novo_veiculo(banco_migrado, dono, "BRA2E19"))


# ------------------------------------------------------- dados antigos incompatíveis

def test_para_sem_alterar_nada_quando_ha_vinculo_entre_veiculos(banco_vazio):
    subir(banco_vazio, "0003")
    dono = novo_usuario(banco_vazio)
    civic, argo = novo_veiculo(banco_vazio, dono, "ABC1234"), novo_veiculo(banco_vazio, dono, "BRA2E19")
    plano_do_argo = novo_plano(banco_vazio, argo)
    manutencao = nova_manutencao(banco_vazio, civic, plano_do_argo)  # o banco antigo aceitava
    foto = nova_foto(banco_vazio, argo, manutencao)

    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0004")
    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem
    assert (f"manutenção {manutencao} (veículo {civic}) está ligada ao plano {plano_do_argo}, "
            f"que é do veículo {argo}") in mensagem
    assert (f"foto {foto} (veículo {argo}) está ligada à manutenção {manutencao}, "
            f"que é do veículo {civic}") in mensagem
    # Nada apagado nem desvinculado; a versão continua a 0003.
    assert valor(banco_vazio, "SELECT plano_id FROM manutencao") == plano_do_argo
    assert valor(banco_vazio, "SELECT manutencao_id FROM veiculo_foto") == manutencao
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0003"


def test_planos_antigos_ficam_sem_base_em_vez_de_base_inventada(banco_vazio):
    """A view original usava CURRENT_DATE e 0 km; agora a situação é "sem_base"."""
    subir(banco_vazio, "0003")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio), km=85000)
    executar(banco_vazio, "UPDATE veiculo SET data_aquisicao = '2022-03-15', km_aquisicao = 22000")
    por_km = novo_plano(banco_vazio, veiculo, "Filtro de ar")
    por_meses = novo_plano(banco_vazio, veiculo, "Revisão", intervalo_km=None, intervalo_meses=12)
    com_historico = novo_plano(banco_vazio, veiculo, "Óleo")
    nova_manutencao(banco_vazio, veiculo, com_historico, data="2026-09-20", km=84000)
    subir(banco_vazio, "0004")

    for plano in (por_km, por_meses):
        atual = situacao(banco_vazio, plano)
        assert atual["situacao"] == "sem_base"
        assert (atual["proxima_km"], atual["proxima_data"]) == (None, None)
        assert (atual["referencia_km"], atual["referencia_data"]) == (None, None)
    # Plano com manutenção realizada continua calculado a partir dela.
    atual = situacao(banco_vazio, com_historico)
    assert (atual["referencia_km"], atual["proxima_km"], atual["km_restantes"]) == (84000, 94000, 9000)
    assert atual["situacao"] == "em_dia"
    assert linhas(banco_vazio, "SELECT data_base, km_base FROM plano_manutencao") == [(None, None)] * 3


def test_desfazer_e_refazer_a_0004(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    plano = novo_plano(banco_migrado, veiculo)
    manutencao = nova_manutencao(banco_migrado, veiculo, plano, km=85000)
    nova_foto(banco_migrado, veiculo, manutencao)
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0003")
    assert valor(banco_migrado, "SELECT count(*) FROM vw_situacao_manutencao") == 1
    subir(banco_migrado, "0004")
    assert situacao(banco_migrado, plano)["proxima_km"] == 95000
    assert valor(banco_migrado, "SELECT manutencao_id FROM veiculo_foto") == manutencao


# ------------------------------------------------------------ mesmo veículo no banco

def test_banco_recusa_manutencao_em_plano_de_outro_veiculo_do_mesmo_dono(banco_migrado, dois_veiculos):
    civic, argo = dois_veiculos
    plano_do_argo = novo_plano(banco_migrado, argo)
    with pytest.raises(IntegrityError, match="manutencao_plano_mesmo_veiculo_fk"):
        nova_manutencao(banco_migrado, civic, plano_do_argo)
    manutencao = nova_manutencao(banco_migrado, argo, plano_do_argo)  # no veículo certo, aceita
    with pytest.raises(IntegrityError, match="manutencao_plano_mesmo_veiculo_fk"):
        executar(banco_migrado, "UPDATE manutencao SET veiculo_id = :v WHERE id = :m",
                 v=civic, m=manutencao)


def test_banco_recusa_foto_em_manutencao_de_outro_veiculo_do_mesmo_dono(banco_migrado, dois_veiculos):
    civic, argo = dois_veiculos
    manutencao_do_argo = nova_manutencao(banco_migrado, argo)
    with pytest.raises(IntegrityError, match="veiculo_foto_manutencao_mesmo_veiculo_fk"):
        nova_foto(banco_migrado, civic, manutencao_do_argo)
    assert nova_foto(banco_migrado, argo, manutencao_do_argo) > 0


def test_regras_de_exclusao_continuam_as_mesmas(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    plano = novo_plano(banco_migrado, civic)
    manutencao = nova_manutencao(banco_migrado, civic, plano, km=85000)
    nova_foto(banco_migrado, civic, manutencao)

    # Apagar o plano: a manutenção fica como avulsa, no mesmo veículo.
    executar(banco_migrado, "DELETE FROM plano_manutencao WHERE id = :p", p=plano)
    assert linhas(banco_migrado, "SELECT plano_id, veiculo_id FROM manutencao") == [(None, civic)]
    # Apagar a manutenção: a foto ligada sai junto.
    executar(banco_migrado, "DELETE FROM manutencao WHERE id = :m", m=manutencao)
    assert valor(banco_migrado, "SELECT count(*) FROM veiculo_foto") == 0
    assert valor(banco_migrado, "SELECT count(*) FROM veiculo") == 2


# ----------------------------------------------------------------- classificação

@pytest.mark.parametrize("dias, km_restantes, no_dia, esperado", [
    # só data (planos e lembretes: no dia do vencimento já é atraso)
    (-1, None, True, "atrasada"),
    (0, None, True, "atrasada"),
    (1, None, True, "proxima"),
    (30, None, True, "proxima"),
    (31, None, True, "em_dia"),
    # só km
    (None, -1, True, "atrasada"),
    (None, 0, True, "atrasada"),
    (None, 1, True, "proxima"),
    (None, 1000, True, "proxima"),
    (None, 1001, True, "em_dia"),
    # os dois: vale o limite atingido primeiro
    (200, 0, True, "atrasada"),
    (0, 9000, True, "atrasada"),
    (200, 1000, True, "proxima"),
    (30, 9000, True, "proxima"),
    (31, 1001, True, "em_dia"),
    # manutenção agendada: o dia marcado ainda não é atraso
    (0, None, False, "proxima"),
    (-1, None, False, "atrasada"),
    (31, None, False, "em_dia"),
    # nada para comparar
    (None, None, True, None),
])
def test_classificar_prazo_limites_exatos(banco_migrado, dias, km_restantes, no_dia, esperado):
    km_atual = 85000
    resultado = valor(
        banco_migrado,
        "SELECT classificar_prazo(CAST(:hoje AS date) + CAST(:dias AS int), :proxima_km, :km_atual, "
        "CAST(:hoje AS date), :no_dia)",
        hoje="2026-09-24", dias=dias, no_dia=no_dia, km_atual=km_atual,
        proxima_km=None if km_restantes is None else km_atual + km_restantes,
    )
    assert resultado == esperado


def test_prazo_usa_base_fixa_e_nao_anda_com_o_calendario(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado), km=85000)
    plano = novo_plano(banco_migrado, veiculo, "Revisão", intervalo_km=10000, intervalo_meses=12,
                       data_base="2025-09-01", km_base=80000)
    atual = situacao(banco_migrado, plano)
    assert str(atual["proxima_data"]) == "2026-09-01"  # base + 12 meses, não "hoje + 12 meses"
    assert atual["proxima_km"] == 90000                # base + intervalo, não 0 + intervalo
    assert atual["situacao"] == "atrasada"             # a data venceu; o km ainda não


def test_referencia_e_o_mais_recente_entre_base_e_ultima_manutencao(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado), km=85000)
    plano = novo_plano(banco_migrado, veiculo, "Óleo", intervalo_km=10000, intervalo_meses=12,
                       data_base="2026-03-01", km_base=80000)
    # Manutenção histórica, anterior à base: não puxa a referência para trás.
    nova_manutencao(banco_migrado, veiculo, plano, data="2025-01-10", km=60000)
    atual = situacao(banco_migrado, plano)
    assert (str(atual["referencia_data"]), atual["referencia_km"]) == ("2026-03-01", 80000)
    # Manutenção agendada não conta; realizada mais recente passa a ser a referência.
    nova_manutencao(banco_migrado, veiculo, plano, status="agendada", data="2026-12-01", km=90000)
    assert situacao(banco_migrado, plano)["referencia_km"] == 80000
    nova_manutencao(banco_migrado, veiculo, plano, data="2026-09-20", km=84500)
    atual = situacao(banco_migrado, plano)
    assert (str(atual["referencia_data"]), atual["referencia_km"]) == ("2026-09-20", 84500)
    assert (str(atual["proxima_data"]), atual["proxima_km"]) == ("2027-09-20", 94500)


def test_falta_de_uma_base_nao_esconde_atraso_conhecido(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado), km=85000)
    # Tem base de km (já vencida) e não tem base de data.
    vencido = novo_plano(banco_migrado, veiculo, "A", intervalo_km=5000, intervalo_meses=12,
                         km_base=70000)
    # Tem base de km (longe de vencer) e não tem base de data: não dá para dizer "em dia".
    incerto = novo_plano(banco_migrado, veiculo, "B", intervalo_km=50000, intervalo_meses=12,
                         km_base=80000)
    assert situacao(banco_migrado, vencido)["situacao"] == "atrasada"
    assert situacao(banco_migrado, incerto)["situacao"] == "sem_base"


def test_plano_inativo_sai_da_view(banco_migrado):
    veiculo = novo_veiculo(banco_migrado, novo_usuario(banco_migrado))
    plano = novo_plano(banco_migrado, veiculo, km_base=80000)
    executar(banco_migrado, "UPDATE plano_manutencao SET ativo = FALSE WHERE id = :p", p=plano)
    assert valor(banco_migrado, "SELECT count(*) FROM vw_situacao_manutencao") == 0
