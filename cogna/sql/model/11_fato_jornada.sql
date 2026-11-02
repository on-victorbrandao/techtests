-- fato jornada: grao = 1 linha por contato_id, ordenada por aluno_hash, data_hora_contato, canal, contato_id
CREATE OR REPLACE TABLE fato_jornada AS
WITH janelas AS (
    SELECT
        c.contato_id,
        c.aluno_hash,
        c.canal,
        c.data_contato,
        c.data_hora_contato,
        c.duracao_s,
        c.agente_id,
        ROW_NUMBER() OVER w_global AS ordem_contato_aluno,
        COUNT(*) OVER (PARTITION BY c.aluno_hash) AS total_contatos_aluno,
        -- atendimento imediatamente anterior na jornada global (4 canais)
        LAG(c.contato_id) OVER w_global AS contato_id_anterior,
        LAG(c.canal) OVER w_global AS canal_anterior,
        LAG(c.data_contato) OVER w_global AS data_contato_anterior,
        LAG(c.data_hora_contato) OVER w_global AS data_hora_anterior,
        LAG(c.duracao_s) OVER w_global AS duracao_anterior_s,
        LAG(c.agente_id) OVER w_global AS agente_id_anterior,
        -- proximo atendimento na jornada global (4 canais)
        LEAD(c.contato_id) OVER w_global AS contato_id_proximo,
        LEAD(c.canal) OVER w_global AS canal_proximo,
        LEAD(c.data_hora_contato) OVER w_global AS data_hora_proximo,
        -- atendimento imediatamente anterior dentro do mesmo canal (Visao B Intracanal pura)
        LAG(c.data_contato) OVER w_intra AS data_contato_anterior_mesmo_canal,
        LAG(c.agente_id) OVER w_intra AS agente_id_anterior_mesmo_canal,
        -- maior timestamp futuro de WhatsApp e de Retencao para o aluno
        MAX(CASE WHEN c.canal = 'whatsapp' THEN c.data_hora_contato END)
            OVER (PARTITION BY c.aluno_hash) AS max_ts_wa_aluno,
        MAX(CASE WHEN c.eh_retencao_fila THEN c.data_hora_contato END)
            OVER (PARTITION BY c.aluno_hash) AS max_ts_ret_fila_aluno,
        MAX(CASE WHEN c.eh_assunto_retencao THEN c.data_hora_contato END)
            OVER (PARTITION BY c.aluno_hash) AS max_ts_ret_assunto_aluno
    FROM fato_contato AS c
    WINDOW
        w_global AS (PARTITION BY c.aluno_hash ORDER BY c.data_hora_contato, c.canal, c.contato_id),
        w_intra AS (PARTITION BY c.aluno_hash, c.canal ORDER BY c.data_hora_contato, c.contato_id)
),
calculado AS (
    SELECT
        *,
        CASE
            WHEN data_hora_anterior IS NOT NULL
            THEN CAST(round(epoch(data_hora_contato - data_hora_anterior)) AS BIGINT)
        END AS segundos_desde_anterior,
        CASE
            WHEN data_hora_anterior IS NOT NULL
            THEN round(epoch(data_hora_contato - data_hora_anterior) / 60.0, 2)
        END AS minutos_desde_anterior,
        CASE
            WHEN data_hora_anterior IS NOT NULL AND duracao_anterior_s IS NOT NULL
            THEN data_hora_anterior + to_seconds(duracao_anterior_s)
        END AS fim_estimado_anterior,
        CASE
            WHEN data_hora_proximo IS NOT NULL
            THEN CAST(round(epoch(data_hora_proximo - data_hora_contato)) AS BIGINT)
        END AS segundos_ate_proximo,
        COALESCE(data_contato = data_contato_anterior, FALSE) AS flag_recontato_mesmo_dia,
        COALESCE(data_contato = data_contato_anterior AND canal = canal_anterior, FALSE) AS flag_recontato_mesmo_dia_mesmo_canal,
        COALESCE(
            data_contato = data_contato_anterior
            AND agente_id_anterior IS NOT NULL
            AND agente_id_anterior <> 'AG-000',
            FALSE
        ) AS flag_recontato_mesmo_dia_canal_com_agente,
        COALESCE(
            data_contato = data_contato_anterior_mesmo_canal
            AND agente_id_anterior_mesmo_canal IS NOT NULL
            AND agente_id_anterior_mesmo_canal <> 'AG-000',
            FALSE
        ) AS flag_recontato_intracanal_mesmo_dia
    FROM janelas
)
SELECT
    CAST(contato_id AS VARCHAR) AS contato_id,
    CAST(aluno_hash AS VARCHAR) AS aluno_hash,
    CAST(canal AS VARCHAR) AS canal,
    CAST(data_contato AS DATE) AS data_contato,
    CAST(data_hora_contato AS TIMESTAMP) AS data_hora_contato,
    CAST(ordem_contato_aluno AS INTEGER) AS ordem_contato_aluno,
    CAST(total_contatos_aluno AS INTEGER) AS total_contatos_aluno,
    CAST(contato_id_anterior AS VARCHAR) AS contato_id_anterior,
    CAST(canal_anterior AS VARCHAR) AS canal_anterior,
    CAST(data_hora_anterior AS TIMESTAMP) AS data_hora_anterior,
    CAST(agente_id_anterior AS VARCHAR) AS agente_id_anterior,
    CAST(segundos_desde_anterior AS BIGINT) AS segundos_desde_anterior,
    CAST(minutos_desde_anterior AS DOUBLE) AS minutos_desde_anterior,
    CAST(fim_estimado_anterior AS TIMESTAMP) AS fim_estimado_anterior,
    CAST(CASE
        WHEN fim_estimado_anterior IS NULL THEN 'sem_sobreposicao'
        WHEN fim_estimado_anterior > data_hora_contato AND canal = canal_anterior THEN 'intracanal'
        WHEN fim_estimado_anterior > data_hora_contato AND canal <> canal_anterior THEN 'intercanal'
        ELSE 'sem_sobreposicao'
    END AS VARCHAR) AS flag_sobreposicao_estimada,
    CAST(contato_id_proximo AS VARCHAR) AS contato_id_proximo,
    CAST(canal_proximo AS VARCHAR) AS canal_proximo,
    CAST(data_hora_proximo AS TIMESTAMP) AS data_hora_proximo,
    CAST(segundos_ate_proximo AS BIGINT) AS segundos_ate_proximo,
    CAST(flag_recontato_mesmo_dia AS BOOLEAN) AS flag_recontato_mesmo_dia,
    CAST(flag_recontato_mesmo_dia_mesmo_canal AS BOOLEAN) AS flag_recontato_mesmo_dia_mesmo_canal,
    CAST(flag_recontato_mesmo_dia_canal_com_agente AS BOOLEAN) AS flag_recontato_mesmo_dia_canal_com_agente,
    CAST(CASE
        WHEN flag_recontato_mesmo_dia THEN agente_id_anterior
    END AS VARCHAR) AS agente_id_atribuido_recontato,
    CAST(flag_recontato_intracanal_mesmo_dia AS BOOLEAN) AS flag_recontato_intracanal_mesmo_dia,
    CAST(CASE
        WHEN flag_recontato_intracanal_mesmo_dia THEN agente_id_anterior_mesmo_canal
    END AS VARCHAR) AS agente_id_atribuido_recontato_intracanal,
    CAST(COALESCE(max_ts_wa_aluno > data_hora_contato, FALSE) AS BOOLEAN) AS flag_teve_wa_posterior,
    CAST(COALESCE(max_ts_ret_fila_aluno > data_hora_contato, FALSE) AS BOOLEAN) AS flag_teve_retencao_fila_posterior,
    CAST(COALESCE(max_ts_ret_assunto_aluno > data_hora_contato, FALSE) AS BOOLEAN) AS flag_teve_retencao_assunto_posterior
FROM calculado
ORDER BY aluno_hash, ordem_contato_aluno;
