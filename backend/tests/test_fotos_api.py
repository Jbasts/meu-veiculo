"""Fotos de ponta a ponta: envio validado, arquivo protegido, capa e exclusão.

As imagens e os metadados ficam no PostgreSQL de teste (migration 0013);
nada é gravado em pasta. A fixture pasta_fotos é usada só pelo comando
importar-fotos, que lê a antiga pasta.
"""

import io
import threading

import pytest
from PIL import Image
from sqlalchemy import text

from app.entities.veiculo_foto import TAMANHO_MAXIMO_BYTES
from app.repositories.foto_repository import FotoRepository
from app.services.erros import DadosInvalidos
from app.services.imagem_service import LADO_MAXIMO, identificar_formato, preparar_imagem
from gerenciar import main as gerenciar
from tests.auth_utils import entrar, executar_sql, novo_aparelho, valor_sql
from tests.veiculo_utils import (  # noqa: F401  (fixtures)
    admin,
    arquivos_na_pasta,
    banco,
    criar_veiculo,
    enviar_foto,
    imagem,
    imagens_no_banco,
    pasta_fotos,
    paula,
    rafael,
)


@pytest.fixture
def civic(paula) -> dict:
    return criar_veiculo(paula)


def fotos(cliente, veiculo_id: int, **parametros) -> dict:
    resposta = cliente.get(f"/api/veiculos/{veiculo_id}/fotos", params=parametros)
    assert resposta.status_code == 200, resposta.text
    return resposta.json()


def capas_no_banco(banco, veiculo_id: int) -> list[int]:
    with banco.connect() as conexao:
        return list(conexao.execute(
            text("SELECT id FROM veiculo_foto WHERE veiculo_id = :v AND principal ORDER BY id"),
            {"v": veiculo_id}).scalars())


# ---------------------------------------------------------------------- envio

def test_envia_foto_e_guarda_a_imagem_no_banco(banco, paula, civic, pasta_fotos):
    resposta = enviar_foto(paula, civic["id"], nome="../../segredo.exe",
                           legenda="  Frente do carro ", data_foto="2026-09-20")
    assert resposta.status_code == 201, resposta.text
    corpo = resposta.json()
    assert corpo["tipo_mime"] == "image/jpeg" and corpo["legenda"] == "Frente do carro"
    assert corpo["data_foto"] == "2026-09-20" and corpo["principal"] is False
    assert "arquivo" not in corpo  # o caminho no servidor não é exposto

    # Nome de referência gerado pelo backend; o nome enviado é ignorado.
    nome = valor_sql(banco, "SELECT arquivo FROM veiculo_foto")
    assert nome.startswith(f"veiculos/{civic['id']}/") and nome.endswith(".jpg")
    assert "segredo" not in nome
    # A imagem está no banco, e o tamanho gravado é o dela.
    assert imagens_no_banco(banco) == 1
    assert corpo["tamanho_bytes"] == valor_sql(
        banco, "SELECT octet_length(dados) FROM foto_conteudo WHERE foto_id = :f", f=corpo["id"])
    baixada = paula.get(f"/api/veiculos/{civic['id']}/fotos/{corpo['id']}/arquivo")
    assert len(baixada.content) == corpo["tamanho_bytes"]
    # Nada foi gravado em pasta.
    assert arquivos_na_pasta(pasta_fotos) == []


@pytest.mark.parametrize("formato, tipo_esperado, extensao", [
    ("JPEG", "image/jpeg", ".jpg"),
    ("PNG", "image/png", ".png"),
    ("WEBP", "image/webp", ".webp"),
    ("HEIF", "image/jpeg", ".jpg"),  # HEIC do iPhone é convertido para JPEG
])
def test_formatos_aceitos(banco, paula, civic, pasta_fotos, formato, tipo_esperado, extensao):
    # Nome e tipo informados de propósito errados: valem os bytes do arquivo.
    resposta = enviar_foto(paula, civic["id"], imagem(formato), nome="x.bin",
                           tipo="application/octet-stream")
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["tipo_mime"] == tipo_esperado
    assert valor_sql(banco, "SELECT arquivo FROM veiculo_foto").endswith(extensao)
    baixada = paula.get(f"/api/veiculos/{civic['id']}/fotos/{resposta.json()['id']}/arquivo")
    assert baixada.headers["content-type"] == tipo_esperado
    assert Image.open(io.BytesIO(baixada.content)).size == (80, 60)


@pytest.mark.parametrize("conteudo, nome, tipo, trecho", [
    (b"isto nao e uma imagem", "foto.jpg", "image/jpeg", "Formato não aceito"),
    (b"GIF89a" + b"\x00" * 50, "foto.gif", "image/gif", "Formato não aceito"),
    (b"%PDF-1.7 conteudo", "foto.png", "image/png", "Formato não aceito"),
    (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "foto.svg",
     "image/svg+xml", "Formato não aceito"),
    (b"\xff\xd8\xff\xe0" + b"lixo" * 200, "foto.jpg", "image/jpeg", "corrompido"),
    (imagem("PNG")[:40], "foto.png", "image/png", "corrompido"),
    (b"", "foto.jpg", "image/jpeg", "Escolha uma foto"),
])
def test_conteudo_invalido_e_recusado_mesmo_com_extensao_e_tipo_de_imagem(
        banco, paula, civic, pasta_fotos, conteudo, nome, tipo, trecho):
    resposta = enviar_foto(paula, civic["id"], conteudo, nome=nome, tipo=tipo)
    assert resposta.status_code == 422, resposta.text
    assert trecho in resposta.json()["campos"]["arquivo"]
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0
    assert imagens_no_banco(banco) == 0


def test_tamanho_maximo_de_10_mb(banco, paula, civic, pasta_fotos):
    um_byte_a_mais = b"\xff\xd8\xff" + b"\x00" * (TAMANHO_MAXIMO_BYTES - 2)
    assert len(um_byte_a_mais) == 10_485_761
    resposta = enviar_foto(paula, civic["id"], um_byte_a_mais)
    assert resposta.status_code == 422
    assert "limite é 10 MB" in resposta.json()["campos"]["arquivo"]

    # Muito acima do limite: recusado antes de o servidor guardar o conteúdo.
    resposta = enviar_foto(paula, civic["id"], b"\xff\xd8\xff" + b"\x00" * (12 * 1024 * 1024))
    assert resposta.status_code == 413
    assert "10 MB" in resposta.json()["mensagem"]

    # Envio em pedaços, sem tamanho declarado.
    def pedacos():
        for _ in range(13):
            yield b"\x00" * (1024 * 1024)

    resposta = paula.post(f"/api/veiculos/{civic['id']}/fotos", content=pedacos(),
                          headers={"Content-Type": "multipart/form-data; boundary=x"})
    assert resposta.status_code == 413
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0
    assert imagens_no_banco(banco) == 0


def test_foto_grande_e_reduzida_e_metadados_sao_removidos(banco, paula, civic):
    """A localização GPS gravada pelo celular não fica no arquivo guardado."""
    original = Image.new("RGB", (4000, 3000), "blue")
    exif = Image.Exif()
    exif[0x010F] = "Fabricante Secreto"          # marca da câmera
    exif[0x0112] = 6                              # orientação: girar 90 graus
    exif.get_ifd(0x8825)[2] = (23.0, 33.0, 0.0)  # latitude GPS
    saida = io.BytesIO()
    original.save(saida, "JPEG", exif=exif)
    assert b"Fabricante Secreto" in saida.getvalue()
    assert Image.open(io.BytesIO(saida.getvalue())).getexif().get_ifd(0x8825)  # GPS no original

    resposta = enviar_foto(paula, civic["id"], saida.getvalue())
    assert resposta.status_code == 201, resposta.text
    baixada = paula.get(f"/api/veiculos/{civic['id']}/fotos/{resposta.json()['id']}/arquivo").content
    assert b"Fabricante Secreto" not in baixada
    guardada = Image.open(io.BytesIO(baixada))
    assert len(guardada.getexif()) == 0 and not guardada.getexif().get_ifd(0x8825)
    assert guardada.size == (1920, LADO_MAXIMO)  # girada (3000x4000) e reduzida


def test_validacao_dos_campos_da_foto(banco, paula, civic, pasta_fotos):
    resposta = enviar_foto(paula, civic["id"], data_foto="2999-01-01")
    assert resposta.status_code == 422 and "futuro" in resposta.json()["campos"]["data_foto"]
    resposta = enviar_foto(paula, civic["id"], legenda="x" * 151)
    assert resposta.status_code == 422 and "Legenda longa" in resposta.json()["campos"]["legenda"]
    resposta = paula.post(f"/api/veiculos/{civic['id']}/fotos", data={"legenda": "sem arquivo"})
    assert resposta.status_code == 422 and resposta.json()["campos"] == {"arquivo": "Campo obrigatório."}
    assert imagens_no_banco(banco) == 0


def test_sem_data_a_foto_fica_com_a_data_de_hoje(banco, paula, civic):
    corpo = enviar_foto(paula, civic["id"]).json()
    assert corpo["data_foto"] == str(valor_sql(banco, "SELECT current_date"))


# ------------------------------------------------------------------ permissões

def test_conhecer_o_endereco_da_foto_nao_da_acesso(banco, paula, rafael, civic, pasta_fotos):
    foto = enviar_foto(paula, civic["id"]).json()
    base = f"/api/veiculos/{civic['id']}/fotos"
    assert paula.get(f"{base}/{foto['id']}/arquivo").status_code == 200

    anonimo = novo_aparelho()
    assert anonimo.get(f"{base}/{foto['id']}/arquivo").status_code == 401
    assert anonimo.get(base).status_code == 401

    for resposta in (
        rafael.get(base),
        rafael.get(f"{base}/{foto['id']}"),
        rafael.get(f"{base}/{foto['id']}/arquivo"),
        rafael.put(f"{base}/{foto['id']}", json={"legenda": "minha"}),
        rafael.post(f"{base}/{foto['id']}/capa"),
        rafael.delete(f"{base}/{foto['id']}"),
        rafael.delete(f"/api/veiculos/{civic['id']}/capa"),
        enviar_foto(rafael, civic["id"]),
    ):
        assert resposta.status_code == 404, resposta.request.url
    assert imagens_no_banco(banco) == 1
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 1

    # Não existe caminho público que leve à imagem pelo nome de referência.
    caminho = valor_sql(banco, "SELECT arquivo FROM veiculo_foto")
    for endereco in (f"/{caminho}", f"/api/{caminho}", f"/storage/{caminho}"):
        assert paula.get(endereco).status_code == 404


def test_foto_de_outro_veiculo_nao_e_aceita_nem_do_mesmo_dono(banco, paula, rafael, civic):
    """Trocar o veículo do endereço não dá acesso: a foto precisa ser daquele veículo."""
    foto_da_paula = enviar_foto(paula, civic["id"]).json()
    argo_da_paula = criar_veiculo(paula, placa="BRA2E19")
    gol_do_rafael = criar_veiculo(rafael, placa="QWE4567")

    for cliente, veiculo in ((paula, argo_da_paula), (rafael, gol_do_rafael)):
        base = f"/api/veiculos/{veiculo['id']}/fotos/{foto_da_paula['id']}"
        for resposta in (
            cliente.get(base), cliente.get(f"{base}/arquivo"),
            cliente.put(base, json={"legenda": "x"}), cliente.post(f"{base}/capa"),
            cliente.delete(base),
        ):
            assert resposta.status_code == 404
            assert resposta.json()["mensagem"] == "Foto não encontrada."
    assert capas_no_banco(banco, argo_da_paula["id"]) == []
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 1


def test_admin_acessa_fotos_de_qualquer_veiculo_mas_respeita_o_vinculo(banco, paula, admin, civic):
    foto = enviar_foto(paula, civic["id"]).json()
    base = f"/api/veiculos/{civic['id']}/fotos"
    assert fotos(admin, civic["id"])["total"] == 1
    assert admin.get(f"{base}/{foto['id']}/arquivo").status_code == 200
    assert admin.post(f"{base}/{foto['id']}/capa").json()["principal"] is True
    do_admin = criar_veiculo(admin, placa="ADM1N23")
    assert admin.get(f"/api/veiculos/{do_admin['id']}/fotos/{foto['id']}/arquivo").status_code == 404


def test_imagem_so_e_reutilizada_depois_de_conferir_a_permissao(banco, paula, civic):
    foto = enviar_foto(paula, civic["id"]).json()
    caminho = f"/api/veiculos/{civic['id']}/fotos/{foto['id']}/arquivo"
    primeira = paula.get(caminho)
    assert primeira.headers["cache-control"] == "private, no-cache"
    assert primeira.headers["x-content-type-options"] == "nosniff"
    etiqueta = primeira.headers["etag"]
    segunda = paula.get(caminho, headers={"If-None-Match": etiqueta})
    assert segunda.status_code == 304 and segunda.content == b""
    # Depois de sair, a mesma requisição condicional não devolve nada.
    paula.post("/api/auth/sair")
    assert paula.get(caminho, headers={"If-None-Match": etiqueta}).status_code == 401


# ------------------------------------------------------------------------ capa

def test_capa_no_envio_e_troca_de_capa(banco, paula, civic):
    primeira = enviar_foto(paula, civic["id"], principal="true").json()
    assert primeira["principal"] is True
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["foto_capa_id"] == primeira["id"]
    assert paula.get("/api/veiculos").json()[0]["foto_capa_id"] == primeira["id"]

    # Enviar outra já como capa substitui a anterior.
    segunda = enviar_foto(paula, civic["id"], principal="true").json()
    assert capas_no_banco(banco, civic["id"]) == [segunda["id"]]

    # Trocar por uma foto que já está na galeria.
    base = f"/api/veiculos/{civic['id']}/fotos"
    assert paula.post(f"{base}/{primeira['id']}/capa").json()["principal"] is True
    assert capas_no_banco(banco, civic["id"]) == [primeira["id"]]
    assert paula.post(f"{base}/{primeira['id']}/capa").status_code == 200  # repetir não dá erro

    # Tirar a capa: a foto continua na galeria.
    assert paula.delete(f"/api/veiculos/{civic['id']}/capa").status_code == 204
    assert capas_no_banco(banco, civic["id"]) == []
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["foto_capa_id"] is None
    assert fotos(paula, civic["id"])["total"] == 2


def test_trocas_de_capa_simultaneas_deixam_exatamente_uma_capa(banco, paula, civic):
    ids = [enviar_foto(paula, civic["id"]).json()["id"] for _ in range(4)]
    aparelhos = []
    for _ in ids:
        aparelho = novo_aparelho()
        assert entrar(aparelho).status_code == 200
        aparelhos.append(aparelho)

    for _rodada in range(5):
        largada = threading.Barrier(len(ids))
        codigos: list[int] = []

        def trocar(aparelho, foto_id):
            largada.wait(timeout=10)
            codigos.append(
                aparelho.post(f"/api/veiculos/{civic['id']}/fotos/{foto_id}/capa").status_code)

        tarefas = [threading.Thread(target=trocar, args=par) for par in zip(aparelhos, ids)]
        for tarefa in tarefas:
            tarefa.start()
        for tarefa in tarefas:
            tarefa.join(timeout=30)

        assert codigos == [200] * len(ids)  # nenhuma falhou por causa da outra
        capas = capas_no_banco(banco, civic["id"])
        assert len(capas) == 1 and capas[0] in ids


# ------------------------------------------------------------ galeria e edição

def test_galeria_paginada_da_mais_recente_para_a_mais_antiga(banco, paula, civic):
    datas = ["2026-07-18", "2026-09-20", "2026-09-20", "2026-08-05", "2026-09-24"]
    for data in datas:
        assert enviar_foto(paula, civic["id"], data_foto=data).status_code == 201
    primeira = fotos(paula, civic["id"], pagina=1, por_pagina=2)
    segunda = fotos(paula, civic["id"], pagina=2, por_pagina=2)
    terceira = fotos(paula, civic["id"], pagina=3, por_pagina=2)
    assert (primeira["total"], primeira["pagina"], primeira["por_pagina"]) == (5, 1, 2)
    todas = primeira["itens"] + segunda["itens"] + terceira["itens"]
    assert [f["data_foto"] for f in todas] == sorted(datas, reverse=True)
    assert len({f["id"] for f in todas}) == 5
    mesmo_dia = [f["id"] for f in todas if f["data_foto"] == "2026-09-20"]
    assert mesmo_dia == sorted(mesmo_dia, reverse=True)  # o id desempata


def test_edita_legenda_e_data(banco, paula, civic):
    foto = enviar_foto(paula, civic["id"], legenda="Antiga").json()
    caminho = f"/api/veiculos/{civic['id']}/fotos/{foto['id']}"
    corpo = paula.put(caminho, json={"legenda": " Nova legenda ", "data_foto": "2026-08-01"}).json()
    assert (corpo["legenda"], corpo["data_foto"]) == ("Nova legenda", "2026-08-01")
    assert paula.put(caminho, json={"legenda": "", "data_foto": "2026-08-01"}).json()["legenda"] is None
    recusada = paula.put(caminho, json={"legenda": "x", "veiculo_id": 99})
    assert recusada.status_code == 422 and "veiculo_id" in recusada.json()["campos"]


def test_veiculo_inativo_mostra_as_fotos_mas_nao_aceita_alteracoes(banco, paula, civic, pasta_fotos):
    foto = enviar_foto(paula, civic["id"]).json()
    paula.post(f"/api/veiculos/{civic['id']}/inativar")
    base = f"/api/veiculos/{civic['id']}/fotos"
    assert fotos(paula, civic["id"])["total"] == 1
    assert paula.get(f"{base}/{foto['id']}/arquivo").status_code == 200
    for resposta in (enviar_foto(paula, civic["id"]), paula.delete(f"{base}/{foto['id']}"),
                     paula.post(f"{base}/{foto['id']}/capa")):
        assert resposta.status_code == 409 and "inativo" in resposta.json()["mensagem"]
    assert imagens_no_banco(banco) == 1


# --------------------------------------------- foto e imagem andando juntas

def test_apagar_foto_remove_a_linha_e_a_imagem(banco, paula, civic):
    foto = enviar_foto(paula, civic["id"], principal="true").json()
    outra = enviar_foto(paula, civic["id"]).json()
    caminho = f"/api/veiculos/{civic['id']}/fotos/{foto['id']}"
    assert paula.delete(caminho).status_code == 204
    assert paula.get(f"{caminho}/arquivo").status_code == 404
    assert [f["id"] for f in fotos(paula, civic["id"])["itens"]] == [outra["id"]]
    assert imagens_no_banco(banco) == 1
    assert paula.get(f"/api/veiculos/{civic['id']}").json()["foto_capa_id"] is None
    assert paula.delete(caminho).status_code == 404


def test_falha_ao_gravar_a_imagem_desfaz_a_foto(banco, paula, civic, monkeypatch):
    def falhar(self, *args, **kwargs):
        raise RuntimeError("falha forçada no banco")

    monkeypatch.setattr(FotoRepository, "salvar_conteudo", falhar)
    with pytest.raises(RuntimeError, match="falha forçada"):
        enviar_foto(paula, civic["id"], principal="true")
    # A linha da foto (já criada) foi desfeita junto: nada pela metade.
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0
    assert imagens_no_banco(banco) == 0


def test_foto_sem_imagem_responde_nao_encontrado(banco, paula, civic):
    """Caso de foto antiga cujo arquivo já tinha sumido antes da 0013."""
    foto = enviar_foto(paula, civic["id"]).json()
    executar_sql(banco, "DELETE FROM foto_conteudo WHERE foto_id = :f", f=foto["id"])
    resposta = paula.get(f"/api/veiculos/{civic['id']}/fotos/{foto['id']}/arquivo")
    assert resposta.status_code == 404
    assert "não está mais disponível" in resposta.json()["mensagem"]
    assert fotos(paula, civic["id"])["total"] == 1  # continua na galeria


def test_banco_recusa_imagem_vazia(banco, paula, civic):
    foto = enviar_foto(paula, civic["id"]).json()
    with pytest.raises(Exception):
        executar_sql(banco, "UPDATE foto_conteudo SET dados = '' WHERE foto_id = :f", f=foto["id"])


def test_apagar_veiculo_direto_no_banco_apaga_as_imagens(banco, paula, civic):
    enviar_foto(paula, civic["id"])
    executar_sql(banco, "DELETE FROM veiculo WHERE id = :v", v=civic["id"])
    assert valor_sql(banco, "SELECT count(*) FROM veiculo_foto") == 0
    assert imagens_no_banco(banco) == 0  # cascata: nada sobra


def test_importar_fotos_da_antiga_pasta_pelo_terminal(banco, paula, civic, pasta_fotos, capsys):
    recuperavel = enviar_foto(paula, civic["id"]).json()
    perdida = enviar_foto(paula, civic["id"]).json()
    vazia = enviar_foto(paula, civic["id"]).json()
    intacta = enviar_foto(paula, civic["id"]).json()
    original = paula.get(f"/api/veiculos/{civic['id']}/fotos/{recuperavel['id']}/arquivo").content
    nomes = {}
    for foto in (recuperavel, perdida, vazia):
        nomes[foto["id"]] = valor_sql(banco, "SELECT arquivo FROM veiculo_foto WHERE id = :f",
                                      f=foto["id"])
        executar_sql(banco, "DELETE FROM foto_conteudo WHERE foto_id = :f", f=foto["id"])
    # Na pasta: o arquivo de uma, um arquivo vazio de outra, um arquivo de ninguém
    # e um arquivo com o nome da foto intacta (que NÃO pode substituir a do banco).
    for foto, conteudo in ((recuperavel, original), (vazia, b"")):
        destino = pasta_fotos / nomes[foto["id"]]
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(conteudo)
    (pasta_fotos / "veiculos" / "999").mkdir(parents=True)
    (pasta_fotos / "veiculos" / "999" / "solta.jpg").write_bytes(b"x")
    nome_intacta = valor_sql(banco, "SELECT arquivo FROM veiculo_foto WHERE id = :f", f=intacta["id"])
    (pasta_fotos / nome_intacta).write_bytes(b"nao e a imagem")

    gerenciar(["importar-fotos", "--teste", "--pasta", str(pasta_fotos)])
    saida = capsys.readouterr().out
    assert "Fotos copiadas para o banco agora: 1" in saida and nomes[recuperavel["id"]] in saida
    assert "sem arquivo na pasta: 1" in saida and nomes[perdida["id"]] in saida
    assert "acima de 10 MB (não copiados): 1" in saida
    assert "não são de nenhuma foto: 1" in saida and "veiculos/999/solta.jpg" in saida
    assert "Nenhum arquivo foi apagado" in saida

    base = f"/api/veiculos/{civic['id']}/fotos"
    assert paula.get(f"{base}/{recuperavel['id']}/arquivo").content == original
    assert paula.get(f"{base}/{perdida['id']}/arquivo").status_code == 404
    assert paula.get(f"{base}/{intacta['id']}/arquivo").content != b"nao e a imagem"
    assert len(arquivos_na_pasta(pasta_fotos)) == 4  # nada apagado

    # Rodar de novo não duplica nem troca nada.
    gerenciar(["importar-fotos", "--teste", "--pasta", str(pasta_fotos)])
    assert "Fotos copiadas para o banco agora: 0" in capsys.readouterr().out
    assert imagens_no_banco(banco) == 2

# ------------------------------------------------------------ regras isoladas

def test_identifica_o_formato_pelos_primeiros_bytes():
    assert identificar_formato(imagem("JPEG")) == "jpeg"
    assert identificar_formato(imagem("PNG")) == "png"
    assert identificar_formato(imagem("WEBP")) == "webp"
    assert identificar_formato(imagem("HEIF")) == "heic"
    assert identificar_formato(imagem("GIF")) is None
    assert identificar_formato(imagem("BMP")) is None
    assert identificar_formato(b"") is None


def test_png_transparente_continua_png_e_imagem_gigante_e_recusada():
    pronta = preparar_imagem(imagem("PNG", cor=(255, 0, 0, 0)))
    assert pronta.tipo_mime == "image/png" and pronta.extensao == "png"
    assert Image.open(io.BytesIO(pronta.conteudo)).mode == "RGBA"
    # PNG de uma cor só é minúsculo em bytes, mas enorme em pontos.
    gigante = imagem("PNG", tamanho=(9000, 9000), cor=(0, 0, 0, 0))
    assert len(gigante) < TAMANHO_MAXIMO_BYTES
    with pytest.raises(DadosInvalidos, match="megapixels"):
        preparar_imagem(gigante)
