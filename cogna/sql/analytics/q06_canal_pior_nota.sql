-- Pergunta 6 (Q6): Qual o canal de atendimento possui a pior nota de pesquisa?
-- Populacao analisada: 5.991 contatos nos 4 canais, contendo 1.945 respostas validas (notas 1 a 5), 3.208 notas zero (sem resposta) e 838 notas nulas (sem resposta).
-- Denominador: total de contatos do canal (para taxa_resposta_pct) e total de notas validas 1 a 5 (para nota_media = SUM(nota)/COUNT(nota) e pct_notas_ruins = notas 1 e 2 sobre respondidos).
-- Premissas aplicadas: nota 0 e nulo sao excluidos do denominador da media (respondeu_pesquisa = FALSE). Nota ruim = 1 ou 2. Agregacao geral calculada pela soma total das notas dividida pelo total de respostas validas (8.643 / 1.945 = 4,44), nunca como media de medias arredondadas.
-- Limitacoes: o Totem possui cobertura amostral extremamente baixa (apenas 24 respostas validas em 1.499 contatos = 1,60%), o que reduz a precisao estatistica de sua media isolada. O WhatsApp apresenta tanto a pior nota media (3,89) quanto o maior percentual de notas ruins (17,07% = 84/492) com amostra robusta (32,93% de resposta).
WITH por_canal AS (
    SELECT
        COALESCE(fc.canal, 'TOTAL_GERAL') AS canal,
        COUNT(*) AS total_contatos,
        COUNT(fc.nota) AS notas_validas,
        COUNT(*) FILTER (WHERE fc.status_nota = 'sem_resposta_zero') AS sem_resposta_zero,
        COUNT(*) FILTER (WHERE fc.status_nota = 'sem_resposta_nula') AS sem_resposta_nula,
        ROUND(100.0 * COUNT(fc.nota) / NULLIF(COUNT(*), 0), 2) AS taxa_resposta_pct,
        SUM(fc.nota) AS soma_notas,
        ROUND(CAST(SUM(fc.nota) AS DOUBLE) / NULLIF(COUNT(fc.nota), 0), 2) AS nota_media,
        COUNT(*) FILTER (WHERE fc.flag_nota_ruim) AS qtd_notas_ruins,
        ROUND(100.0 * COUNT(*) FILTER (WHERE fc.flag_nota_ruim) / NULLIF(COUNT(fc.nota), 0), 2) AS pct_notas_ruins,
        COUNT(*) FILTER (WHERE fc.nota = 1) AS nota_1,
        COUNT(*) FILTER (WHERE fc.nota = 2) AS nota_2,
        COUNT(*) FILTER (WHERE fc.nota = 3) AS nota_3,
        COUNT(*) FILTER (WHERE fc.nota = 4) AS nota_4,
        COUNT(*) FILTER (WHERE fc.nota = 5) AS nota_5
    FROM fato_contato AS fc
    GROUP BY GROUPING SETS ((fc.canal), ())
)
SELECT
    CASE
        WHEN canal = 'TOTAL_GERAL' THEN 99
        ELSE ROW_NUMBER() OVER (
            ORDER BY CASE WHEN canal = 'TOTAL_GERAL' THEN 1 ELSE 0 END, nota_media ASC
        )
    END AS ranking_pior_nota,
    canal,
    total_contatos,
    notas_validas,
    sem_resposta_zero,
    sem_resposta_nula,
    taxa_resposta_pct,
    soma_notas,
    nota_media,
    qtd_notas_ruins,
    pct_notas_ruins,
    nota_1,
    nota_2,
    nota_3,
    nota_4,
    nota_5,
    CASE
        WHEN canal = 'whatsapp' THEN 'Pior nota média (3,89) e maior % de notas ruins (17,07%)'
        WHEN canal = 'totem' THEN 'Atenção: baixíssima cobertura amostral (24 respostas = 1,60%)'
        WHEN canal = 'TOTAL_GERAL' THEN 'Consolidado global (soma 8.643 / 1.945 válidas)'
        ELSE 'Cobertura amostral adequada (> 44%)'
    END AS observacao_analitica
FROM por_canal
ORDER BY
    CASE WHEN canal = 'TOTAL_GERAL' THEN 1 ELSE 0 END,
    nota_media ASC;
