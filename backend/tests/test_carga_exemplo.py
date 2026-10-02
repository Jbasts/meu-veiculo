"""Carga opcional de dados de exemplo (demonstração do TCC)."""

from datetime import date

import pytest

from app.config import obter_configuracoes
from demonstracao.carga_exemplo import EMAIL_ADMIN, SENHA_EXEMPLO, carregar
from gerenciar import main as gerenciar
from tests.auth_utils import CaixaDeEntrada, ligar_app_ao_banco, novo_aparelho, valor_sql
from app.main import app


@pytest.fixture
def carregado(banco_migrado):
    resumo = carregar(banco_migrado)
    ligar_app_ao_banco(banco_migrado, CaixaDeEntrada())
    yield banco_migrado, resumo
    app.dependency_overrides.clear()


def entrar_como_paula():
    cliente = novo_aparelho()
    resposta = cliente.post("/api/auth/entrar", json={"email": EMAIL_ADMIN, "senha": SENHA_EXEMPLO})
    assert resposta.status_code == 200, resposta.text
    return cliente


def test_carga_cria_contas_veiculos_e_historico(carregado):
    banco, resumo = carregado
    assert resumo.contas == ["paula@exemplo.com.br", "rafael@exemplo.com.br"]
    assert resumo.veiculos == 3 and resumo.fotos == 5
    assert valor_sql(banco, "SELECT perfil FROM usuario WHERE email = :e", e=EMAIL_ADMIN) == "admin"
    assert valor_sql(banco, "SELECT count(*) FROM foto_conteudo") == 5
    for tabela, minimo in (("abastecimento", 20), ("manutencao", 4), ("diagnostico", 3),
                           ("gasto", 10), ("projeto", 3), ("plano_manutencao", 3)):
        assert valor_sql(banco, f"SELECT count(*) FROM {tabela}") >= minimo, tabela


def test_inicio_do_veiculo_em_uso_tem_indicadores_de_verdade(carregado):
    paula = entrar_como_paula()
    [civic] = [v for v in paula.get("/api/veiculos").json() if v["em_uso"]]
    assert civic["placa"] == "BRA2E19" and civic["quilometragem"] == 85000
    painel = paula.get(f"/api/veiculos/{civic['id']}/painel").json()
    texto = str(painel)
    assert "'disponivel': True" in texto  # consumo e custo por km calculados
    custo = paula.get(f"/api/veiculos/{civic['id']}/custo").json()
    assert custo["custo_por_km"]["disponivel"] is True
    historico = paula.get(f"/api/veiculos/{civic['id']}/historico").json()
    assert historico["total"] > 20


def test_admin_ve_as_duas_contas(carregado):
    paula = entrar_como_paula()
    resumo = paula.get("/api/admin/resumo").json()
    assert resumo["usuarios"] == 2 and resumo["veiculos"] == 3


@pytest.mark.parametrize("dia", [date(2026, 3, 1), date(2026, 8, 31)])
def test_carga_funciona_em_qualquer_dia(banco_migrado, dia):
    resumo = carregar(banco_migrado, hoje=dia)
    assert resumo.veiculos == 3


def test_comando_so_aceita_banco_de_demonstracao(monkeypatch, capsys):
    cfg = obter_configuracoes()
    monkeypatch.setattr(cfg, "db_nome_demo", cfg.db_nome)
    with pytest.raises(SystemExit, match="Trava de segurança"):
        gerenciar(["carregar-exemplo"])
    monkeypatch.setattr(cfg, "db_nome_demo", "qualquer_nome")
    with pytest.raises(SystemExit, match="Trava de segurança"):
        gerenciar(["carregar-exemplo"])


def test_comando_migra_carrega_e_nao_carrega_duas_vezes(banco_migrado, monkeypatch, capsys):
    import gerenciar as modulo

    # Aponta o comando para o banco de teste (a trava do nome é testada acima).
    monkeypatch.setattr(modulo, "nome_do_banco_demo", lambda: banco_migrado.url.database)
    gerenciar(["carregar-exemplo", "--recomecar"])
    saida = capsys.readouterr().out
    assert "esvaziado" in saida and "3 veículos" in saida and "5 fotos" in saida
    with pytest.raises(SystemExit, match="já tem 2 conta"):
        gerenciar(["carregar-exemplo"])
    gerenciar(["carregar-exemplo", "--recomecar"])
    assert valor_sql(banco_migrado, "SELECT count(*) FROM usuario") == 2
