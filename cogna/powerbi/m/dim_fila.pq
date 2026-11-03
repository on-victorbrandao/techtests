let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_fila.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"fila_id", type text},
            {"recepcao_fila", type text},
            {"fila_atend", type text},
            {"flag_filas_divergentes", type logical},
            {"eh_retencao_fila", type logical},
            {"eh_fila_cra_retencao_exata", type logical},
            {"grupo_fila", type text}
        }
    )
in
    tiposDefinidos
