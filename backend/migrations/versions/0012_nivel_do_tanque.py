"""Tamanho do tanque, nível do marcador e marcação do tanque (pedido da Paula, 01/10/2026).

Revisão: 0012
Anterior: 0011

Tamanho do tanque
    veiculo.capacidade_tanque: litros do tanque de combustível líquido
    (gasolina, etanol ou diesel), com uma casa decimal. Fica vazio nos
    veículos que já existem: o tamanho não é inventado; a tela pede para a
    pessoa informar. Veículo elétrico não tem tanque (CHECK).

Nível antes de abastecer
    abastecimento.nivel_antes: o que o marcador mostrava antes de abastecer,
    em oitavos do tanque (0 = vazio, 2 = 1/4, 3 = "1,5/4", 4 = meio, 8 = cheio).
    Opcional, e só para combustível líquido (o GNV e a recarga elétrica têm
    outro reservatório).

Marcação do tanque
    Tabela nova medicao_tanque: data, quilometragem e nível (em oitavos), sem
    abastecer. A ideia da Paula é registrar no início de cada mês. A
    quilometragem vira leitura do hodômetro (origem 'medicao_tanque'), como a
    do abastecimento: o hodômetro só anda para a frente e apagar a marcação
    retira a leitura.

Dados existentes
    Só há colunas novas e vazias e uma tabela nova: nenhum dado antigo é
    alterado e não há o que conferir antes.
"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE veiculo ADD COLUMN capacidade_tanque NUMERIC(5,1);
ALTER TABLE veiculo ADD CONSTRAINT veiculo_capacidade_tanque_valida
    CHECK (capacidade_tanque IS NULL OR (capacidade_tanque > 0 AND capacidade_tanque <= 2000));
ALTER TABLE veiculo ADD CONSTRAINT veiculo_eletrico_sem_tanque
    CHECK (tipo_combustivel <> 'eletrico' OR capacidade_tanque IS NULL);

ALTER TABLE abastecimento ADD COLUMN nivel_antes SMALLINT;
ALTER TABLE abastecimento ADD CONSTRAINT abastecimento_nivel_antes_valido
    CHECK (nivel_antes IS NULL OR (nivel_antes BETWEEN 0 AND 8
                                   AND combustivel IN ('gasolina', 'etanol', 'diesel')));

CREATE TABLE medicao_tanque (
    id             SERIAL       PRIMARY KEY,
    veiculo_id     INT          NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    data           DATE         NOT NULL,
    quilometragem  INT          NOT NULL CHECK (quilometragem >= 0),
    nivel          SMALLINT     NOT NULL CHECK (nivel BETWEEN 0 AND 8),  -- oitavos do tanque
    criado_em      TIMESTAMPTZ  NOT NULL DEFAULT now()
);
CREATE INDEX medicao_tanque_ordem_idx ON medicao_tanque (veiculo_id, data, quilometragem, id);

-- A marcação também é uma leitura do hodômetro.
ALTER TABLE leitura_km DROP CONSTRAINT leitura_km_origem_check;
ALTER TABLE leitura_km ADD CONSTRAINT leitura_km_origem_check
    CHECK (origem IN ('cadastro', 'manual', 'abastecimento', 'manutencao', 'diagnostico',
                      'legado', 'medicao_tanque'));
ALTER TABLE leitura_km DROP CONSTRAINT leitura_km_check1;
ALTER TABLE leitura_km ADD CONSTRAINT leitura_km_check1
    CHECK ((origem IN ('abastecimento', 'manutencao', 'diagnostico', 'medicao_tanque'))
           = (origem_id IS NOT NULL));

CREATE TRIGGER trg_km_medicao_tanque
    AFTER INSERT OR UPDATE OR DELETE ON medicao_tanque
    FOR EACH ROW EXECUTE FUNCTION sincronizar_leitura_km('medicao_tanque', 'data');
"""

SQL_DESFAZER = """
DROP TRIGGER trg_km_medicao_tanque ON medicao_tanque;
DELETE FROM leitura_km WHERE origem = 'medicao_tanque';
ALTER TABLE leitura_km DROP CONSTRAINT leitura_km_check1;
ALTER TABLE leitura_km ADD CONSTRAINT leitura_km_check1
    CHECK ((origem IN ('abastecimento', 'manutencao', 'diagnostico')) = (origem_id IS NOT NULL));
ALTER TABLE leitura_km DROP CONSTRAINT leitura_km_origem_check;
ALTER TABLE leitura_km ADD CONSTRAINT leitura_km_origem_check
    CHECK (origem IN ('cadastro', 'manual', 'abastecimento', 'manutencao', 'diagnostico', 'legado'));
DROP TABLE medicao_tanque;
ALTER TABLE abastecimento DROP CONSTRAINT abastecimento_nivel_antes_valido;
ALTER TABLE abastecimento DROP COLUMN nivel_antes;
ALTER TABLE veiculo DROP CONSTRAINT veiculo_eletrico_sem_tanque;
ALTER TABLE veiculo DROP CONSTRAINT veiculo_capacidade_tanque_valida;
ALTER TABLE veiculo DROP COLUMN capacidade_tanque;
"""


def conferir_antes_de_desfazer(conexao) -> None:
    """Voltar para a 0011 apagaria marcações, níveis e tamanhos do tanque: só com tudo vazio."""
    contagens = conexao.exec_driver_sql("""
        SELECT (SELECT count(*) FROM medicao_tanque),
               (SELECT count(*) FROM abastecimento WHERE nivel_antes IS NOT NULL),
               (SELECT count(*) FROM veiculo WHERE capacidade_tanque IS NOT NULL)""").one()
    if any(contagens):
        medicoes, niveis, tanques = contagens
        raise RuntimeError(
            "Não dá para voltar para a 0011 sem perder dados: há "
            f"{medicoes} marcação(ões) do tanque, {niveis} abastecimento(s) com nível e "
            f"{tanques} veículo(s) com tamanho do tanque. Nada foi alterado."
        )


def upgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    conexao = op.get_bind()
    conferir_antes_de_desfazer(conexao)
    conexao.connection.driver_connection.execute(SQL_DESFAZER)
