-- ============================================================================
-- TP Banco de Dados — DCC/UFMG
-- Etapa 3 — DDL (Data Definition Language)
-- Alvo: PostgreSQL 14+
-- Dataset: CPGF — Cartão de Pagamento do Governo Federal
-- ============================================================================

-- Drop em ordem reversa de dependência (idempotente para reexecução)
DROP TABLE IF EXISTS transacao          CASCADE;
DROP TABLE IF EXISTS pessoa_fisica      CASCADE;
DROP TABLE IF EXISTS pessoa_juridica    CASCADE;
DROP TABLE IF EXISTS favorecido         CASCADE;
DROP TABLE IF EXISTS portador           CASCADE;
DROP TABLE IF EXISTS tipo_transacao     CASCADE;
DROP TABLE IF EXISTS unidade_gestora    CASCADE;
DROP TABLE IF EXISTS orgao_subordinado  CASCADE;
DROP TABLE IF EXISTS orgao_superior     CASCADE;
DROP TABLE IF EXISTS stg_cpgf           CASCADE;

-- ----------------------------------------------------------------------------
-- Staging (espelha o CSV bruto do Portal da Transparência)
-- ----------------------------------------------------------------------------
CREATE TABLE stg_cpgf (
    codigo_orgao_superior        TEXT,
    nome_orgao_superior          TEXT,
    codigo_orgao_subordinado     TEXT,
    nome_orgao_subordinado       TEXT,
    codigo_unidade_gestora       TEXT,
    nome_unidade_gestora         TEXT,
    ano_extrato                  TEXT,
    mes_extrato                  TEXT,
    cpf_portador                 TEXT,
    nome_portador                TEXT,
    transacao                    TEXT,
    data_transacao               TEXT,
    cpf_cnpj_favorecido          TEXT,
    nome_favorecido              TEXT,
    valor_transacao              TEXT
);

-- ----------------------------------------------------------------------------
-- Tabelas dimensionais (hierarquia organizacional)
-- ----------------------------------------------------------------------------
CREATE TABLE orgao_superior (
    codigo  INTEGER PRIMARY KEY,
    nome    TEXT    NOT NULL
);

CREATE TABLE orgao_subordinado (
    codigo                   INTEGER PRIMARY KEY,
    nome                     TEXT    NOT NULL,
    codigo_orgao_superior    INTEGER NOT NULL
        REFERENCES orgao_superior(codigo) ON UPDATE CASCADE ON DELETE RESTRICT
);

CREATE TABLE unidade_gestora (
    codigo                      INTEGER PRIMARY KEY,
    nome                        TEXT    NOT NULL,
    codigo_orgao_subordinado    INTEGER NOT NULL
        REFERENCES orgao_subordinado(codigo) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Atores
-- ----------------------------------------------------------------------------
CREATE TABLE portador (
    -- CPF vem anonimizado no formato "***.NNN.NNN-**" — armazenamos como TEXT
    cpf   TEXT PRIMARY KEY,
    nome  TEXT NOT NULL
);

CREATE TABLE favorecido (
    cpf_cnpj  TEXT PRIMARY KEY,
    nome      TEXT NOT NULL,
    tipo      CHAR(2) NOT NULL CHECK (tipo IN ('PF', 'PJ', 'NI'))
);

CREATE TABLE pessoa_fisica (
    cpf_cnpj  TEXT PRIMARY KEY
        REFERENCES favorecido(cpf_cnpj) ON UPDATE CASCADE ON DELETE CASCADE
);

CREATE TABLE pessoa_juridica (
    cpf_cnpj  TEXT PRIMARY KEY
        REFERENCES favorecido(cpf_cnpj) ON UPDATE CASCADE ON DELETE CASCADE
);

-- ----------------------------------------------------------------------------
-- Catálogo de tipos de transação
-- ----------------------------------------------------------------------------
CREATE TABLE tipo_transacao (
    codigo     SERIAL  PRIMARY KEY,
    descricao  TEXT    NOT NULL UNIQUE
);

-- ----------------------------------------------------------------------------
-- Fato — Transações
-- ----------------------------------------------------------------------------
CREATE TABLE transacao (
    id                       BIGSERIAL PRIMARY KEY,
    data_transacao           DATE        NOT NULL,
    valor                    NUMERIC(14,2) NOT NULL CHECK (valor <> 0),
    ano_extrato              SMALLINT    NOT NULL
        CHECK (ano_extrato BETWEEN 2003 AND EXTRACT(YEAR FROM CURRENT_DATE)::INT),
    mes_extrato              SMALLINT    NOT NULL
        CHECK (mes_extrato BETWEEN 1 AND 12),
    codigo_ug                INTEGER     NOT NULL
        REFERENCES unidade_gestora(codigo) ON UPDATE CASCADE ON DELETE RESTRICT,
    cpf_portador             TEXT        NOT NULL
        REFERENCES portador(cpf) ON UPDATE CASCADE ON DELETE RESTRICT,
    cpf_cnpj_favorecido      TEXT        NOT NULL
        REFERENCES favorecido(cpf_cnpj) ON UPDATE CASCADE ON DELETE RESTRICT,
    codigo_tipo_transacao    INTEGER     NOT NULL
        REFERENCES tipo_transacao(codigo) ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ----------------------------------------------------------------------------
-- Índices auxiliares para consultas analíticas (Etapa 4)
-- ----------------------------------------------------------------------------
CREATE INDEX idx_transacao_data           ON transacao(data_transacao);
CREATE INDEX idx_transacao_ug             ON transacao(codigo_ug);
CREATE INDEX idx_transacao_portador       ON transacao(cpf_portador);
CREATE INDEX idx_transacao_favorecido     ON transacao(cpf_cnpj_favorecido);
CREATE INDEX idx_transacao_tipo           ON transacao(codigo_tipo_transacao);
CREATE INDEX idx_transacao_ano_mes        ON transacao(ano_extrato, mes_extrato);
CREATE INDEX idx_orgsub_orgsup            ON orgao_subordinado(codigo_orgao_superior);
CREATE INDEX idx_ug_orgsub                ON unidade_gestora(codigo_orgao_subordinado);

-- ----------------------------------------------------------------------------
-- Comentários (documentação dentro do schema)
-- ----------------------------------------------------------------------------
COMMENT ON TABLE  orgao_superior     IS 'Ministério ou órgão equivalente da Administração Direta.';
COMMENT ON TABLE  orgao_subordinado  IS 'Entidade supervisionada por um Órgão Superior.';
COMMENT ON TABLE  unidade_gestora    IS 'UG: unidade orçamentária/administrativa em cujo nome o cartão foi emitido.';
COMMENT ON TABLE  portador           IS 'Servidor autorizado a portar o CPGF.';
COMMENT ON TABLE  favorecido         IS 'Recebedor do pagamento (PF ou PJ). Discriminador em tipo.';
COMMENT ON TABLE  tipo_transacao     IS 'Catálogo de naturezas de operação CPGF.';
COMMENT ON TABLE  transacao          IS 'Fato — pagamentos individuais via CPGF.';

COMMENT ON COLUMN transacao.valor          IS 'Valor em R$. Pode ser negativo nos tipos de reversão/estorno.';
COMMENT ON COLUMN transacao.ano_extrato    IS 'Ano do extrato (fatura). Pode diferir de EXTRACT(YEAR FROM data_transacao).';
COMMENT ON COLUMN favorecido.tipo          IS 'PF=Pessoa Física, PJ=Pessoa Jurídica, NI=Não Identificado/sigiloso.';
