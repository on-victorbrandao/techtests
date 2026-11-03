let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_agente.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"agente_id", type text},
            {"agente_rotulo", type text},
            {"agente_hash", type text},
            {"canal_agente", type text},
            {"eh_agente_humano", type logical},
            {"supervisor_id", type text},
            {"supervisor_rotulo", type text},
            {"supervisor_hash", type text}
        }
    )
in
    tiposDefinidos
