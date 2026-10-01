"""Tipos de cada combustível, eletricidade (recarga AC/DC) e unidades.

Revisão: 0010
Anterior: 0009

Tabela da Paula (01/10/2026)

    Combustível   Tipos                                             Unidade
    gasolina      comum, comum_aditivada, premium, premium_aditivada  litro
    etanol        comum (hidratado), aditivado, premium,              litro
                  premium_aditivado
    diesel        s10, s10_aditivado, s500, s500_aditivado            litro
    gnv           (sem tipo)                                          m³
    eletrica      ac, dc (recarga em corrente alternada/contínua)     kWh

    A quantidade continua na coluna "litros" (no GNV são m³; na
    eletricidade, kWh). O código da eletricidade é "eletrica" porque a
    coluna combustivel tem 10 caracteres e é usada pela vw_historico.

Dados existentes
    O tipo da 0009 era "comum" ou "aditivada". Conversão sem perder nada:
      gasolina comum -> comum;  gasolina aditivada -> comum_aditivada
      etanol   comum -> comum;  etanol   aditivada -> aditivado
    Diesel com "comum"/"aditivada" não tem equivalente seguro (S10 ou
    S500?): a migration lista esses abastecimentos e PARA sem alterar nada
    (veja README, seção 15.6). Tipo vazio ("não informado") continua vazio.
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_combustivel_check;
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_combustivel_check
    CHECK (combustivel IN ('gasolina', 'etanol', 'diesel', 'gnv', 'eletrica'));

ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_tipo_check;
ALTER TABLE abastecimento ALTER COLUMN tipo TYPE VARCHAR(20);

UPDATE abastecimento SET tipo = 'comum_aditivada' WHERE combustivel = 'gasolina' AND tipo = 'aditivada';
UPDATE abastecimento SET tipo = 'aditivado'       WHERE combustivel = 'etanol'   AND tipo = 'aditivada';

ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_tipo_check CHECK (
    tipo IS NULL
    OR (combustivel = 'gasolina' AND tipo IN ('comum', 'comum_aditivada', 'premium', 'premium_aditivada'))
    OR (combustivel = 'etanol'   AND tipo IN ('comum', 'aditivado', 'premium', 'premium_aditivado'))
    OR (combustivel = 'diesel'   AND tipo IN ('s10', 's10_aditivado', 's500', 's500_aditivado'))
    OR (combustivel = 'eletrica' AND tipo IN ('ac', 'dc'))
);
"""

SQL_DESFAZER = """
ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_tipo_check;
UPDATE abastecimento SET tipo = 'aditivada' WHERE combustivel = 'gasolina' AND tipo = 'comum_aditivada';
UPDATE abastecimento SET tipo = 'aditivada' WHERE combustivel = 'etanol'   AND tipo = 'aditivado';
ALTER TABLE abastecimento ALTER COLUMN tipo TYPE VARCHAR(10);
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_tipo_check CHECK (tipo IN ('comum', 'aditivada'));

ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_combustivel_check;
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_combustivel_check
    CHECK (combustivel IN ('gasolina', 'etanol', 'diesel', 'gnv'));
"""

CONFERENCIA_SUBIDA = """
SELECT id, veiculo_id, data, tipo FROM abastecimento
 WHERE combustivel = 'diesel' AND tipo IS NOT NULL ORDER BY id
"""

# Na volta, só dá para desfazer o que tem equivalente na 0009.
CONFERENCIA_DESCIDA = """
SELECT id, veiculo_id, data, combustivel, tipo FROM abastecimento
 WHERE combustivel = 'eletrica'
    OR tipo IN ('premium', 'premium_aditivada', 'premium_aditivado')
    OR combustivel = 'diesel' AND tipo IS NOT NULL
 ORDER BY id
"""


def upgrade() -> None:
    conexao = op.get_bind()
    linhas = [f"  - abastecimento {aid} (veículo {vid}, {data:%d/%m/%Y}): diesel \"{tipo}\""
              for aid, vid, data, tipo in conexao.exec_driver_sql(CONFERENCIA_SUBIDA)]
    if linhas:
        raise RuntimeError(
            "A migration 0010 parou: há abastecimentos de diesel com tipo \"comum\" ou \"aditivada\", que "
            "não dizem se era S10 ou S500. Nada foi alterado.\n" + "\n".join(linhas)
            + "\nNo pgAdmin, troque o tipo para s10, s10_aditivado, s500 ou s500_aditivado (ou deixe vazio, "
            "não informado) e rode 'gerenciar.py migrar' (veja o README, seção 15.6)."
        )
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    conexao = op.get_bind()
    linhas = [f"  - abastecimento {aid} (veículo {vid}, {data:%d/%m/%Y}): {comb} {tipo or ''}".rstrip()
              for aid, vid, data, comb, tipo in conexao.exec_driver_sql(CONFERENCIA_DESCIDA)]
    if linhas:
        raise RuntimeError("Não dá para voltar para a 0009: estes abastecimentos não existem lá.\n"
                           + "\n".join(linhas))
    conexao.connection.driver_connection.execute(SQL_DESFAZER)
