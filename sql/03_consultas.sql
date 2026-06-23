-- ============================================================================
-- TP Banco de Dados — DCC/UFMG
-- Etapa 4 — Consultas SQL + EDA
-- Compatível com PostgreSQL 14+ (e ANSI SQL — testado também em SQLite 3.37)
--
-- Cada bloco abaixo cobre os REQUISITOS MÍNIMOS do enunciado e responde
-- uma das 5 PERGUNTAS INVESTIGATIVAS da análise exploratória.
-- ============================================================================

-- ----------------------------------------------------------------------------
-- Q0 — SANITY CHECK (cobertura: SELECT + WHERE + agregações simples)
-- Pergunta: qual o panorama geral da base?
-- ----------------------------------------------------------------------------
SELECT
    COUNT(*)                          AS total_transacoes,
    COUNT(DISTINCT cpf_portador)      AS portadores_unicos,
    COUNT(DISTINCT cpf_cnpj_favorecido) AS favorecidos_unicos,
    COUNT(DISTINCT codigo_ug)         AS ugs_unicas,
    MIN(valor)                        AS valor_min,
    MAX(valor)                        AS valor_max,
    ROUND(AVG(valor)::numeric, 2)     AS valor_medio,
    ROUND(SUM(valor)::numeric, 2)     AS valor_total,
    MIN(data_transacao)               AS data_min,
    MAX(data_transacao)               AS data_max
FROM transacao
WHERE valor <> 0;


-- ============================================================================
-- PERGUNTA 1: Quais Órgãos Superiores (ministérios) mais gastam via CPGF?
-- Cobertura: JOIN (3 tabelas) + GROUP BY + ORDER BY + agregações
-- ============================================================================
SELECT
    os.nome                                            AS ministerio,
    COUNT(t.id)                                        AS qtd_transacoes,
    ROUND(SUM(t.valor)::numeric, 2)                    AS gasto_total_brl,
    ROUND(AVG(t.valor)::numeric, 2)                    AS ticket_medio_brl,
    COUNT(DISTINCT t.cpf_portador)                     AS portadores_distintos
FROM transacao         t
JOIN unidade_gestora   ug  ON ug.codigo = t.codigo_ug
JOIN orgao_subordinado osub ON osub.codigo = ug.codigo_orgao_subordinado
JOIN orgao_superior    os  ON os.codigo = osub.codigo_orgao_superior
WHERE t.valor > 0   -- ignora reversões/estornos
GROUP BY os.nome
ORDER BY gasto_total_brl DESC;


-- ============================================================================
-- PERGUNTA 2: Há sazonalidade nos gastos? Como evoluem por mês?
-- Cobertura: GROUP BY composto + agregação + filtros temporais
-- ============================================================================
SELECT
    ano_extrato,
    mes_extrato,
    COUNT(*)                              AS qtd_transacoes,
    ROUND(SUM(valor)::numeric, 2)         AS gasto_total,
    ROUND(AVG(valor)::numeric, 2)         AS ticket_medio
FROM transacao
WHERE valor > 0
GROUP BY ano_extrato, mes_extrato
ORDER BY ano_extrato, mes_extrato;


-- ============================================================================
-- PERGUNTA 3: Top-10 favorecidos por valor recebido — há concentração suspeita?
-- Cobertura: JOIN + GROUP BY + HAVING + LIMIT
-- ============================================================================
SELECT
    f.nome                                  AS favorecido,
    f.tipo                                  AS pf_ou_pj,
    COUNT(t.id)                             AS qtd_pagamentos,
    ROUND(SUM(t.valor)::numeric, 2)         AS total_recebido,
    ROUND(AVG(t.valor)::numeric, 2)         AS ticket_medio,
    COUNT(DISTINCT t.cpf_portador)          AS portadores_distintos
FROM transacao  t
JOIN favorecido f ON f.cpf_cnpj = t.cpf_cnpj_favorecido
WHERE t.valor > 0
GROUP BY f.nome, f.tipo
HAVING COUNT(t.id) >= 5                      -- só favorecidos com volume mínimo
ORDER BY total_recebido DESC
LIMIT 10;


-- ============================================================================
-- PERGUNTA 4: Distribuição de valor por tipo de transação — há anomalias?
-- Cobertura: JOIN + agregações múltiplas (MIN/MAX/AVG/SUM/COUNT)
-- ============================================================================
SELECT
    tt.descricao                            AS tipo_transacao,
    COUNT(t.id)                             AS qtd,
    ROUND(SUM(t.valor)::numeric, 2)         AS total,
    ROUND(MIN(t.valor)::numeric, 2)         AS minimo,
    ROUND(MAX(t.valor)::numeric, 2)         AS maximo,
    ROUND(AVG(t.valor)::numeric, 2)         AS media,
    COUNT(DISTINCT t.cpf_portador)          AS portadores
FROM transacao      t
JOIN tipo_transacao tt ON tt.codigo = t.codigo_tipo_transacao
GROUP BY tt.descricao
ORDER BY total DESC;


-- ============================================================================
-- PERGUNTA 5: Quais portadores estão muito acima da média do seu ministério?
-- Cobertura: CTE + WINDOW FUNCTION (avg + rank por partição)
-- Mostra detecção de outliers — ganha bônus (técnica além do escopo).
-- ============================================================================
WITH gasto_por_portador AS (
    SELECT
        t.cpf_portador,
        p.nome                                AS nome_portador,
        os.nome                               AS ministerio,
        SUM(t.valor)                          AS gasto_portador
    FROM transacao         t
    JOIN portador          p   ON p.cpf = t.cpf_portador
    JOIN unidade_gestora   ug  ON ug.codigo = t.codigo_ug
    JOIN orgao_subordinado osub ON osub.codigo = ug.codigo_orgao_subordinado
    JOIN orgao_superior    os  ON os.codigo = osub.codigo_orgao_superior
    WHERE t.valor > 0
    GROUP BY t.cpf_portador, p.nome, os.nome
),
estatisticas_ministerio AS (
    SELECT
        cpf_portador,
        nome_portador,
        ministerio,
        gasto_portador,
        AVG(gasto_portador)  OVER (PARTITION BY ministerio) AS media_min,
        RANK()               OVER (PARTITION BY ministerio
                                   ORDER BY gasto_portador DESC) AS rank_no_min
    FROM gasto_por_portador
)
SELECT
    ministerio,
    nome_portador,
    ROUND(gasto_portador::numeric, 2)          AS gasto_brl,
    ROUND(media_min::numeric, 2)               AS media_do_ministerio,
    ROUND((gasto_portador / NULLIF(media_min,0))::numeric, 2) AS razao_vs_media,
    rank_no_min
FROM estatisticas_ministerio
WHERE rank_no_min <= 3                          -- top-3 por ministério
ORDER BY ministerio, rank_no_min;


-- ============================================================================
-- PERGUNTA 6 (BÔNUS): Detecção de anomalias — transações fora do padrão estatístico
-- Cobertura: SUBCONSULTA + estatísticas + filtragem
-- ============================================================================
SELECT
    t.id,
    t.data_transacao,
    t.valor,
    p.nome                                  AS portador,
    f.nome                                  AS favorecido,
    tt.descricao                            AS tipo
FROM transacao         t
JOIN portador          p  ON p.cpf = t.cpf_portador
JOIN favorecido        f  ON f.cpf_cnpj = t.cpf_cnpj_favorecido
JOIN tipo_transacao    tt ON tt.codigo = t.codigo_tipo_transacao
WHERE ABS(t.valor) > (
        -- threshold: 3 desvios-padrão acima da média (heurística clássica de outlier)
        SELECT AVG(valor) + 3 * STDDEV(valor) FROM transacao WHERE valor > 0
    )
ORDER BY ABS(t.valor) DESC
LIMIT 20;
