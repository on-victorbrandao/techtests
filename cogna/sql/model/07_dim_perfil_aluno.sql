-- dimensao perfil do aluno no momento do contato: sem inferir cadastro entre canais
CREATE OR REPLACE TABLE dim_perfil_aluno AS
WITH perfis_observados AS (
    -- Call Center: perfil cadastral completo
    SELECT DISTINCT
        canal,
        id_type_codigo,
        COALESCE(id_type_rotulo, id_type_rotulo_original, 'Não Informado no Canal') AS id_type_rotulo,
        id_type_status,
        modalidade_codigo,
        COALESCE(modalidade_rotulo, modalidade_rotulo_original, 'Não Informado no Canal') AS modalidade_rotulo,
        COALESCE(modalidade_cadastro_grupo, 'Não Informado no Canal') AS modalidade_grupo,
        modalidade_status,
        categoria_aluno_codigo,
        COALESCE(categoria_aluno_rotulo, categoria_aluno_rotulo_original, 'Não Informado no Canal') AS categoria_aluno_rotulo,
        categoria_aluno_status,
        instituicao_codigo,
        COALESCE(instituicao_rotulo, instituicao_rotulo_original, 'Não Informado no Canal') AS instituicao_rotulo,
        regexp_replace(COALESCE(instituicao_rotulo, instituicao_rotulo_original, 'Não Informado no Canal'), '^[0-9]+\s*-\s*', '') AS instituicao_nome_limpo,
        instituicao_status
    FROM silver_callcenter
    UNION
    -- WhatsApp: perfil cadastral completo
    SELECT DISTINCT
        canal,
        id_type_codigo,
        COALESCE(id_type_rotulo, 'Não Informado no Canal') AS id_type_rotulo,
        id_type_status,
        modalidade_codigo,
        COALESCE(modalidade_rotulo, modalidade_rotulo_original, 'Não Informado no Canal') AS modalidade_rotulo,
        COALESCE(modalidade_cadastro_grupo, 'Não Informado no Canal') AS modalidade_grupo,
        modalidade_status,
        categoria_aluno_codigo,
        COALESCE(categoria_aluno_rotulo, categoria_aluno_rotulo_original, 'Não Informado no Canal') AS categoria_aluno_rotulo,
        categoria_aluno_status,
        instituicao_codigo,
        COALESCE(instituicao_rotulo, instituicao_rotulo_original, 'Não Informado no Canal') AS instituicao_rotulo,
        regexp_replace(COALESCE(instituicao_rotulo, instituicao_rotulo_original, 'Não Informado no Canal'), '^[0-9]+\s*-\s*', '') AS instituicao_nome_limpo,
        instituicao_status
    FROM silver_whatsapp
    UNION
    -- Video Chamada: nao possui colunas de perfil cadastral
    SELECT DISTINCT
        canal,
        CAST(NULL AS INTEGER) AS id_type_codigo,
        'Não Informado no Canal' AS id_type_rotulo,
        'nao_aplicavel' AS id_type_status,
        CAST(NULL AS INTEGER) AS modalidade_codigo,
        'Não Informado no Canal' AS modalidade_rotulo,
        'Não Informado no Canal' AS modalidade_grupo,
        'nao_aplicavel' AS modalidade_status,
        CAST(NULL AS INTEGER) AS categoria_aluno_codigo,
        'Não Informado no Canal' AS categoria_aluno_rotulo,
        'nao_aplicavel' AS categoria_aluno_status,
        CAST(NULL AS INTEGER) AS instituicao_codigo,
        'Não Informado no Canal' AS instituicao_rotulo,
        'Não Informado no Canal' AS instituicao_nome_limpo,
        'nao_aplicavel' AS instituicao_status
    FROM silver_video_chamada
    UNION
    -- Totem: possui apenas instituicao em texto livre (sem modalidade/categoria)
    SELECT DISTINCT
        canal,
        CAST(NULL AS INTEGER) AS id_type_codigo,
        'Não Informado no Canal' AS id_type_rotulo,
        'nao_aplicavel' AS id_type_status,
        CAST(NULL AS INTEGER) AS modalidade_codigo,
        'Não Informado no Canal' AS modalidade_rotulo,
        'Não Informado no Canal' AS modalidade_grupo,
        'nao_aplicavel' AS modalidade_status,
        CAST(NULL AS INTEGER) AS categoria_aluno_codigo,
        'Não Informado no Canal' AS categoria_aluno_rotulo,
        'nao_aplicavel' AS categoria_aluno_status,
        CAST(NULL AS INTEGER) AS instituicao_codigo,
        COALESCE(instituicao_original, 'Não Informado no Canal') AS instituicao_rotulo,
        CASE
            WHEN flag_instituicao_nao_identificada OR instituicao_original IS NULL THEN 'Não Identificado (Totem)'
            ELSE instituicao_original
        END AS instituicao_nome_limpo,
        CASE
            WHEN flag_instituicao_nao_identificada OR instituicao_original IS NULL THEN 'nao_identificado'
            ELSE 'texto_totem'
        END AS instituicao_status
    FROM silver_totem
)
SELECT
    CAST('PF-' || lpad(CAST(ROW_NUMBER() OVER (
        ORDER BY canal,
                 COALESCE(id_type_codigo, 999),
                 COALESCE(modalidade_codigo, 999),
                 COALESCE(categoria_aluno_codigo, 999),
                 COALESCE(instituicao_codigo, 999),
                 instituicao_rotulo
    ) AS VARCHAR), 3, '0') AS VARCHAR) AS perfil_id,
    CAST(canal AS VARCHAR) AS canal_perfil,
    CAST(id_type_codigo AS INTEGER) AS id_type_codigo,
    CAST(id_type_rotulo AS VARCHAR) AS id_type_rotulo,
    CAST(id_type_status AS VARCHAR) AS id_type_status,
    CAST(modalidade_codigo AS INTEGER) AS modalidade_codigo,
    CAST(modalidade_rotulo AS VARCHAR) AS modalidade_rotulo,
    CAST(modalidade_grupo AS VARCHAR) AS modalidade_grupo,
    CAST(modalidade_status AS VARCHAR) AS modalidade_status,
    CAST(categoria_aluno_codigo AS INTEGER) AS categoria_aluno_codigo,
    CAST(categoria_aluno_rotulo AS VARCHAR) AS categoria_aluno_rotulo,
    CAST(categoria_aluno_status AS VARCHAR) AS categoria_aluno_status,
    CAST(instituicao_codigo AS INTEGER) AS instituicao_codigo,
    CAST(instituicao_rotulo AS VARCHAR) AS instituicao_rotulo,
    CAST(instituicao_nome_limpo AS VARCHAR) AS instituicao_nome_limpo,
    CAST(instituicao_status AS VARCHAR) AS instituicao_status
FROM perfis_observados
ORDER BY perfil_id;
