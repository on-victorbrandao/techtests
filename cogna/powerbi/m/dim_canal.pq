let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_canal.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"canal_id", Int64.Type},
            {"canal", type text},
            {"canal_nome", type text},
            {"tipo_atendimento", type text},
            {"possui_agente_humano", type logical},
            {"possui_fila", type logical},
            {"possui_tme", type logical},
            {"possui_perfil_completo", type logical},
            {"taxonomia_motivo", type text},
            {"canal_ordem", Int64.Type}
        }
    )
in
    tiposDefinidos
