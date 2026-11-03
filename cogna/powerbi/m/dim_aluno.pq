let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_aluno.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"aluno_hash", type text},
            {"aluno_codigo", type text},
            {"total_contatos", Int64.Type},
            {"qtd_canais_distintos", Int64.Type},
            {"qtd_contatos_cc", Int64.Type},
            {"qtd_contatos_wa", Int64.Type},
            {"qtd_contatos_video", Int64.Type},
            {"qtd_contatos_totem", Int64.Type},
            {"primeiro_contato_em", type datetime},
            {"ultimo_contato_em", type datetime}
        }
    )
in
    tiposDefinidos
