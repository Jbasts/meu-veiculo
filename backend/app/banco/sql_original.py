"""Tudo o que envolve o SQL original (database/original/meu_veiculo_banco.sql).

1. Ler o arquivo e conferir a "impressão digital" (SHA-256). Se alguém editar
   o arquivo, a migration 0001 se recusa a rodar: mudanças no banco entram
   sempre como migration nova.
2. Comparar um banco existente com o que o SQL original cria. É isso que
   permite "adotar" um banco criado antes do controle de migrations sem
   rodar o script de novo.

Atenção: a migration 0001 depende deste módulo. Não mude o comportamento
destas funções; se um dia precisar de outra lógica, crie funções novas.
"""

import hashlib
from dataclasses import dataclass, field
from pathlib import Path

import psycopg
from psycopg import sql

from app.config import PASTA_PROJETO

CAMINHO_SQL_ORIGINAL = PASTA_PROJETO / "database" / "original" / "meu_veiculo_banco.sql"

# SHA-256 do arquivo com quebras de linha LF. O Git no Windows pode trocar
# LF por CRLF ao baixar o projeto; por isso o cálculo converte antes.
SHA256_SQL_ORIGINAL = "dbcb6d0b6d133d987c6c4f11023ad871d5bef645a93a6be14ce6287c24b40051"

ESQUEMA_REFERENCIA = "mv_referencia_original"

# A tabela de controle do Alembic não faz parte do SQL original.
TABELAS_IGNORADAS = ("alembic_version",)


class SqlOriginalAlterado(Exception):
    """O arquivo do SQL original não é mais o que foi recebido."""


def ler_sql_original(caminho: Path = CAMINHO_SQL_ORIGINAL) -> str:
    texto = caminho.read_bytes().decode("utf-8").replace("\r\n", "\n")
    obtido = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    if obtido != SHA256_SQL_ORIGINAL:
        raise SqlOriginalAlterado(
            f"O arquivo {caminho} foi alterado (SHA-256 {obtido}, esperado "
            f"{SHA256_SQL_ORIGINAL}). O SQL original é somente leitura: "
            "restaure-o com 'git checkout -- database/original/meu_veiculo_banco.sql' "
            "e coloque mudanças numa migration nova."
        )
    return texto


def remover_transacao(texto: str) -> str:
    """Tira as linhas 'BEGIN;' e 'COMMIT;' do script.

    O Alembic já executa cada migration dentro de uma transação. Se o
    COMMIT do arquivo rodasse, ele fecharia essa transação no meio e uma
    falha posterior deixaria o banco pela metade.
    """
    linhas = texto.split("\n")
    inicios = [i for i, linha in enumerate(linhas) if linha.strip() == "BEGIN;"]
    fins = [i for i, linha in enumerate(linhas) if linha.strip() == "COMMIT;"]
    if len(inicios) != 1 or len(fins) != 1 or inicios[0] > fins[0]:
        raise SqlOriginalAlterado(
            "Esperava exatamente um 'BEGIN;' antes de um 'COMMIT;' no SQL original."
        )
    remover = {inicios[0], fins[0]}
    return "\n".join(linha for i, linha in enumerate(linhas) if i not in remover)


def sql_original_para_executar(caminho: Path = CAMINHO_SQL_ORIGINAL) -> str:
    return remover_transacao(ler_sql_original(caminho))


# ---------------------------------------------------------------------------
# Comparação de estrutura
# ---------------------------------------------------------------------------

_CONSULTAS = {
    "coluna": """
        SELECT c.relname, a.attname, format_type(a.atttypid, a.atttypmod),
               CASE WHEN a.attnotnull THEN 'NOT NULL' ELSE 'NULL' END
          FROM pg_attribute a
          JOIN pg_class c     ON c.oid = a.attrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = %(esquema)s
           AND c.relkind IN ('r', 'v')
           AND a.attnum > 0 AND NOT a.attisdropped
           AND c.relname <> ALL(%(ignoradas)s)
    """,
    "restrição": """
        SELECT c.relname, con.conname, pg_get_constraintdef(con.oid)
          FROM pg_constraint con
          JOIN pg_class c     ON c.oid = con.conrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = %(esquema)s
           AND c.relname <> ALL(%(ignoradas)s)
    """,
    "índice": """
        SELECT tablename, indexname, indexdef
          FROM pg_indexes
         WHERE schemaname = %(esquema)s
           AND tablename <> ALL(%(ignoradas)s)
    """,
    "view": """
        SELECT viewname, definition
          FROM pg_views
         WHERE schemaname = %(esquema)s
    """,
    "trigger": """
        SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid)
          FROM pg_trigger t
          JOIN pg_class c     ON c.oid = t.tgrelid
          JOIN pg_namespace n ON n.oid = c.relnamespace
         WHERE n.nspname = %(esquema)s
           AND NOT t.tgisinternal
    """,
    "função": """
        SELECT p.proname, pg_get_functiondef(p.oid)
          FROM pg_proc p
          JOIN pg_namespace n ON n.oid = p.pronamespace
         WHERE n.nspname = %(esquema)s
    """,
    "domain": """
        SELECT t.typname, format_type(t.typbasetype, t.typtypmod),
               COALESCE(string_agg(pg_get_constraintdef(con.oid), ' ' ORDER BY con.conname), '')
          FROM pg_type t
          JOIN pg_namespace n ON n.oid = t.typnamespace
          LEFT JOIN pg_constraint con ON con.contypid = t.oid
         WHERE n.nspname = %(esquema)s
           AND t.typtype = 'd'
         GROUP BY t.typname, t.typbasetype, t.typtypmod
    """,
}

Estrutura = dict[str, frozenset[tuple[str, ...]]]


def _normalizar(valor: str, esquema: str) -> str:
    return valor.replace(f'"{esquema}".', "").replace(f"{esquema}.", "")


def ler_estrutura(conexao: psycopg.Connection, esquema: str = "public") -> Estrutura:
    """Descreve tabelas, colunas, restrições, índices, views, triggers,
    funções e domains de um esquema, sem o nome do esquema nos textos.

    Precisa rodar dentro de uma transação (conexão sem autocommit).
    """
    conexao.execute(sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(esquema)))
    estrutura: dict[str, frozenset[tuple[str, ...]]] = {}
    for tipo, consulta in _CONSULTAS.items():
        linhas = conexao.execute(
            consulta, {"esquema": esquema, "ignoradas": list(TABELAS_IGNORADAS)}
        ).fetchall()
        estrutura[tipo] = frozenset(
            tuple(_normalizar(str(valor), esquema) for valor in linha) for linha in linhas
        )
    return estrutura


def estrutura_de_referencia(conexao: psycopg.Connection) -> Estrutura:
    """Cria o SQL original num esquema temporário, lê a estrutura e desfaz tudo.

    Nada fica gravado: o esquema é criado dentro de um SAVEPOINT que é
    desfeito no final.
    """
    texto = sql_original_para_executar()
    conexao.execute("SAVEPOINT referencia_original")
    try:
        conexao.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(ESQUEMA_REFERENCIA)))
        conexao.execute(
            sql.SQL("SET LOCAL search_path TO {}").format(sql.Identifier(ESQUEMA_REFERENCIA))
        )
        conexao.execute(texto)
        return ler_estrutura(conexao, ESQUEMA_REFERENCIA)
    finally:
        conexao.execute("ROLLBACK TO SAVEPOINT referencia_original")
        conexao.execute("SET LOCAL search_path TO public")


@dataclass
class Diferencas:
    faltando: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)
    sobrando: list[tuple[str, tuple[str, ...]]] = field(default_factory=list)

    @property
    def iguais(self) -> bool:
        return not self.faltando and not self.sobrando

    def descrever(self, limite: int = 40) -> str:
        partes: list[str] = []
        for titulo, itens in (
            ("Existe no SQL original, mas NÃO no banco", self.faltando),
            ("Existe no banco, mas NÃO no SQL original", self.sobrando),
        ):
            if itens:
                partes.append(f"{titulo} ({len(itens)}):")
                for tipo, item in itens[:limite]:
                    resumo = " | ".join(" ".join(parte.split()) for parte in item)
                    partes.append(f"  - {tipo}: {resumo[:200]}")
                if len(itens) > limite:
                    partes.append(f"  ... e mais {len(itens) - limite}")
        return "\n".join(partes)


def comparar_estruturas(banco: Estrutura, referencia: Estrutura) -> Diferencas:
    diferencas = Diferencas()
    for tipo in _CONSULTAS:
        atual = banco.get(tipo, frozenset())
        esperado = referencia.get(tipo, frozenset())
        diferencas.faltando += [(tipo, item) for item in sorted(esperado - atual)]
        diferencas.sobrando += [(tipo, item) for item in sorted(atual - esperado)]
    return diferencas


def comparar_com_original(conexao: psycopg.Connection, esquema: str = "public") -> Diferencas:
    referencia = estrutura_de_referencia(conexao)
    banco = ler_estrutura(conexao, esquema)
    return comparar_estruturas(banco, referencia)
