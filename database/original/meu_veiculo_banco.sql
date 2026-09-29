-- =====================================================================
--  Meu Veículo: banco de dados (PostgreSQL 12+)
--  Controle financeiro, manutenções, projetos e diagnósticos do veículo
-- =====================================================================
--
--  Perfis de acesso (coluna usuario.perfil)
--    admin  : vê e gerencia todos os usuários, veículos e registros
--    padrao : vê somente os próprios veículos e tudo o que está ligado a eles
--
--  Toda tabela de registro aponta para veiculo, e veiculo aponta para
--  usuario. Por isso a regra de acesso é uma só, aplicada na API:
--      o registro é visível se veiculo.usuario_id = usuário logado
--      OU se o usuário logado tem perfil 'admin'.
--  As views abaixo não filtram por usuário; a API aplica essa regra.
-- =====================================================================

BEGIN;

-- ---------------------------------------------------------------------
-- Tipos reutilizáveis
-- ---------------------------------------------------------------------
CREATE DOMAIN dinheiro AS NUMERIC(12,2)
    CHECK (VALUE >= 0);

CREATE DOMAIN sistema_veiculo AS VARCHAR(20)
    CHECK (VALUE IN ('motor', 'transmissao', 'suspensao', 'freios', 'direcao',
                     'pneus', 'eletrica', 'arrefecimento', 'ar_condicionado',
                     'carroceria', 'interior', 'outros'));

-- ---------------------------------------------------------------------
-- Usuário
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id             SERIAL        PRIMARY KEY,
    nome           VARCHAR(120)  NOT NULL,
    email          VARCHAR(160)  NOT NULL,
    senha_hash     VARCHAR(255)  NOT NULL,               -- hash bcrypt/Argon2, nunca a senha
    perfil         VARCHAR(10)   NOT NULL DEFAULT 'padrao'
                   CHECK (perfil IN ('admin', 'padrao')),
    ativo          BOOLEAN       NOT NULL DEFAULT TRUE,  -- o admin pode desativar contas
    ultimo_acesso  TIMESTAMPTZ,
    criado_em      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- e-mail único, sem diferenciar maiúsculas de minúsculas
CREATE UNIQUE INDEX usuario_email_unico ON usuario (lower(email));

-- ---------------------------------------------------------------------
-- Veículo
-- ---------------------------------------------------------------------
CREATE TABLE veiculo (
    id                SERIAL        PRIMARY KEY,
    usuario_id        INT           NOT NULL REFERENCES usuario(id) ON DELETE CASCADE,
    marca             VARCHAR(60)   NOT NULL,
    modelo            VARCHAR(80)   NOT NULL,
    versao            VARCHAR(80),
    ano               SMALLINT      NOT NULL CHECK (ano BETWEEN 1900 AND 2100),
    placa             VARCHAR(8)    NOT NULL,
    cor               VARCHAR(40),
    tipo_combustivel  VARCHAR(10)   NOT NULL DEFAULT 'flex'
                      CHECK (tipo_combustivel IN ('flex', 'gasolina', 'etanol', 'diesel',
                                                  'gnv', 'hibrido', 'eletrico')),
    quilometragem     INT           NOT NULL DEFAULT 0 CHECK (quilometragem >= 0),  -- km atual
    km_aquisicao      INT           CHECK (km_aquisicao >= 0),
    data_aquisicao    DATE,
    valor_aquisicao   dinheiro,
    ativo             BOOLEAN       NOT NULL DEFAULT TRUE,  -- vendeu o carro? mantém o histórico
    criado_em         TIMESTAMPTZ   NOT NULL DEFAULT now(),
    UNIQUE (usuario_id, placa)
);

-- ---------------------------------------------------------------------
-- Plano de manutenção (o que se repete: "troca de óleo a cada 10.000 km")
-- ---------------------------------------------------------------------
CREATE TABLE plano_manutencao (
    id               SERIAL          PRIMARY KEY,
    veiculo_id       INT             NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    nome             VARCHAR(100)    NOT NULL,
    sistema          sistema_veiculo NOT NULL DEFAULT 'outros',
    intervalo_km     INT             CHECK (intervalo_km > 0),
    intervalo_meses  SMALLINT        CHECK (intervalo_meses > 0),
    ativo            BOOLEAN         NOT NULL DEFAULT TRUE,
    criado_em        TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CHECK (intervalo_km IS NOT NULL OR intervalo_meses IS NOT NULL)
);

-- ---------------------------------------------------------------------
-- Manutenção (o que foi feito ou está agendado)
-- A situação "em dia / próxima / atrasada" NÃO é gravada: é calculada
-- na view vw_situacao_manutencao.
-- ---------------------------------------------------------------------
CREATE TABLE manutencao (
    id             SERIAL          PRIMARY KEY,
    veiculo_id     INT             NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    plano_id       INT             REFERENCES plano_manutencao(id) ON DELETE SET NULL,  -- nulo = avulsa
    descricao      VARCHAR(150)    NOT NULL,
    sistema        sistema_veiculo NOT NULL DEFAULT 'outros',
    status         VARCHAR(10)     NOT NULL DEFAULT 'realizada'
                   CHECK (status IN ('realizada', 'agendada')),
    data           DATE            NOT NULL DEFAULT CURRENT_DATE,
    quilometragem  INT             CHECK (quilometragem >= 0),
    valor          dinheiro        NOT NULL DEFAULT 0,
    oficina        VARCHAR(120),
    garantia_ate   DATE,
    garantia_km    INT             CHECK (garantia_km >= 0),
    proxima_data   DATE,           -- manual; se houver plano, a view calcula
    proxima_km     INT,
    observacao     TEXT,
    criado_em      TIMESTAMPTZ     NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Gasto avulso (IPVA, seguro, multa, estacionamento...)
-- ---------------------------------------------------------------------
CREATE TABLE gasto (
    id               SERIAL        PRIMARY KEY,
    veiculo_id       INT           NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    categoria        VARCHAR(20)   NOT NULL
                     CHECK (categoria IN ('ipva', 'licenciamento', 'seguro', 'multa',
                                          'estacionamento', 'pedagio', 'lavagem',
                                          'acessorios', 'outros')),
    descricao        VARCHAR(150),
    data             DATE          NOT NULL DEFAULT CURRENT_DATE,
    valor            dinheiro      NOT NULL,
    data_vencimento  DATE,                               -- contas a vencer
    pago             BOOLEAN       NOT NULL DEFAULT TRUE,
    criado_em        TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Projeto (melhorias/modificações) e seus itens de gasto
-- O valor gasto do projeto é a soma dos itens (vw_projeto_resumo).
-- ---------------------------------------------------------------------
CREATE TABLE projeto (
    id             SERIAL        PRIMARY KEY,
    veiculo_id     INT           NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    nome           VARCHAR(120)  NOT NULL,
    descricao      TEXT,
    categoria      VARCHAR(20)   NOT NULL DEFAULT 'outros'
                   CHECK (categoria IN ('exterior', 'interior', 'mecanica', 'som', 'outros')),
    orcamento      dinheiro,
    data_prevista  DATE,
    status         VARCHAR(15)   NOT NULL DEFAULT 'planejado'
                   CHECK (status IN ('planejado', 'em_andamento', 'concluido', 'cancelado')),
    data_conclusao DATE,
    criado_em      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE projeto_item (
    id          SERIAL        PRIMARY KEY,
    projeto_id  INT           NOT NULL REFERENCES projeto(id) ON DELETE CASCADE,
    descricao   VARCHAR(150)  NOT NULL,
    data        DATE          NOT NULL DEFAULT CURRENT_DATE,
    valor       dinheiro      NOT NULL,
    criado_em   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Abastecimento
-- Consumo correto: entre dois abastecimentos com tanque_cheio = TRUE.
-- ---------------------------------------------------------------------
CREATE TABLE abastecimento (
    id             SERIAL        PRIMARY KEY,
    veiculo_id     INT           NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    data           DATE          NOT NULL DEFAULT CURRENT_DATE,
    quilometragem  INT           NOT NULL CHECK (quilometragem >= 0),
    combustivel    VARCHAR(10)   NOT NULL
                   CHECK (combustivel IN ('gasolina', 'etanol', 'diesel', 'gnv')),
    litros         NUMERIC(7,3)  NOT NULL CHECK (litros > 0),
    valor_litro    NUMERIC(6,3)  NOT NULL CHECK (valor_litro > 0),
    valor_total    dinheiro      NOT NULL,
    tanque_cheio   BOOLEAN       NOT NULL DEFAULT TRUE,
    posto          VARCHAR(80),
    criado_em      TIMESTAMPTZ   NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Diagnóstico (problemas do dia a dia) e suas anotações
-- data_identificacao vem com a data de hoje, mas pode ser editada.
-- ---------------------------------------------------------------------
CREATE TABLE diagnostico (
    id                  SERIAL          PRIMARY KEY,
    veiculo_id          INT             NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    titulo              VARCHAR(150)    NOT NULL,
    descricao           TEXT,
    sistema             sistema_veiculo NOT NULL DEFAULT 'outros',
    gravidade           VARCHAR(10)     NOT NULL DEFAULT 'media'
                        CHECK (gravidade IN ('baixa', 'media', 'alta', 'critica')),
    status              VARCHAR(15)     NOT NULL DEFAULT 'aberto'
                        CHECK (status IN ('aberto', 'em_observacao', 'resolvido', 'descartado')),
    data_identificacao  DATE            NOT NULL DEFAULT CURRENT_DATE,
    quilometragem       INT             CHECK (quilometragem >= 0),
    data_resolucao      DATE,
    solucao             TEXT,
    manutencao_id       INT             REFERENCES manutencao(id) ON DELETE SET NULL,
    criado_em           TIMESTAMPTZ     NOT NULL DEFAULT now(),
    CHECK (status NOT IN ('resolvido', 'descartado') OR data_resolucao IS NOT NULL),
    CHECK (data_resolucao IS NULL OR data_resolucao >= data_identificacao)
);

CREATE TABLE diagnostico_nota (
    id              SERIAL       PRIMARY KEY,
    diagnostico_id  INT          NOT NULL REFERENCES diagnostico(id) ON DELETE CASCADE,
    data            DATE         NOT NULL DEFAULT CURRENT_DATE,
    texto           TEXT         NOT NULL,
    criado_em       TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------
-- Fotos do veículo
-- Toda foto pertence a um veículo, então a regra de acesso continua a
-- mesma (admin vê todas; padrão só as dos próprios veículos).
-- Opcionalmente, a foto fica ligada a UM registro: projeto (antes/depois),
-- diagnóstico (foto do problema) ou manutenção (nota fiscal, peça trocada).
-- O arquivo fica no storage (pasta ou bucket); aqui vai só o caminho.
-- Ao apagar o registro ligado, a foto sai junto: a API apaga o arquivo.
-- ---------------------------------------------------------------------
CREATE TABLE veiculo_foto (
    id              SERIAL        PRIMARY KEY,
    veiculo_id      INT           NOT NULL REFERENCES veiculo(id) ON DELETE CASCADE,
    arquivo         VARCHAR(255)  NOT NULL UNIQUE,   -- ex.: veiculos/12/3f9c1e7a.jpg
    tipo_mime       VARCHAR(20)   NOT NULL
                    CHECK (tipo_mime IN ('image/jpeg', 'image/png', 'image/webp', 'image/heic')),
    tamanho_bytes   INT           NOT NULL CHECK (tamanho_bytes BETWEEN 1 AND 10485760),  -- até 10 MB
    legenda         VARCHAR(150),
    data_foto       DATE          NOT NULL DEFAULT CURRENT_DATE,
    principal       BOOLEAN       NOT NULL DEFAULT FALSE,   -- foto de capa do veículo
    projeto_id      INT           REFERENCES projeto(id)     ON DELETE CASCADE,
    momento         VARCHAR(6)    CHECK (momento IN ('antes', 'depois')),
    diagnostico_id  INT           REFERENCES diagnostico(id) ON DELETE CASCADE,
    manutencao_id   INT           REFERENCES manutencao(id)  ON DELETE CASCADE,
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now(),
    CHECK (num_nonnulls(projeto_id, diagnostico_id, manutencao_id) <= 1),
    CHECK (momento IS NULL OR projeto_id IS NOT NULL)
);

-- no máximo uma foto de capa por veículo
CREATE UNIQUE INDEX veiculo_foto_uma_capa ON veiculo_foto (veiculo_id) WHERE principal;

-- ---------------------------------------------------------------------
-- Índices (consultas sempre filtram por veículo e costumam ordenar por data)
-- ---------------------------------------------------------------------
CREATE INDEX ON veiculo          (usuario_id);
CREATE INDEX ON plano_manutencao (veiculo_id);
CREATE INDEX ON manutencao       (veiculo_id, data DESC);
CREATE INDEX ON manutencao       (plano_id);
CREATE INDEX ON gasto            (veiculo_id, data DESC);
CREATE INDEX ON projeto          (veiculo_id);
CREATE INDEX ON projeto_item     (projeto_id);
CREATE INDEX ON abastecimento    (veiculo_id, data DESC);
CREATE INDEX ON diagnostico      (veiculo_id, status);
CREATE INDEX ON diagnostico_nota (diagnostico_id);
CREATE INDEX ON veiculo_foto     (veiculo_id, data_foto DESC);

-- ---------------------------------------------------------------------
-- Quilometragem do veículo acompanha os registros automaticamente:
-- se um registro trouxer km maior que a atual, o veículo é atualizado.
-- ---------------------------------------------------------------------
CREATE FUNCTION atualizar_km_veiculo() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.quilometragem IS NOT NULL THEN
        UPDATE veiculo
           SET quilometragem = NEW.quilometragem
         WHERE id = NEW.veiculo_id
           AND quilometragem < NEW.quilometragem;
    END IF;
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_km_abastecimento
    AFTER INSERT OR UPDATE OF quilometragem ON abastecimento
    FOR EACH ROW EXECUTE FUNCTION atualizar_km_veiculo();

CREATE TRIGGER trg_km_manutencao
    AFTER INSERT OR UPDATE OF quilometragem ON manutencao
    FOR EACH ROW WHEN (NEW.status = 'realizada')
    EXECUTE FUNCTION atualizar_km_veiculo();

CREATE TRIGGER trg_km_diagnostico
    AFTER INSERT OR UPDATE OF quilometragem ON diagnostico
    FOR EACH ROW EXECUTE FUNCTION atualizar_km_veiculo();

-- ---------------------------------------------------------------------
-- VIEW: situação de cada plano de manutenção (em dia / próxima / atrasada)
-- "próxima" = faltam até 1.000 km ou 30 dias (ajuste como preferir)
-- ---------------------------------------------------------------------
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

-- ---------------------------------------------------------------------
-- VIEW: projeto com valor gasto e percentual do orçamento
-- ---------------------------------------------------------------------
CREATE VIEW vw_projeto_resumo AS
SELECT p.*,
       COALESCE(SUM(i.valor), 0) AS valor_gasto,
       CASE WHEN p.orcamento > 0
            THEN ROUND(100 * COALESCE(SUM(i.valor), 0) / p.orcamento, 1)
       END                       AS percentual_orcamento
  FROM projeto p
  LEFT JOIN projeto_item i ON i.projeto_id = p.id
 GROUP BY p.id;

-- ---------------------------------------------------------------------
-- VIEW: histórico completo do veículo (timeline e "quanto gastei")
-- ---------------------------------------------------------------------
CREATE VIEW vw_historico AS
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

-- ---------------------------------------------------------------------
-- VIEW: resumo de usuários para a tela de administração (sem senha_hash)
-- ---------------------------------------------------------------------
CREATE VIEW vw_usuario_resumo AS
SELECT u.id, u.nome, u.email, u.perfil, u.ativo, u.ultimo_acesso, u.criado_em,
       COUNT(v.id) FILTER (WHERE v.ativo) AS veiculos
  FROM usuario u
  LEFT JOIN veiculo v ON v.usuario_id = u.id
 GROUP BY u.id;

COMMIT;

-- ---------------------------------------------------------------------
-- Primeiro administrador: crie a conta pelo cadastro normal do app
-- (a API grava o hash da senha) e depois promova pelo SQL:
--
--   UPDATE usuario SET perfil = 'admin' WHERE lower(email) = lower('seu@email.com');
-- ---------------------------------------------------------------------
