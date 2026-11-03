let
    fonte = Parquet.Document(File.Contents(pDataPath & "\fato_navegacao.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"contato_id", type text},
            {"canal", type text},
            {"aluno_hash", type text},
            {"tipo_sequencia", type text},
            {"ordem_passo", Int64.Type},
            {"ponto_navegacao", type text},
            {"eh_token_98_99", type logical},
            {"eh_repeticao_consecutiva", type logical}
        }
    )
in
    tiposDefinidos
