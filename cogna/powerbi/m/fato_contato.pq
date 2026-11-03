let
    fonte = Parquet.Document(File.Contents(pDataPath & "\fato_contato.parquet")),

    tiposDefinidos = Table.TransformColumnTypes(
        fonte,
        {
            {"contato_id", type text},
            {"aluno_hash", type text},
            {"canal_id", Int64.Type},
            {"canal", type text},
            {"data_contato", type date},
            {"hora_inteira", Int64.Type},
            {"agente_id", type text},
            {"fila_id", type text},
            {"perfil_id", type text},
            {"motivo_id", type text},
            {"data_hora_contato", type datetime},
            {"duracao_s", Int64.Type},
            {"tme_s", Int64.Type},
            {"nota", Int64.Type},
            {"status_nota", type text},
            {"respondeu_pesquisa", type logical},
            {"flag_nota_ruim", type logical},
            {"flag_duracao_zero", type logical},
            {"flag_outlier_duracao", type logical},
            {"flag_outlier_tme", type logical},
            {"flag_tme_maior_duracao", type logical},
            {"recepcao_fila", type text},
            {"fila_atend", type text},
            {"flag_filas_divergentes", type logical},
            {"eh_retencao_fila", type logical},
            {"eh_assunto_retencao", type logical},
            {"flag_encaminhamento_retencao", type logical},
            {"flag_retencao_protocolo", type logical},
            {"desfecho_retencao", type text},
            {"formato_protocolo", type text},
            {"protocolo_padrao_cs", type logical},
            {"qtd_niveis_tab", Int64.Type},
            {"modalidade_tab", type text},
            {"flag_divergencia_modalidade", type logical},
            {"qtd_passos_original", Int64.Type},
            {"flag_dominio_inconsistente", type logical},
            {"origem_aba", type text},
            {"origem_linha", Int64.Type}
        }
    )
in
    tiposDefinidos
