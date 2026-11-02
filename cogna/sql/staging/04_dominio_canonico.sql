-- rotulos normalizados so no espacamento do hifen, sem cruzar codigos entre canais
CREATE OR REPLACE TABLE dom_canonico AS
WITH rotulos AS (
    SELECT
        canal,
        campo,
        trim(codigo) AS codigo,
        regexp_replace(
            regexp_replace(regexp_replace(trim(rotulo), '\s+', ' ', 'g'), '^([0-9]+) ?- ?', '\1 - '),
            '^([0-9]+) ?= ?', '\1 = ') AS rotulo_norm
    FROM dic_dominio
    WHERE codigo IS NOT NULL
),
por_codigo AS (
    SELECT
        canal,
        campo,
        codigo,
        count(DISTINCT rotulo_norm) AS qtd_rotulos,
        min(rotulo_norm) AS primeiro_rotulo
    FROM rotulos
    GROUP BY canal, campo, codigo
)
SELECT
    canal,
    campo,
    codigo,
    CASE WHEN qtd_rotulos = 1 THEN primeiro_rotulo END AS rotulo_canonico,
    qtd_rotulos,
    CASE
        WHEN qtd_rotulos > 1 THEN 'conflito_dicionario'
        WHEN regexp_matches(primeiro_rotulo, '^[0-9]+ ')
             AND CAST(regexp_extract(primeiro_rotulo, '^([0-9]+)', 1) AS BIGINT) <> TRY_CAST(codigo AS BIGINT)
            THEN 'rotulo_diverge_codigo'
        ELSE 'ok'
    END AS status_dicionario
FROM por_codigo;
