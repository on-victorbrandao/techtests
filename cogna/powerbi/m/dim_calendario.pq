let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_calendario.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"data", type date},
            {"ano_mes_num", type text},
            {"ano_mes_ordem", Int64.Type},
            {"ano", Int64.Type},
            {"mes", Int64.Type},
            {"dia", Int64.Type},
            {"dia_semana_num", Int64.Type},
            {"dia_semana_nome", type text},
            {"mes_nome", type text},
            {"mes_ano", type text},
            {"semana_ano", Int64.Type},
            {"trimestre", type text},
            {"tipo_dia", type text},
            {"dia_util", Int64.Type},
            {"nome_feriado", type text}
        }
    )
in
    tiposDefinidos
