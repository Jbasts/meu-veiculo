"""Abastecimentos: valor total coerente com litros × preço e ordem estável.

Revisão: 0008
Anterior: 0007

Valor total (decisão da Paula, 01/10/2026)
    O total é litros × preço por litro, arredondado para centavos meio para
    cima (38,5 L × R$ 4,29 = 165,165 → R$ 165,17). Quando o cupom da bomba
    mostra outro valor, vale o do cupom, desde que a diferença seja de no
    máximo R$ 0,10 (CHECK abastecimento_total_coerente). Diferença maior é
    quase sempre erro de digitação.

    Antes de criar a regra, a migration lista os abastecimentos antigos fora
    dela e PARA sem alterar nada (veja README, seção 15.6).

Ordem
    Índice (veiculo_id, data, quilometragem, id): a ordem dos abastecimentos
    do mesmo dia é a da quilometragem (o hodômetro só anda para a frente), e
    o id desempata. O consumo é calculado nessa ordem.
"""

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TOLERANCIA = "0.10"

SQL_ESTRUTURA = f"""
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_total_coerente
    CHECK (abs(valor_total - round(litros * valor_litro, 2)) <= {TOLERANCIA});

CREATE INDEX abastecimento_ordem_idx ON abastecimento (veiculo_id, data, quilometragem, id);
"""

SQL_DESFAZER = """
DROP INDEX abastecimento_ordem_idx;
ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_total_coerente;
"""

CONSULTA_DE_CONFERENCIA = f"""
SELECT id, veiculo_id, data, litros, valor_litro, valor_total, round(litros * valor_litro, 2)
  FROM abastecimento
 WHERE abs(valor_total - round(litros * valor_litro, 2)) > {TOLERANCIA}
 ORDER BY id
"""


def conferir_dados_antigos(conexao) -> None:
    linhas = [
        f"  - abastecimento {aid} (veículo {vid}, {data:%d/%m/%Y}): {litros} × R$ {preco} = "
        f"R$ {calculado}, mas o total gravado é R$ {total}"
        for aid, vid, data, litros, preco, total, calculado
        in conexao.exec_driver_sql(CONSULTA_DE_CONFERENCIA)
    ]
    if linhas:
        raise RuntimeError(
            "A migration 0008 parou: há abastecimentos com total diferente de litros × preço "
            "(mais de R$ 0,10). Nada foi alterado.\n" + "\n".join(linhas)
            + "\nConfira o cupom e corrija litros, preço ou total (veja o README, seção 15.6); "
            "depois rode 'gerenciar.py migrar'."
        )


def upgrade() -> None:
    conexao = op.get_bind()
    conferir_dados_antigos(conexao)
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
