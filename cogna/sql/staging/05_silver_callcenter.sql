-- silver do call center: uma linha de saida para cada linha de raw_cc
CREATE OR REPLACE TABLE silver_callcenter AS
WITH base AS (
    -- textos limpos, campos originais preservados e dominios do dicionario do proprio canal
    SELECT
        'call_center' AS canal,
        r.origem_arquivo,
        r.origem_aba,
        r.origem_linha,
        m_nulo(trim(r.identificador_aluno)) AS aluno_id_original,
        r."date" AS date_original,
        r.calldate AS data_hora_contato,
        TRY_CAST(m_nulo(r.id_type) AS INTEGER) AS id_type_codigo,
        m_nulo(r.id_type_desc) AS id_type_rotulo_original,
        d_id.rotulo_canonico AS id_type_rotulo,
        m_status_dominio(m_nulo(r.id_type), d_id.codigo, d_id.status_dicionario) AS id_type_status,
        TRY_CAST(m_nulo(r.disconnect_type) AS INTEGER) AS disconnect_type_codigo,
        m_nulo(r.disconnect_type_desc) AS disconnect_type_rotulo_original,
        d_dc.rotulo_canonico AS disconnect_type_rotulo,
        m_status_dominio(m_nulo(r.disconnect_type), d_dc.codigo, d_dc.status_dicionario) AS disconnect_type_status,
        m_inteiro_s(r.duration_callcenter) AS duracao_s,
        m_tempo_invalido(r.duration_callcenter) AS flag_tempo_invalido,
        m_nulo(r.dna_soa) AS dna_soa_original,
        m_nulo(r.recepcao_fila) AS recepcao_fila,
        m_nulo(r.fila_atend) AS fila_atend,
        m_nulo(r.agent) AS agente_original,
        m_nulo(r.supervisor) AS supervisor_original,
        m_nulo(r.pesquisa_1) AS nota_original,
        m_nulo(r.protocolo) AS protocolo_original,
        m_nulo(r.tabulacao) AS tabulacao_original,
        TRY_CAST(m_nulo(r.modalidade_nova) AS INTEGER) AS modalidade_codigo,
        m_nulo(r.modalidade_nova_desc) AS modalidade_rotulo_original,
        d_mo.rotulo_canonico AS modalidade_rotulo,
        m_status_dominio(m_nulo(r.modalidade_nova), d_mo.codigo, d_mo.status_dicionario) AS modalidade_status,
        TRY_CAST(m_nulo(r.categoria_aluno) AS INTEGER) AS categoria_aluno_codigo,
        m_nulo(r.categoria_aluno_desc) AS categoria_aluno_rotulo_original,
        d_ca.rotulo_canonico AS categoria_aluno_rotulo,
        m_status_dominio(m_nulo(r.categoria_aluno), d_ca.codigo, d_ca.status_dicionario) AS categoria_aluno_status,
        TRY_CAST(m_nulo(r.instituicao) AS INTEGER) AS instituicao_codigo,
        m_nulo(r.instituicao_desc) AS instituicao_rotulo_original,
        d_in.rotulo_canonico AS instituicao_rotulo,
        m_status_dominio(m_nulo(r.instituicao), d_in.codigo, d_in.status_dicionario) AS instituicao_status
    FROM raw_cc AS r
    LEFT JOIN dom_canonico AS d_id
        ON d_id.canal = 'call_center' AND d_id.campo = 'id_type' AND d_id.codigo = trim(m_nulo(r.id_type))
    LEFT JOIN dom_canonico AS d_dc
        ON d_dc.canal = 'call_center' AND d_dc.campo = 'disconnect_type' AND d_dc.codigo = trim(m_nulo(r.disconnect_type))
    LEFT JOIN dom_canonico AS d_mo
        ON d_mo.canal = 'call_center' AND d_mo.campo = 'modalidade_nova' AND d_mo.codigo = trim(m_nulo(r.modalidade_nova))
    LEFT JOIN dom_canonico AS d_ca
        ON d_ca.canal = 'call_center' AND d_ca.campo = 'categoria_aluno' AND d_ca.codigo = trim(m_nulo(r.categoria_aluno))
    LEFT JOIN dom_canonico AS d_in
        ON d_in.canal = 'call_center' AND d_in.campo = 'instituicao' AND d_in.codigo = trim(m_nulo(r.instituicao))
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
    -- flags e derivacoes de satisfacao, retencao, protocolo, tabulacao e navegacao
    SELECT
        *,
        m_status_nota(nota_original) AS status_nota,
        m_nota(nota_original) AS nota,
        m_formato_protocolo(protocolo_original) AS formato_protocolo,
        m_assunto_retencao(tabulacao_original) AS eh_assunto_retencao,
        COALESCE(contains(m_norm(fila_atend), 'retenc'), FALSE) AS eh_retencao_fila,
        m_modalidade_grupo(COALESCE(modalidade_rotulo, modalidade_rotulo_original)) AS modalidade_cadastro_grupo,
        m_modalidade_tab(tabulacao_original) AS modalidade_tab
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
    CAST(date_original AS DATE) AS date_original,
    CAST(data_hora_contato AS TIMESTAMP) AS data_hora_contato,
    CAST(id_type_codigo AS INTEGER) AS id_type_codigo,
    CAST(id_type_rotulo_original AS VARCHAR) AS id_type_rotulo_original,
    CAST(id_type_rotulo AS VARCHAR) AS id_type_rotulo,
    CAST(id_type_status AS VARCHAR) AS id_type_status,
    CAST(disconnect_type_codigo AS INTEGER) AS disconnect_type_codigo,
    CAST(disconnect_type_rotulo_original AS VARCHAR) AS disconnect_type_rotulo_original,
    CAST(disconnect_type_rotulo AS VARCHAR) AS disconnect_type_rotulo,
    CAST(disconnect_type_status AS VARCHAR) AS disconnect_type_status,
    CAST(duracao_s AS INTEGER) AS duracao_s,
    CAST(COALESCE(duracao_s = 0, FALSE) AS BOOLEAN) AS flag_duracao_zero,
    CAST(COALESCE(duracao_s < dur_q1 - 1.5 * (dur_q3 - dur_q1)
                  OR duracao_s > dur_q3 + 1.5 * (dur_q3 - dur_q1), FALSE) AS BOOLEAN) AS flag_outlier_duracao,
    CAST(flag_tempo_invalido AS BOOLEAN) AS flag_tempo_invalido,
    CAST(dna_soa_original AS VARCHAR) AS dna_soa_original,
    CAST(m_qtd_passos(dna_soa_original) AS INTEGER) AS qtd_passos_original,
    CAST(m_sem_repeticao(dna_soa_original) AS VARCHAR) AS dna_soa_sem_repeticao_consecutiva,
    CAST(recepcao_fila AS VARCHAR) AS recepcao_fila,
    CAST(fila_atend AS VARCHAR) AS fila_atend,
    CAST(recepcao_fila IS DISTINCT FROM fila_atend AS BOOLEAN) AS flag_filas_divergentes,
    CAST(eh_retencao_fila AS BOOLEAN) AS eh_retencao_fila,
    CAST(eh_assunto_retencao AS BOOLEAN) AS eh_assunto_retencao,
    CAST(m_encaminhamento_retencao(tabulacao_original) AS BOOLEAN) AS flag_encaminhamento_retencao,
    CAST(formato_protocolo = 'cra_retencao' AS BOOLEAN) AS flag_retencao_protocolo,
    CAST(m_desfecho_retencao(tabulacao_original, eh_assunto_retencao) AS VARCHAR) AS desfecho_retencao,
    CAST(agente_original AS VARCHAR) AS agente_original,
    CAST(supervisor_original AS VARCHAR) AS supervisor_original,
    CAST(nota_original AS VARCHAR) AS nota_original,
    CAST(status_nota AS VARCHAR) AS status_nota,
    CAST(nota AS INTEGER) AS nota,
    CAST(status_nota = 'respondida' AS BOOLEAN) AS respondeu_pesquisa,
    CAST(COALESCE(nota IN (1, 2), FALSE) AS BOOLEAN) AS flag_nota_ruim,
    CAST(protocolo_original AS VARCHAR) AS protocolo_original,
    CAST(formato_protocolo AS VARCHAR) AS formato_protocolo,
    CAST(formato_protocolo = 'cs' AS BOOLEAN) AS protocolo_padrao_cs,
    CAST(tabulacao_original AS VARCHAR) AS tabulacao_original,
    CAST(m_tab_nivel(tabulacao_original, 1) AS VARCHAR) AS tab_nivel1,
    CAST(m_tab_nivel(tabulacao_original, 2) AS VARCHAR) AS tab_nivel2,
    CAST(m_tab_nivel(tabulacao_original, 3) AS VARCHAR) AS tab_nivel3,
    CAST(m_tab_nivel(tabulacao_original, 4) AS VARCHAR) AS tab_nivel4,
    CAST(m_tab_nivel(tabulacao_original, 5) AS VARCHAR) AS tab_nivel5,
    CAST(m_tab_nivel(tabulacao_original, 6) AS VARCHAR) AS tab_nivel6,
    CAST(m_tab_nivel(tabulacao_original, 7) AS VARCHAR) AS tab_nivel7,
    CAST(m_qtd_niveis_tab(tabulacao_original) AS INTEGER) AS qtd_niveis_tab,
    CAST(modalidade_tab AS VARCHAR) AS modalidade_tab,
    CAST(modalidade_codigo AS INTEGER) AS modalidade_codigo,
    CAST(modalidade_rotulo_original AS VARCHAR) AS modalidade_rotulo_original,
    CAST(modalidade_rotulo AS VARCHAR) AS modalidade_rotulo,
    CAST(modalidade_status AS VARCHAR) AS modalidade_status,
    CAST(modalidade_cadastro_grupo AS VARCHAR) AS modalidade_cadastro_grupo,
    CAST(COALESCE(modalidade_tab <> modalidade_cadastro_grupo, FALSE) AS BOOLEAN) AS flag_divergencia_modalidade,
    CAST(categoria_aluno_codigo AS INTEGER) AS categoria_aluno_codigo,
    CAST(categoria_aluno_rotulo_original AS VARCHAR) AS categoria_aluno_rotulo_original,
    CAST(categoria_aluno_rotulo AS VARCHAR) AS categoria_aluno_rotulo,
    CAST(categoria_aluno_status AS VARCHAR) AS categoria_aluno_status,
    CAST(instituicao_codigo AS INTEGER) AS instituicao_codigo,
    CAST(instituicao_rotulo_original AS VARCHAR) AS instituicao_rotulo_original,
    CAST(instituicao_rotulo AS VARCHAR) AS instituicao_rotulo,
    CAST(instituicao_status AS VARCHAR) AS instituicao_status,
    CAST(list_has_any([id_type_status, disconnect_type_status, modalidade_status,
                       categoria_aluno_status, instituicao_status],
                      ['sem_dicionario', 'conflito_dicionario', 'rotulo_diverge_codigo']) AS BOOLEAN) AS flag_dominio_inconsistente
FROM regras
ORDER BY origem_linha;

-- confere se algum registro tem mais niveis de tabulacao do que as 7 colunas criadas
SELECT CASE
    WHEN max(len(string_split(tabulacao_original, '>'))) > 7 THEN error('tabulacao do call center com mais de 7 niveis')
END AS niveis_ok
FROM silver_callcenter;
