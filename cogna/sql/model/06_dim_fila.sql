-- dimensao fila: combinacoes de recepcao_fila e fila_atend do Call Center + linha padrao Sem Fila
CREATE OR REPLACE TABLE dim_fila AS
WITH filas_cc AS (
    SELECT DISTINCT
        COALESCE(recepcao_fila, 'Sem Recepção Fila') AS recepcao_fila,
        COALESCE(fila_atend, 'Sem Fila Atendimento') AS fila_atend,
        COALESCE(flag_filas_divergentes, FALSE) AS flag_filas_divergentes,
        COALESCE(eh_retencao_fila, FALSE) AS eh_retencao_fila,
        COALESCE(fila_atend = 'cra_retencao', FALSE) AS eh_fila_cra_retencao_exata
    FROM silver_callcenter
),
numeradas AS (
    SELECT
        'FL-' || lpad(CAST(ROW_NUMBER() OVER (ORDER BY fila_atend, recepcao_fila) AS VARCHAR), 2, '0') AS fila_id,
        recepcao_fila,
        fila_atend,
        flag_filas_divergentes,
        eh_retencao_fila,
        eh_fila_cra_retencao_exata,
        CASE
            WHEN eh_fila_cra_retencao_exata THEN 'Retenção (CRA_Retenção)'
            WHEN eh_retencao_fila THEN 'Retenção (Outras Filas)'
            ELSE 'Atendimento Regular / Outras'
        END AS grupo_fila
    FROM filas_cc
)
SELECT
    CAST('FL-00' AS VARCHAR) AS fila_id,
    CAST('Sem Fila no Canal' AS VARCHAR) AS recepcao_fila,
    CAST('Sem Fila no Canal' AS VARCHAR) AS fila_atend,
    CAST(FALSE AS BOOLEAN) AS flag_filas_divergentes,
    CAST(FALSE AS BOOLEAN) AS eh_retencao_fila,
    CAST(FALSE AS BOOLEAN) AS eh_fila_cra_retencao_exata,
    CAST('Sem Fila no Canal' AS VARCHAR) AS grupo_fila
UNION ALL
SELECT
    CAST(fila_id AS VARCHAR) AS fila_id,
    CAST(recepcao_fila AS VARCHAR) AS recepcao_fila,
    CAST(fila_atend AS VARCHAR) AS fila_atend,
    CAST(flag_filas_divergentes AS BOOLEAN) AS flag_filas_divergentes,
    CAST(eh_retencao_fila AS BOOLEAN) AS eh_retencao_fila,
    CAST(eh_fila_cra_retencao_exata AS BOOLEAN) AS eh_fila_cra_retencao_exata,
    CAST(grupo_fila AS VARCHAR) AS grupo_fila
FROM numeradas
ORDER BY fila_id;
