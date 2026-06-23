-- ============================================================================
-- TP Banco de Dados — DCC/UFMG
-- Etapa 3 — Carga + ETL (do staging para o modelo normalizado)
-- Pré-requisito: stg_cpgf populada via COPY a partir do CSV do Portal
--
-- USO (após popular stg_cpgf):
--   psql -d cpgf -f sql/01_ddl.sql                  -- cria schema
--   psql -d cpgf -c "\copy stg_cpgf FROM 'data/raw/202504_CPGF.csv' WITH (FORMAT csv, HEADER true, DELIMITER ';', ENCODING 'LATIN1');"
--   psql -d cpgf -f sql/02_carga_etl.sql            -- popula tabelas normalizadas
-- ============================================================================

BEGIN;

-- ----------------------------------------------------------------------------
-- 0. View de staging "limpa": tipa as colunas e descarta linhas inválidas
-- ----------------------------------------------------------------------------
DROP MATERIALIZED VIEW IF EXISTS vw_stg_limpo CASCADE;

CREATE MATERIALIZED VIEW vw_stg_limpo AS
SELECT
    NULLIF(TRIM(codigo_orgao_superior),     '')::INTEGER                AS cod_org_sup,
    NULLIF(TRIM(nome_orgao_superior),       '')                         AS nome_org_sup,
    NULLIF(TRIM(codigo_orgao_subordinado),  '')::INTEGER                AS cod_org_sub,
    NULLIF(TRIM(nome_orgao_subordinado),    '')                         AS nome_org_sub,
    NULLIF(TRIM(codigo_unidade_gestora),    '')::INTEGER                AS cod_ug,
    NULLIF(TRIM(nome_unidade_gestora),      '')                         AS nome_ug,
    NULLIF(TRIM(ano_extrato),               '')::SMALLINT               AS ano_extrato,
    NULLIF(TRIM(mes_extrato),               '')::SMALLINT               AS mes_extrato,
    NULLIF(TRIM(cpf_portador),              '')                         AS cpf_portador,
    NULLIF(TRIM(nome_portador),             '')                         AS nome_portador,
    NULLIF(TRIM(transacao),                 '')                         AS desc_transacao,
    TO_DATE(NULLIF(TRIM(data_transacao),''), 'DD/MM/YYYY')              AS data_transacao,
    NULLIF(TRIM(cpf_cnpj_favorecido),       '')                         AS cpf_cnpj_fav,
    NULLIF(TRIM(nome_favorecido),           '')                         AS nome_favorecido,
    -- valor vem com vírgula decimal e às vezes com sinal no início
    REPLACE(REPLACE(NULLIF(TRIM(valor_transacao),''), '.', ''), ',', '.')::NUMERIC(14,2)
                                                                        AS valor
FROM stg_cpgf
WHERE TRIM(COALESCE(codigo_unidade_gestora,'')) <> ''
  AND TRIM(COALESCE(cpf_portador,''))           <> ''
  AND TRIM(COALESCE(data_transacao,''))         <> ''
  AND TRIM(COALESCE(valor_transacao,''))        <> '';

-- ----------------------------------------------------------------------------
-- 1. ORGAO_SUPERIOR — distinct (codigo, nome)
-- ----------------------------------------------------------------------------
INSERT INTO orgao_superior(codigo, nome)
SELECT DISTINCT cod_org_sup, nome_org_sup
FROM vw_stg_limpo
WHERE cod_org_sup IS NOT NULL
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 2. ORGAO_SUBORDINADO
-- ----------------------------------------------------------------------------
INSERT INTO orgao_subordinado(codigo, nome, codigo_orgao_superior)
SELECT DISTINCT cod_org_sub, nome_org_sub, cod_org_sup
FROM vw_stg_limpo
WHERE cod_org_sub IS NOT NULL
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 3. UNIDADE_GESTORA
-- ----------------------------------------------------------------------------
INSERT INTO unidade_gestora(codigo, nome, codigo_orgao_subordinado)
SELECT DISTINCT cod_ug, nome_ug, cod_org_sub
FROM vw_stg_limpo
WHERE cod_ug IS NOT NULL
ON CONFLICT (codigo) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 4. PORTADOR
-- ----------------------------------------------------------------------------
INSERT INTO portador(cpf, nome)
SELECT DISTINCT ON (cpf_portador) cpf_portador, nome_portador
FROM vw_stg_limpo
WHERE cpf_portador IS NOT NULL
ORDER BY cpf_portador, nome_portador
ON CONFLICT (cpf) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 5. FAVORECIDO + especialização PF/PJ
--    Regra: 11 dígitos numéricos = PF, 14 = PJ, demais = NI (Não Informado)
-- ----------------------------------------------------------------------------
INSERT INTO favorecido(cpf_cnpj, nome, tipo)
SELECT DISTINCT ON (cpf_cnpj_fav)
       cpf_cnpj_fav,
       COALESCE(nome_favorecido, '(SEM NOME)'),
       CASE
           WHEN cpf_cnpj_fav ~ '^\d{11}$' THEN 'PF'
           WHEN cpf_cnpj_fav ~ '^\d{14}$' THEN 'PJ'
           -- formato anonimizado de CPF com asteriscos também é PF
           WHEN cpf_cnpj_fav ~ '^\*{3}\.\d{3}\.\d{3}-\*{2}$' THEN 'PF'
           ELSE 'NI'
       END
FROM vw_stg_limpo
WHERE cpf_cnpj_fav IS NOT NULL
ORDER BY cpf_cnpj_fav, nome_favorecido
ON CONFLICT (cpf_cnpj) DO NOTHING;

INSERT INTO pessoa_fisica(cpf_cnpj)
SELECT cpf_cnpj FROM favorecido WHERE tipo = 'PF'
ON CONFLICT (cpf_cnpj) DO NOTHING;

INSERT INTO pessoa_juridica(cpf_cnpj)
SELECT cpf_cnpj FROM favorecido WHERE tipo = 'PJ'
ON CONFLICT (cpf_cnpj) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 6. TIPO_TRANSACAO
-- ----------------------------------------------------------------------------
INSERT INTO tipo_transacao(descricao)
SELECT DISTINCT desc_transacao
FROM vw_stg_limpo
WHERE desc_transacao IS NOT NULL
ON CONFLICT (descricao) DO NOTHING;

-- ----------------------------------------------------------------------------
-- 7. TRANSACAO (fato)
-- ----------------------------------------------------------------------------
INSERT INTO transacao(
    data_transacao, valor, ano_extrato, mes_extrato,
    codigo_ug, cpf_portador, cpf_cnpj_favorecido, codigo_tipo_transacao
)
SELECT
    s.data_transacao,
    s.valor,
    s.ano_extrato,
    s.mes_extrato,
    s.cod_ug,
    s.cpf_portador,
    s.cpf_cnpj_fav,
    tt.codigo
FROM vw_stg_limpo s
JOIN tipo_transacao tt ON tt.descricao = s.desc_transacao
WHERE s.valor <> 0
  AND s.ano_extrato BETWEEN 2003 AND EXTRACT(YEAR FROM CURRENT_DATE)::INT
  AND s.mes_extrato BETWEEN 1 AND 12;

-- ----------------------------------------------------------------------------
-- 8. Relatório de carga (counts antes/depois)
-- ----------------------------------------------------------------------------
\echo '====================== RELATÓRIO DE CARGA ======================'
SELECT 'stg_cpgf (bruto)'           AS objeto, COUNT(*) AS qtd FROM stg_cpgf
UNION ALL SELECT 'vw_stg_limpo',               COUNT(*) FROM vw_stg_limpo
UNION ALL SELECT 'orgao_superior',             COUNT(*) FROM orgao_superior
UNION ALL SELECT 'orgao_subordinado',          COUNT(*) FROM orgao_subordinado
UNION ALL SELECT 'unidade_gestora',            COUNT(*) FROM unidade_gestora
UNION ALL SELECT 'portador',                   COUNT(*) FROM portador
UNION ALL SELECT 'favorecido',                 COUNT(*) FROM favorecido
UNION ALL SELECT '  -> pessoa_fisica',         COUNT(*) FROM pessoa_fisica
UNION ALL SELECT '  -> pessoa_juridica',       COUNT(*) FROM pessoa_juridica
UNION ALL SELECT 'tipo_transacao',             COUNT(*) FROM tipo_transacao
UNION ALL SELECT 'transacao',                  COUNT(*) FROM transacao;

COMMIT;
