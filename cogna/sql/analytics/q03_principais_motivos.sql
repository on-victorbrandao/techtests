-- Pergunta 3 (Q3): Quais sao os principais motivos de contato em todos os canais?
-- Populacao analisada: 5.991 contatos nos 4 canais (Call Center = 1.499, WhatsApp = 1.494, Video Chamada = 1.499, Totem = 1.499).
-- Denominador: total de contatos do canal (para pct_total_canal) e total de contatos com motivo preenchido no canal (para pct_preenchidos_canal); na visao macro consolidada, tambem o total geral de 5.991 contatos.
-- Premissas aplicadas: respeitamos a taxonomia propria de cada canal: no Totem o motivo vem de mdc_original (taxonomia 'mdc'); em Call Center, WhatsApp e Video Chamada vem da hierarquia tabulacao_original (tab_nivel1..3). O Call Center possui 530 registros com tabulacao nula (35,36% do canal), reportados explicitamente.
-- Limitacoes: o campo MDC do Totem representa opcoes de menu de autoatendimento (ex.: JA_SOU_ALUNO, QUERO_SER_ALUNO) e nao tem equivalencia semantica 1:1 com os motivos detalhados da tabulacao humana.
WITH base_motivos AS (
    SELECT
        fc.contato_id,
        fc.canal,
        fc.aluno_hash,
        dm.taxonomia_motivo,
        dm.macro_tema,
        dm.motivo_principal,
        dm.tabulacao_original,
        dm.mdc_original,
        dm.tab_nivel1,
        dm.tab_nivel2,
        dm.tab_nivel3,
        CASE
            WHEN dm.taxonomia_motivo = 'mdc' THEN dm.mdc_original IS NOT NULL
            ELSE dm.tabulacao_original IS NOT NULL
        END AS motivo_preenchido,
        CASE
            WHEN dm.taxonomia_motivo = 'mdc' THEN COALESCE(dm.mdc_original, 'MDC Nulo')
            WHEN dm.tabulacao_original IS NULL THEN 'Sem Tabulação (Nulo)'
            ELSE COALESCE(dm.tab_nivel2 || ' > ' || dm.tab_nivel3, dm.tab_nivel2, dm.tab_nivel1)
        END AS caminho_n2_n3
    FROM fato_contato AS fc
    INNER JOIN dim_motivo AS dm
        ON dm.motivo_id = fc.motivo_id
),
totais_canal AS (
    SELECT
        canal,
        COUNT(*) AS total_canal,
        COUNT(*) FILTER (WHERE motivo_preenchido) AS preenchidos_canal,
        COUNT(*) FILTER (WHERE NOT motivo_preenchido) AS nulos_canal
    FROM base_motivos
    GROUP BY canal
),
cobertura AS (
    SELECT
        1 AS secao_ordem,
        '1_cobertura_motivos_por_canal' AS secao,
        b.canal,
        MAX(b.taxonomia_motivo) AS taxonomia,
        'RESUMO_COBERTURA_CANAL' AS item_motivo,
        t. preenched_or_total AS contatos,
        t.total_canal,
        t.preenchidos_canal,
        t.nulos_canal,
        ROUND(100.0 * t.preenchidos_canal / NULLIF(t.total_canal, 0), 2) AS pct_total_canal,
        100.00 AS pct_preenchidos_canal
    FROM (
        SELECT canal, total_canal, preenchidos_canal, nulos_canal, preenchidos_canal AS preenched_or_total
        FROM totais_canal
    ) AS t
    INNER JOIN base_motivos AS b ON b.canal = t.canal
    GROUP BY b.canal, t.total_canal, t.preenchidos_canal, t.nulos_canal, t.preenched_or_total
),
top_por_canal AS (
    SELECT
        2 AS secao_ordem,
        '2_principais_motivos_por_canal_n2_n3_ou_mdc' AS secao,
        b.canal,
        b.taxonomia_motivo AS taxonomia,
        b.caminho_n2_n3 AS item_motivo,
        COUNT(*) AS contatos,
        t.total_canal,
        t.preenchidos_canal,
        t.nulos_canal,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_canal, 0), 2) AS pct_total_canal,
        CASE
            WHEN b.caminho_n2_n3 = 'Sem Tabulação (Nulo)' THEN NULL
            ELSE ROUND(100.0 * COUNT(*) / NULLIF(t.preenchidos_canal, 0), 2)
        END AS pct_preenchidos_canal
    FROM base_motivos AS b
    INNER JOIN totais_canal AS t
        ON t.canal = b.canal
    GROUP BY
        b.canal,
        b.taxonomia_motivo,
        b.caminho_n2_n3,
        t.total_canal,
        t.preenchidos_canal,
        t.nulos_canal
    QUALIFY ROW_NUMBER() OVER (PARTITION BY b.canal ORDER BY COUNT(*) DESC, b.caminho_n2_n3) <= 10
),
top_caminho_completo AS (
    SELECT
        3 AS secao_ordem,
        '3_top5_caminho_completo_por_canal' AS secao,
        b.canal,
        b.taxonomia_motivo AS taxonomia,
        COALESCE(b.tabulacao_original, b.mdc_original, 'Sem Tabulação (Nulo)') AS item_motivo,
        COUNT(*) AS contatos,
        t.total_canal,
        t.preenchidos_canal,
        t.nulos_canal,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_canal, 0), 2) AS pct_total_canal,
        CASE
            WHEN NOT b.motivo_preenchido THEN NULL
            ELSE ROUND(100.0 * COUNT(*) / NULLIF(t.preenchidos_canal, 0), 2)
        END AS pct_preenchidos_canal
    FROM base_motivos AS b
    INNER JOIN totais_canal AS t
        ON t.canal = b.canal
    GROUP BY
        b.canal,
        b.taxonomia_motivo,
        b.motivo_preenchido,
        COALESCE(b.tabulacao_original, b.mdc_original, 'Sem Tabulação (Nulo)'),
        t.total_canal,
        t.preenchidos_canal,
        t.nulos_canal
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY b.canal
        ORDER BY COUNT(*) DESC, COALESCE(b.tabulacao_original, b.mdc_original, 'Sem Tabulação (Nulo)')
    ) <= 5
),
macro_consolidado AS (
    SELECT
        4 AS secao_ordem,
        '4_visao_macro_tema_todos_canais' AS secao,
        'TODOS_OS_CANAIS' AS canal,
        'mista_tabulacao_e_mdc' AS taxonomia,
        b.macro_tema AS item_motivo,
        COUNT(*) AS contatos,
        5991 AS total_canal,
        5461 AS preenchidos_canal,
        530 AS nulos_canal,
        ROUND(100.0 * COUNT(*) / 5991.0, 2) AS pct_total_canal,
        CASE
            WHEN b.macro_tema = 'Não Identificado / Sem Tabulação' THEN NULL
            ELSE ROUND(100.0 * COUNT(*) / 5461.0, 2)
        END AS pct_preenchidos_canal
    FROM base_motivos AS b
    GROUP BY b.macro_tema
)
SELECT
    secao_ordem,
    secao,
    canal,
    taxonomia,
    item_motivo,
    contatos,
    total_canal,
    preenchidos_canal,
    nulos_canal,
    pct_total_canal,
    pct_preenchidos_canal
FROM (
    SELECT * FROM cobertura
    UNION ALL
    SELECT * FROM top_por_canal
    UNION ALL
    SELECT * FROM top_caminho_completo
    UNION ALL
    SELECT * FROM macro_consolidado
)
ORDER BY secao_ordem, canal, contatos DESC, item_motivo;
