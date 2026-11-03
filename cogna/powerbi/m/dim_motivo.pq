let
    fonte = Parquet.Document(File.Contents(pDataPath & "\dim_motivo.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"motivo_id", type text},
            {"taxonomia_motivo", type text},
            {"motivo_principal", type text},
            {"macro_tema", type text},
            {"tabulacao_original", type text},
            {"mdc_original", type text},
            {"tab_nivel1", type text},
            {"tab_nivel2", type text},
            {"tab_nivel3", type text},
            {"tab_nivel4", type text},
            {"tab_nivel5", type text},
            {"tab_nivel6", type text},
            {"tab_nivel7", type text},
            {"qtd_niveis_tab", Int64.Type},
            {"modalidade_tab", type text},
            {"eh_assunto_retencao", type logical},
            {"flag_encaminhamento_retencao", type logical},
            {"desfecho_retencao", type text}
        }
    )
in
    tiposDefinidos
