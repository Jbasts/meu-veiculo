"""Veículos: placa normalizada, histórico de leituras de quilometragem e
veículo em uso.

Revisão: 0003
Anterior: 0002

Placa
    Guardada em maiúsculas, sem hífen e sem espaços ("abc-1234" -> "ABC1234").
    A unicidade continua sendo por dono: UNIQUE (usuario_id, placa).
    Antes de alterar qualquer dado, a migration procura veículos do MESMO
    dono que ficariam com a mesma placa e placas com caracteres inválidos.
    Se houver, lista os registros e PARA, sem apagar nem unir nada.

Quilometragem
    Nova tabela leitura_km: cada leitura do hodômetro, com a data em que
    foi lida (data_leitura), separada da data em que foi digitada (criado_em).
    veiculo.quilometragem passa a ser sempre a MAIOR leitura válida, e
    veiculo.data_leitura_km é a data dessa leitura. Por isso:
    - um registro antigo (km menor) nunca reduz a quilometragem atual;
    - manutenção apenas agendada não gera leitura;
    - mudar só o status de agendada para realizada gera a leitura (o trigger
      antigo não disparava nesse caso);
    - corrigir ou apagar um registro digitado errado recalcula o km atual.
    Os abastecimentos, manutenções realizadas e diagnósticos já existentes
    viram leituras com as datas deles. Quando o km atual do veículo não vem
    de nenhum registro, é criada uma leitura "legado" SEM data (a data é
    desconhecida e não é inventada).

Veículo em uso
    usuario.veiculo_em_uso_id guarda o veículo selecionado. A chave
    estrangeira composta garante que ele pertence ao próprio usuário.
"""

import logging

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

log = logging.getLogger("alembic.runtime.migration")

PLACA_NORMALIZADA = r"upper(regexp_replace(placa, '[\s-]', '', 'g'))"

SQL_ESTRUTURA = r"""
ALTER TABLE veiculo
    ADD CONSTRAINT veiculo_placa_normalizada CHECK (placa ~ '^[A-Z0-9]+$');

-- Data da leitura que define a quilometragem atual. NULL = data desconhecida.
ALTER TABLE veiculo ADD COLUMN data_leitura_km DATE;

-- Permite chaves estrangeiras compostas que conferem o dono do veículo.
ALTER TABLE veiculo ADD CONSTRAINT veiculo_id_usuario_unico UNIQUE (id, usuario_id);

ALTER TABLE usuario ADD COLUMN veiculo_em_uso_id INT;
ALTER TABLE usuario
    ADD CONSTRAINT usuario_veiculo_em_uso_fk
    FOREIGN KEY (veiculo_em_uso_id, id) REFERENCES veiculo (id, usuario_id)
    ON DELETE SET NULL (veiculo_em_uso_id);

CREATE TABLE leitura_km (
    id                BIGSERIAL    PRIMARY KEY,
    veiculo_id        INT          NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    quilometragem     INT          NOT NULL CHECK (quilometragem >= 0),
    data_leitura      DATE,                                -- quando o hodômetro foi lido
    origem            VARCHAR(15)  NOT NULL
                      CHECK (origem IN ('cadastro', 'manual', 'abastecimento',
                                        'manutencao', 'diagnostico', 'legado')),
    origem_id         INT,                                 -- id do abastecimento/manutenção/diagnóstico
    corrige_id        BIGINT       REFERENCES leitura_km(id) ON DELETE SET NULL,  -- leitura que esta substituiu
    anulada_em        TIMESTAMPTZ,                         -- leitura errada: fica no histórico, não conta
    motivo_anulacao   VARCHAR(200),
    criado_em         TIMESTAMPTZ  NOT NULL DEFAULT now(), -- quando foi digitada
    -- Só a leitura herdada de antes desta migration pode ficar sem data.
    CHECK (data_leitura IS NOT NULL OR origem = 'legado'),
    CHECK ((origem IN ('abastecimento', 'manutencao', 'diagnostico')) = (origem_id IS NOT NULL)),
    CHECK (anulada_em IS NOT NULL OR motivo_anulacao IS NULL)
);
CREATE INDEX leitura_km_veiculo_idx ON leitura_km (veiculo_id, quilometragem DESC)
    WHERE anulada_em IS NULL;
CREATE UNIQUE INDEX leitura_km_origem_unica ON leitura_km (origem, origem_id)
    WHERE origem_id IS NOT NULL;
"""

# Leituras a partir dos registros que já existem (datas reais dos registros).
SQL_CARGA_INICIAL = """
INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem, origem_id)
SELECT veiculo_id, quilometragem, data, 'abastecimento', id FROM abastecimento;

INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem, origem_id)
SELECT veiculo_id, quilometragem, data, 'manutencao', id FROM manutencao
 WHERE status = 'realizada' AND quilometragem IS NOT NULL;

INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem, origem_id)
SELECT veiculo_id, quilometragem, data_identificacao, 'diagnostico', id FROM diagnostico
 WHERE quilometragem IS NOT NULL;

-- Km atual que não veio de nenhum registro: leitura herdada, sem data.
INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem)
SELECT v.id, v.quilometragem, NULL, 'legado'
  FROM veiculo v
 WHERE v.quilometragem > COALESCE(
           (SELECT max(l.quilometragem) FROM leitura_km l WHERE l.veiculo_id = v.id), -1);
"""

SQL_FUNCOES = r"""
-- A quilometragem atual é a maior leitura válida; a data é a dessa leitura.
CREATE FUNCTION recalcular_km_veiculo(p_veiculo_id INT) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    v_km   INT;
    v_data DATE;
BEGIN
    SELECT quilometragem, data_leitura INTO v_km, v_data
      FROM leitura_km
     WHERE veiculo_id = p_veiculo_id AND anulada_em IS NULL
     ORDER BY quilometragem DESC, data_leitura DESC NULLS LAST, id DESC
     LIMIT 1;
    IF FOUND THEN
        PERFORM set_config('meu_veiculo.recalculando_km', 'sim', true);
        UPDATE veiculo
           SET quilometragem = v_km, data_leitura_km = v_data
         WHERE id = p_veiculo_id
           AND (quilometragem, data_leitura_km) IS DISTINCT FROM (v_km, v_data);
        PERFORM set_config('meu_veiculo.recalculando_km', '', true);
    END IF;
END;
$$;

CREATE FUNCTION trg_leitura_km_recalcular() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        PERFORM recalcular_km_veiculo(OLD.veiculo_id);
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        PERFORM recalcular_km_veiculo(NEW.veiculo_id);
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_leitura_km_recalcular
    AFTER INSERT OR UPDATE OR DELETE ON leitura_km
    FOR EACH ROW EXECUTE FUNCTION trg_leitura_km_recalcular();

-- Ninguém altera veiculo.quilometragem direto: a mudança vem sempre de uma leitura.
CREATE FUNCTION proteger_km_veiculo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF COALESCE(current_setting('meu_veiculo.recalculando_km', true), '') <> 'sim' THEN
        RAISE EXCEPTION 'A quilometragem atual é calculada a partir das leituras (tabela leitura_km). Registre ou corrija uma leitura em vez de alterar o veículo.'
              USING ERRCODE = 'P0001', HINT = 'km_protegido';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_veiculo_proteger_km
    BEFORE UPDATE OF quilometragem, data_leitura_km ON veiculo
    FOR EACH ROW
    WHEN (OLD.quilometragem IS DISTINCT FROM NEW.quilometragem
          OR OLD.data_leitura_km IS DISTINCT FROM NEW.data_leitura_km)
    EXECUTE FUNCTION proteger_km_veiculo();

-- Veículo novo: a quilometragem informada no cadastro é a primeira leitura (data de hoje).
CREATE FUNCTION trg_veiculo_leitura_inicial() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem)
    VALUES (NEW.id, NEW.quilometragem, CURRENT_DATE, 'cadastro');
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_veiculo_leitura_inicial
    AFTER INSERT ON veiculo
    FOR EACH ROW EXECUTE FUNCTION trg_veiculo_leitura_inicial();

-- Abastecimento, manutenção REALIZADA e diagnóstico com km viram leitura.
-- Dispara em qualquer alteração (inclusive só do status ou da data) e na exclusão.
-- Argumentos: origem e nome da coluna de data do registro.
CREATE FUNCTION sincronizar_leitura_km() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_origem TEXT := TG_ARGV[0];
    v_novo   JSONB;
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        DELETE FROM leitura_km WHERE origem = v_origem AND origem_id = OLD.id;
    END IF;
    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        v_novo := to_jsonb(NEW);
        IF v_novo->>'quilometragem' IS NOT NULL
           AND NOT (v_origem = 'manutencao' AND v_novo->>'status' <> 'realizada') THEN
            INSERT INTO leitura_km (veiculo_id, quilometragem, data_leitura, origem, origem_id)
            VALUES (NEW.veiculo_id, NEW.quilometragem, (v_novo->>TG_ARGV[1])::date, v_origem, NEW.id);
        END IF;
    END IF;
    RETURN NULL;
END;
$$;

DROP TRIGGER trg_km_abastecimento ON abastecimento;
DROP TRIGGER trg_km_manutencao ON manutencao;
DROP TRIGGER trg_km_diagnostico ON diagnostico;
DROP FUNCTION atualizar_km_veiculo();

CREATE TRIGGER trg_km_abastecimento
    AFTER INSERT OR UPDATE OR DELETE ON abastecimento
    FOR EACH ROW EXECUTE FUNCTION sincronizar_leitura_km('abastecimento', 'data');

CREATE TRIGGER trg_km_manutencao
    AFTER INSERT OR UPDATE OR DELETE ON manutencao
    FOR EACH ROW EXECUTE FUNCTION sincronizar_leitura_km('manutencao', 'data');

CREATE TRIGGER trg_km_diagnostico
    AFTER INSERT OR UPDATE OR DELETE ON diagnostico
    FOR EACH ROW EXECUTE FUNCTION sincronizar_leitura_km('diagnostico', 'data_identificacao');
"""

SQL_DESFAZER = """
DROP TRIGGER trg_km_diagnostico ON diagnostico;
DROP TRIGGER trg_km_manutencao ON manutencao;
DROP TRIGGER trg_km_abastecimento ON abastecimento;
DROP FUNCTION sincronizar_leitura_km();
DROP TRIGGER trg_veiculo_leitura_inicial ON veiculo;
DROP FUNCTION trg_veiculo_leitura_inicial();
DROP TRIGGER trg_veiculo_proteger_km ON veiculo;
DROP FUNCTION proteger_km_veiculo();
DROP TABLE leitura_km;
DROP FUNCTION trg_leitura_km_recalcular();
DROP FUNCTION recalcular_km_veiculo(INT);
ALTER TABLE usuario DROP COLUMN veiculo_em_uso_id;
ALTER TABLE veiculo DROP CONSTRAINT veiculo_id_usuario_unico;
ALTER TABLE veiculo DROP COLUMN data_leitura_km;
ALTER TABLE veiculo DROP CONSTRAINT veiculo_placa_normalizada;

-- Triggers do SQL original.
CREATE FUNCTION atualizar_km_veiculo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.quilometragem IS NOT NULL THEN
        UPDATE veiculo
           SET quilometragem = NEW.quilometragem
         WHERE id = NEW.veiculo_id
           AND quilometragem < NEW.quilometragem;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_km_abastecimento
    AFTER INSERT OR UPDATE OF quilometragem ON abastecimento
    FOR EACH ROW EXECUTE FUNCTION atualizar_km_veiculo();

CREATE TRIGGER trg_km_manutencao
    AFTER INSERT OR UPDATE OF quilometragem ON manutencao
    FOR EACH ROW WHEN (NEW.status = 'realizada')
    EXECUTE FUNCTION atualizar_km_veiculo();

CREATE TRIGGER trg_km_diagnostico
    AFTER INSERT OR UPDATE OF quilometragem ON diagnostico
    FOR EACH ROW EXECUTE FUNCTION atualizar_km_veiculo();
"""


def verificar_placas(conexao) -> None:
    colisoes = conexao.exec_driver_sql(
        f"""
        SELECT usuario_id, {PLACA_NORMALIZADA} AS normalizada,
               string_agg(id::text || ' (' || placa || ')', ', ' ORDER BY id)
          FROM veiculo
         GROUP BY usuario_id, {PLACA_NORMALIZADA}
        HAVING count(*) > 1
         ORDER BY usuario_id
        """
    ).fetchall()
    invalidas = conexao.exec_driver_sql(
        f"SELECT id, usuario_id, placa FROM veiculo "
        f"WHERE {PLACA_NORMALIZADA} !~ '^[A-Z0-9]+$' ORDER BY id"
    ).fetchall()
    if not colisoes and not invalidas:
        return
    linhas = ["A migration 0003 parou: há placas incompatíveis com a normalização. Nada foi alterado."]
    for usuario_id, normalizada, veiculos in colisoes:
        linhas.append(
            f"  - usuário {usuario_id}: ficariam com a mesma placa '{normalizada}': veículos {veiculos}"
        )
    for veiculo_id, usuario_id, placa in invalidas:
        linhas.append(
            f"  - veículo {veiculo_id} (usuário {usuario_id}): placa '{placa}' tem caracteres "
            "que não são letras nem números"
        )
    linhas.append("Corrija esses cadastros (veja o README, seção 11.6) e rode 'gerenciar.py migrar'.")
    raise RuntimeError("\n".join(linhas))


def avisar_km_abaixo_dos_registros(conexao) -> None:
    """Veículos cujo km atual é MENOR que o de algum registro já lançado.

    O trigger antigo não via a mudança de agendada para realizada, então isso
    pode existir. O km atual passa a ser a maior leitura; o caso fica avisado
    para conferência (a tela de quilometragem mostra de onde veio cada leitura).
    """
    linhas = conexao.exec_driver_sql(
        """
        SELECT v.id, v.placa, v.quilometragem, m.maior
          FROM veiculo v
          JOIN (SELECT veiculo_id, max(quilometragem) AS maior
                  FROM leitura_km GROUP BY veiculo_id) m ON m.veiculo_id = v.id
         WHERE m.maior > v.quilometragem
         ORDER BY v.id
        """
    ).fetchall()
    for veiculo_id, placa, atual, maior in linhas:
        log.warning(
            "Veículo %s (%s): o km atual era %s, mas há registro com %s km. "
            "O km atual passa a ser %s; confira em 'Quilometragem' no app.",
            veiculo_id, placa, atual, maior, maior,
        )


def upgrade() -> None:
    conexao = op.get_bind()
    driver = conexao.connection.driver_connection
    verificar_placas(conexao)
    alteradas = conexao.exec_driver_sql(
        f"UPDATE veiculo SET placa = {PLACA_NORMALIZADA} WHERE placa <> {PLACA_NORMALIZADA}"
    ).rowcount
    if alteradas:
        log.info("Placas normalizadas (maiúsculas, sem hífen e sem espaços): %s", alteradas)
    driver.execute(SQL_ESTRUTURA)
    driver.execute(SQL_CARGA_INICIAL)
    avisar_km_abaixo_dos_registros(conexao)
    driver.execute(SQL_FUNCOES)
    driver.execute("SELECT recalcular_km_veiculo(id) FROM veiculo")


def downgrade() -> None:
    # As placas não voltam ao formato antigo (não há como saber onde havia hífen)
    # e o histórico de leituras é apagado: faça backup antes.
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
