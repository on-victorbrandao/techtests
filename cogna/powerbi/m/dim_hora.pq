let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_hora.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"hora_inteira", Int64.Type},
            {"hora_rotulo", type text},
            {"faixa_horaria", type text},
            {"turno", type text},
            {"turno_ordem", Int64.Type},
            {"horario_comercial_padrao", type logical}
        }
    )
in
    tiposDefinidos
