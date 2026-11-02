-- silver da video chamada: uma linha de saida para cada linha de raw_video
CREATE OR REPLACE TABLE silver_video_chamada AS
WITH base AS (
    -- data com milissegundos lida do texto dd/mm/aaaa hh:mm:ss.mmm, sem conversao de fuso
    SELECT
        'video_chamada' AS canal,
        r.origem_arquivo,
        r.origem_aba,
        r.origem_linha,
        m_nulo(trim(r.identificador_aluno)) AS aluno_id_original,
        m_nulo(r.calldate) AS calldate_original,
        m_nulo(r.calldate_sem_ms) AS calldate_sem_ms_original,
        COALESCE(TRY_STRPTIME(trim(r.calldate), '%d/%m/%Y %H:%M:%S.%g'),
                 TRY_STRPTIME(trim(r.calldate), '%d/%m/%Y %H:%M:%S')) AS data_hora_contato,
        TRY_STRPTIME(trim(r.calldate_sem_ms), '%d/%m/%Y %H:%M:%S') AS data_hora_sem_ms,
        m_inteiro_s(r.duracao_da_chamada) AS duracao_s,
        m_tempo_invalido(r.duracao_da_chamada) AS flag_duracao_invalida,
        m_inteiro_s(r.tme) AS tme_s,
        m_tempo_invalido(r.tme) AS flag_tme_invalido,
        m_nulo(r.agente) AS agente_original,
        m_nulo(r.protocolo) AS protocolo_original,
        m_nulo(r.nota_pergunta1) AS nota_original,
        m_nulo(r.tabulacao) AS tabulacao_original
    FROM raw_video AS r
),
quartis AS (
    -- quartis de duracao e TME do canal para a regra IQR 1,5 (valores nulos ficam fora)
    SELECT
        *,
        quantile_cont(duracao_s, 0.25) OVER () AS dur_q1,
        quantile_cont(duracao_s, 0.75) OVER () AS dur_q3,
        quantile_cont(tme_s, 0.25) OVER () AS tme_q1,
        quantile_cont(tme_s, 0.75) OVER () AS tme_q3
    FROM base
),
regras AS (
    -- flags e derivacoes de satisfacao, protocolo, retencao e tabulacao
    SELECT
        *,
        m_status_nota(nota_original) AS status_nota,
        m_nota(nota_original) AS nota,
        m_formato_protocolo(protocolo_original) AS formato_protocolo,
        m_assunto_retencao(tabulacao_original) AS eh_assunto_retencao
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
    CAST(calldate_original AS VARCHAR) AS calldate_original,
    CAST(calldate_sem_ms_original AS VARCHAR) AS calldate_sem_ms_original,
    CAST(data_hora_contato AS TIMESTAMP) AS data_hora_contato,
    CAST(COALESCE(date_trunc('second', data_hora_contato) <> data_hora_sem_ms, FALSE) AS BOOLEAN) AS flag_calldate_sem_ms_diverge,
    CAST(duracao_s AS INTEGER) AS duracao_s,
    CAST(tme_s AS INTEGER) AS tme_s,
    CAST(COALESCE(duracao_s = 0, FALSE) AS BOOLEAN) AS flag_duracao_zero,
    CAST(COALESCE(duracao_s < dur_q1 - 1.5 * (dur_q3 - dur_q1)
                  OR duracao_s > dur_q3 + 1.5 * (dur_q3 - dur_q1), FALSE) AS BOOLEAN) AS flag_outlier_duracao,
    CAST(COALESCE(tme_s < tme_q1 - 1.5 * (tme_q3 - tme_q1)
                  OR tme_s > tme_q3 + 1.5 * (tme_q3 - tme_q1), FALSE) AS BOOLEAN) AS flag_outlier_tme,
    CAST(COALESCE(tme_s > duracao_s, FALSE) AS BOOLEAN) AS flag_tme_maior_duracao,
    CAST(flag_duracao_invalida OR flag_tme_invalido AS BOOLEAN) AS flag_tempo_invalido,
    CAST(agente_original AS VARCHAR) AS agente_original,
    CAST(protocolo_original AS VARCHAR) AS protocolo_original,
    CAST(formato_protocolo AS VARCHAR) AS formato_protocolo,
    CAST(formato_protocolo = 'cs' AS BOOLEAN) AS protocolo_padrao_cs,
    CAST(formato_protocolo = 'cra_retencao' AS BOOLEAN) AS flag_retencao_protocolo,
    CAST(nota_original AS VARCHAR) AS nota_original,
    CAST(status_nota AS VARCHAR) AS status_nota,
    CAST(nota AS INTEGER) AS nota,
    CAST(status_nota = 'respondida' AS BOOLEAN) AS respondeu_pesquisa,
    CAST(COALESCE(nota IN (1, 2), FALSE) AS BOOLEAN) AS flag_nota_ruim,
    CAST(tabulacao_original AS VARCHAR) AS tabulacao_original,
    CAST(m_tab_nivel(tabulacao_original, 1) AS VARCHAR) AS tab_nivel1,
    CAST(m_tab_nivel(tabulacao_original, 2) AS VARCHAR) AS tab_nivel2,
    CAST(m_tab_nivel(tabulacao_original, 3) AS VARCHAR) AS tab_nivel3,
    CAST(m_tab_nivel(tabulacao_original, 4) AS VARCHAR) AS tab_nivel4,
    CAST(m_tab_nivel(tabulacao_original, 5) AS VARCHAR) AS tab_nivel5,
    CAST(m_tab_nivel(tabulacao_original, 6) AS VARCHAR) AS tab_nivel6,
    CAST(m_tab_nivel(tabulacao_original, 7) AS VARCHAR) AS tab_nivel7,
    CAST(m_qtd_niveis_tab(tabulacao_original) AS INTEGER) AS qtd_niveis_tab,
    CAST(m_modalidade_tab(tabulacao_original) AS VARCHAR) AS modalidade_tab,
    CAST(eh_assunto_retencao AS BOOLEAN) AS eh_assunto_retencao,
    CAST(m_encaminhamento_retencao(tabulacao_original) AS BOOLEAN) AS flag_encaminhamento_retencao,
    CAST(m_desfecho_retencao(tabulacao_original, eh_assunto_retencao) AS VARCHAR) AS desfecho_retencao
FROM regras
ORDER BY origem_linha;

-- confere se algum registro tem mais niveis de tabulacao do que as 7 colunas criadas
SELECT CASE
    WHEN max(len(string_split(tabulacao_original, '>'))) > 7 THEN error('tabulacao da video chamada com mais de 7 niveis')
END AS niveis_ok
FROM silver_video_chamada;
