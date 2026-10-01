"""Projetos: conclusão coerente com a data, fotos do mesmo veículo e o projeto nas despesas.

Revisão: 0011
Anterior: 0010

Conclusão
    status = 'concluido' exige data_conclusao, e só o concluído tem essa data
    (CHECK projeto_conclusao_coerente). Reabrir um projeto apaga a data; ao
    concluir de novo, grava a nova.

Fotos
    veiculo_foto.projeto_id passa a ser chave composta com veiculo_id: a foto
    só pode ser de um projeto do MESMO veículo. A regra antiga continua:
    antes/depois exigem projeto (momento só com projeto_id).

Despesas
    vw_despesa ganha a coluna projeto_id no fim (nula fora dos itens de
    projeto), para o lançamento das Finanças abrir o projeto. Nada muda nos
    valores: item de projeto continua contando uma vez, inclusive de projeto
    cancelado.

Dados existentes
    Antes de mudar, a migration lista projetos concluídos sem data, datas de
    conclusão em projeto não concluído e fotos ligadas a projeto de outro
    veículo, e PARA sem alterar nada (veja README, seção 16.6).
"""

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE projeto ADD CONSTRAINT projeto_id_veiculo_unico UNIQUE (id, veiculo_id);
ALTER TABLE projeto ADD CONSTRAINT projeto_conclusao_coerente
    CHECK ((status = 'concluido') = (data_conclusao IS NOT NULL));

ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_projeto_id_fkey;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_projeto_mesmo_veiculo_fk
    FOREIGN KEY (projeto_id, veiculo_id) REFERENCES projeto (id, veiculo_id) ON DELETE CASCADE;
CREATE INDEX veiculo_foto_projeto_idx ON veiculo_foto (projeto_id) WHERE projeto_id IS NOT NULL;

CREATE OR REPLACE VIEW vw_despesa AS
SELECT veiculo_id, data, 'manutencao'::text AS tipo, 'manutencao'::text AS categoria,
       descricao::text AS descricao, valor, id AS origem_id, NULL::int AS projeto_id
  FROM manutencao
 WHERE status = 'realizada'
UNION ALL
SELECT veiculo_id, data, 'abastecimento', 'combustivel',
       'Abastecimento' || COALESCE(', ' || posto, ''), valor_total, id, NULL::int
  FROM abastecimento
UNION ALL
SELECT veiculo_id, COALESCE(data_pagamento, data), 'gasto', categoria::text,
       descricao::text, valor, id, NULL::int
  FROM gasto
 WHERE pago
UNION ALL
SELECT p.veiculo_id, i.data, 'projeto', 'projeto', p.nome || ': ' || i.descricao, i.valor, i.id, p.id
  FROM projeto_item i
  JOIN projeto p ON p.id = i.projeto_id;
"""

# A coluna nova da view não dá para tirar com CREATE OR REPLACE: recria a view.
SQL_DESFAZER = """
DROP VIEW vw_despesa;
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

DROP INDEX veiculo_foto_projeto_idx;
ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_projeto_mesmo_veiculo_fk;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_projeto_id_fkey
    FOREIGN KEY (projeto_id) REFERENCES projeto (id) ON DELETE CASCADE;
ALTER TABLE projeto DROP CONSTRAINT projeto_conclusao_coerente;
ALTER TABLE projeto DROP CONSTRAINT projeto_id_veiculo_unico;
"""

CONSULTAS_DE_CONFERENCIA = [
    ("""SELECT id, veiculo_id, nome FROM projeto
         WHERE status = 'concluido' AND data_conclusao IS NULL ORDER BY id""",
     "  - projeto {0} (veículo {1}, \"{2}\") está concluído e sem data de conclusão"),
    ("""SELECT id, veiculo_id, nome, status FROM projeto
         WHERE status <> 'concluido' AND data_conclusao IS NOT NULL ORDER BY id""",
     "  - projeto {0} (veículo {1}, \"{2}\") tem data de conclusão, mas está {3}"),
    ("""SELECT f.id, f.veiculo_id, f.projeto_id, p.veiculo_id
          FROM veiculo_foto f JOIN projeto p ON p.id = f.projeto_id
         WHERE p.veiculo_id <> f.veiculo_id ORDER BY f.id""",
     "  - foto {0} (veículo {1}) está ligada ao projeto {2}, que é do veículo {3}"),
]


def conferir_dados_antigos(conexao) -> None:
    linhas: list[str] = []
    for consulta, modelo in CONSULTAS_DE_CONFERENCIA:
        linhas += [modelo.format(*registro) for registro in conexao.exec_driver_sql(consulta)]
    if linhas:
        raise RuntimeError(
            "A migration 0011 parou: há projetos ou fotos incompatíveis. Nada foi alterado.\n"
            + "\n".join(linhas)
            + "\nCorrija esses registros (veja o README, seção 16.6) e rode 'gerenciar.py migrar'."
        )


def upgrade() -> None:
    conexao = op.get_bind()
    conferir_dados_antigos(conexao)
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
