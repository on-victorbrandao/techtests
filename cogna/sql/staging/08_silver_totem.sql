-- silver do totem: uma linha de saida para cada linha de raw_totem
CREATE OR REPLACE TABLE silver_totem AS
WITH base AS (
    -- o totem nao tem agente, fila, protocolo nem tabulacao; motivo (mdc) e navegacao ficam como vieram
    SELECT
        'totem' AS canal,
        r.origem_arquivo,
        r.origem_aba,
        r.origem_linha,
        m_nulo(trim(r.identificador_aluno)) AS aluno_id_original,
        r.data_inicio AS data_hora_contato,
        m_inteiro_s(r.duracao) AS duracao_s,
        m_tempo_invalido(r.duracao) AS flag_tempo_invalido,
        m_nulo(r.instituicao) AS instituicao_original,
        m_nulo(r.mdc) AS mdc_original,
        m_nulo(r.navegacao) AS navegacao_original,
        m_nulo(r.nota_pergunta1) AS nota_original
    FROM raw_totem AS r
),
quartis AS (
    -- quartis da duracao do canal para a regra IQR 1,5 (valores nulos ficam fora)
    SELECT
        *,
        quantile_cont(duracao_s, 0.25) OVER () AS dur_q1,
        quantile_cont(duracao_s, 0.75) OVER () AS dur_q3
    FROM base
),
regras AS (
    -- satisfacao do totem
    SELECT
        *,
        m_status_nota(nota_original) AS status_nota,
        m_nota(nota_original) AS nota
    FROM quartis
)
SELECT
    CAST(m_contato_id(canal, origem_aba, origem_linha) AS VARCHAR) AS contato_id,
    CAST(canal AS VARCHAR) AS canal,
    CAST(origem_arquivo AS VARCHAR) AS origem_arquivo,
    CAST(origem_aba AS VARCHAR) AS origem_aba,
    CAST(origem_linha AS INTEGER) AS origem_linha,
    CAST(aluno_id_original AS VARCHAR) AS aluno_id_original,
    CAST(m_hash_aluno(aluno_id_original) AS VARCHAR) AS aluno_hash,
    CAST(data_hora_contato AS TIMESTAMP) AS data_hora_contato,
    CAST(duracao_s AS INTEGER) AS duracao_s,
    CAST(COALESCE(duracao_s = 0, FALSE) AS BOOLEAN) AS flag_duracao_zero,
    CAST(COALESCE(duracao_s < dur_q1 - 1.5 * (dur_q3 - dur_q1)
                  OR duracao_s > dur_q3 + 1.5 * (dur_q3 - dur_q1), FALSE) AS BOOLEAN) AS flag_outlier_duracao,
    CAST(flag_tempo_invalido AS BOOLEAN) AS flag_tempo_invalido,
    CAST(instituicao_original AS VARCHAR) AS instituicao_original,
    CAST(COALESCE(m_norm(instituicao_original) = 'nao identificado', FALSE) AS BOOLEAN) AS flag_instituicao_nao_identificada,
    CAST(mdc_original AS VARCHAR) AS mdc_original,
    CAST(COALESCE(m_norm(mdc_original) = 'nao identificado', FALSE) AS BOOLEAN) AS flag_mdc_nao_identificado,
    CAST(navegacao_original AS VARCHAR) AS navegacao_original,
    CAST(m_qtd_passos(navegacao_original) AS INTEGER) AS qtd_passos_original,
    CAST(nota_original AS VARCHAR) AS nota_original,
    CAST(status_nota AS VARCHAR) AS status_nota,
    CAST(nota AS INTEGER) AS nota,
    CAST(status_nota = 'respondida' AS BOOLEAN) AS respondeu_pesquisa,
    CAST(COALESCE(nota IN (1, 2), FALSE) AS BOOLEAN) AS flag_nota_ruim
FROM regras
ORDER BY origem_linha;
