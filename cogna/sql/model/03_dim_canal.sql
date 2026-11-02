-- dimensao canal: os 4 canais de atendimento do ecossistema
CREATE OR REPLACE TABLE dim_canal AS
SELECT
    CAST(canal_id AS INTEGER) AS canal_id,
    CAST(canal AS VARCHAR) AS canal,
    CAST(canal_nome AS VARCHAR) AS canal_nome,
    CAST(tipo_atendimento AS VARCHAR) AS tipo_atendimento,
    CAST(possui_agente_humano AS BOOLEAN) AS possui_agente_humano,
    CAST(possui_fila AS BOOLEAN) AS possui_fila,
    CAST(possui_tme AS BOOLEAN) AS possui_tme,
    CAST(possui_perfil_completo AS BOOLEAN) AS possui_perfil_completo,
    CAST(taxonomia_motivo AS VARCHAR) AS taxonomia_motivo,
    CAST(canal_ordem AS INTEGER) AS canal_ordem
FROM (
    VALUES
        (1, 'call_center', 'Call Center', 'Humano (Voz + URA)', TRUE, TRUE, FALSE, TRUE, 'tabulacao', 1),
        (2, 'whatsapp', 'WhatsApp', 'Humano + Bot (Texto)', TRUE, FALSE, TRUE, TRUE, 'tabulacao', 2),
        (3, 'video_chamada', 'Vídeo Chamada', 'Humano (Vídeo)', TRUE, FALSE, TRUE, FALSE, 'tabulacao', 3),
        (4, 'totem', 'Totem', 'Autoatendimento Presencial', FALSE, FALSE, FALSE, FALSE, 'mdc', 4)
) AS t(
    canal_id,
    canal,
    canal_nome,
    tipo_atendimento,
    possui_agente_humano,
    possui_fila,
    possui_tme,
    possui_perfil_completo,
    taxonomia_motivo,
    canal_ordem
)
ORDER BY canal_id;
