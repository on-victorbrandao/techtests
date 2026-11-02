-- Pergunta 2 (Q2): Algum aluno que entrou em contato com o Call Center, depois no WhatsApp e depois em qualquer outro canal?
-- Populacao analisada: 173 alunos distintos e 5.991 contatos ordenados cronologicamente na jornada global (fato_jornada).
-- Denominador: 173 alunos distintos da base (e 340 transicoes consecutivas CC -> WA para a leitura estritamente consecutiva).
-- Premissas aplicadas: separamos (a) sequencia estritamente consecutiva (contato k = call_center, k+1 = whatsapp, k+2 = 3o canal) e (b) sequencia com contatos intermediarios (t_cc < t_wa < t_terceiro). Em ambas as leituras exibimos os recortes consolidados ("qualquer canal exceto WhatsApp", "qualquer um dos 4 canais" e "apenas Video Chamada ou Totem") e o detalhamento individual por terceiro canal.
-- Limitacoes: um mesmo aluno pode realizar multiplas trincas ao longo dos 12 dias, passando por diferentes terceiros canais; por isso a soma de alunos por canal individual excede o total consolidado de alunos distintos.
WITH trincas_consecutivas AS (
    SELECT
        j1.aluno_hash,
        j1.contato_id AS contato_cc_id,
        j2.contato_id AS contato_wa_id,
        j3.contato_id AS contato_terceiro_id,
        j3.canal AS terceiro_canal
    FROM fato_jornada AS j1
    INNER JOIN fato_jornada AS j2
        ON j2.contato_id = j1.contato_id_proximo
    INNER JOIN fato_jornada AS j3
        ON j3.contato_id = j2.contato_id_proximo
    WHERE j1.canal = 'call_center'
      AND j2.canal = 'whatsapp'
),
primeiro_cc AS (
    SELECT
        aluno_hash,
        MIN(data_hora_contato) AS min_ts_cc
    FROM fato_contato
    WHERE canal = 'call_center'
    GROUP BY aluno_hash
),
primeiro_wa_apos_cc AS (
    SELECT
        fc.aluno_hash,
        MIN(fc.data_hora_contato) AS min_ts_wa_apos_cc
    FROM fato_contato AS fc
    INNER JOIN primeiro_cc AS cc
        ON cc.aluno_hash = fc.aluno_hash
       AND fc.data_hora_contato > cc.min_ts_cc
    WHERE fc.canal = 'whatsapp'
    GROUP BY fc.aluno_hash
),
terceiro_com_intermediarios AS (
    SELECT
        fc.aluno_hash,
        fc.contato_id AS contato_terceiro_id,
        fc.canal AS terceiro_canal
    FROM fato_contato AS fc
    INNER JOIN primeiro_wa_apos_cc AS wa
        ON wa.aluno_hash = fc.aluno_hash
       AND fc.data_hora_contato > wa.min_ts_wa_apos_cc
),
resultados AS (
    -- (a) Sequencia estritamente consecutiva: consolidados
    SELECT
        1 AS ordem,
        'a_estritamente_consecutiva' AS tipo_sequencia,
        'consolidado_exceto_whatsapp' AS escopo_terceiro_canal,
        'TODOS_EXCETO_WHATSAPP' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM trincas_consecutivas
    WHERE terceiro_canal <> 'whatsapp'
    UNION ALL
    SELECT
        2 AS ordem,
        'a_estritamente_consecutiva' AS tipo_sequencia,
        'consolidado_qualquer_4_canais' AS escopo_terceiro_canal,
        'QUALQUER_UM_DOS_4_CANAIS' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM trincas_consecutivas
    UNION ALL
    SELECT
        3 AS ordem,
        'a_estritamente_consecutiva' AS tipo_sequencia,
        'consolidado_exceto_wa_e_cc' AS escopo_terceiro_canal,
        'VIDEO_CHAMADA_OU_TOTEM' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM trincas_consecutivas
    WHERE terceiro_canal NOT IN ('whatsapp', 'call_center')
    UNION ALL
    -- (a) Sequencia estritamente consecutiva: detalhe por canal
    SELECT
        4 AS ordem,
        'a_estritamente_consecutiva' AS tipo_sequencia,
        'detalhe_por_terceiro_canal' AS escopo_terceiro_canal,
        terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM trincas_consecutivas
    GROUP BY terceiro_canal
    UNION ALL
    -- (b) Sequencia com contatos intermediarios: consolidados
    SELECT
        5 AS ordem,
        'b_com_contatos_intermediarios' AS tipo_sequencia,
        'consolidado_exceto_whatsapp' AS escopo_terceiro_canal,
        'TODOS_EXCETO_WHATSAPP' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM terceiro_com_intermediarios
    WHERE terceiro_canal <> 'whatsapp'
    UNION ALL
    SELECT
        6 AS ordem,
        'b_com_contatos_intermediarios' AS tipo_sequencia,
        'consolidado_qualquer_4_canais' AS escopo_terceiro_canal,
        'QUALQUER_UM_DOS_4_CANAIS' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM terceiro_com_intermediarios
    UNION ALL
    SELECT
        7 AS ordem,
        'b_com_contatos_intermediarios' AS tipo_sequencia,
        'consolidado_exceto_wa_e_cc' AS escopo_terceiro_canal,
        'VIDEO_CHAMADA_OU_TOTEM' AS terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM terceiro_com_intermediarios
    WHERE terceiro_canal NOT IN ('whatsapp', 'call_center')
    UNION ALL
    -- (b) Sequencia com contatos intermediarios: detalhe por canal
    SELECT
        8 AS ordem,
        'b_com_contatos_intermediarios' AS tipo_sequencia,
        'detalhe_por_terceiro_canal' AS escopo_terceiro_canal,
        terceiro_canal,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos,
        COUNT(*) AS qtd_ocorrencias
    FROM terceiro_com_intermediarios
    GROUP BY terceiro_canal
)
SELECT
    ordem,
    tipo_sequencia,
    escopo_terceiro_canal,
    terceiro_canal,
    alunos_distintos,
    173 AS denominador_alunos_base,
    ROUND(100.0 * alunos_distintos / 173.0, 2) AS pct_alunos_base,
    qtd_ocorrencias
FROM resultados
ORDER BY ordem, alunos_distintos DESC, terceiro_canal;
