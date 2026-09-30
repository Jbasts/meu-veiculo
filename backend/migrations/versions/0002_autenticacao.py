"""Autenticação: e-mail normalizado, sessões, recuperação de senha,
limite de tentativas e proteção do último administrador ativo.

Revisão: 0002
Anterior: 0001

Antes de mudar qualquer dado, confere se há e-mails que ficariam iguais
depois de tirar espaços e passar para minúsculas (ex.: "Ana@x.com" e
" ana@x.com"). Se houver, lista os registros e PARA, sem apagar nem unir
nada. Corrija à mão (veja o README) e rode "gerenciar.py migrar" de novo.
"""

import logging

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

SQL_TABELAS = """
ALTER TABLE usuario
    ADD CONSTRAINT usuario_email_normalizado
    CHECK (email = lower(btrim(email)) AND position('@' IN email) > 1);

CREATE TABLE sessao (
    id                BIGSERIAL    PRIMARY KEY,
    usuario_id        INT          NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    token_hash        CHAR(64)     NOT NULL UNIQUE,     -- SHA-256 do token; o token em si nunca é gravado
    criada_em         TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expira_em         TIMESTAMPTZ  NOT NULL,
    ultimo_uso_em     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    revogada_em       TIMESTAMPTZ,
    motivo_revogacao  VARCHAR(30),
    CHECK (expira_em > criada_em),
    CHECK ((revogada_em IS NULL) = (motivo_revogacao IS NULL))
);
CREATE INDEX sessao_usuario_ativas_idx ON sessao (usuario_id) WHERE revogada_em IS NULL;

CREATE TABLE recuperacao_senha (
    id            BIGSERIAL    PRIMARY KEY,
    usuario_id    INT          NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    token_hash    CHAR(64)     NOT NULL UNIQUE,         -- SHA-256 do token do link
    finalidade    VARCHAR(12)  NOT NULL DEFAULT 'recuperacao'
                  CHECK (finalidade IN ('recuperacao', 'convite')),
    criado_em     TIMESTAMPTZ  NOT NULL DEFAULT now(),
    expira_em     TIMESTAMPTZ  NOT NULL,
    usado_em      TIMESTAMPTZ,                          -- preenchido uma única vez, ao trocar a senha
    cancelado_em  TIMESTAMPTZ,                          -- substituído por um link mais novo
    CHECK (expira_em > criado_em),
    CHECK (usado_em IS NULL OR cancelado_em IS NULL)
);
CREATE INDEX recuperacao_senha_usuario_idx ON recuperacao_senha (usuario_id);

CREATE TABLE tentativa_acesso (
    id           BIGSERIAL    PRIMARY KEY,
    tipo         VARCHAR(12)  NOT NULL CHECK (tipo IN ('login', 'recuperacao')),
    chave_email  CHAR(64),                              -- SHA-256 do e-mail (não guarda o e-mail)
    ip           VARCHAR(45),
    sucesso      BOOLEAN      NOT NULL,
    criado_em    TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX tentativa_acesso_email_idx ON tentativa_acesso (tipo, chave_email, criado_em);
CREATE INDEX tentativa_acesso_ip_idx    ON tentativa_acesso (tipo, ip, criado_em);

-- Nunca deixar o sistema sem administrador ativo.
-- A trava (advisory lock) faz duas alterações simultâneas esperarem uma pela
-- outra; a segunda enxerga a primeira já gravada e é recusada.
CREATE FUNCTION garantir_admin_ativo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    PERFORM pg_advisory_xact_lock(hashtext('meu_veiculo:ultimo_admin'));
    IF NOT EXISTS (SELECT 1 FROM usuario WHERE perfil = 'admin' AND ativo) THEN
        RAISE EXCEPTION 'Não é possível desativar, rebaixar ou apagar o último administrador ativo.'
              USING ERRCODE = 'P0001', HINT = 'ultimo_admin';
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_ultimo_admin_alteracao
    AFTER UPDATE OF perfil, ativo ON usuario
    FOR EACH ROW
    WHEN (OLD.perfil = 'admin' AND OLD.ativo AND NOT (NEW.perfil = 'admin' AND NEW.ativo))
    EXECUTE FUNCTION garantir_admin_ativo();

CREATE TRIGGER trg_ultimo_admin_exclusao
    AFTER DELETE ON usuario
    FOR EACH ROW
    WHEN (OLD.perfil = 'admin' AND OLD.ativo)
    EXECUTE FUNCTION garantir_admin_ativo();
"""


def verificar_emails(conexao) -> None:
    colisoes = conexao.exec_driver_sql(
        """
        SELECT lower(btrim(email)) AS normalizado,
               string_agg(id::text || ' (' || email || ')', ', ' ORDER BY id)
          FROM usuario
         GROUP BY lower(btrim(email))
        HAVING count(*) > 1
        """
    ).fetchall()
    invalidos = conexao.exec_driver_sql(
        "SELECT id, email FROM usuario WHERE position('@' IN btrim(email)) <= 1 ORDER BY id"
    ).fetchall()
    if not colisoes and not invalidos:
        return
    linhas = ["A migration 0002 parou: há e-mails incompatíveis com a normalização. Nada foi alterado."]
    for normalizado, usuarios in colisoes:
        linhas.append(f"  - ficariam iguais a '{normalizado}': usuários {usuarios}")
    for usuario_id, email in invalidos:
        linhas.append(f"  - usuário {usuario_id}: e-mail sem '@' válido: '{email}'")
    linhas.append("Corrija esses cadastros (veja o README, seção de migrations) e rode 'gerenciar.py migrar'.")
    raise RuntimeError("\n".join(linhas))


def upgrade() -> None:
    conexao = op.get_bind()
    verificar_emails(conexao)
    alterados = conexao.exec_driver_sql(
        "UPDATE usuario SET email = lower(btrim(email)) WHERE email <> lower(btrim(email))"
    ).rowcount
    if alterados:
        log.info("E-mails normalizados (espaços e maiúsculas): %s", alterados)
    conexao.connection.driver_connection.execute(SQL_TABELAS)


def downgrade() -> None:
    # A normalização dos e-mails não é desfeita (não há como saber a grafia original).
    conexao = op.get_bind()
    conexao.connection.driver_connection.execute(
        """
        DROP TRIGGER trg_ultimo_admin_exclusao ON usuario;
        DROP TRIGGER trg_ultimo_admin_alteracao ON usuario;
        DROP FUNCTION garantir_admin_ativo();
        DROP TABLE tentativa_acesso;
        DROP TABLE recuperacao_senha;
        DROP TABLE sessao;
        ALTER TABLE usuario DROP CONSTRAINT usuario_email_normalizado;
        """
    )
