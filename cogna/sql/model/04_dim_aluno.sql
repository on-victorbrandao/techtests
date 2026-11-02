-- dimensao aluno: chave unica aluno_hash com metricas resumo de cobertura, sem fixar perfil unico
CREATE OR REPLACE TABLE dim_aluno AS
WITH uniao AS (
    SELECT aluno_hash, canal, data_hora_contato FROM silver_callcenter WHERE aluno_hash IS NOT NULL
    UNION ALL
    SELECT aluno_hash, canal, data_hora_contato FROM silver_whatsapp WHERE aluno_hash IS NOT NULL
    UNION ALL
    SELECT aluno_hash, canal, data_hora_contato FROM silver_video_chamada WHERE aluno_hash IS NOT NULL
    UNION ALL
    SELECT aluno_hash, canal, data_hora_contato FROM silver_totem WHERE aluno_hash IS NOT NULL
),
agregado AS (
    SELECT
        aluno_hash,
        count(*) AS total_contatos,
        count(DISTINCT canal) AS qtd_canais_distintos,
        count(*) FILTER (WHERE canal = 'call_center') AS qtd_contatos_cc,
        count(*) FILTER (WHERE canal = 'whatsapp') AS qtd_contatos_wa,
        count(*) FILTER (WHERE canal = 'video_chamada') AS qtd_contatos_video,
        count(*) FILTER (WHERE canal = 'totem') AS qtd_contatos_totem,
        MIN(data_hora_contato) AS primeiro_contato_em,
        MAX(data_hora_contato) AS ultimo_contato_em
    FROM uniao
    GROUP BY aluno_hash
)
SELECT
    CAST(aluno_hash AS VARCHAR) AS aluno_hash,
    CAST('AL-' || lpad(CAST(ROW_NUMBER() OVER (ORDER BY aluno_hash) AS VARCHAR), 3, '0') AS VARCHAR) AS aluno_codigo,
    CAST(total_contatos AS INTEGER) AS total_contatos,
    CAST(qtd_canais_distintos AS INTEGER) AS qtd_canais_distintos,
    CAST(qtd_contatos_cc AS INTEGER) AS qtd_contatos_cc,
    CAST(qtd_contatos_wa AS INTEGER) AS qtd_contatos_wa,
    CAST(qtd_contatos_video AS INTEGER) AS qtd_contatos_video,
    CAST(qtd_contatos_totem AS INTEGER) AS qtd_contatos_totem,
    CAST(primeiro_contato_em AS TIMESTAMP) AS primeiro_contato_em,
    CAST(ultimo_contato_em AS TIMESTAMP) AS ultimo_contato_em
FROM agregado
ORDER BY aluno_hash;
