"""Conferência e preparo das fotos enviadas.

O que o backend faz com cada arquivo recebido:
1. Identifica o formato pelos PRIMEIROS BYTES do arquivo (a "assinatura"),
   não pela extensão nem pelo tipo informado pelo navegador.
2. Abre a imagem inteira com a biblioteca Pillow. Arquivo corrompido, ou
   que só finge ser imagem, é recusado aqui.
3. Regrava a imagem do zero. O arquivo guardado contém só os pontos da
   imagem: some qualquer conteúdo escondido e somem os metadados (inclusive
   a localização GPS que o celular grava na foto). A rotação indicada nos
   metadados é aplicada antes, para a foto não ficar deitada.
4. Reduz fotos muito grandes para no máximo 2560 pontos no lado maior.

Formatos aceitos: JPEG, PNG, WebP e HEIC (padrão da câmera do iPhone).
HEIC é convertido para JPEG, porque o Chrome do Android e a maioria dos
navegadores não exibem HEIC. O tipo e o tamanho gravados no banco são os
do arquivo realmente guardado (depois da conversão).
"""

import io

import pillow_heif
from PIL import Image, ImageOps, UnidentifiedImageError

from app.entities.veiculo_foto import TAMANHO_MAXIMO_BYTES, ImagemPronta
from app.services.erros import DadosInvalidos

pillow_heif.register_heif_opener()

LADO_MAXIMO = 2560
PIXELS_MAXIMO = 60_000_000  # bem acima de qualquer câmera de celular
QUALIDADE = 86

MENSAGEM_FORMATO = "Formato não aceito. Envie uma foto JPEG, PNG, WebP ou HEIC."
MENSAGEM_CORROMPIDA = "O arquivo não é uma imagem válida ou está corrompido."
MENSAGEM_TAMANHO = "Foto grande demais. O limite é 10 MB."

# Marcas ("brands") de arquivos HEIC/HEIF de foto.
MARCAS_HEIC = {b"heic", b"heix", b"heim", b"heis", b"hevc", b"hevx", b"mif1", b"msf1"}
# formato identificado -> formatos que o Pillow pode reportar ao abrir
FORMATO_PILLOW = {"jpeg": {"JPEG", "MPO"}, "png": {"PNG"}, "webp": {"WEBP"}, "heic": {"HEIF"}}
# formato identificado -> (formato de gravação, tipo MIME, extensão)
SAIDA = {
    "jpeg": ("JPEG", "image/jpeg", "jpg"),
    "heic": ("JPEG", "image/jpeg", "jpg"),
    "png": ("PNG", "image/png", "png"),
    "webp": ("WEBP", "image/webp", "webp"),
}


def identificar_formato(conteudo: bytes) -> str | None:
    """Formato pela assinatura do arquivo; None se não for um dos aceitos."""
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "webp"
    if conteudo[4:8] == b"ftyp" and conteudo[8:12] in MARCAS_HEIC:
        return "heic"
    return None


def preparar_imagem(conteudo: bytes) -> ImagemPronta:
    """Confere o arquivo recebido e devolve a imagem regravada, pronta para guardar."""
    if not conteudo:
        raise DadosInvalidos("Escolha uma foto.", campo="arquivo")
    if len(conteudo) > TAMANHO_MAXIMO_BYTES:
        raise DadosInvalidos(MENSAGEM_TAMANHO, campo="arquivo")
    formato = identificar_formato(conteudo)
    if formato is None:
        raise DadosInvalidos(MENSAGEM_FORMATO, campo="arquivo")

    try:
        # Abrir só lê o cabeçalho; o tamanho é conferido ANTES de carregar os
        # pontos, para uma imagem gigante não esgotar a memória.
        imagem = Image.open(io.BytesIO(conteudo))
        if imagem.format not in FORMATO_PILLOW[formato]:
            raise DadosInvalidos(MENSAGEM_FORMATO, campo="arquivo")
        largura, altura = imagem.size
        if largura * altura > PIXELS_MAXIMO:
            raise DadosInvalidos("Imagem grande demais (muitos megapixels).", campo="arquivo")
        imagem.load()
        imagem = ImageOps.exif_transpose(imagem)
    except DadosInvalidos:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError,
            Image.DecompressionBombError):
        raise DadosInvalidos(MENSAGEM_CORROMPIDA, campo="arquivo") from None

    imagem.thumbnail((LADO_MAXIMO, LADO_MAXIMO), Image.Resampling.LANCZOS)
    formato_saida, tipo_mime, extensao = SAIDA[formato]
    saida = io.BytesIO()
    if formato_saida == "JPEG":
        # JPEG não tem transparência: fundo branco para o que for transparente.
        if imagem.mode in ("RGBA", "LA", "P"):
            rgba = imagem.convert("RGBA")
            fundo = Image.new("RGB", rgba.size, "white")
            fundo.paste(rgba, mask=rgba.getchannel("A"))
            imagem = fundo
        imagem.convert("RGB").save(saida, "JPEG", quality=QUALIDADE, optimize=True)
    elif formato_saida == "PNG":
        if imagem.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            imagem = imagem.convert("RGBA")
        imagem.save(saida, "PNG", optimize=True)
    else:
        if imagem.mode not in ("RGB", "RGBA"):
            imagem = imagem.convert("RGBA" if "A" in imagem.getbands() else "RGB")
        imagem.save(saida, "WEBP", quality=QUALIDADE)

    pronta = saida.getvalue()
    if len(pronta) > TAMANHO_MAXIMO_BYTES:
        raise DadosInvalidos(MENSAGEM_TAMANHO, campo="arquivo")
    return ImagemPronta(conteudo=pronta, tipo_mime=tipo_mime, extensao=extensao)
