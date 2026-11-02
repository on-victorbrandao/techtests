-- Pergunta 9 (Q9): Qual agente gera o maior volume de recontatos do mesmo CPF no mesmo dia?
-- Populacao analisada: 170 agentes humanos (dim_agente com eh_agente_humano = TRUE) nos canais Call Center (12), WhatsApp (87) e Video Chamada (71), avaliados sobre os 5.991 contatos da jornada dos 173 alunos.
-- Denominador: total de atendimentos realizados pelo agente (para o calculo da taxa de recontato = 100 * volume_recontatos_gerados / total_atendimentos_agente). A pergunta pede "maior volume de recontatos", portanto a ordenacao principal e por volume de recontatos (DESC) e a taxa (%) acompanha como contexto operacional.
-- Premissas aplicadas: quando o mesmo aluno (aluno_hash) realiza um contato k e depois outro contato k+1 no mesmo dia calendario (data_contato), o recontato e atribuido ao agente do atendimento k (imediatamente anterior). Apresentamos duas visoes principais e duas subleituras de sensibilidade:
--   1. Visao A (Omnichannel - Jornada Global com Agente Anterior): o atendimento anterior k teve agente humano (CC, WA ou Video) e o aluno realizou novo contato k+1 no mesmo dia em qualquer canal (exibindo tambem a coluna recontatos_proximo_humano quando k+1 ocorre exclusivamente em CC, WA ou Video).
--   2. Visao A_Restrita (Omnichannel apenas entre canais humanos): sequencia cronologica filtrando previamente apenas os 3 canais com agente humano (CC, WA e Video, excluindo Totem da trilha antes do LAG).
--   3. Visao B (Intracanal Puro): sequencia cronologica particionada por (aluno_hash, canal), medindo quando o aluno volta ao MESMO canal no mesmo dia (atribuido ao agente anterior daquele canal), acompanhada da coluna recontatos_mesmo_canal_consecutivo_global (quando k e k+1 na jornada global sao do mesmo canal no mesmo dia).
-- Limitacoes (LGPD e Causalidade): os agentes sao identificados pelo codigo deterministico (AG-001..AG-170) e pelo hash curto de 12 caracteres (agente_hash = substr(sha256(nome), 1, 12)), permitindo reconciliacao exata sem expor nomes pessoais na camada Gold. Atribuir o recontato ao agente anterior e uma convencao analitica de monitoramento (proxy operacional), nao prova de falha individual do agente, pois na base ha sobreposicoes de horario e multiplas tentativas simultaneas dos alunos.
WITH atendimentos_por_agente AS (
    SELECT
        da.agente_id,
        da.agente_rotulo,
        da.agente_hash,
        da.canal_agente AS canal,
        da.supervisor_id,
        COUNT(fc.contato_id) AS total_atendimentos
    FROM dim_agente AS da
    INNER JOIN fato_contato AS fc
        ON fc.agente_id = da.agente_id
    WHERE da.eh_agente_humano = TRUE
    GROUP BY
        da.agente_id,
        da.agente_rotulo,
        da.agente_hash,
        da.canal_agente,
        da.supervisor_id
),
visao_a_omnichannel AS (
    SELECT
        fj.agente_id_atribuido_recontato AS agente_id,
        COUNT(*) AS recontatos_mesmo_dia,
        COUNT(*) FILTER (WHERE fj.canal <> 'totem') AS recontatos_proximo_canal_humano,
        COUNT(*) FILTER (WHERE fj.flag_recontato_mesmo_dia_mesmo_canal) AS recontatos_mesmo_canal_consecutivo,
        COUNT(DISTINCT fj.aluno_hash) AS alunos_distintos_recontato
    FROM fato_jornada AS fj
    WHERE fj.flag_recontato_mesmo_dia_canal_com_agente = TRUE
    GROUP BY fj.agente_id_atribuido_recontato
),
seq_apenas_canais_humanos AS (
    SELECT
        fc.contato_id,
        fc.aluno_hash,
        fc.canal,
        fc.data_contato,
        LAG(fc.data_contato) OVER (
            PARTITION BY fc.aluno_hash
            ORDER BY fc.data_hora_contato, fc.canal, fc.contato_id
        ) AS data_ant_3c,
        LAG(fc.agente_id) OVER (
            PARTITION BY fc.aluno_hash
            ORDER BY fc.data_hora_contato, fc.canal, fc.contato_id
        ) AS agente_ant_3c
    FROM fato_contato AS fc
    WHERE fc.canal IN ('call_center', 'whatsapp', 'video_chamada')
),
visao_a_restrita_3canais AS (
    SELECT
        agente_ant_3c AS agente_id,
        COUNT(*) AS recontatos_mesmo_dia_3canais,
        COUNT(DISTINCT aluno_hash) AS alunos_distintos_3canais
    FROM seq_apenas_canais_humanos
    WHERE data_contato = data_ant_3c
      AND agente_ant_3c IS NOT NULL
      AND agente_ant_3c <> 'AG-000'
    GROUP BY agente_ant_3c
),
visao_b_intracanal AS (
    SELECT
        fj.agente_id_atribuido_recontato_intracanal AS agente_id,
        COUNT(*) AS recontatos_intracanal_mesmo_dia,
        COUNT(DISTINCT fj.aluno_hash) AS alunos_distintos_intracanal
    FROM fato_jornada AS fj
    WHERE fj.flag_recontato_intracanal_mesmo_dia = TRUE
    GROUP BY fj.agente_id_atribuido_recontato_intracanal
),
consolidado AS (
    SELECT
        a.agente_id,
        a.agente_rotulo,
        a.agente_hash,
        a.canal,
        a.supervisor_id,
        a.total_atendimentos,
        COALESCE(va.recontatos_mesmo_dia, 0) AS recontatos_omnichannel,
        ROUND(100.0 * COALESCE(va.recontatos_mesmo_dia, 0) / NULLIF(a.total_atendimentos, 0), 2) AS taxa_omnichannel_pct,
        COALESCE(va.recontatos_proximo_canal_humano, 0) AS recontatos_omni_prox_humano,
        COALESCE(va3.recontatos_mesmo_dia_3canais, 0) AS recontatos_omni_seq_3canais,
        ROUND(100.0 * COALESCE(va3.recontatos_mesmo_dia_3canais, 0) / NULLIF(a.total_atendimentos, 0), 2) AS taxa_omni_seq_3canais_pct,
        COALESCE(vb.recontatos_intracanal_mesmo_dia, 0) AS recontatos_intracanal,
        ROUND(100.0 * COALESCE(vb.recontatos_intracanal_mesmo_dia, 0) / NULLIF(a.total_atendimentos, 0), 2) AS taxa_intracanal_pct,
        COALESCE(va.recontatos_mesmo_canal_consecutivo, 0) AS recontatos_mesmo_canal_consecutivo_global
    FROM atendimentos_por_agente AS a
    LEFT JOIN visao_a_omnichannel AS va
        ON va.agente_id = a.agente_id
    LEFT JOIN visao_a_restrita_3canais AS va3
        ON va3.agente_id = a.agente_id
    LEFT JOIN visao_b_intracanal AS vb
        ON vb.agente_id = a.agente_id
),
top_visao_a AS (
    SELECT
        1 AS visao_ordem,
        'VISAO_A_OMNICHANNEL_JORNADA_GLOBAL' AS visao,
        ROW_NUMBER() OVER (ORDER BY recontatos_omnichannel DESC, total_atendimentos DESC, agente_id) AS ranking,
        agente_id,
        agente_hash,
        canal,
        supervisor_id,
        total_atendimentos,
        recontatos_omnichannel AS volume_recontatos_mesmo_dia,
        taxa_omnichannel_pct AS taxa_recontato_pct,
        recontatos_omni_prox_humano AS sub_recontatos_prox_humano,
        recontatos_omni_seq_3canais AS sub_recontatos_seq_3canais,
        recontatos_intracanal AS ref_recontatos_intracanal
    FROM consolidado
    QUALIFY ranking <= 10
),
top_visao_a_3canais AS (
    SELECT
        2 AS visao_ordem,
        'VISAO_A2_OMNICHANNEL_APENAS_3_CANAIS_HUMANOS' AS visao,
        ROW_NUMBER() OVER (ORDER BY recontatos_omni_seq_3canais DESC, total_atendimentos DESC, agente_id) AS ranking,
        agente_id,
        agente_hash,
        canal,
        supervisor_id,
        total_atendimentos,
        recontatos_omni_seq_3canais AS volume_recontatos_mesmo_dia,
        taxa_omni_seq_3canais_pct AS taxa_recontato_pct,
        recontatos_omni_prox_humano AS sub_recontatos_prox_humano,
        recontatos_omnichannel AS sub_recontatos_seq_3canais,
        recontatos_intracanal AS ref_recontatos_intracanal
    FROM consolidado
    QUALIFY ranking <= 10
),
top_visao_b AS (
    SELECT
        3 AS visao_ordem,
        'VISAO_B_INTRACANAL_MESMO_CANAL_MESMO_DIA' AS visao,
        ROW_NUMBER() OVER (ORDER BY recontatos_intracanal DESC, total_atendimentos DESC, agente_id) AS ranking,
        agente_id,
        agente_hash,
        canal,
        supervisor_id,
        total_atendimentos,
        recontatos_intracanal AS volume_recontatos_mesmo_dia,
        taxa_intracanal_pct AS taxa_recontato_pct,
        recontatos_mesmo_canal_consecutivo_global AS sub_recontatos_prox_humano,
        recontatos_omni_seq_3canais AS sub_recontatos_seq_3canais,
        recontatos_omnichannel AS ref_recontatos_intracanal
    FROM consolidado
    QUALIFY ranking <= 10
)
SELECT
    visao_ordem,
    visao,
    ranking,
    agente_id,
    agente_hash,
    canal,
    supervisor_id,
    total_atendimentos,
    volume_recontatos_mesmo_dia,
    taxa_recontato_pct,
    sub_recontatos_prox_humano,
    sub_recontatos_seq_3canais,
    ref_recontatos_intracanal
FROM (
    SELECT * FROM top_visao_a
    UNION ALL
    SELECT * FROM top_visao_a_3canais
    UNION ALL
    SELECT * FROM top_visao_b
)
ORDER BY visao_ordem, ranking;
