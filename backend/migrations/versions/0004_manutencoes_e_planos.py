"""Manutenções e planos: base fixa dos planos, situação corrigida e
integridade "mesmo veículo" no banco.

Revisão: 0004
Anterior: 0003

Base dos planos
    plano_manutencao ganha data_base e km_base: o ponto a partir do qual o
    intervalo é contado enquanto não há manutenção realizada do plano (por
    exemplo, "última troca em 10/03/2026, aos 80.000 km", ou o dia em que o
    plano foi criado). Substitui o que a view original fazia: usar
    CURRENT_DATE (o prazo andava um dia a cada dia) e inventar 0 km.
    Planos antigos ficam com a base vazia: a situação deles passa a ser
    "sem_base" (dados insuficientes) até a base ser informada na tela. Nada
    é preenchido por suposição.

Situação (vw_situacao_manutencao, recriada)
    referência = o mais recente entre a base do plano e a última manutenção
    realizada do plano; próxima = referência + intervalo.
      atrasada : km atual >= próxima km  OU  hoje >= próxima data
      próxima  : faltam até 1.000 km  OU  até 30 dias
      em_dia   : os demais casos
      sem_base : falta a base de algum intervalo do plano e o que se conhece
                 não está atrasado (desconhecido não é "em dia")
    Vale o limite atingido primeiro. A regra fica numa única função,
    classificar_prazo(), usada pela view e pelas consultas do backend.

Mesmo veículo
    manutencao.plano_id e veiculo_foto.manutencao_id passam a ser chaves
    estrangeiras compostas com veiculo_id: o banco recusa ligar uma
    manutenção a um plano de outro veículo, ou uma foto a uma manutenção de
    outro veículo (mesmo que os dois veículos sejam do mesmo dono). As regras
    de exclusão continuam as mesmas (SET NULL e CASCADE).
    Antes de criar as chaves, a migration procura vínculos antigos entre
    veículos diferentes; se houver, lista e PARA sem alterar nada.
"""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE plano_manutencao
    ADD COLUMN data_base DATE,
    ADD COLUMN km_base   INT CHECK (km_base >= 0);

ALTER TABLE plano_manutencao ADD CONSTRAINT plano_manutencao_id_veiculo_unico UNIQUE (id, veiculo_id);
ALTER TABLE manutencao       ADD CONSTRAINT manutencao_id_veiculo_unico       UNIQUE (id, veiculo_id);

ALTER TABLE manutencao DROP CONSTRAINT manutencao_plano_id_fkey;
ALTER TABLE manutencao
    ADD CONSTRAINT manutencao_plano_mesmo_veiculo_fk
    FOREIGN KEY (plano_id, veiculo_id) REFERENCES plano_manutencao (id, veiculo_id)
    ON DELETE SET NULL (plano_id);

ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_manutencao_id_fkey;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_manutencao_mesmo_veiculo_fk
    FOREIGN KEY (manutencao_id, veiculo_id) REFERENCES manutencao (id, veiculo_id)
    ON DELETE CASCADE;

CREATE INDEX veiculo_foto_manutencao_idx ON veiculo_foto (manutencao_id)
    WHERE manutencao_id IS NOT NULL;

-- Regra única de classificação de um prazo (data e/ou km).
-- p_atrasa_no_dia: TRUE para planos e lembretes (no dia do vencimento já
-- conta como atrasada, como no SQL original); FALSE para manutenção
-- agendada (o dia marcado ainda não é atraso).
-- Devolve NULL quando não há nem data nem km para comparar.
CREATE FUNCTION classificar_prazo(p_proxima_data DATE, p_proxima_km INT, p_km_atual INT,
                                  p_hoje DATE, p_atrasa_no_dia BOOLEAN DEFAULT TRUE)
RETURNS TEXT
LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE
        WHEN p_proxima_data IS NULL AND p_proxima_km IS NULL THEN NULL
        WHEN p_km_atual >= p_proxima_km
             OR p_hoje > p_proxima_data
             OR (p_atrasa_no_dia AND p_hoje = p_proxima_data) THEN 'atrasada'
        WHEN p_proxima_km - p_km_atual <= 1000
             OR p_proxima_data - p_hoje <= 30 THEN 'proxima'
        ELSE 'em_dia'
    END
$$;

DROP VIEW vw_situacao_manutencao;

CREATE VIEW vw_situacao_manutencao AS
WITH ultima AS (
    -- O hodômetro só anda para a frente: a maior data e o maior km das
    -- manutenções realizadas do plano são os da mais recente.
    SELECT plano_id, max(data) AS data, max(quilometragem) AS quilometragem
      FROM manutencao
     WHERE plano_id IS NOT NULL AND status = 'realizada'
     GROUP BY plano_id
),
referencia AS (
    SELECT p.id AS plano_id, p.veiculo_id, p.nome, p.sistema,
           p.intervalo_km, p.intervalo_meses, p.data_base, p.km_base,
           u.data          AS ultima_data,
           u.quilometragem AS ultima_km,
           -- GREATEST ignora NULL: só fica NULL se os dois forem NULL.
           GREATEST(u.data, p.data_base)        AS referencia_data,
           GREATEST(u.quilometragem, p.km_base) AS referencia_km,
           v.quilometragem AS km_atual
      FROM plano_manutencao p
      JOIN veiculo v     ON v.id = p.veiculo_id
      LEFT JOIN ultima u ON u.plano_id = p.id
     WHERE p.ativo
),
calc AS (
    SELECT r.*,
           CASE WHEN intervalo_km IS NOT NULL THEN referencia_km + intervalo_km END AS proxima_km,
           CASE WHEN intervalo_meses IS NOT NULL
                THEN (referencia_data + make_interval(months => intervalo_meses))::date
           END AS proxima_data
      FROM referencia r
)
SELECT calc.*,
       proxima_km - km_atual       AS km_restantes,
       proxima_data - CURRENT_DATE AS dias_restantes,
       CASE
           WHEN classificar_prazo(proxima_data, proxima_km, km_atual, CURRENT_DATE) = 'atrasada'
               THEN 'atrasada'
           WHEN (intervalo_km IS NOT NULL AND proxima_km IS NULL)
                OR (intervalo_meses IS NOT NULL AND proxima_data IS NULL)
               THEN 'sem_base'
           ELSE classificar_prazo(proxima_data, proxima_km, km_atual, CURRENT_DATE)
       END AS situacao
  FROM calc;
"""

SQL_DESFAZER = """
DROP VIEW vw_situacao_manutencao;
DROP FUNCTION classificar_prazo(DATE, INT, INT, DATE, BOOLEAN);
DROP INDEX veiculo_foto_manutencao_idx;

ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_manutencao_mesmo_veiculo_fk;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_manutencao_id_fkey
    FOREIGN KEY (manutencao_id) REFERENCES manutencao (id) ON DELETE CASCADE;

ALTER TABLE manutencao DROP CONSTRAINT manutencao_plano_mesmo_veiculo_fk;
ALTER TABLE manutencao
    ADD CONSTRAINT manutencao_plano_id_fkey
    FOREIGN KEY (plano_id) REFERENCES plano_manutencao (id) ON DELETE SET NULL;

ALTER TABLE manutencao       DROP CONSTRAINT manutencao_id_veiculo_unico;
ALTER TABLE plano_manutencao DROP CONSTRAINT plano_manutencao_id_veiculo_unico;
ALTER TABLE plano_manutencao DROP COLUMN km_base, DROP COLUMN data_base;

-- View do SQL original.
CREATE VIEW vw_situacao_manutencao AS
WITH ultima AS (
    SELECT DISTINCT ON (plano_id)
           plano_id, data, quilometragem
      FROM manutencao
     WHERE plano_id IS NOT NULL
       AND status = 'realizada'
     ORDER BY plano_id, data DESC, quilometragem DESC NULLS LAST
),
calc AS (
    SELECT p.id              AS plano_id,
           p.veiculo_id,
           p.nome,
           p.sistema,
           u.data            AS ultima_data,
           u.quilometragem   AS ultima_km,
           CASE WHEN p.intervalo_km IS NOT NULL
                THEN COALESCE(u.quilometragem, v.km_aquisicao, 0) + p.intervalo_km
           END               AS proxima_km,
           CASE WHEN p.intervalo_meses IS NOT NULL
                THEN (COALESCE(u.data, v.data_aquisicao, CURRENT_DATE)
                      + make_interval(months => p.intervalo_meses))::date
           END               AS proxima_data,
           v.quilometragem   AS km_atual
      FROM plano_manutencao p
      JOIN veiculo v       ON v.id = p.veiculo_id
      LEFT JOIN ultima u   ON u.plano_id = p.id
     WHERE p.ativo
)
SELECT calc.*,
       proxima_km - km_atual        AS km_restantes,
       proxima_data - CURRENT_DATE  AS dias_restantes,
       CASE
           WHEN km_atual >= proxima_km OR CURRENT_DATE >= proxima_data
               THEN 'atrasada'
           WHEN proxima_km - km_atual <= 1000 OR proxima_data - CURRENT_DATE <= 30
               THEN 'proxima'
           ELSE 'em_dia'
       END                          AS situacao
  FROM calc;
"""


def verificar_vinculos_entre_veiculos(conexao) -> None:
    manutencoes = conexao.exec_driver_sql(
        """
        SELECT m.id, m.veiculo_id, p.id, p.veiculo_id
          FROM manutencao m JOIN plano_manutencao p ON p.id = m.plano_id
         WHERE p.veiculo_id <> m.veiculo_id
         ORDER BY m.id
        """
    ).fetchall()
    fotos = conexao.exec_driver_sql(
        """
        SELECT f.id, f.veiculo_id, m.id, m.veiculo_id
          FROM veiculo_foto f JOIN manutencao m ON m.id = f.manutencao_id
         WHERE m.veiculo_id <> f.veiculo_id
         ORDER BY f.id
        """
    ).fetchall()
    if not manutencoes and not fotos:
        return
    linhas = ["A migration 0004 parou: há registros ligados a outro veículo. Nada foi alterado."]
    for manutencao_id, veiculo_id, plano_id, veiculo_do_plano in manutencoes:
        linhas.append(
            f"  - manutenção {manutencao_id} (veículo {veiculo_id}) está ligada ao plano "
            f"{plano_id}, que é do veículo {veiculo_do_plano}"
        )
    for foto_id, veiculo_id, manutencao_id, veiculo_da_manutencao in fotos:
        linhas.append(
            f"  - foto {foto_id} (veículo {veiculo_id}) está ligada à manutenção "
            f"{manutencao_id}, que é do veículo {veiculo_da_manutencao}"
        )
    linhas.append("Corrija esses vínculos (veja o README, seção 12.6) e rode 'gerenciar.py migrar'.")
    raise RuntimeError("\n".join(linhas))


def upgrade() -> None:
    conexao = op.get_bind()
    verificar_vinculos_entre_veiculos(conexao)
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    # As bases dos planos (data_base, km_base) são apagadas: faça backup antes.
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
