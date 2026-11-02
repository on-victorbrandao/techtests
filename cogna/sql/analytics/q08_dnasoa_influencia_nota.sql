-- Pergunta 8 (Q8): Utilizando a coluna DNASoa do arquivo de Call Center e possivel avaliar se os pontos de navegacao que o aluno utilizou influenciaram na nota obtida no atendimento?
-- Populacao analisada: 1.499 contatos do Call Center (1.497 com dna_soa preenchido e 2 nulos; 661 notas validas no total, sendo 660 com dna_soa preenchido e 1 nula).
-- Denominador: na analise por ponto de navegacao, usamos presenca unica por contato (COUNT(DISTINCT contato_id) sobre fato_navegacao com tipo_sequencia = 'original'), evitando multiplicar a nota de um mesmo atendimento pelo numero de repeticoes em trio (ex.: 3x consecutivas) do mesmo no. Na analise complementar por complexidade da trilha, o denominador e o total de contatos com nota valida em cada faixa de quantidade de passos.
-- Premissas aplicadas: avaliamos (1) associacao por ponto de navegacao unico no contato, (2) associacao com a presenca dos tokens 98 e 99 e (3) associacao com o comprimento/complexidade da trilha (qtd_passos_original e qtd_passos_sem_repeticao).
-- Limitacoes (DIFERENCA ENTRE ASSOCIACAO E CAUSALIDADE): o desenho do estudo e puramente observacional. A nota de pesquisa no Call Center e atribuida ao final do atendimento (que envolve espera na fila e interacao com o agente humano, alem da passagem previa pela URA/DNA_SOA). Portanto, é possivel medir ASSOCIACAO/CORRELACAO estatistica entre os nos/comprimentos de trilha e a nota (que neste dataset mostra variacao pequena entre os nos, com medias entre 4,55 e 4,64 e notas ruins entre 5,69% e 7,52%), mas NAO e possivel inferir causalidade direta dos pontos de navegacao sobre a nota.
WITH presenca_no_contato AS (
    SELECT DISTINCT
        fn.contato_id,
        fn.ponto_navegacao,
        fn.eh_token_98_99,
        fc.nota,
        fc.respondeu_pesquisa,
        fc.flag_nota_ruim
    FROM fato_navegacao AS fn
    INNER JOIN fato_contato AS fc
        ON fc.contato_id = fn.contato_id
    WHERE fn.canal = 'call_center'
      AND fn.tipo_sequencia = 'original'
),
por_ponto_navegacao AS (
    SELECT
        1 AS secao_ordem,
        '1_presenca_unica_por_ponto_navegacao' AS secao,
        ponto_navegacao AS categoria_analisada,
        COUNT(DISTINCT contato_id) AS contatos_totais,
        COUNT(DISTINCT contato_id) FILTER (WHERE respondeu_pesquisa) AS contatos_com_nota,
        ROUND(100.0 * COUNT(DISTINCT contato_id) FILTER (WHERE respondeu_pesquisa) / NULLIF(COUNT(DISTINCT contato_id), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(DISTINCT contato_id) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(DISTINCT contato_id) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins
    FROM presenca_no_contato
    GROUP BY ponto_navegacao
),
resumo_contato_cc AS (
    SELECT
        fc.contato_id,
        fc.nota,
        fc.respondeu_pesquisa,
        fc.flag_nota_ruim,
        fc.qtd_passos_original,
        COUNT(DISTINCT fn_sem.ordem_passo) AS qtd_passos_sem_repeticao,
        COALESCE(BOOL_OR(fn_orig.ponto_navegacao = '98'), FALSE) AS tem_token_98,
        COALESCE(BOOL_OR(fn_orig.ponto_navegacao = '99'), FALSE) AS tem_token_99
    FROM fato_contato AS fc
    LEFT JOIN fato_navegacao AS fn_orig
        ON fn_orig.contato_id = fc.contato_id
       AND fn_orig.tipo_sequencia = 'original'
    LEFT JOIN fato_navegacao AS fn_sem
        ON fn_sem.contato_id = fc.contato_id
       AND fn_sem.tipo_sequencia = 'sem_repeticao_consecutiva'
    WHERE fc.canal = 'call_center'
    GROUP BY
        fc.contato_id,
        fc.nota,
        fc.respondeu_pesquisa,
        fc.flag_nota_ruim,
        fc.qtd_passos_original
),
por_grupo_token AS (
    SELECT
        2 AS secao_ordem,
        '2_presenca_tokens_98_99_vs_trios_estritos' AS secao,
        CASE
            WHEN qtd_passos_original IS NULL THEN 'Sem DNA_SOA (Nulo)'
            WHEN tem_token_98 THEN 'Com token 98'
            WHEN tem_token_99 THEN 'Com token 99'
            ELSE 'Sem token 98/99 (Trios estritos)'
        END AS categoria_analisada,
        COUNT(*) AS contatos_totais,
        COUNT(nota) AS contatos_com_nota,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins
    FROM resumo_contato_cc
    GROUP BY 3
),
por_complexidade AS (
    SELECT
        3 AS secao_ordem,
        '3_complexidade_trilha_passos_sem_repeticao' AS secao,
        CASE
            WHEN qtd_passos_original IS NULL THEN '00 passos (DNA_SOA nulo)'
            WHEN qtd_passos_sem_repeticao <= 3 THEN '01_curta (3 passos sem repetição; 9-15 brutos)'
            WHEN qtd_passos_sem_repeticao BETWEEN 4 AND 6 THEN '02_media (4 a 6 passos sem repetição; 12-30 brutos)'
            WHEN qtd_passos_sem_repeticao BETWEEN 7 AND 9 THEN '03_longa (7 a 9 passos sem repetição; 15-36 brutos)'
            ELSE '04_muito_longa (10 a 14 passos sem repetição; 18-42 brutos)'
        END AS categoria_analisada,
        COUNT(*) AS contatos_totais,
        COUNT(nota) AS contatos_com_nota,
        ROUND(100.0 * COUNT(nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(nota) AS soma_notas,
        ROUND(CAST(SUM(nota) AS DOUBLE) / NULLIF(COUNT(nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE flag_nota_ruim) / NULLIF(COUNT(nota), 0), 2) AS pct_notas_ruins
    FROM resumo_contato_cc
    GROUP BY 3
)
SELECT
    secao_ordem,
    secao,
    categoria_analisada,
    contatos_totais,
    contatos_com_nota,
    taxa_resposta_pct,
    soma_notas,
    nota_media,
    qtd_notas_ruins,
    pct_notas_ruins,
    'Observacional: mede associação/correlação no grão do contato, sem inferência causal direta da URA sobre a nota.' AS nota_metodologica
FROM (
    SELECT * FROM por_ponto_navegacao
    UNION ALL
    SELECT * FROM por_grupo_token
    UNION ALL
    SELECT * FROM por_complexidade
)
ORDER BY
    secao_ordem,
    CASE WHEN secao_ordem = 3 THEN categoria_analisada ELSE '' END ASC,
    contatos_totais DESC,
    categoria_analisada;
