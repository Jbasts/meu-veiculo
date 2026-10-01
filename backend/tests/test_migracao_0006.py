"""Migration 0006: diagnósticos ligados só ao mesmo veículo e sempre coerentes com a manutenção.

Testes direto no PostgreSQL de teste: as regras valem também fora da API.
"""

import pytest
from alembic import command
from sqlalchemy.exc import DBAPIError

from app.banco.migracoes import config_alembic
from tests.test_migracao_0003 import executar, linhas, novo_usuario, novo_veiculo, subir, valor
from tests.test_migracao_0004 import nova_manutencao


def novo_diagnostico(engine, veiculo_id: int, status: str = "aberto",
                     manutencao_id: int | None = None, data: str = "2026-08-01",
                     data_resolucao: str | None = None) -> int:
    return executar(
        engine,
        "INSERT INTO diagnostico (veiculo_id, titulo, status, data_identificacao, "
        "manutencao_id, data_resolucao) VALUES (:v, 'Barulho', :s, :d, :m, :r) RETURNING id",
        v=veiculo_id, s=status, d=data, m=manutencao_id, r=data_resolucao,
    ).scalar()


def situacao(engine, diagnostico_id: int) -> tuple:
    [linha] = linhas(engine, "SELECT status, manutencao_id, data_resolucao::text FROM diagnostico "
                             "WHERE id = :d", d=diagnostico_id)
    return linha


@pytest.fixture
def dois_veiculos(banco_migrado) -> tuple[int, int]:
    """Dois veículos do MESMO dono: a regra é por veículo, não por dono."""
    dono = novo_usuario(banco_migrado)
    return (novo_veiculo(banco_migrado, dono, placa="ABC1234"),
            novo_veiculo(banco_migrado, dono, placa="XYZ9876"))


# ------------------------------------------------------------- instalação e atualização

def test_banco_vazio_ate_a_0006_tem_as_chaves_compostas(banco_migrado):
    nomes = {n for (n,) in linhas(banco_migrado,
                                  "SELECT conname FROM pg_constraint WHERE conname LIKE '%mesmo_veiculo%'")}
    assert {"diagnostico_manutencao_mesmo_veiculo_fk",
            "veiculo_foto_diagnostico_mesmo_veiculo_fk"} <= nomes


def test_banco_na_0005_com_dados_coerentes_atualiza_sem_mudar_nada(banco_vazio):
    subir(banco_vazio, "0005")
    veiculo = novo_veiculo(banco_vazio, novo_usuario(banco_vazio))
    feita = nova_manutencao(banco_vazio, veiculo)
    resolvido = novo_diagnostico(banco_vazio, veiculo, "resolvido", feita,
                                 data_resolucao="2026-09-01")
    aberto = novo_diagnostico(banco_vazio, veiculo)
    antes = linhas(banco_vazio, "SELECT * FROM diagnostico ORDER BY id")

    subir(banco_vazio, "0006")

    assert linhas(banco_vazio, "SELECT * FROM diagnostico ORDER BY id") == antes
    assert situacao(banco_vazio, resolvido) == ("resolvido", feita, "2026-09-01")
    assert situacao(banco_vazio, aberto) == ("aberto", None, None)


def test_para_sem_alterar_nada_quando_ha_vinculos_incompativeis(banco_vazio):
    subir(banco_vazio, "0005")
    dono = novo_usuario(banco_vazio)
    civic = novo_veiculo(banco_vazio, dono, placa="ABC1234")
    moto = novo_veiculo(banco_vazio, dono, placa="XYZ9876")
    da_moto = nova_manutencao(banco_vazio, moto)
    agendada = nova_manutencao(banco_vazio, civic, status="agendada", data="2026-12-01")
    cruzado = novo_diagnostico(banco_vazio, civic, "aberto", da_moto)
    incoerente = novo_diagnostico(banco_vazio, civic, "resolvido", agendada,
                                  data_resolucao="2026-09-01")
    foto = executar(banco_vazio,
                    "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, "
                    "diagnostico_id) VALUES (:v, 'x.jpg', 'image/jpeg', 10, :d) RETURNING id",
                    v=moto, d=cruzado).scalar()
    antes = linhas(banco_vazio, "SELECT * FROM diagnostico ORDER BY id")

    with pytest.raises(RuntimeError) as erro:
        subir(banco_vazio, "0006")

    mensagem = str(erro.value)
    assert "Nada foi alterado" in mensagem and "13.6" in mensagem
    assert f"diagnóstico {cruzado} (veículo {civic}) está ligado à manutenção {da_moto}" in mensagem
    assert f"foto {foto} (veículo {moto}) está ligada ao diagnóstico {cruzado}" in mensagem
    assert f"diagnóstico {incoerente} (resolvido) está ligado à manutenção {agendada}" in mensagem
    assert valor(banco_vazio, "SELECT version_num FROM alembic_version") == "0005"
    assert linhas(banco_vazio, "SELECT * FROM diagnostico ORDER BY id") == antes


def test_desfazer_e_refazer_a_0006(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    feita = nova_manutencao(banco_migrado, civic)
    diagnostico = novo_diagnostico(banco_migrado, civic, "resolvido", feita,
                                   data_resolucao="2026-09-01")
    command.downgrade(config_alembic(banco_migrado, configurar_logs=False), "0005")
    assert valor(banco_migrado, "SELECT count(*) FROM pg_trigger "
                                "WHERE tgname = 'trg_diagnostico_conferir_vinculo'") == 0
    subir(banco_migrado, "0006")
    assert situacao(banco_migrado, diagnostico) == ("resolvido", feita, "2026-09-01")


# ------------------------------------------------------------------- mesmo veículo

def test_banco_recusa_diagnostico_ligado_a_manutencao_de_outro_veiculo(banco_migrado,
                                                                       dois_veiculos):
    civic, moto = dois_veiculos
    da_moto = nova_manutencao(banco_migrado, moto, status="agendada", data="2026-12-01")
    with pytest.raises(DBAPIError):
        novo_diagnostico(banco_migrado, civic, "aberto", da_moto)


def test_banco_recusa_foto_ligada_a_diagnostico_de_outro_veiculo(banco_migrado, dois_veiculos):
    civic, moto = dois_veiculos
    diagnostico = novo_diagnostico(banco_migrado, civic)
    with pytest.raises(DBAPIError):
        executar(banco_migrado,
                 "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, "
                 "diagnostico_id) VALUES (:v, 'x.jpg', 'image/jpeg', 10, :d)",
                 v=moto, d=diagnostico)


# ------------------------------------------------------------- coerência do vínculo

@pytest.mark.parametrize("status_diag, status_manut, trecho", [
    ("resolvido", "agendada", "só pode estar ligado a manutenção realizada"),
    ("aberto", "realizada", "só pode estar ligado a manutenção agendada"),
    ("em_observacao", "realizada", "só pode estar ligado a manutenção agendada"),
    ("descartado", "agendada", "descartado não fica ligado"),
])
def test_banco_recusa_vinculo_incoerente(banco_migrado, dois_veiculos, status_diag, status_manut,
                                         trecho):
    civic, _ = dois_veiculos
    manutencao = nova_manutencao(banco_migrado, civic, status=status_manut, data="2026-09-01")
    with pytest.raises(DBAPIError) as erro:
        novo_diagnostico(banco_migrado, civic, status_diag, manutencao,
                         data_resolucao="2026-09-01" if status_diag != "aberto" else None)
    assert trecho in str(erro.value)


def test_concluir_a_agendada_resolve_o_diagnostico_com_a_data_dela(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    prevista = nova_manutencao(banco_migrado, civic, status="agendada", data="2026-09-20")
    diagnostico = novo_diagnostico(banco_migrado, civic, "em_observacao", prevista)
    executar(banco_migrado, "UPDATE manutencao SET status = 'realizada', data = '2026-09-18' "
                            "WHERE id = :m", m=prevista)
    assert situacao(banco_migrado, diagnostico) == ("resolvido", prevista, "2026-09-18")


def test_voltar_para_agendada_reabre_e_mantem_como_prevista(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    feita = nova_manutencao(banco_migrado, civic)
    diagnostico = novo_diagnostico(banco_migrado, civic, "resolvido", feita,
                                   data_resolucao="2026-09-01")
    executar(banco_migrado, "UPDATE manutencao SET status = 'agendada' WHERE id = :m", m=feita)
    assert situacao(banco_migrado, diagnostico) == ("aberto", feita, None)


def test_mudar_a_data_da_realizada_acompanha_a_resolucao(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    feita = nova_manutencao(banco_migrado, civic)
    diagnostico = novo_diagnostico(banco_migrado, civic, "resolvido", feita,
                                   data_resolucao="2026-09-01")
    executar(banco_migrado, "UPDATE manutencao SET data = '2026-09-05' WHERE id = :m", m=feita)
    assert situacao(banco_migrado, diagnostico) == ("resolvido", feita, "2026-09-05")


def test_apagar_a_manutencao_reabre_o_resolvido_e_solta_o_aberto(banco_migrado, dois_veiculos):
    civic, _ = dois_veiculos
    feita = nova_manutencao(banco_migrado, civic)
    prevista = nova_manutencao(banco_migrado, civic, status="agendada", data="2026-12-01")
    resolvido = novo_diagnostico(banco_migrado, civic, "resolvido", feita,
                                 data_resolucao="2026-09-01")
    aberto = novo_diagnostico(banco_migrado, civic, "em_observacao", prevista)
    executar(banco_migrado, "DELETE FROM manutencao WHERE id IN (:a, :b)", a=feita, b=prevista)
    assert situacao(banco_migrado, resolvido) == ("aberto", None, None)
    assert situacao(banco_migrado, aberto) == ("em_observacao", None, None)


def test_apagar_o_veiculo_apaga_diagnosticos_notas_e_fotos(banco_migrado, dois_veiculos):
    civic, moto = dois_veiculos
    feita = nova_manutencao(banco_migrado, civic)
    diagnostico = novo_diagnostico(banco_migrado, civic, "resolvido", feita,
                                   data_resolucao="2026-09-01")
    executar(banco_migrado, "INSERT INTO diagnostico_nota (diagnostico_id, texto) VALUES (:d, 'x')",
             d=diagnostico)
    executar(banco_migrado,
             "INSERT INTO veiculo_foto (veiculo_id, arquivo, tipo_mime, tamanho_bytes, "
             "diagnostico_id) VALUES (:v, 'x.jpg', 'image/jpeg', 10, :d)", v=civic, d=diagnostico)
    da_moto = novo_diagnostico(banco_migrado, moto)
    executar(banco_migrado, "DELETE FROM veiculo WHERE id = :v", v=civic)
    assert linhas(banco_migrado, "SELECT id FROM diagnostico") == [(da_moto,)]
    assert valor(banco_migrado, "SELECT count(*) FROM diagnostico_nota") == 0
    assert valor(banco_migrado, "SELECT count(*) FROM veiculo_foto") == 0
