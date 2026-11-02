-- Pergunta 5 (Q5): Algum comportamento de aluno que entra em contato em qualquer um dos canais e depois na retencao?
-- Populacao analisada: todos os 5.991 contatos e 173 alunos, avaliando os atendimentos previos (< data_hora_contato) aos eventos de retencao.
-- Denominador: reportado lado a lado para (1) retencao por fila no Call Center (eh_retencao_fila = TRUE, 270 contatos / 171 alunos), (2) retencao por assunto no Call Center (eh_assunto_retencao = TRUE no CC, 266 contatos / 143 alunos) e (3) sensibilidade incluindo assunto de retencao em todos os canais (CC 266 + WA 402 + Video 75 = 743 contatos / 173 alunos).
-- Premissas aplicadas: analisamos volume de contatos previos, tempo medio e mediano (em horas) desde o primeiro e desde o ultimo contato previo ate chegar na retencao, canais previos mais frequentes, motivos previos (tab_nivel2/3 e mdc) e desfechos registrados na retencao.
-- Limitacoes: como um mesmo aluno pode passar pela retencao mais de uma vez no periodo, calculamos tanto metricas por evento de retencao quanto a contagem de contatos previos distintos que antecedem ao menos uma passagem pela retencao.
WITH eventos_retencao AS (
    SELECT
        '1_retencao_fila_cc_270' AS visao_retencao,
        contato_id,
        aluno_hash,
        canal,
        data_hora_contato,
        desfecho_retencao
    FROM fato_contato
    WHERE canal = 'call_center' AND eh_retencao_fila = TRUE
    UNION ALL
    SELECT
        '2_retencao_assunto_cc_266' AS visao_retencao,
        contato_id,
        aluno_hash,
        canal,
        data_hora_contato,
        desfecho_retencao
    FROM fato_contato
    WHERE canal = 'call_center' AND eh_assunto_retencao = TRUE
    UNION ALL
    SELECT
        '3_retencao_assunto_todos_canais_743' AS visao_retencao,
        contato_id,
        aluno_hash,
        canal,
        data_hora_contato,
        desfecho_retencao
    FROM fato_contato
    WHERE eh_assunto_retencao = TRUE
),
metricas_por_evento AS (
    SELECT
        e.visao_retencao,
        e.contato_id,
        e.aluno_hash,
        e.data_hora_contato,
        e.desfecho_retencao,
        COUNT(p.contato_id) AS qtd_previos,
        epoch(e.data_hora_contato - MAX(p.data_hora_contato)) / 3600.0 AS horas_desde_ultimo_previo,
        epoch(e.data_hora_contato - MIN(p.data_hora_contato)) / 3600.0 AS horas_desde_primeiro_previo
    FROM eventos_retencao AS e
    LEFT JOIN fato_contato AS p
        ON p.aluno_hash = e.aluno_hash
       AND p.data_hora_contato < e.data_hora_contato
    GROUP BY
        e.visao_retencao,
        e.contato_id,
        e.aluno_hash,
        e.data_hora_contato,
        e.desfecho_retencao
),
resumo_comportamento AS (
    SELECT
        1 AS secao_ordem,
        '1_resumo_volume_e_tempo_ate_retencao' AS secao,
        visao_retencao,
        'resumo_geral' AS categoria,
        COUNT(*) AS atendimentos_ou_ocorrencias,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        ROUND(100.0 * COUNT(*) FILTER (WHERE qtd_previos > 0) / NULLIF(COUNT(*), 0), 2) AS pct_com_contato_previo,
        ROUND(AVG(qtd_previos) FILTER (WHERE qtd_previos > 0), 2) AS media_contatos_previos,
        ROUND(MEDIAN(qtd_previos) FILTER (WHERE qtd_previos > 0), 2) AS mediana_contatos_previos,
        ROUND(AVG(horas_desde_ultimo_previo), 2) AS media_horas_ultimo_previo,
        ROUND(MEDIAN(horas_desde_ultimo_previo), 2) AS mediana_horas_ultimo_previo
    FROM metricas_por_evento
    GROUP BY visao_retencao
),
contatos_previos_distintos AS (
    SELECT DISTINCT
        e.visao_retencao,
        p.contato_id,
        p.aluno_hash,
        p.canal AS canal_previo,
        dm.macro_tema AS macro_tema_previo,
        CASE
            WHEN dm.taxonomia_motivo = 'mdc' THEN 'Totem MDC: ' || COALESCE(dm.mdc_original, 'Nulo')
            WHEN dm.tabulacao_original IS NULL THEN 'Sem Tabulação (Nulo)'
            ELSE COALESCE(dm.tab_nivel2 || ' > ' || dm.tab_nivel3, dm.tab_nivel2, dm.tab_nivel1)
        END AS motivo_previo
    FROM eventos_retencao AS e
    INNER JOIN fato_contato AS p
        ON p.aluno_hash = e.aluno_hash
       AND p.data_hora_contato < e.data_hora_contato
    INNER JOIN dim_motivo AS dm
        ON dm.motivo_id = p.motivo_id
),
totais_previos AS (
    SELECT
        visao_retencao,
        COUNT(*) AS total_previos_distintos
    FROM contatos_previos_distintos
    GROUP BY visao_retencao
),
canais_previos AS (
    SELECT
        2 AS secao_ordem,
        '2_canais_previos_mais_frequentes' AS secao,
        c.visao_retencao,
        c.canal_previo AS categoria,
        COUNT(*) AS atendimentos_ou_ocorrencias,
        COUNT(DISTINCT c.aluno_hash) AS alunos_distintos,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_previos_distintos, 0), 2) AS pct_com_contato_previo,
        CAST(NULL AS DOUBLE) AS media_contatos_previos,
        CAST(NULL AS DOUBLE) AS mediana_contatos_previos,
        CAST(NULL AS DOUBLE) AS media_horas_ultimo_previo,
        CAST(NULL AS DOUBLE) AS mediana_horas_ultimo_previo
    FROM contatos_previos_distintos AS c
    INNER JOIN totais_previos AS t
        ON t.visao_retencao = c.visao_retencao
    GROUP BY c.visao_retencao, c.canal_previo, t.total_previos_distintos
),
motivos_previos AS (
    SELECT
        3 AS secao_ordem,
        '3_top6_motivos_previos_antes_da_retencao' AS secao,
        c.visao_retencao,
        c.motivo_previo AS categoria,
        COUNT(*) AS atendimentos_ou_ocorrencias,
        COUNT(DISTINCT c.aluno_hash) AS alunos_distintos,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_previos_distintos, 0), 2) AS pct_com_contato_previo,
        CAST(NULL AS DOUBLE) AS media_contatos_previos,
        CAST(NULL AS DOUBLE) AS mediana_contatos_previos,
        CAST(NULL AS DOUBLE) AS media_horas_ultimo_previo,
        CAST(NULL AS DOUBLE) AS mediana_horas_ultimo_previo
    FROM contatos_previos_distintos AS c
    INNER JOIN totais_previos AS t
        ON t.visao_retencao = c.visao_retencao
    GROUP BY c.visao_retencao, c.motivo_previo, t.total_previos_distintos
    QUALIFY ROW_NUMBER() OVER (PARTITION BY c.visao_retencao ORDER BY COUNT(*) DESC, c.motivo_previo) <= 6
),
desfechos AS (
    SELECT
        4 AS secao_ordem,
        '4_desfechos_registrados_na_retencao' AS secao,
        e.visao_retencao,
        COALESCE(e.desfecho_retencao, 'sem_desfecho_retencao_na_tabulacao') AS categoria,
        COUNT(*) AS atendimentos_ou_ocorrencias,
        COUNT(DISTINCT e.aluno_hash) AS alunos_distintos,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY e.visao_retencao), 2) AS pct_com_contato_previo,
        CAST(NULL AS DOUBLE) AS media_contatos_previos,
        CAST(NULL AS DOUBLE) AS mediana_contatos_previos,
        CAST(NULL AS DOUBLE) AS media_horas_ultimo_previo,
        CAST(NULL AS DOUBLE) AS mediana_horas_ultimo_previo
    FROM metricas_por_evento AS e
    GROUP BY e.visao_retencao, COALESCE(e.desfecho_retencao, 'sem_desfecho_retencao_na_tabulacao')
)
SELECT
    secao_ordem,
    secao,
    visao_retencao,
    categoria,
    atendimentos_ou_ocorrencias,
    alunos_distintos,
    pct_com_contato_previo AS percentual_no_recorte,
    media_contatos_previos,
    mediana_contatos_previos,
    media_horas_ultimo_previo,
    mediana_horas_ultimo_previo
FROM (
    SELECT * FROM resumo_comportamento
    UNION ALL
    SELECT * FROM canais_previos
    UNION ALL
    SELECT * FROM motivos_previos
    UNION ALL
    SELECT * FROM desfechos
)
ORDER BY secao_ordem, visao_retencao, atendimentos_ou_ocorrencias DESC, categoria;
