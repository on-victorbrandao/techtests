-- Pergunta 1 (Q1): Qual a quantidade de alunos que entraram em contato com o call center e posteriormente com o WhatsApp?
-- Populacao analisada: 1.499 contatos do Call Center (173 alunos distintos) cruzados com 1.494 contatos do WhatsApp.
-- Denominador: 173 alunos distintos com contato no Call Center (para percentual de alunos) e 1.499 contatos do Call Center (para percentual de contatos).
-- Premissas aplicadas: "posteriormente" significa timestamp estritamente maior (data_hora_contato_wa > data_hora_contato_cc). Reportamos tambem a quebra entre transicao imediata (proximo contato na jornada global = WhatsApp) e transicao com canais intermediarios, alem da sensibilidade para janelas de ate 24 horas e ate 7 dias.
-- Limitacoes: um mesmo atendimento de WhatsApp pode ser posterior a mais de um contato de Call Center do mesmo aluno; por isso separamos a contagem de alunos distintos (173) da contagem de contatos/transicoes de Call Center (1.403 no total, sendo 340 imediatas e 1.063 com intermediarios).
WITH contatos_cc AS (
    SELECT
        fc.contato_id,
        fc.aluno_hash,
        fc.data_hora_contato AS ts_cc,
        fj.canal_proximo,
        fj.data_hora_proximo
    FROM fato_contato AS fc
    INNER JOIN fato_jornada AS fj
        ON fj.contato_id = fc.contato_id
    WHERE fc.canal = 'call_center'
),
pareamento_wa AS (
    SELECT
        cc.contato_id,
        cc.aluno_hash,
        cc.ts_cc,
        cc.canal_proximo,
        MIN(wa.data_hora_contato) AS min_ts_wa_posterior,
        epoch(MIN(wa.data_hora_contato) - cc.ts_cc) AS segundos_ate_primeiro_wa
    FROM contatos_cc AS cc
    LEFT JOIN fato_contato AS wa
        ON wa.aluno_hash = cc.aluno_hash
       AND wa.canal = 'whatsapp'
       AND wa.data_hora_contato > cc.ts_cc
    GROUP BY
        cc.contato_id,
        cc.aluno_hash,
        cc.ts_cc,
        cc.canal_proximo
),
totais AS (
    SELECT
        COUNT(DISTINCT aluno_hash) AS total_alunos_cc,
        COUNT(*) AS total_contatos_cc
    FROM pareamento_wa
),
metricas AS (
    SELECT
        1 AS ordem,
        '1_qualquer_wa_posterior_no_periodo' AS recorte,
        'Qualquer contato no WhatsApp em timestamp estritamente posterior (> ts_cc)' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE min_ts_wa_posterior IS NOT NULL) AS alunos_distintos,
        COUNT(*) FILTER (WHERE min_ts_wa_posterior IS NOT NULL) AS contatos_cc
    FROM pareamento_wa
    UNION ALL
    SELECT
        2 AS ordem,
        '2_transicao_imediata_cc_para_wa' AS recorte,
        'Próximo contato imediato do aluno na jornada global (k+1) foi no WhatsApp' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE canal_proximo = 'whatsapp') AS alunos_distintos,
        COUNT(*) FILTER (WHERE canal_proximo = 'whatsapp') AS contatos_cc
    FROM pareamento_wa
    UNION ALL
    SELECT
        3 AS ordem,
        '3_transicao_com_canais_intermediarios' AS recorte,
        'Teve WhatsApp posterior, mas o contato imediato (k+1) foi em outro canal' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE min_ts_wa_posterior IS NOT NULL AND COALESCE(canal_proximo, '') <> 'whatsapp') AS alunos_distintos,
        COUNT(*) FILTER (WHERE min_ts_wa_posterior IS NOT NULL AND COALESCE(canal_proximo, '') <> 'whatsapp') AS contatos_cc
    FROM pareamento_wa
    UNION ALL
    SELECT
        4 AS ordem,
        '4_sem_wa_posterior' AS recorte,
        'Contatos de Call Center sem nenhum contato de WhatsApp posterior no período' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE min_ts_wa_posterior IS NULL) AS alunos_distintos,
        COUNT(*) FILTER (WHERE min_ts_wa_posterior IS NULL) AS contatos_cc
    FROM pareamento_wa
    UNION ALL
    SELECT
        5 AS ordem,
        '5_sensibilidade_janela_ate_24h' AS recorte,
        'Contato no WhatsApp em até 24 horas (86.400s) após o Call Center' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE segundos_ate_primeiro_wa <= 86400) AS alunos_distintos,
        COUNT(*) FILTER (WHERE segundos_ate_primeiro_wa <= 86400) AS contatos_cc
    FROM pareamento_wa
    UNION ALL
    SELECT
        6 AS ordem,
        '6_sensibilidade_janela_ate_7_dias' AS recorte,
        'Contato no WhatsApp em até 7 dias (604.800s) após o Call Center' AS descricao,
        COUNT(DISTINCT aluno_hash) FILTER (WHERE segundos_ate_primeiro_wa <= 604800) AS alunos_distintos,
        COUNT(*) FILTER (WHERE segundos_ate_primeiro_wa <= 604800) AS contatos_cc
    FROM pareamento_wa
)
SELECT
    m.ordem,
    m.recorte,
    m.descricao,
    m.alunos_distintos,
    t.total_alunos_cc AS denominador_alunos_cc,
    ROUND(100.0 * m.alunos_distintos / NULLIF(t.total_alunos_cc, 0), 2) AS pct_alunos_cc,
    m.contatos_cc,
    t.total_contatos_cc AS denominador_contatos_cc,
    ROUND(100.0 * m.contatos_cc / NULLIF(t.total_contatos_cc, 0), 2) AS pct_contatos_cc
FROM metricas AS m
CROSS JOIN totais AS t
ORDER BY m.ordem;
