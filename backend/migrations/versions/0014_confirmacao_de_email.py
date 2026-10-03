"""Confirmação do e-mail no cadastro (pedido da Paula, 02/10/2026).

Revisão: 0014
Anterior: 0013

Antes
    "Criar conta" já entrava no sistema, sem conferir se o e-mail era da pessoa.

Agora
    usuario.email_confirmado (obrigatório, padrão FALSE) e
    usuario.email_confirmado_em (quando o link foi aberto). A conta criada pela
    tela só entra depois de abrir o link de confirmação enviado por e-mail.
    O link usa a mesma tabela dos links de senha (recuperacao_senha), com a
    finalidade nova "confirmacao": só o hash do token, validade e uso único.

Dados existentes
    As contas que já existem continuam entrando: ficam com email_confirmado =
    TRUE e email_confirmado_em vazio (a data da confirmação não é inventada;
    vazio quer dizer "conta anterior à regra"). Nenhum dado é apagado.
"""

import logging

from alembic import op
from sqlalchemy import text

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

SQL_SUBIR = """
ALTER TABLE usuario
    ADD COLUMN email_confirmado    BOOLEAN      NOT NULL DEFAULT FALSE,
    ADD COLUMN email_confirmado_em TIMESTAMPTZ,
    ADD CONSTRAINT usuario_confirmacao_coerente_check
        CHECK (email_confirmado OR email_confirmado_em IS NULL);

-- Contas anteriores à regra continuam entrando (sem inventar a data).
UPDATE usuario SET email_confirmado = TRUE;

ALTER TABLE recuperacao_senha DROP CONSTRAINT recuperacao_senha_finalidade_check;
ALTER TABLE recuperacao_senha ADD CONSTRAINT recuperacao_senha_finalidade_check
    CHECK (finalidade IN ('recuperacao', 'convite', 'confirmacao'));
"""


def upgrade() -> None:
    op.execute(SQL_SUBIR)


def downgrade() -> None:
    # Nenhum dado da pessoa se perde: só a marca "esperando confirmação" e os
    # links de confirmação. Avisa quais contas passam a entrar sem confirmar.
    pendentes = [linha[0] for linha in op.get_bind().execute(
        text("SELECT email FROM usuario WHERE NOT email_confirmado ORDER BY id"))]
    if pendentes:
        log.warning("0014 desfeita: %d conta(s) ainda não tinham confirmado o e-mail e passam a "
                    "entrar sem confirmar: %s", len(pendentes), ", ".join(pendentes))
    op.execute("""
        DELETE FROM recuperacao_senha WHERE finalidade = 'confirmacao';
        ALTER TABLE recuperacao_senha DROP CONSTRAINT recuperacao_senha_finalidade_check;
        ALTER TABLE recuperacao_senha ADD CONSTRAINT recuperacao_senha_finalidade_check
            CHECK (finalidade IN ('recuperacao', 'convite'));
        ALTER TABLE usuario DROP CONSTRAINT usuario_confirmacao_coerente_check,
            DROP COLUMN email_confirmado_em,
            DROP COLUMN email_confirmado;
    """)
