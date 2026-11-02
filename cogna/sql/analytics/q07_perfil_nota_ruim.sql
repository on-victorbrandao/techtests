-- Pergunta 7 (Q7): Temos algum perfil de aluno que nos dao uma nota de satisfacao ruim?
-- Populacao analisada: contatos dos canais que possuem atributos de perfil no momento do atendimento (Call Center e WhatsApp para modalidade, categoria_aluno e instituicao; Totem adicionalmente para instituicao). Video Chamada nao possui colunas de perfil cadastral.
-- Denominador: total de respostas validas (notas 1 a 5) de cada recorte de perfil. Sinalizamos explicitamente se o recorte atinge tamanho amostral minimo (amostra_minima_30_respostas = TRUE quando respostas_validas >= 30; no cruzamento multidimensional detalhado incluimos grupos com respostas_validas >= 10).
-- Premissas aplicadas: nota ruim = 1 ou 2. Perfil avaliado no momento do contato sem copiar cadastro entre canais.
-- Limitacoes: como o WhatsApp concentra mais alunos de Presencial Campus (1.309 de 1.494 contatos) e tem nota media mais baixa (3,89), na visao agregada sem separar canal a modalidade Presencial Campus apresenta maior % de nota ruim (13,24%). Ao abrir o cruzamento por canal + perfil, verifica-se que o efeito principal vem do canal WhatsApp (onde Presencial Calouro Anhanguera tem 20,13% de nota ruim e Presencial Veterano Anhanguera tem 16,41%), enquanto no Call Center os mesmos perfis tem 5,56% e 8,97% de nota ruim.
WITH base_perfil AS (
    SELECT
        fc.contato_id,
        fc.canal,
        fc.nota,
        fc.respondeu_pesquisa,
        fc.flag_nota_ruim,
        dp.modalidade_rotulo,
        dp.modalidade_grupo,
        dp.categoria_aluno_rotulo,
        dp.instituicao_rotulo,
        dp.instituicao_nome_limpo,
        dp.id_type_rotulo
    FROM fato_contato AS fc
    INNER JOIN dim_perfil_aluno AS dp
        ON dp.perfil_id = fc.perfil_id
),
por_modalidade AS (
    SELECT
        1 AS secao_ordem,
        '1_por_modalidade_cc_wa' AS secao,
        'call_center + whatsapp' AS escopo_canal,
        modalidade_rotulo AS perfil_recorte,
        COUNT(*) AS total_contatos,
        COUNT(nota) AS respostas_validas,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins,
        COUNT(nota) >= 30 AS amostra_robusta_min30
    FROM base_perfil
    WHERE canal IN ('call_center', 'whatsapp')
    GROUP BY modalidade_rotulo
),
por_categoria AS (
    SELECT
        2 AS secao_ordem,
        '2_por_categoria_aluno_cc_wa' AS secao,
        'call_center + whatsapp' AS escopo_canal,
        categoria_aluno_rotulo AS perfil_recorte,
        COUNT(*) AS total_contatos,
        COUNT(nota) AS respostas_validas,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins,
        COUNT(nota) >= 30 AS amostra_robusta_min30
    FROM base_perfil
    WHERE canal IN ('call_center', 'whatsapp')
    GROUP BY categoria_aluno_rotulo
),
por_instituicao AS (
    SELECT
        3 AS secao_ordem,
        '3_por_instituicao_cc_wa_totem' AS secao,
        canal AS escopo_canal,
        instituicao_rotulo AS perfil_recorte,
        COUNT(*) AS total_contatos,
        COUNT(nota) AS respostas_validas,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins,
        COUNT(nota) >= 30 AS amostra_robusta_min30
    FROM base_perfil
    WHERE canal IN ('call_center', 'whatsapp', 'totem')
    GROUP BY canal, instituicao_rotulo
    HAVING COUNT(nota) > 0
),
cruzamento_completo_sem_canal AS (
    SELECT
        4 AS secao_ordem,
        '4_cruzamento_perfil_consolidado_min10_respostas' AS secao,
        'call_center + whatsapp' AS escopo_canal,
        modalidade_rotulo || ' | ' || categoria_aluno_rotulo || ' | ' || instituicao_rotulo AS perfil_recorte,
        COUNT(*) AS total_contatos,
        COUNT(nota) AS respostas_validas,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins,
        COUNT(nota) >= 30 AS amostra_robusta_min30
    FROM base_perfil
    WHERE canal IN ('call_center', 'whatsapp')
    GROUP BY modalidade_rotulo, categoria_aluno_rotulo, instituicao_rotulo
    HAVING COUNT(nota) >= 10
),
cruzamento_por_canal_e_perfil AS (
    SELECT
        5 AS secao_ordem,
        '5_cruzamento_canal_e_perfil_min10_respostas' AS secao,
        canal AS escopo_canal,
        modalidade_rotulo || ' | ' || categoria_aluno_rotulo || ' | ' || instituicao_rotulo AS perfil_recorte,
        COUNT(*) AS total_contatos,
        COUNT(nota) AS respostas_validas,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins,
        COUNT(nota) >= 30 AS amostra_robusta_min30
    FROM base_perfil
    WHERE canal IN ('call_center', 'whatsapp')
    GROUP BY canal, modalidade_rotulo, categoria_aluno_rotulo, instituicao_rotulo
    HAVING COUNT(nota) >= 10
)
SELECT
    secao_ordem,
    secao,
    escopo_canal,
    perfil_recorte,
    total_contatos,
    respostas_validas,
    taxa_resposta_pct,
    soma_notas,
    nota_media,
    qtd_notas_ruins,
    pct_notas_ruins,
    amostra_robusta_min30
FROM (
    SELECT * FROM por_modalidade
    UNION ALL
    SELECT * FROM por_categoria
    UNION ALL
    SELECT * FROM por_instituicao
    UNION ALL
    SELECT * FROM cruzamento_completo_sem_canal
    UNION ALL
    SELECT * FROM cruzamento_por_canal_e_perfil
)
ORDER BY
    secao_ordem,
    pct_notas_ruins DESC NULLS LAST,
    nota_media ASC,
    respostas_validas DESC,
    escopo_canal,
    perfil_recorte;
