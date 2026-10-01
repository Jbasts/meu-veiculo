"""Gastos e finanças: data do pagamento, vencimento obrigatório e despesas do mês sem duplicar.

Revisão: 0007
Anterior: 0006

Data do pagamento (decisão da Paula, 01/10/2026)
    gasto.data_pagamento: o dia em que o gasto foi pago. Um gasto pago entra
    no mês do PAGAMENTO, não no mês em que foi lançado. Gastos pagos que já
    existiam ficam com data_pagamento vazia (a data não é inventada) e
    continuam contando pela data do gasto.

Pendente
    Gasto pendente precisa de vencimento e não tem data de pagamento
    (CHECK). Antes de criar a regra, a migration lista os pendentes antigos
    sem vencimento e PARA sem alterar nada (veja README, seção 14.6).

Despesas efetivadas (vw_despesa)
    Uma linha para cada valor que realmente saiu do bolso, cada um contado
    pela tabela de origem, uma vez só:
      manutenção REALIZADA (agendada não entra)  -> categoria "manutencao"
      abastecimento                               -> categoria "combustivel"
      gasto PAGO (pendente não entra)             -> a categoria do gasto
      item de projeto (inclusive de projeto cancelado: a despesa aconteceu)
                                                  -> categoria "projeto"
    Nenhuma cópia é criada em gasto para valores que já existem na origem.

vw_historico
    Mesmas colunas e mesma finalidade; o gasto pago passa a aparecer na data
    do pagamento (ou na data do gasto, se a do pagamento não foi informada).
"""

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE gasto ADD COLUMN data_pagamento DATE;

ALTER TABLE gasto ADD CONSTRAINT gasto_pendente_com_vencimento
    CHECK (pago OR data_vencimento IS NOT NULL);
ALTER TABLE gasto ADD CONSTRAINT gasto_pendente_sem_pagamento
    CHECK (pago OR data_pagamento IS NULL);

CREATE INDEX gasto_pendentes_idx ON gasto (veiculo_id, data_vencimento) WHERE NOT pago;

CREATE VIEW vw_despesa AS
SELECT veiculo_id, data, 'manutencao'::text AS tipo, 'manutencao'::text AS categoria,
       descricao::text AS descricao, valor, id AS origem_id
  FROM manutencao
 WHERE status = 'realizada'
UNION ALL
SELECT veiculo_id, data, 'abastecimento', 'combustivel',
       'Abastecimento' || COALESCE(', ' || posto, ''), valor_total, id
  FROM abastecimento
UNION ALL
SELECT veiculo_id, COALESCE(data_pagamento, data), 'gasto', categoria::text,
       descricao::text, valor, id
  FROM gasto
 WHERE pago
UNION ALL
SELECT p.veiculo_id, i.data, 'projeto', 'projeto', p.nome || ': ' || i.descricao, i.valor, i.id
  FROM projeto_item i
  JOIN projeto p ON p.id = i.projeto_id;

CREATE OR REPLACE VIEW vw_historico AS
SELECT veiculo_id, data, 'manutencao'::text AS tipo, descricao::text AS descricao,
       valor, quilometragem, id AS origem_id
  FROM manutencao
 WHERE status = 'realizada'
UNION ALL
SELECT veiculo_id, data, 'abastecimento',
       'Abastecimento ' || combustivel || COALESCE(' (' || posto || ')', ''),
       valor_total, quilometragem, id
  FROM abastecimento
UNION ALL
SELECT veiculo_id, COALESCE(data_pagamento, data), 'gasto', COALESCE(descricao, categoria),
       valor, NULL::int, id
  FROM gasto
 WHERE pago
UNION ALL
SELECT p.veiculo_id, i.data, 'projeto', p.nome || ': ' || i.descricao,
       i.valor, NULL::int, i.id
  FROM projeto_item i
  JOIN projeto p ON p.id = i.projeto_id;
"""

# vw_historico como no SQL original (a coluna data_pagamento sai junto).
SQL_DESFAZER = """
CREATE OR REPLACE VIEW vw_historico AS
SELECT veiculo_id, data, 'manutencao'::text AS tipo, descricao::text AS descricao,
       valor, quilometragem, id AS origem_id
  FROM manutencao
 WHERE status = 'realizada'
UNION ALL
SELECT veiculo_id, data, 'abastecimento',
       'Abastecimento ' || combustivel || COALESCE(' (' || posto || ')', ''),
       valor_total, quilometragem, id
  FROM abastecimento
UNION ALL
SELECT veiculo_id, data, 'gasto', COALESCE(descricao, categoria),
       valor, NULL::int, id
  FROM gasto
 WHERE pago
UNION ALL
SELECT p.veiculo_id, i.data, 'projeto', p.nome || ': ' || i.descricao,
       i.valor, NULL::int, i.id
  FROM projeto_item i
  JOIN projeto p ON p.id = i.projeto_id;

DROP VIEW vw_despesa;
DROP INDEX gasto_pendentes_idx;
ALTER TABLE gasto DROP CONSTRAINT gasto_pendente_sem_pagamento;
ALTER TABLE gasto DROP CONSTRAINT gasto_pendente_com_vencimento;
ALTER TABLE gasto DROP COLUMN data_pagamento;
"""

CONSULTA_DE_CONFERENCIA = """
SELECT id, veiculo_id, categoria, valor, data
  FROM gasto
 WHERE NOT pago AND data_vencimento IS NULL
 ORDER BY id
"""


def conferir_dados_antigos(conexao) -> None:
    linhas = [
        f"  - gasto {gid} (veículo {vid}, {categoria}, R$ {valor}, lançado em {data:%d/%m/%Y}) "
        "está pendente e sem vencimento"
        for gid, vid, categoria, valor, data in conexao.exec_driver_sql(CONSULTA_DE_CONFERENCIA)
    ]
    if linhas:
        raise RuntimeError(
            "A migration 0007 parou: há gastos pendentes sem vencimento. Nada foi alterado.\n"
            + "\n".join(linhas)
            + "\nInforme o vencimento ou marque como pago (veja o README, seção 14.6) e rode "
            "'gerenciar.py migrar'."
        )


def upgrade() -> None:
    conexao = op.get_bind()
    conferir_dados_antigos(conexao)
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
