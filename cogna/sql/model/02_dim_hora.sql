-- dimensao hora: 24 horas do dia (0 a 23) com turno e faixa horaria
CREATE OR REPLACE TABLE dim_hora AS
WITH horas AS (
    SELECT CAST(unnest(generate_series(0, 23)) AS INTEGER) AS hora_inteira
)
SELECT
    CAST(hora_inteira AS INTEGER) AS hora_inteira,
    CAST(lpad(CAST(hora_inteira AS VARCHAR), 2, '0') || ':00' AS VARCHAR) AS hora_rotulo,
    CAST(lpad(CAST(hora_inteira AS VARCHAR), 2, '0') || ':00 - '
         || lpad(CAST(hora_inteira AS VARCHAR), 2, '0') || ':59' AS VARCHAR) AS faixa_horaria,
    CAST(CASE
        WHEN hora_inteira BETWEEN 0 AND 5 THEN 'Madrugada'
        WHEN hora_inteira BETWEEN 6 AND 11 THEN 'Manhã'
        WHEN hora_inteira BETWEEN 12 AND 17 THEN 'Tarde'
        ELSE 'Noite'
    END AS VARCHAR) AS turno,
    CAST(CASE
        WHEN hora_inteira BETWEEN 0 AND 5 THEN 1
        WHEN hora_inteira BETWEEN 6 AND 11 THEN 2
        WHEN hora_inteira BETWEEN 12 AND 17 THEN 3
        ELSE 4
    END AS INTEGER) AS turno_ordem,
    CAST(hora_inteira BETWEEN 8 AND 20 AS BOOLEAN) AS horario_comercial_padrao
FROM horas
ORDER BY hora_inteira;
