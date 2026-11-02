-- dominios dos dicionarios JSON locais, uma linha por canal, campo, codigo e rotulo
CREATE OR REPLACE TABLE dic_dominio AS
WITH arquivos AS (
    SELECT
        regexp_extract(filename, '([a-z_]+)_dicionario[.]json$', 1) AS arq,
        CAST(content AS JSON) AS dic
    FROM read_text(getvariable('dic_dir') || '/*_dicionario.json')
),
campos AS (
    SELECT a.arq, j.value AS def
    FROM arquivos AS a, json_each(a.dic) AS j
),
dominios AS (
    SELECT c.arq, c.def ->> 'campo_bronze' AS campo, d.value AS item
    FROM campos AS c, json_each(c.def -> 'dominio') AS d
)
SELECT
    CASE arq WHEN 'callcenter' THEN 'call_center' ELSE arq END AS canal,
    campo,
    item ->> 'codigo' AS codigo,
    item ->> 'rotulo' AS rotulo
FROM dominios;
