"""Itens da manutenção: peças e mão de obra, cada uma com nome e valor.

Revisão: 0005
Anterior: 0004

Tabela manutencao_item
    Uma linha por peça ou por serviço de mão de obra, ligada à manutenção.
    Apagar a manutenção (ou o veículo) apaga os itens (ON DELETE CASCADE).

Total da manutenção (manutencao.valor)
    Continua existindo (as despesas e o histórico usam essa coluna).
    - Sem nenhum item: o valor é o informado pela pessoa (valor manual).
    - Com pelo menos um item: o valor é SEMPRE a soma dos itens.
    O banco garante isso de dois jeitos:
    1. trigger BEFORE UPDATE em manutencao: se há itens, troca o valor
       recebido pela soma (um total diferente nunca chega a ser gravado; numa
       manutenção recém-criada ainda não há itens);
    2. constraint trigger ADIADA em manutencao_item: no fim da transação,
       confere que o valor é a soma dos itens; se não for, desfaz tudo.
    O item NÃO atualiza a manutenção por conta própria: um UPDATE em
    manutencao recria a leitura do hodômetro (trigger trg_km_manutencao da
    0003). O total é gravado junto com o resto da manutenção, pelo backend.

Dados existentes
    Nada é alterado: manutenções antigas ficam sem itens e com o valor que já
    tinham. Nenhuma divisão entre peças e mão de obra é inventada.

Desfazer (downgrade)
    Remove a tabela e os triggers; os itens são perdidos (faça backup antes).
    O valor de cada manutenção continua com o total.
"""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
CREATE TABLE manutencao_item (
    id             SERIAL       PRIMARY KEY,
    manutencao_id  INT          NOT NULL REFERENCES manutencao (id) ON DELETE CASCADE,
    tipo           VARCHAR(12)  NOT NULL CHECK (tipo IN ('peca', 'mao_de_obra')),
    nome           VARCHAR(150) NOT NULL CHECK (btrim(nome) <> ''),
    valor          dinheiro     NOT NULL,
    criado_em      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE INDEX manutencao_item_manutencao_idx ON manutencao_item (manutencao_id);

-- 1. Com itens, o valor gravado na manutenção é a soma deles.
CREATE FUNCTION manutencao_valor_pelos_itens() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_soma NUMERIC(12,2);
BEGIN
    SELECT sum(valor) INTO v_soma FROM manutencao_item WHERE manutencao_id = NEW.id;
    IF v_soma IS NOT NULL THEN
        NEW.valor := v_soma;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_manutencao_valor_pelos_itens
    BEFORE UPDATE ON manutencao
    FOR EACH ROW EXECUTE FUNCTION manutencao_valor_pelos_itens();

-- 2. No fim da transação, o total precisa bater com os itens.
CREATE FUNCTION conferir_total_da_manutencao() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_id    INT := CASE WHEN TG_OP = 'DELETE' THEN OLD.manutencao_id ELSE NEW.manutencao_id END;
    v_valor NUMERIC(12,2);
    v_soma  NUMERIC(12,2);
BEGIN
    SELECT valor INTO v_valor FROM manutencao WHERE id = v_id;
    IF NOT FOUND THEN
        RETURN NULL;  -- a manutenção foi apagada junto (cascata)
    END IF;
    SELECT sum(valor) INTO v_soma FROM manutencao_item WHERE manutencao_id = v_id;
    IF v_soma IS NOT NULL AND v_valor <> v_soma THEN
        RAISE EXCEPTION 'O total da manutenção % (%) difere da soma dos itens (%).',
                        v_id, v_valor, v_soma
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NULL;
END;
$$;

CREATE CONSTRAINT TRIGGER trg_manutencao_item_conferir_total
    AFTER INSERT OR UPDATE OR DELETE ON manutencao_item
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION conferir_total_da_manutencao();
"""

SQL_DESFAZER = """
DROP TRIGGER trg_manutencao_item_conferir_total ON manutencao_item;
DROP FUNCTION conferir_total_da_manutencao();
DROP TRIGGER trg_manutencao_valor_pelos_itens ON manutencao;
DROP FUNCTION manutencao_valor_pelos_itens();
DROP TABLE manutencao_item;
"""


def upgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
