-- dimensao motivo: preserva a distincao de taxonomia entre tabulacao (CC, WA, Video) e mdc (Totem)
CREATE OR REPLACE TABLE dim_motivo AS
WITH motivos_tab AS (
    SELECT DISTINCT
        'tabulacao' AS taxonomia_motivo,
        tabulacao_original,
        CAST(NULL AS VARCHAR) AS mdc_original,
        tab_nivel1,
        tab_nivel2,
        tab_nivel3,
        tab_nivel4,
        tab_nivel5,
        tab_nivel6,
        tab_nivel7,
        qtd_niveis_tab,
        modalidade_tab,
        eh_assunto_retencao,
        flag_encaminhamento_retencao,
        desfecho_retencao
    FROM (
        SELECT
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, tab_nivel4,
            tab_nivel5, tab_nivel6, tab_nivel7, qtd_niveis_tab, modalidade_tab,
            eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao
        FROM silver_callcenter
        UNION ALL
        SELECT
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, tab_nivel4,
            tab_nivel5, tab_nivel6, tab_nivel7, qtd_niveis_tab, modalidade_tab,
            eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao
        FROM silver_whatsapp
        UNION ALL
        SELECT
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, tab_nivel4,
            tab_nivel5, tab_nivel6, tab_nivel7, qtd_niveis_tab, modalidade_tab,
            eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao
        FROM silver_video_chamada
    )
),
motivos_mdc AS (
    SELECT DISTINCT
        'mdc' AS taxonomia_motivo,
        CAST(NULL AS VARCHAR) AS tabulacao_original,
        mdc_original,
        CAST(NULL AS VARCHAR) AS tab_nivel1,
        CAST(NULL AS VARCHAR) AS tab_nivel2,
        CAST(NULL AS VARCHAR) AS tab_nivel3,
        CAST(NULL AS VARCHAR) AS tab_nivel4,
        CAST(NULL AS VARCHAR) AS tab_nivel5,
        CAST(NULL AS VARCHAR) AS tab_nivel6,
        CAST(NULL AS VARCHAR) AS tab_nivel7,
        0 AS qtd_niveis_tab,
        CAST(NULL AS VARCHAR) AS modalidade_tab,
        FALSE AS eh_assunto_retencao,
        FALSE AS flag_encaminhamento_retencao,
        CAST(NULL AS VARCHAR) AS desfecho_retencao
    FROM silver_totem
),
unificados AS (
    SELECT * FROM motivos_tab
    UNION ALL
    SELECT * FROM motivos_mdc
),
classificados AS (
    SELECT
        *,
        CASE
            WHEN taxonomia_motivo = 'mdc' THEN COALESCE(mdc_original, 'MDC Não Informado')
            WHEN tabulacao_original IS NULL THEN 'Sem Tabulação (Nulo)'
            ELSE COALESCE(tab_nivel3, tab_nivel2, tab_nivel1, tabulacao_original)
        END AS motivo_principal,
        CASE
            WHEN taxonomia_motivo = 'mdc' THEN
                CASE
                    WHEN mdc_original IN ('TermoQuitacaoDebitos') THEN 'Financeiro / Boletos / Negociação'
                    WHEN mdc_original IN ('MATRIZ_CURRICULAR', 'HISTORICO_ESCOLAR') THEN 'Acadêmico / Documentos'
                    WHEN mdc_original IN ('JA_SOU_ALUNO', 'EX-ALUNO', 'QUERO_SER_ALUNO', 'INFO_EAD', 'OUTROS_ASSUNTOS') THEN 'Menu Inicial / Triagem Autoatendimento (MDC)'
                    ELSE 'Não Identificado / Sem Tabulação'
                END
            WHEN tabulacao_original IS NULL THEN 'Não Identificado / Sem Tabulação'
            WHEN eh_assunto_retencao THEN 'Retenção (Cancelamento / Trancamento / Manutenção)'
            WHEN contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'boleto')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'financeir')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'bolsa')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'fies')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'negociac')
                 THEN 'Financeiro / Boletos / Bolsas'
            WHEN contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'academico')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'curricular')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'document')
                 THEN 'Acadêmico / Secretaria'
            WHEN contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'aprendizagem')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'apredinzagem')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'ava')
                 OR contains(m_norm(COALESCE(tab_nivel2, '') || ' ' || COALESCE(tab_nivel3, '')), 'virtual')
                 THEN 'Portal / AVA / Acesso'
            ELSE 'Outros Assuntos / Triagem'
        END AS macro_tema
    FROM unificados
)
SELECT
    CAST('MOT-' || lpad(CAST(ROW_NUMBER() OVER (
        ORDER BY taxonomia_motivo,
                 COALESCE(tabulacao_original, ''),
                 COALESCE(mdc_original, '')
    ) AS VARCHAR), 3, '0') AS VARCHAR) AS motivo_id,
    CAST(taxonomia_motivo AS VARCHAR) AS taxonomia_motivo,
    CAST(motivo_principal AS VARCHAR) AS motivo_principal,
    CAST(macro_tema AS VARCHAR) AS macro_tema,
    CAST(tabulacao_original AS VARCHAR) AS tabulacao_original,
    CAST(mdc_original AS VARCHAR) AS mdc_original,
    CAST(tab_nivel1 AS VARCHAR) AS tab_nivel1,
    CAST(tab_nivel2 AS VARCHAR) AS tab_nivel2,
    CAST(tab_nivel3 AS VARCHAR) AS tab_nivel3,
    CAST(tab_nivel4 AS VARCHAR) AS tab_nivel4,
    CAST(tab_nivel5 AS VARCHAR) AS tab_nivel5,
    CAST(tab_nivel6 AS VARCHAR) AS tab_nivel6,
    CAST(tab_nivel7 AS VARCHAR) AS tab_nivel7,
    CAST(qtd_niveis_tab AS INTEGER) AS qtd_niveis_tab,
    CAST(modalidade_tab AS VARCHAR) AS modalidade_tab,
    CAST(eh_assunto_retencao AS BOOLEAN) AS eh_assunto_retencao,
    CAST(flag_encaminhamento_retencao AS BOOLEAN) AS flag_encaminhamento_retencao,
    CAST(desfecho_retencao AS VARCHAR) AS desfecho_retencao
FROM classificados
ORDER BY motivo_id;
