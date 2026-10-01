"""Diagnósticos: vínculos do mesmo veículo e resolução sempre coerente com a manutenção.

Revisão: 0006
Anterior: 0005

Mesmo veículo
    diagnostico.manutencao_id e veiculo_foto.diagnostico_id passam a ser
    chaves estrangeiras compostas com veiculo_id: o banco recusa ligar um
    diagnóstico a uma manutenção de outro veículo, ou uma foto a um
    diagnóstico de outro veículo (mesmo que sejam do mesmo dono). As regras
    de exclusão continuam as mesmas (SET NULL e CASCADE).

Vínculo com a manutenção (decisões da Paula, 30/09/2026)
    - resolvido            -> a manutenção ligada (se houver) está REALIZADA;
    - aberto/em observação -> a manutenção ligada (se houver) está AGENDADA:
                              é a manutenção prevista para resolver o problema;
    - descartado           -> sem manutenção ligada.
    A regra é conferida por trigger a cada gravação do diagnóstico, e a
    manutenção leva o diagnóstico junto:
    - agendada passa a realizada -> o diagnóstico ligado é resolvido, com a
      data da manutenção como data de resolução;
    - realizada volta a agendada -> o diagnóstico resolvido é reaberto (a
      manutenção continua ligada, agora como prevista);
    - a data de uma manutenção realizada muda -> a data de resolução acompanha;
    - a manutenção é apagada -> o diagnóstico resolvido por ela é reaberto e
      fica sem vínculo.
    Nunca sobra diagnóstico "resolvido" por uma manutenção agendada ou apagada.

Dados existentes
    Antes de mudar qualquer coisa, a migration procura vínculos entre
    veículos diferentes e vínculos incoerentes com a regra acima. Se houver,
    lista e PARA sem alterar nada (veja README, seção 13.6).
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL_ESTRUTURA = """
ALTER TABLE diagnostico ADD CONSTRAINT diagnostico_id_veiculo_unico UNIQUE (id, veiculo_id);

ALTER TABLE diagnostico DROP CONSTRAINT diagnostico_manutencao_id_fkey;
ALTER TABLE diagnostico
    ADD CONSTRAINT diagnostico_manutencao_mesmo_veiculo_fk
    FOREIGN KEY (manutencao_id, veiculo_id) REFERENCES manutencao (id, veiculo_id)
    ON DELETE SET NULL (manutencao_id);

ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_diagnostico_id_fkey;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_diagnostico_mesmo_veiculo_fk
    FOREIGN KEY (diagnostico_id, veiculo_id) REFERENCES diagnostico (id, veiculo_id)
    ON DELETE CASCADE;

CREATE INDEX diagnostico_manutencao_idx ON diagnostico (manutencao_id)
    WHERE manutencao_id IS NOT NULL;
CREATE INDEX veiculo_foto_diagnostico_idx ON veiculo_foto (diagnostico_id)
    WHERE diagnostico_id IS NOT NULL;

-- A situação do diagnóstico precisa combinar com a da manutenção ligada.
CREATE FUNCTION conferir_vinculo_do_diagnostico() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE
    v_status TEXT;
BEGIN
    IF NEW.manutencao_id IS NULL THEN
        RETURN NEW;
    END IF;
    SELECT status INTO v_status FROM manutencao WHERE id = NEW.manutencao_id;
    IF NEW.status = 'descartado' THEN
        RAISE EXCEPTION 'Diagnóstico descartado não fica ligado a manutenção.'
              USING ERRCODE = 'check_violation';
    ELSIF NEW.status = 'resolvido' AND v_status <> 'realizada' THEN
        RAISE EXCEPTION 'Diagnóstico resolvido só pode estar ligado a manutenção realizada.'
              USING ERRCODE = 'check_violation';
    ELSIF NEW.status IN ('aberto', 'em_observacao') AND v_status <> 'agendada' THEN
        RAISE EXCEPTION 'Diagnóstico aberto só pode estar ligado a manutenção agendada.'
              USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_diagnostico_conferir_vinculo
    BEFORE INSERT OR UPDATE ON diagnostico
    FOR EACH ROW EXECUTE FUNCTION conferir_vinculo_do_diagnostico();

-- A manutenção leva o diagnóstico junto quando muda de situação ou de data.
CREATE FUNCTION manutencao_atualiza_diagnosticos() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.status = 'agendada' AND NEW.status = 'realizada' THEN
        UPDATE diagnostico
           SET status = 'resolvido', data_resolucao = NEW.data
         WHERE manutencao_id = NEW.id AND status IN ('aberto', 'em_observacao');
    ELSIF OLD.status = 'realizada' AND NEW.status = 'agendada' THEN
        UPDATE diagnostico
           SET status = 'aberto', data_resolucao = NULL, solucao = NULL
         WHERE manutencao_id = NEW.id AND status = 'resolvido';
    ELSIF NEW.status = 'realizada' AND NEW.data IS DISTINCT FROM OLD.data THEN
        UPDATE diagnostico
           SET data_resolucao = NEW.data
         WHERE manutencao_id = NEW.id AND status = 'resolvido';
    END IF;
    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_manutencao_atualiza_diagnosticos
    AFTER UPDATE OF status, data ON manutencao
    FOR EACH ROW EXECUTE FUNCTION manutencao_atualiza_diagnosticos();

-- Manutenção apagada: o diagnóstico resolvido por ela volta a ficar aberto.
CREATE FUNCTION manutencao_apagada_reabre_diagnosticos() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    UPDATE diagnostico
       SET status = CASE WHEN status = 'resolvido' THEN 'aberto' ELSE status END,
           data_resolucao = CASE WHEN status = 'resolvido' THEN NULL ELSE data_resolucao END,
           solucao = CASE WHEN status = 'resolvido' THEN NULL ELSE solucao END,
           manutencao_id = NULL
     WHERE manutencao_id = OLD.id;
    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_manutencao_apagada_reabre_diagnosticos
    BEFORE DELETE ON manutencao
    FOR EACH ROW EXECUTE FUNCTION manutencao_apagada_reabre_diagnosticos();
"""

SQL_DESFAZER = """
DROP TRIGGER trg_manutencao_apagada_reabre_diagnosticos ON manutencao;
DROP FUNCTION manutencao_apagada_reabre_diagnosticos();
DROP TRIGGER trg_manutencao_atualiza_diagnosticos ON manutencao;
DROP FUNCTION manutencao_atualiza_diagnosticos();
DROP TRIGGER trg_diagnostico_conferir_vinculo ON diagnostico;
DROP FUNCTION conferir_vinculo_do_diagnostico();
DROP INDEX veiculo_foto_diagnostico_idx;
DROP INDEX diagnostico_manutencao_idx;

ALTER TABLE veiculo_foto DROP CONSTRAINT veiculo_foto_diagnostico_mesmo_veiculo_fk;
ALTER TABLE veiculo_foto
    ADD CONSTRAINT veiculo_foto_diagnostico_id_fkey
    FOREIGN KEY (diagnostico_id) REFERENCES diagnostico (id) ON DELETE CASCADE;

ALTER TABLE diagnostico DROP CONSTRAINT diagnostico_manutencao_mesmo_veiculo_fk;
ALTER TABLE diagnostico
    ADD CONSTRAINT diagnostico_manutencao_id_fkey
    FOREIGN KEY (manutencao_id) REFERENCES manutencao (id) ON DELETE SET NULL;

ALTER TABLE diagnostico DROP CONSTRAINT diagnostico_id_veiculo_unico;
"""

CONSULTAS_DE_CONFERENCIA = [
    (
        """SELECT d.id, d.veiculo_id, d.manutencao_id, m.veiculo_id
             FROM diagnostico d JOIN manutencao m ON m.id = d.manutencao_id
            WHERE m.veiculo_id <> d.veiculo_id ORDER BY d.id""",
        "  - diagnóstico {0} (veículo {1}) está ligado à manutenção {2}, que é do veículo {3}",
    ),
    (
        """SELECT f.id, f.veiculo_id, f.diagnostico_id, d.veiculo_id
             FROM veiculo_foto f JOIN diagnostico d ON d.id = f.diagnostico_id
            WHERE d.veiculo_id <> f.veiculo_id ORDER BY f.id""",
        "  - foto {0} (veículo {1}) está ligada ao diagnóstico {2}, que é do veículo {3}",
    ),
    (
        """SELECT d.id, d.status, d.manutencao_id, m.status
             FROM diagnostico d JOIN manutencao m ON m.id = d.manutencao_id
            WHERE d.status = 'descartado'
               OR (d.status = 'resolvido' AND m.status <> 'realizada')
               OR (d.status IN ('aberto', 'em_observacao') AND m.status <> 'agendada')
            ORDER BY d.id""",
        "  - diagnóstico {0} ({1}) está ligado à manutenção {2}, que está {3}",
    ),
]


def conferir_dados_antigos(conexao) -> None:
    linhas: list[str] = []
    for consulta, modelo in CONSULTAS_DE_CONFERENCIA:
        linhas += [modelo.format(*registro) for registro in conexao.exec_driver_sql(consulta)]
    if linhas:
        raise RuntimeError(
            "A migration 0006 parou: há vínculos de diagnóstico incompatíveis. Nada foi alterado.\n"
            + "\n".join(linhas)
            + "\nCorrija esses vínculos (veja o README, seção 13.6) e rode 'gerenciar.py migrar'."
        )


def upgrade() -> None:
    conexao = op.get_bind()
    conferir_dados_antigos(conexao)
    conexao.connection.driver_connection.execute(SQL_ESTRUTURA)


def downgrade() -> None:
    op.get_bind().connection.driver_connection.execute(SQL_DESFAZER)
