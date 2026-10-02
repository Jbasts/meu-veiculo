"""Nada da conta fica guardado no navegador (etapa 10, PWA e celular).

Respostas da API saem com "no-store"; as fotos mantêm a regra própria
(guardar, mas conferir a permissão a cada uso); sair pede ao navegador que
apague o cache deste endereço.
"""

from tests.auth_utils import novo_aparelho
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    banco,
    criar_veiculo,
    enviar_foto,
    imagem,
    pasta_fotos,
    paula,
    rafael,
)


def test_respostas_com_dados_da_conta_nao_sao_guardadas(banco, paula):
    veiculo = criar_veiculo(paula)
    base = f"/api/veiculos/{veiculo['id']}"
    for caminho in ("/api/auth/eu", "/api/veiculos", base, f"{base}/painel", f"{base}/historico"):
        resposta = paula.get(caminho)
        assert resposta.status_code == 200, caminho
        assert resposta.headers["cache-control"] == "no-store", caminho


def test_erros_e_gravacoes_tambem_saem_sem_cache(banco, paula):
    assert novo_aparelho().get("/api/auth/eu").headers["cache-control"] == "no-store"
    assert paula.get("/api/veiculos/999999").headers["cache-control"] == "no-store"
    criado = paula.post("/api/veiculos", json={})
    assert criado.status_code == 422
    assert criado.headers["cache-control"] == "no-store"


def test_um_unico_cache_control_e_a_foto_mantem_a_regra_dela(banco, paula):
    veiculo = criar_veiculo(paula)
    foto = enviar_foto(paula, veiculo["id"]).json()
    resposta = paula.get(f"/api/veiculos/{veiculo['id']}/fotos/{foto['id']}/arquivo")
    assert resposta.status_code == 200
    assert resposta.headers.get_list("cache-control") == ["private, no-cache"]
    assert paula.get("/api/auth/eu").headers.get_list("cache-control") == ["no-store"]


def test_sair_pede_para_apagar_o_cache_do_endereco(banco, paula):
    resposta = paula.post("/api/auth/sair")
    assert resposta.status_code == 204
    assert resposta.headers["clear-site-data"] == '"cache"'
    assert resposta.headers["cache-control"] == "no-store"
