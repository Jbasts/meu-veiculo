"""Tipo do combustível (comum ou aditivada) e tolerância do cupom de R$ 50,00.

Revisão: 0009
Anterior: 0008

Pedidos da Paula (01/10/2026), depois de testar a etapa 7:

Tipo do combustível
    abastecimento.tipo: 'comum' ou 'aditivada'. Abastecimentos já
    registrados ficam com tipo vazio ("não informado"): o tipo não é
    inventado. GNV não tem tipo (CHECK). O consumo continua agrupado pelo
    combustível: gasolina comum e aditivada são o mesmo combustível.

Cupom
    O valor do cupom passa a ser aceito com diferença de até R$ 50,00 para
    litros × preço (antes, R$ 0,10 na 0008). A restrição é trocada pela nova,
    com o mesmo nome. Como a regra fica mais folgada, nenhum dado antigo pode
    deixar de cumpri-la: não há conferência prévia.
"""

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE abastecimento ADD COLUMN tipo VARCHAR(10)
    CHECK (tipo IN ('comum', 'aditivada'));
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_gnv_sem_tipo
    CHECK (combustivel <> 'gnv' OR tipo IS NULL);

ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_total_coerente;
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_total_coerente
    CHECK (abs(valor_total - round(litros * valor_litro, 2)) <= 50.00);
"""

# Volta à regra de R$ 0,10. NOT VALID: abastecimentos gravados com a regra de
# R$ 50,00 continuam como estão (não são apagados nem alterados); a regra
# antiga volta a valer para gravações novas.
SQL_DESFAZER = """
ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_total_coerente;
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_total_coerente
    CHECK (abs(valor_total - round(litros * valor_litro, 2)) <= 0.10) NOT VALID;

ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_gnv_sem_tipo;
ALTER TABLE abastecimento DROP COLUMN tipo;
"""


def upgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
