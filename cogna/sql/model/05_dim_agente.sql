-- dimensao agente: codigos mascarados deterministicos (LGPD) por canal e hash do nome
CREATE OR REPLACE TABLE dim_agente AS
WITH agentes_brutos AS (
    SELECT
        canal,
        agente_original,
        MAX(supervisor_original) AS supervisor_original
    FROM silver_callcenter
    WHERE agente_original IS NOT NULL
    GROUP BY canal, agente_original
    UNION ALL
    SELECT
        canal,
        agente_original,
        CAST(NULL AS VARCHAR) AS supervisor_original
    FROM silver_whatsapp
    WHERE agente_original IS NOT NULL
    GROUP BY canal, agente_original
    UNION ALL
    SELECT
        canal,
        agente_original,
        CAST(NULL AS VARCHAR) AS supervisor_original
    FROM silver_video_chamada
    WHERE agente_original IS NOT NULL
    GROUP BY canal, agente_original
),
supervisores_dist AS (
    SELECT
        supervisor_original,
        'SUP-' || lpad(CAST(ROW_NUMBER() OVER (ORDER BY sha256(supervisor_original)) AS VARCHAR), 2, '0') AS supervisor_id,
        substr(sha256(supervisor_original), 1, 12) AS supervisor_hash
    FROM (
        SELECT DISTINCT supervisor_original
        FROM agentes_brutos
        WHERE supervisor_original IS NOT NULL
    )
),
agentes_numerados AS (
    SELECT
        'AG-' || lpad(CAST(ROW_NUMBER() OVER (ORDER BY a.canal, sha256(a.agente_original)) AS VARCHAR), 3, '0') AS agente_id,
        substr(sha256(a.agente_original), 1, 12) AS agente_hash,
        a.canal,
        TRUE AS eh_agente_humano,
        COALESCE(s.supervisor_id, CASE WHEN a.canal = 'call_center' THEN 'SUP-00' ELSE 'SUP-NA' END) AS supervisor_id,
        s.supervisor_hash
    FROM agentes_brutos AS a
    LEFT JOIN supervisores_dist AS s
        ON s.supervisor_original = a.supervisor_original
)
SELECT
    CAST(agente_id AS VARCHAR) AS agente_id,
    CAST('Agente ' || agente_id AS VARCHAR) AS agente_rotulo,
    CAST(agente_hash AS VARCHAR) AS agente_hash,
    CAST(canal AS VARCHAR) AS canal_agente,
    CAST(eh_agente_humano AS BOOLEAN) AS eh_agente_humano,
    CAST(supervisor_id AS VARCHAR) AS supervisor_id,
    CAST(CASE
        WHEN supervisor_id = 'SUP-00' THEN 'Sem Supervisor Informado (CC)'
        WHEN supervisor_id = 'SUP-NA' THEN 'Não Aplicável no Canal'
        ELSE 'Supervisor ' || supervisor_id
    END AS VARCHAR) AS supervisor_rotulo,
    CAST(supervisor_hash AS VARCHAR) AS supervisor_hash
FROM agentes_numerados
UNION ALL
SELECT
    CAST('AG-000' AS VARCHAR) AS agente_id,
    CAST('Sem Agente / Autoatendimento' AS VARCHAR) AS agente_rotulo,
    CAST(NULL AS VARCHAR) AS agente_hash,
    CAST('autoatendimento' AS VARCHAR) AS canal_agente,
    CAST(FALSE AS BOOLEAN) AS eh_agente_humano,
    CAST('SUP-NA' AS VARCHAR) AS supervisor_id,
    CAST('Não Aplicável no Canal' AS VARCHAR) AS supervisor_rotulo,
    CAST(NULL AS VARCHAR) AS supervisor_hash
ORDER BY agente_id;
