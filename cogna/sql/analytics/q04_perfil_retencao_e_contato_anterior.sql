-- Pergunta 4 (Q4): Qual o perfil de aluno que nos procura na fila de atendimento da CRA_Retencao do call center? Esse aluno entrou em contato anteriormente em algum outro canal antes de pedir o cancelamento?
-- Populacao analisada: 1.499 contatos do Call Center para o perfil na fila/assunto de retencao, cruzados com os 5.991 contatos da jornada global para identificar contatos estritamente anteriores (< data_hora_contato) em outros canais (canal <> 'call_center').
-- Denominador: Parte A = total de atendimentos de cada recorte de retencao no Call Center: (1) fila exata cra_retencao = 229 contatos (144 alunos), (2) todas as 4 filas contendo retenc = 270 contatos (171 alunos), (3) assunto de tabulacao Atendimento de Retencao no CC = 266 contatos (143 alunos). Parte B = 114 pedidos de cancelamento no CC (90 alunos), alem dos demais recortes de retencao.
-- Premissas aplicadas: perfil avaliado no momento do contato via dim_perfil_aluno. Antecedencia estrita (< data_hora_contato) em canal diferente de call_center. Pedido de cancelamento corresponde a desfecho_retencao = 'pedido_cancelamento' (que representa solicitacao registrada na tabulacao, e nao efetivacao confirmada).
-- Limitacoes: 114 contatos de fila de retencao no CC estao com tabulacao nula, portanto nao possuem desfecho_retencao informado; por isso reportamos Parte B tanto para os 114 pedidos de cancelamento explicitos quanto para os 229 contatos da fila cra_retencao e 270 das 4 filas de retencao.
WITH base_cc AS (
    SELECT
        fc.contato_id,
        fc.aluno_hash,
        fc.data_hora_contato,
        fc.fila_atend,
        fc.eh_retencao_fila,
        fc.eh_assunto_retencao,
        fc.desfecho_retencao,
        dp.modalidade_rotulo,
        dp.categoria_aluno_rotulo,
        dp.instituicao_rotulo,
        dp.id_type_rotulo
    FROM fato_contato AS fc
    INNER JOIN dim_perfil_aluno AS dp
        ON dp.perfil_id = fc.perfil_id
    WHERE fc.canal = 'call_center'
),
recortes_retencao AS (
    SELECT '1_fila_exata_cra_retencao_229' AS escopo, * FROM base_cc WHERE fila_atend = 'cra_retencao'
    UNION ALL
    SELECT '2_quatro_filas_retencao_270' AS escopo, * FROM base_cc WHERE eh_retencao_fila = TRUE
    UNION ALL
    SELECT '3_assunto_retencao_cc_266' AS escopo, * FROM base_cc WHERE eh_assunto_retencao = TRUE
    UNION ALL
    SELECT '4_pedido_cancelamento_cc_114' AS escopo, * FROM base_cc WHERE desfecho_retencao = 'pedido_cancelamento'
    UNION ALL
    SELECT '5_cra_retencao_e_pedido_cancelamento_66' AS escopo, * FROM base_cc WHERE fila_atend = 'cra_retencao' AND desfecho_retencao = 'pedido_cancelamento'
),
totais_escopo AS (
    SELECT
        escopo,
        COUNT(*) AS total_contatos_escopo,
        COUNT(DISTINCT aluno_hash) AS total_alunos_escopo
    FROM recortes_retencao
    GROUP BY escopo
),
parte_a_perfil AS (
    SELECT
        1 AS parte_ordem,
        'PARTE_A_PERFIL' AS parte,
        r.escopo,
        'modalidade' AS dimensao_analisada,
        r.modalidade_rotulo AS categoria_valor,
        COUNT(*) AS contatos,
        t.total_contatos_escopo AS denominador_contatos,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_contatos_escopo, 0), 2) AS pct_contatos,
        COUNT(DISTINCT r.aluno_hash) AS alunos_distintos,
        t.total_alunos_escopo AS denominador_alunos,
        ROUND(100.0 * COUNT(DISTINCT r.aluno_hash) / NULLIF(t.total_alunos_escopo, 0), 2) AS pct_alunos
    FROM recortes_retencao AS r
    INNER JOIN totais_escopo AS t ON t.escopo = r.escopo
    WHERE r.escopo IN ('1_fila_exata_cra_retencao_229', '2_quatro_filas_retencao_270', '3_assunto_retencao_cc_266')
    GROUP BY r.escopo, r.modalidade_rotulo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        1 AS parte_ordem,
        'PARTE_A_PERFIL' AS parte,
        r.escopo,
        'categoria_aluno' AS dimensao_analisada,
        r.categoria_aluno_rotulo AS categoria_valor,
        COUNT(*) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT r.aluno_hash),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT r.aluno_hash) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM recortes_retencao AS r
    INNER JOIN totais_escopo AS t ON t.escopo = r.escopo
    WHERE r.escopo IN ('1_fila_exata_cra_retencao_229', '2_quatro_filas_retencao_270', '3_assunto_retencao_cc_266')
    GROUP BY r.escopo, r.categoria_aluno_rotulo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        1 AS parte_ordem,
        'PARTE_A_PERFIL' AS parte,
        r.escopo,
        'instituicao' AS dimensao_analisada,
        r.instituicao_rotulo AS categoria_valor,
        COUNT(*) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT r.aluno_hash),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT r.aluno_hash) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM recortes_retencao AS r
    INNER JOIN totais_escopo AS t ON t.escopo = r.escopo
    WHERE r.escopo IN ('1_fila_exata_cra_retencao_229', '2_quatro_filas_retencao_270', '3_assunto_retencao_cc_266')
    GROUP BY r.escopo, r.instituicao_rotulo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        1 AS parte_ordem,
        'PARTE_A_PERFIL' AS parte,
        r.escopo,
        'id_type' AS dimensao_analisada,
        r.id_type_rotulo AS categoria_valor,
        COUNT(*) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT r.aluno_hash),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT r.aluno_hash) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM recortes_retencao AS r
    INNER JOIN totais_escopo AS t ON t.escopo = r.escopo
    WHERE r.escopo IN ('1_fila_exata_cra_retencao_229', '2_quatro_filas_retencao_270', '3_assunto_retencao_cc_266')
    GROUP BY r.escopo, r.id_type_rotulo, t.total_contatos_escopo, t.total_alunos_escopo
),
historico_anterior AS (
    SELECT
        r.escopo,
        r.contato_id,
        r.aluno_hash,
        COUNT(ant.contato_id) FILTER (WHERE ant.canal <> 'call_center') > 0 AS teve_outro_canal_ant,
        COUNT(ant.contato_id) FILTER (WHERE ant.canal = 'whatsapp') > 0 AS teve_wa_ant,
        COUNT(ant.contato_id) FILTER (WHERE ant.canal = 'video_chamada') > 0 AS teve_video_ant,
        COUNT(ant.contato_id) FILTER (WHERE ant.canal = 'totem') > 0 AS teve_totem_ant,
        COUNT(ant.contato_id) FILTER (WHERE ant.canal = 'call_center') > 0 AS teve_cc_ant
    FROM recortes_retencao AS r
    LEFT JOIN fato_contato AS ant
        ON ant.aluno_hash = r.aluno_hash
       AND ant.data_hora_contato < r.data_hora_contato
    GROUP BY r.escopo, r.contato_id, r.aluno_hash
),
parte_b_anterior AS (
    SELECT
        2 AS parte_ordem,
        'PARTE_B_CONTATO_ANTERIOR' AS parte,
        h.escopo,
        'canal_anterior_acionado' AS dimensao_analisada,
        '1_qualquer_outro_canal_exceto_cc' AS categoria_valor,
        COUNT(*) FILTER (WHERE h.teve_outro_canal_ant) AS contatos,
        t.total_contatos_escopo AS denominador_contatos,
        ROUND(100.0 * COUNT(*) FILTER (WHERE h.teve_outro_canal_ant) / NULLIF(t.total_contatos_escopo, 0), 2) AS pct_contatos,
        COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_outro_canal_ant) AS alunos_distintos,
        t.total_alunos_escopo AS denominador_alunos,
        ROUND(100.0 * COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_outro_canal_ant) / NULLIF(t.total_alunos_escopo, 0), 2) AS pct_alunos
    FROM historico_anterior AS h
    INNER JOIN totais_escopo AS t ON t.escopo = h.escopo
    GROUP BY h.escopo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        2 AS parte_ordem,
        'PARTE_B_CONTATO_ANTERIOR' AS parte,
        h.escopo,
        'canal_anterior_acionado' AS dimensao_analisada,
        '2_whatsapp_anterior' AS categoria_valor,
        COUNT(*) FILTER (WHERE h.teve_wa_ant) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) FILTER (WHERE h.teve_wa_ant) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_wa_ant),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_wa_ant) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM historico_anterior AS h
    INNER JOIN totais_escopo AS t ON t.escopo = h.escopo
    GROUP BY h.escopo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        2 AS parte_ordem,
        'PARTE_B_CONTATO_ANTERIOR' AS parte,
        h.escopo,
        'canal_anterior_acionado' AS dimensao_analisada,
        '3_video_chamada_anterior' AS categoria_valor,
        COUNT(*) FILTER (WHERE h.teve_video_ant) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) FILTER (WHERE h.teve_video_ant) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_video_ant),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_video_ant) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM historico_anterior AS h
    INNER JOIN totais_escopo AS t ON t.escopo = h.escopo
    GROUP BY h.escopo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        2 AS parte_ordem,
        'PARTE_B_CONTATO_ANTERIOR' AS parte,
        h.escopo,
        'canal_anterior_acionado' AS dimensao_analisada,
        '4_totem_anterior' AS categoria_valor,
        COUNT(*) FILTER (WHERE h.teve_totem_ant) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) FILTER (WHERE h.teve_totem_ant) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_totem_ant),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_totem_ant) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM historico_anterior AS h
    INNER JOIN totais_escopo AS t ON t.escopo = h.escopo
    GROUP BY h.escopo, t.total_contatos_escopo, t.total_alunos_escopo
    UNION ALL
    SELECT
        2 AS parte_ordem,
        'PARTE_B_CONTATO_ANTERIOR' AS parte,
        h.escopo,
        'canal_anterior_acionado' AS dimensao_analisada,
        '5_call_center_anterior' AS categoria_valor,
        COUNT(*) FILTER (WHERE h.teve_cc_ant) AS contatos,
        t.total_contatos_escopo,
        ROUND(100.0 * COUNT(*) FILTER (WHERE h.teve_cc_ant) / NULLIF(t.total_contatos_escopo, 0), 2),
        COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_cc_ant),
        t.total_alunos_escopo,
        ROUND(100.0 * COUNT(DISTINCT h.aluno_hash) FILTER (WHERE h.teve_cc_ant) / NULLIF(t.total_alunos_escopo, 0), 2)
    FROM historico_anterior AS h
    INNER JOIN totais_escopo AS t ON t.escopo = h.escopo
    GROUP BY h.escopo, t.total_contatos_escopo, t.total_alunos_escopo
)
SELECT
    parte_ordem,
    parte,
    escopo,
    dimensao_analisada,
    categoria_valor,
    contatos,
    denominador_contatos,
    pct_contatos,
    alunos_distintos,
    denominador_alunos,
    pct_alunos
FROM (
    SELECT * FROM parte_a_perfil
    UNION ALL
    SELECT * FROM parte_b_anterior
)
ORDER BY
    parte_ordem,
    escopo,
    dimensao_analisada,
    CASE WHEN parte_ordem = 1 THEN -contatos ELSE 0 END,
    categoria_valor;
