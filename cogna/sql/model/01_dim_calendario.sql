-- dimensao calendario: intervalo dinamico da menor a maior data de contato da Silver
CREATE OR REPLACE TABLE dim_calendario AS
WITH limites AS (
    -- menor e maior data entre os 4 canais da Silver
    SELECT
        MIN(CAST(data_hora_contato AS DATE)) AS data_min,
        MAX(CAST(data_hora_contato AS DATE)) AS data_max
    FROM (
        SELECT data_hora_contato FROM silver_callcenter
        UNION ALL
        SELECT data_hora_contato FROM silver_whatsapp
        UNION ALL
        SELECT data_hora_contato FROM silver_video_chamada
        UNION ALL
        SELECT data_hora_contato FROM silver_totem
    )
),
datas AS (
    -- serie continua de datas de data_min ate data_max
    SELECT CAST(unnest(generate_series(data_min, data_max, INTERVAL 1 DAY)) AS DATE) AS data
    FROM limites
    WHERE data_min IS NOT NULL AND data_max IS NOT NULL
),
feriados_nacionais AS (
    -- feriados nacionais oficiais estaticos de 2026 (evita chamadas de API em tempo de execucao)
    SELECT CAST(data_feriado AS DATE) AS data_feriado, nome_feriado
    FROM (
        VALUES
            ('2026-01-01', 'Confraternização Universal'),
            ('2026-04-03', 'Paixão de Cristo'),
            ('2026-04-21', 'Tiradentes'),
            ('2026-05-01', 'Dia Mundial do Trabalho'),
            ('2026-09-07', 'Independência do Brasil'),
            ('2026-10-12', 'Nossa Senhora Aparecida'),
            ('2026-11-02', 'Finados'),
            ('2026-11-15', 'Proclamação da República'),
            ('2026-11-20', 'Dia Nacional de Zumbi e da Consciência Negra'),
            ('2026-12-25', 'Natal')
    ) AS t(data_feriado, nome_feriado)
),
base AS (
    -- calculo de atributos temporais na convencao ISO (1 = Segunda .. 7 = Domingo)
    SELECT
        d.data,
        CAST(strftime(d.data, '%Y%m') AS VARCHAR) AS ano_mes_num,
        CAST(year(d.data) * 100 + month(d.data) AS INTEGER) AS ano_mes_ordem,
        CAST(year(d.data) AS INTEGER) AS ano,
        CAST(month(d.data) AS INTEGER) AS mes,
        CAST(day(d.data) AS INTEGER) AS dia,
        CAST(isodow(d.data) AS INTEGER) AS dia_semana_num,
        CASE isodow(d.data)
            WHEN 1 THEN 'seg'
            WHEN 2 THEN 'ter'
            WHEN 3 THEN 'qua'
            WHEN 4 THEN 'qui'
            WHEN 5 THEN 'sex'
            WHEN 6 THEN 'sáb'
            WHEN 7 THEN 'dom'
        END AS dia_semana_nome,
        CASE month(d.data)
            WHEN 1 THEN 'jan'
            WHEN 2 THEN 'fev'
            WHEN 3 THEN 'mar'
            WHEN 4 THEN 'abr'
            WHEN 5 THEN 'mai'
            WHEN 6 THEN 'jun'
            WHEN 7 THEN 'jul'
            WHEN 8 THEN 'ago'
            WHEN 9 THEN 'set'
            WHEN 10 THEN 'out'
            WHEN 11 THEN 'nov'
            WHEN 12 THEN 'dez'
        END AS mes_nome,
        CAST(weekofyear(d.data) AS INTEGER) AS semana_ano,
        'Q' || CAST(quarter(d.data) AS VARCHAR) AS trimestre,
        f.nome_feriado,
        CASE
            WHEN f.data_feriado IS NOT NULL THEN 'Feriado Nacional'
            WHEN isodow(d.data) >= 6 THEN 'Fim de Semana'
            ELSE 'Dia Útil'
        END AS tipo_dia
    FROM datas AS d
    LEFT JOIN feriados_nacionais AS f
        ON f.data_feriado = d.data
)
SELECT
    CAST(data AS DATE) AS data,
    CAST(ano_mes_num AS VARCHAR) AS ano_mes_num,
    CAST(ano_mes_ordem AS INTEGER) AS ano_mes_ordem,
    CAST(ano AS INTEGER) AS ano,
    CAST(mes AS INTEGER) AS mes,
    CAST(dia AS INTEGER) AS dia,
    CAST(dia_semana_num AS INTEGER) AS dia_semana_num,
    CAST(dia_semana_nome AS VARCHAR) AS dia_semana_nome,
    CAST(mes_nome AS VARCHAR) AS mes_nome,
    CAST(mes_nome || '-' || substr(CAST(ano AS VARCHAR), 3, 2) AS VARCHAR) AS mes_ano,
    CAST(semana_ano AS INTEGER) AS semana_ano,
    CAST(trimestre AS VARCHAR) AS trimestre,
    CAST(tipo_dia AS VARCHAR) AS tipo_dia,
    CAST(CASE WHEN tipo_dia = 'Dia Útil' THEN 1 ELSE 0 END AS INTEGER) AS dia_util,
    CAST(nome_feriado AS VARCHAR) AS nome_feriado
FROM base
ORDER BY data;
