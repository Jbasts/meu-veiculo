"""SQL original do projeto (database/original/meu_veiculo_banco.sql), sem alterações.

Revisão: 0001
Anterior: nenhuma

Só roda em banco vazio. Um banco que já foi criado com o SQL original é
registrado com "python gerenciar.py adotar-banco-existente", sem executar
o script de novo.
"""

from alembic import op

from app.banco.sql_original import sql_original_para_executar

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conexao = op.get_bind()
    if conexao.exec_driver_sql("SELECT to_regclass('public.usuario')").scalar() is not None:
        raise RuntimeError(
            "O banco já tem a tabela 'usuario', mas não tem registro de migrations. "
            "Não vou rodar o SQL original de novo. Faça um backup e use "
            "'python gerenciar.py adotar-banco-existente'."
        )
    # Executa pelo driver (psycopg) para mandar o script inteiro de uma vez,
    # dentro da transação desta migration.
    conexao.connection.driver_connection.execute(sql_original_para_executar())


def downgrade() -> None:
    raise RuntimeError(
        "A migration 0001 não é desfeita automaticamente: desfazê-la apagaria todas "
        "as tabelas e os dados. Para voltar atrás, restaure um backup (veja o README)."
    )
