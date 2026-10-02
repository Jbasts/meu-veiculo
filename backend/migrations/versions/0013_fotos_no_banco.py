"""Conteúdo das fotos dentro do PostgreSQL (pedido da Paula, 02/10/2026).

Revisão: 0013
Anterior: 0012

Antes
    A imagem ficava num arquivo da pasta de fotos do backend (PASTA_FOTOS,
    padrão backend/storage) e o banco guardava só o caminho em
    veiculo_foto.arquivo.

Agora
    Tabela nova foto_conteudo: uma linha por foto, com os bytes da imagem
    (bytea). Fica separada de veiculo_foto para que as listagens da galeria
    não carreguem as imagens. Apagar a foto apaga o conteúdo junto (cascata),
    então apagar veículo, manutenção, diagnóstico ou projeto também não deixa
    nada sobrando. O backup do banco (pg_dump) passa a levar as fotos.
    veiculo_foto.arquivo continua existindo (é do SQL original, obrigatório e
    único) e vira só um nome de referência.

Dados existentes
    Cada foto já cadastrada tem o arquivo copiado da pasta para o banco.
    Nada é apagado da pasta: depois de conferir as fotos no app, a pessoa
    pode apagá-la. Foto cujo arquivo não está na pasta continua na galeria
    como antes ("Imagem indisponível") e aparece na lista do log; se o
    arquivo for encontrado depois, "gerenciar.py importar-fotos" copia o que
    faltou. Nenhum conteúdo é inventado.

    A pasta lida é PASTA_FOTOS do .env. Os testes passam outra pasta pelo
    atributo "pasta_fotos" da configuração do Alembic.
"""

import logging
from pathlib import Path

from alembic import context, op
from sqlalchemy import text

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

TAMANHO_MAXIMO_BYTES = 10_485_760  # 10 MB, o mesmo limite do CHECK de veiculo_foto

SQL_ESTRUTURA = f"""
CREATE TABLE foto_conteudo (
    foto_id  INT    PRIMARY KEY REFERENCES veiculo_foto(id) ON DELETE CASCADE,
    dados    BYTEA  NOT NULL
        CHECK (octet_length(dados) BETWEEN 1 AND {TAMANHO_MAXIMO_BYTES})
);
-- O conteúdo já é JPEG/PNG/WebP comprimido: comprimir de novo só gasta tempo.
ALTER TABLE foto_conteudo ALTER COLUMN dados SET STORAGE EXTERNAL;
"""


def _pasta_fotos() -> Path:
    pasta = context.config.attributes.get("pasta_fotos")
    if pasta is None:
        from app.config import obter_configuracoes

        pasta = obter_configuracoes().pasta_fotos
    return Path(pasta).resolve()


def _arquivo(pasta: Path, relativo: str) -> Path | None:
    """Caminho do arquivo dentro da pasta, ou None se não existe ou sairia da pasta."""
    destino = (pasta / relativo).resolve()
    if not destino.is_relative_to(pasta) or not destino.is_file():
        return None
    return destino


def upgrade() -> None:
    op.execute(SQL_ESTRUTURA)
    conexao = op.get_bind()
    fotos = conexao.execute(text("SELECT id, arquivo FROM veiculo_foto ORDER BY id")).all()
    if not fotos:
        return
    pasta = _pasta_fotos()
    copiadas, sem_arquivo, grandes = 0, [], []
    for foto_id, relativo in fotos:
        caminho = _arquivo(pasta, relativo)
        if caminho is None:
            sem_arquivo.append(f"foto {foto_id} ({relativo})")
            continue
        dados = caminho.read_bytes()
        if not 0 < len(dados) <= TAMANHO_MAXIMO_BYTES:
            grandes.append(f"foto {foto_id} ({relativo}, {len(dados)} bytes)")
            continue
        conexao.execute(text("INSERT INTO foto_conteudo (foto_id, dados) VALUES (:f, :d)"),
                        {"f": foto_id, "d": dados})
        copiadas += 1
    log.info("0013: %d de %d fotos copiadas da pasta %s para o banco. Nenhum arquivo foi apagado.",
             copiadas, len(fotos), pasta)
    if sem_arquivo:
        log.warning("0013: %d foto(s) sem arquivo na pasta; continuam como 'Imagem indisponível'. "
                    "Se encontrar os arquivos, rode 'gerenciar.py importar-fotos': %s",
                    len(sem_arquivo), "; ".join(sem_arquivo))
    if grandes:
        log.warning("0013: %d arquivo(s) vazio(s) ou acima de 10 MB não foram copiados: %s",
                    len(grandes), "; ".join(grandes))


def downgrade() -> None:
    # Voltar para a 0012 apagaria as imagens, que agora só existem no banco.
    # Com alguma foto guardada, recusa: o caminho seguro é restaurar um backup.
    guardadas = op.get_bind().execute(text("SELECT count(*) FROM foto_conteudo")).scalar()
    if guardadas:
        raise RuntimeError(f"Há {guardadas} foto(s) guardada(s) no banco. Desfazer a 0013 apagaria "
                           "essas imagens; restaure um backup feito antes da 0013.")
    op.execute("DROP TABLE foto_conteudo")
