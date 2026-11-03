let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_perfil_aluno.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"perfil_id", type text},
            {"canal_perfil", type text},
            {"id_type_codigo", Int64.Type},
            {"id_type_rotulo", type text},
            {"id_type_status", type text},
            {"modalidade_codigo", Int64.Type},
            {"modalidade_rotulo", type text},
            {"modalidade_grupo", type text},
            {"modalidade_status", type text},
            {"categoria_aluno_codigo", Int64.Type},
            {"categoria_aluno_rotulo", type text},
            {"categoria_aluno_status", type text},
            {"instituicao_codigo", Int64.Type},
            {"instituicao_rotulo", type text},
            {"instituicao_nome_limpo", type text},
            {"instituicao_status", type text}
        }
    )
in
    tiposDefinidos
