-- fato navegacao: grao = 1 linha por contato_id + tipo_sequencia + ordem_passo
CREATE OR REPLACE TABLE fato_navegacao AS
WITH trilhas_brutas AS (
    -- sequencia original do Call Center
    SELECT
        contato_id,
        canal,
        aluno_hash,
        'original' AS tipo_sequencia,
        string_split(dna_soa_original, '|') AS passos
    FROM silver_callcenter
    WHERE dna_soa_original IS NOT NULL
    UNION ALL
    -- sequencia sem repeticao consecutiva do Call Center
    SELECT
        contato_id,
        canal,
        aluno_hash,
        'sem_repeticao_consecutiva' AS tipo_sequencia,
        string_split(dna_soa_sem_repeticao_consecutiva, '|') AS passos
    FROM silver_callcenter
    WHERE dna_soa_sem_repeticao_consecutiva IS NOT NULL
    UNION ALL
    -- sequencia original do WhatsApp
    SELECT
        contato_id,
        canal,
        aluno_hash,
        'original' AS tipo_sequencia,
        string_split(dna_soa_original, '|') AS passos
    FROM silver_whatsapp
    WHERE dna_soa_original IS NOT NULL
    UNION ALL
    -- sequencia original do Totem
    SELECT
        contato_id,
        canal,
        aluno_hash,
        'original' AS tipo_sequencia,
        string_split(navegacao_original, '|') AS passos
    FROM silver_totem
    WHERE navegacao_original IS NOT NULL
),
explodido AS (
    SELECT
        contato_id,
        canal,
        aluno_hash,
        tipo_sequencia,
        passos,
        generate_subscripts(passos, 1) AS ordem_passo,
        trim(unnest(passos)) AS ponto_navegacao
    FROM trilhas_brutas
)
SELECT
    CAST(contato_id AS VARCHAR) AS contato_id,
    CAST(canal AS VARCHAR) AS canal,
    CAST(aluno_hash AS VARCHAR) AS aluno_hash,
    CAST(tipo_sequencia AS VARCHAR) AS tipo_sequencia,
    CAST(ordem_passo AS INTEGER) AS ordem_passo,
    CAST(ponto_navegacao AS VARCHAR) AS ponto_navegacao,
    CAST(ponto_navegacao IN ('98', '99') AS BOOLEAN) AS eh_token_98_99,
    CAST(CASE
        WHEN ordem_passo > 1 AND ponto_navegacao = trim(passos[ordem_passo - 1]) THEN TRUE
        ELSE FALSE
    END AS BOOLEAN) AS eh_repeticao_consecutiva
FROM explodido
ORDER BY canal, contato_id, tipo_sequencia, ordem_passo;
