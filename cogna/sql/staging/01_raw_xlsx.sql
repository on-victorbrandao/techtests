-- entrada do call center: aba lida como texto, cabecalhos da Bronze e linhagem de origem
CREATE OR REPLACE TABLE raw_cc AS
WITH lido AS (
    SELECT row_number() OVER () + 1 AS linha, *
    FROM read_xlsx(getvariable('xlsx_path'), sheet = 'Analitico call center',
                   header = false, all_varchar = true, range = 'A2:V100000')
)
SELECT
    regexp_extract(getvariable('xlsx_path'), '[^/\\]+$') AS origem_arquivo,
    'Analitico call center' AS origem_aba,
    CAST(linha AS INTEGER) AS origem_linha,
    A AS identificador_aluno,
    m_serial_date(B) AS "date",
    m_serial_ts(C) AS calldate,
    D AS id_type,
    E AS id_type_desc,
    F AS disconnect_type,
    G AS disconnect_type_desc,
    H AS duration_callcenter,
    I AS dna_soa,
    J AS recepcao_fila,
    K AS fila_atend,
    L AS agent,
    M AS supervisor,
    N AS pesquisa_1,
    O AS protocolo,
    P AS tabulacao,
    Q AS modalidade_nova,
    R AS modalidade_nova_desc,
    S AS categoria_aluno,
    T AS categoria_aluno_desc,
    U AS instituicao,
    V AS instituicao_desc
FROM lido
WHERE len(list_filter([A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S, T, U, V],
                      lambda x: x IS NOT NULL)) > 0;

-- entrada do WhatsApp
CREATE OR REPLACE TABLE raw_wa AS
WITH lido AS (
    SELECT row_number() OVER () + 1 AS linha, *
    FROM read_xlsx(getvariable('xlsx_path'), sheet = 'Analitico Whatsapp',
                   header = false, all_varchar = true, range = 'A2:S100000')
)
SELECT
    regexp_extract(getvariable('xlsx_path'), '[^/\\]+$') AS origem_arquivo,
    'Analitico Whatsapp' AS origem_aba,
    CAST(linha AS INTEGER) AS origem_linha,
    A AS identificador_aluno,
    m_serial_ts(B) AS calldate,
    C AS id_type,
    D AS disconnect_type,
    E AS disconnect_type_desc,
    F AS modalidade,
    G AS modalidade_desc,
    H AS duration_callcenter,
    I AS after_hour,
    J AS categoria_aluno,
    K AS categoria_aluno_desc,
    L AS instituicao,
    M AS instituicao_desc,
    N AS dna_soa,
    O AS tme,
    P AS codigo_unidade,
    Q AS pesquisa_1,
    R AS agente,
    S AS tabulacao
FROM lido
WHERE len(list_filter([A, B, C, D, E, F, G, H, I, J, K, L, M, N, O, P, Q, R, S],
                      lambda x: x IS NOT NULL)) > 0;

-- entrada da video chamada: data com milissegundos e a coluna sem nome (calldate_sem_ms) ficam como texto
CREATE OR REPLACE TABLE raw_video AS
WITH lido AS (
    SELECT row_number() OVER () + 1 AS linha, *
    FROM read_xlsx(getvariable('xlsx_path'), sheet = 'Analitico_video_chamada',
                   header = false, all_varchar = true, range = 'A2:I100000')
)
SELECT
    regexp_extract(getvariable('xlsx_path'), '[^/\\]+$') AS origem_arquivo,
    'Analitico_video_chamada' AS origem_aba,
    CAST(linha AS INTEGER) AS origem_linha,
    A AS identificador_aluno,
    B AS calldate,
    C AS calldate_sem_ms,
    D AS tme,
    E AS duracao_da_chamada,
    F AS agente,
    G AS protocolo,
    H AS nota_pergunta1,
    I AS tabulacao
FROM lido
WHERE len(list_filter([A, B, C, D, E, F, G, H, I], lambda x: x IS NOT NULL)) > 0;

-- entrada do totem
CREATE OR REPLACE TABLE raw_totem AS
WITH lido AS (
    SELECT row_number() OVER () + 1 AS linha, *
    FROM read_xlsx(getvariable('xlsx_path'), sheet = 'Analitico_Totem',
                   header = false, all_varchar = true, range = 'A2:G100000')
)
SELECT
    regexp_extract(getvariable('xlsx_path'), '[^/\\]+$') AS origem_arquivo,
    'Analitico_Totem' AS origem_aba,
    CAST(linha AS INTEGER) AS origem_linha,
    A AS identificador_aluno,
    m_serial_ts(B) AS data_inicio,
    C AS duracao,
    D AS instituicao,
    E AS mdc,
    F AS navegacao,
    G AS nota_pergunta1
FROM lido
WHERE len(list_filter([A, B, C, D, E, F, G], lambda x: x IS NOT NULL)) > 0;
