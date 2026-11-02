-- texto vazio ou literal de nulo vira NULL
CREATE OR REPLACE MACRO m_nulo(x) AS
    CASE WHEN x IS NULL OR trim(x) IN ('', 'nan', 'NaN', 'None', 'none', 'null', 'NULL') THEN NULL ELSE x END;

-- texto sem acento, minusculo e sem espacos nas pontas
CREATE OR REPLACE MACRO m_norm(x) AS strip_accents(lower(trim(x)));

-- serial do Excel (dias desde 1899-12-30) para timestamp, arredondado em milissegundos
CREATE OR REPLACE MACRO m_serial_ts(x) AS
    CASE WHEN isfinite(TRY_CAST(x AS DOUBLE))
        THEN TIMESTAMP '1899-12-30' + to_milliseconds(CAST(round(CAST(x AS DOUBLE) * 86400000) AS BIGINT))
    END;

-- serial do Excel para data
CREATE OR REPLACE MACRO m_serial_date(x) AS
    CASE WHEN isfinite(TRY_CAST(x AS DOUBLE))
        THEN DATE '1899-12-30' + CAST(floor(CAST(x AS DOUBLE)) AS INTEGER)
    END;

-- contato_id deterministico a partir de canal, aba e linha de origem
CREATE OR REPLACE MACRO m_contato_id(canal, aba, linha) AS
    substr(sha256(canal || '|' || aba || '|' || CAST(linha AS VARCHAR)), 1, 16);

-- hash do aluno com salt vindo da variavel salt (pseudonimizacao, nao anonimizacao)
CREATE OR REPLACE MACRO m_hash_aluno(id) AS
    CASE WHEN id IS NULL THEN NULL ELSE sha256(getvariable('salt') || '|' || id) END;

-- segundos inteiros nao negativos, qualquer outra coisa vira NULL
CREATE OR REPLACE MACRO m_inteiro_s(x) AS
    CASE WHEN isfinite(TRY_CAST(m_nulo(x) AS DOUBLE))
              AND TRY_CAST(m_nulo(x) AS DOUBLE) >= 0
              AND TRY_CAST(m_nulo(x) AS DOUBLE) < 2147483647
              AND TRY_CAST(m_nulo(x) AS DOUBLE) = floor(TRY_CAST(m_nulo(x) AS DOUBLE))
        THEN CAST(TRY_CAST(m_nulo(x) AS DOUBLE) AS INTEGER)
    END;

-- tempo informado na origem mas que nao virou inteiro valido
CREATE OR REPLACE MACRO m_tempo_invalido(x) AS
    m_nulo(x) IS NOT NULL AND m_inteiro_s(x) IS NULL;

-- classificacao da nota original
CREATE OR REPLACE MACRO m_status_nota(x) AS
    CASE
        WHEN m_nulo(x) IS NULL THEN 'sem_resposta_nula'
        WHEN NOT isfinite(TRY_CAST(x AS DOUBLE)) OR TRY_CAST(x AS DOUBLE) IS NULL THEN 'invalida'
        WHEN TRY_CAST(x AS DOUBLE) = 0 THEN 'sem_resposta_zero'
        WHEN TRY_CAST(x AS DOUBLE) IN (1, 2, 3, 4, 5) THEN 'respondida'
        ELSE 'invalida'
    END;

-- nota analitica: so inteiro de 1 a 5
CREATE OR REPLACE MACRO m_nota(x) AS
    CASE WHEN m_status_nota(x) = 'respondida' THEN CAST(TRY_CAST(x AS DOUBLE) AS INTEGER) END;

-- formato do protocolo sem julgar validade
CREATE OR REPLACE MACRO m_formato_protocolo(p) AS
    CASE
        WHEN m_nulo(p) IS NULL THEN 'nulo'
        WHEN regexp_matches(p, '^CS[0-9]{8}$') THEN 'cs'
        WHEN p LIKE '%EDU%' THEN 'edu'
        WHEN regexp_matches(trim(p), '^[0-9]+([.][0-9]+)?[Ee][+-]?[0-9]+$') THEN 'notacao_cientifica'
        WHEN regexp_matches(trim(p), '^[0-9]+$') THEN 'numerico'
        WHEN strip_accents(upper(trim(p))) = 'CRA_RETENCAO' THEN 'cra_retencao'
        WHEN regexp_matches(p, '^S[0-9]+$') THEN 'prefixo_s'
        ELSE 'outro'
    END;

-- nivel n da tabulacao (separador >), vazio vira NULL
CREATE OR REPLACE MACRO m_tab_nivel(t, n) AS
    NULLIF(trim(string_split(t, '>')[n]), '');

-- quantidade de niveis preenchidos na tabulacao
CREATE OR REPLACE MACRO m_qtd_niveis_tab(t) AS
    CASE WHEN m_nulo(t) IS NULL THEN 0
        ELSE len(list_filter(string_split(t, '>'), lambda x: trim(x) <> ''))
    END;

-- modalidade pelo primeiro nivel da tabulacao
CREATE OR REPLACE MACRO m_modalidade_tab(t) AS
    CASE
        WHEN regexp_matches(m_norm(m_tab_nivel(t, 1)), 'presencial') THEN 'Presencial'
        WHEN regexp_matches(m_norm(m_tab_nivel(t, 1)), '\bead\b') THEN 'EAD'
    END;

-- grupo Presencial ou EAD a partir do rotulo cadastral da modalidade
CREATE OR REPLACE MACRO m_modalidade_grupo(rotulo) AS
    CASE
        WHEN regexp_matches(m_norm(rotulo), 'presencial') THEN 'Presencial'
        WHEN regexp_matches(m_norm(rotulo), '\bead\b') THEN 'EAD'
    END;

-- tabulacao com assunto de retencao
CREATE OR REPLACE MACRO m_assunto_retencao(t) AS
    COALESCE(contains(m_norm(t), 'atendimento de retencao'), FALSE);

-- tabulacao de encaminhamento para retencao
CREATE OR REPLACE MACRO m_encaminhamento_retencao(t) AS
    COALESCE(contains(m_norm(t), 'para retencao'), FALSE);

-- desfecho so quando o assunto e retencao; pedido nao e efetivacao
CREATE OR REPLACE MACRO m_desfecho_retencao(t, eh_retencao) AS
    CASE
        WHEN NOT eh_retencao THEN NULL
        WHEN contains(m_norm(t), 'cancelamento') THEN 'pedido_cancelamento'
        WHEN contains(m_norm(t), 'mantido') THEN 'aluno_mantido'
        WHEN contains(m_norm(t), 'transferencia') THEN 'pedido_transferencia'
        WHEN contains(m_norm(t), 'trancamento') THEN 'pedido_trancamento'
        WHEN contains(m_norm(t), 'rematricula') THEN 'rematricula'
        ELSE 'nao_classificado'
    END;

-- quantidade de passos separados por barra vertical
CREATE OR REPLACE MACRO m_qtd_passos(x) AS
    CASE WHEN m_nulo(x) IS NULL THEN NULL ELSE len(string_split(x, '|')) END;

-- sequencia sem passos iguais seguidos, a original continua intacta
CREATE OR REPLACE MACRO m_sem_repeticao(x) AS
    CASE WHEN m_nulo(x) IS NULL THEN NULL
        ELSE array_to_string(
            list_filter(string_split(x, '|'), lambda p, i: i = 1 OR p <> string_split(x, '|')[i - 1]),
            '|')
    END;

-- status do dominio: nulo, sem dicionario ou o status calculado no dicionario
CREATE OR REPLACE MACRO m_status_dominio(codigo, dom_codigo, dom_status) AS
    CASE
        WHEN codigo IS NULL THEN 'nulo'
        WHEN dom_codigo IS NULL THEN 'sem_dicionario'
        ELSE dom_status
    END;
