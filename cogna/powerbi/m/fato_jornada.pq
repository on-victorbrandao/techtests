let
    fonte = Parquet.Document(File.Contents(pDataPath & "\fato_jornada.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"contato_id", type text},
            {"aluno_hash", type text},
            {"canal", type text},
            {"data_contato", type date},
            {"data_hora_contato", type datetime},
            {"ordem_contato_aluno", Int64.Type},
            {"total_contatos_aluno", Int64.Type},
            {"contato_id_anterior", type text},
            {"canal_anterior", type text},
            {"data_hora_anterior", type datetime},
            {"agente_id_anterior", type text},
            {"segundos_desde_anterior", Int64.Type},
            {"minutos_desde_anterior", type number},
            {"fim_estimado_anterior", type datetime},
            {"flag_sobreposicao_estimada", type text},
            {"contato_id_proximo", type text},
            {"canal_proximo", type text},
            {"data_hora_proximo", type datetime},
            {"segundos_ate_proximo", Int64.Type},
            {"flag_recontato_mesmo_dia", type logical},
            {"flag_recontato_mesmo_dia_mesmo_canal", type logical},
            {"flag_recontato_mesmo_dia_canal_com_agente", type logical},
            {"agente_id_atribuido_recontato", type text},
            {"flag_recontato_intracanal_mesmo_dia", type logical},
            {"agente_id_atribuido_recontato_intracanal", type text},
            {"flag_teve_wa_posterior", type logical},
            {"flag_teve_retencao_fila_posterior", type logical},
            {"flag_teve_retencao_assunto_posterior", type logical}
        }
    )
in
    tiposDefinidos
