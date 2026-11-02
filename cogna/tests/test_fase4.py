"""Testes do modelo estrela Gold e das consultas analiticas (Q1-Q9) em SQL (DuckDB).

Os testes sinteticos injetam relacoes silver_* falsas e rodam o mesmo SQL da Gold.
Os testes de integracao usam os Parquets reais da Silver e validam reconciliacao e idempotencia.
"""

import datetime as dt
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from cogna_etl.gold import (
    CHAVES_PK,
    SQL_ANALYTICS,
    SQL_ANALYTICS_DIR,
    ValidacaoGoldError,
    executar_analytics,
    rodar_modelo_gold,
    run_gold,
    validar_modelo_gold,
)

# esquemas minimos compativeis com os Parquets da Silver para testes sinteticos
SCHEMA_SILVER = {
    "silver_callcenter": """
        contato_id VARCHAR, canal VARCHAR, origem_arquivo VARCHAR, origem_aba VARCHAR,
        origem_linha INTEGER, aluno_id_original VARCHAR, aluno_hash VARCHAR,
        date_original DATE, data_hora_contato TIMESTAMP,
        id_type_codigo INTEGER, id_type_rotulo_original VARCHAR, id_type_rotulo VARCHAR, id_type_status VARCHAR,
        disconnect_type_codigo INTEGER, disconnect_type_rotulo_original VARCHAR, disconnect_type_rotulo VARCHAR, disconnect_type_status VARCHAR,
        duracao_s INTEGER, flag_duracao_zero BOOLEAN, flag_outlier_duracao BOOLEAN, flag_tempo_invalido BOOLEAN,
        dna_soa_original VARCHAR, qtd_passos_original INTEGER, dna_soa_sem_repeticao_consecutiva VARCHAR,
        recepcao_fila VARCHAR, fila_atend VARCHAR, flag_filas_divergentes BOOLEAN,
        eh_retencao_fila BOOLEAN, eh_assunto_retencao BOOLEAN, flag_encaminhamento_retencao BOOLEAN,
        flag_retencao_protocolo BOOLEAN, desfecho_retencao VARCHAR,
        agente_original VARCHAR, supervisor_original VARCHAR,
        nota_original VARCHAR, status_nota VARCHAR, nota INTEGER, respondeu_pesquisa BOOLEAN, flag_nota_ruim BOOLEAN,
        protocolo_original VARCHAR, formato_protocolo VARCHAR, protocolo_padrao_cs BOOLEAN,
        tabulacao_original VARCHAR, tab_nivel1 VARCHAR, tab_nivel2 VARCHAR, tab_nivel3 VARCHAR,
        tab_nivel4 VARCHAR, tab_nivel5 VARCHAR, tab_nivel6 VARCHAR, tab_nivel7 VARCHAR,
        qtd_niveis_tab INTEGER, modalidade_tab VARCHAR,
        modalidade_codigo INTEGER, modalidade_rotulo_original VARCHAR, modalidade_rotulo VARCHAR, modalidade_status VARCHAR,
        modalidade_cadastro_grupo VARCHAR, flag_divergencia_modalidade BOOLEAN,
        categoria_aluno_codigo INTEGER, categoria_aluno_rotulo_original VARCHAR, categoria_aluno_rotulo VARCHAR, categoria_aluno_status VARCHAR,
        instituicao_codigo INTEGER, instituicao_rotulo_original VARCHAR, instituicao_rotulo VARCHAR, instituicao_status VARCHAR,
        flag_dominio_inconsistente BOOLEAN
    """,
    "silver_whatsapp": """
        contato_id VARCHAR, canal VARCHAR, origem_arquivo VARCHAR, origem_aba VARCHAR,
        origem_linha INTEGER, aluno_id_original VARCHAR, aluno_hash VARCHAR,
        data_hora_contato TIMESTAMP,
        id_type_codigo INTEGER, id_type_rotulo VARCHAR, id_type_status VARCHAR,
        disconnect_type_codigo INTEGER, disconnect_type_rotulo_original VARCHAR, disconnect_type_rotulo VARCHAR, disconnect_type_status VARCHAR,
        after_hour_codigo INTEGER, after_hour_rotulo VARCHAR, after_hour_status VARCHAR,
        duracao_s INTEGER, tme_s INTEGER, flag_duracao_zero BOOLEAN,
        flag_outlier_duracao BOOLEAN, flag_outlier_tme BOOLEAN, flag_tme_maior_duracao BOOLEAN, flag_tempo_invalido BOOLEAN,
        dna_soa_original VARCHAR, qtd_passos_original INTEGER, codigo_unidade_original VARCHAR,
        agente_original VARCHAR, nota_original VARCHAR, status_nota VARCHAR, nota INTEGER,
        respondeu_pesquisa BOOLEAN, flag_nota_ruim BOOLEAN,
        tabulacao_original VARCHAR, tab_nivel1 VARCHAR, tab_nivel2 VARCHAR, tab_nivel3 VARCHAR,
        tab_nivel4 VARCHAR, tab_nivel5 VARCHAR, tab_nivel6 VARCHAR, tab_nivel7 VARCHAR,
        qtd_niveis_tab INTEGER, modalidade_tab VARCHAR,
        eh_assunto_retencao BOOLEAN, flag_encaminhamento_retencao BOOLEAN, desfecho_retencao VARCHAR,
        modalidade_codigo INTEGER, modalidade_rotulo_original VARCHAR, modalidade_rotulo VARCHAR, modalidade_status VARCHAR,
        modalidade_cadastro_grupo VARCHAR, flag_divergencia_modalidade BOOLEAN,
        categoria_aluno_codigo INTEGER, categoria_aluno_rotulo_original VARCHAR, categoria_aluno_rotulo VARCHAR, categoria_aluno_status VARCHAR,
        instituicao_codigo INTEGER, instituicao_rotulo_original VARCHAR, instituicao_rotulo VARCHAR, instituicao_status VARCHAR,
        flag_dominio_inconsistente BOOLEAN
    """,
    "silver_video_chamada": """
        contato_id VARCHAR, canal VARCHAR, origem_arquivo VARCHAR, origem_aba VARCHAR,
        origem_linha INTEGER, aluno_id_original VARCHAR, aluno_hash VARCHAR,
        calldate_original VARCHAR, calldate_sem_ms_original VARCHAR,
        data_hora_contato TIMESTAMP, flag_calldate_sem_ms_diverge BOOLEAN,
        duracao_s INTEGER, tme_s INTEGER, flag_duracao_zero BOOLEAN,
        flag_outlier_duracao BOOLEAN, flag_outlier_tme BOOLEAN, flag_tme_maior_duracao BOOLEAN, flag_tempo_invalido BOOLEAN,
        agente_original VARCHAR, protocolo_original VARCHAR, formato_protocolo VARCHAR,
        protocolo_padrao_cs BOOLEAN, flag_retencao_protocolo BOOLEAN,
        nota_original VARCHAR, status_nota VARCHAR, nota INTEGER, respondeu_pesquisa BOOLEAN, flag_nota_ruim BOOLEAN,
        tabulacao_original VARCHAR, tab_nivel1 VARCHAR, tab_nivel2 VARCHAR, tab_nivel3 VARCHAR,
        tab_nivel4 VARCHAR, tab_nivel5 VARCHAR, tab_nivel6 VARCHAR, tab_nivel7 VARCHAR,
        qtd_niveis_tab INTEGER, modalidade_tab VARCHAR,
        eh_assunto_retencao BOOLEAN, flag_encaminhamento_retencao BOOLEAN, desfecho_retencao VARCHAR
    """,
    "silver_totem": """
        contato_id VARCHAR, canal VARCHAR, origem_arquivo VARCHAR, origem_aba VARCHAR,
        origem_linha INTEGER, aluno_id_original VARCHAR, aluno_hash VARCHAR,
        data_hora_contato TIMESTAMP, duracao_s INTEGER, flag_duracao_zero BOOLEAN,
        flag_outlier_duracao BOOLEAN, flag_tempo_invalido BOOLEAN,
        instituicao_original VARCHAR, flag_instituicao_nao_identificada BOOLEAN,
        mdc_original VARCHAR, flag_mdc_nao_identificado BOOLEAN,
        navegacao_original VARCHAR, qtd_passos_original INTEGER,
        nota_original VARCHAR, status_nota VARCHAR, nota INTEGER, respondeu_pesquisa BOOLEAN, flag_nota_ruim BOOLEAN
    """,
}


def criar_silver_sintetica(con: duckdb.DuckDBPyConnection) -> None:
    """Cria tabelas silver_* sinteticas em memoria para testar regras da Gold."""
    for nome, ddl in SCHEMA_SILVER.items():
        con.execute(f"CREATE OR REPLACE TABLE {nome} ({ddl})")
    # insere 2 contatos no CC (05/09 sabado e 07/09 feriado, mesmo dia com 2 contatos do ALUNO_A)
    con.execute("""
        INSERT INTO silver_callcenter (
            contato_id, canal, origem_arquivo, origem_aba, origem_linha,
            aluno_id_original, aluno_hash, date_original, data_hora_contato,
            id_type_codigo, id_type_rotulo, id_type_status,
            disconnect_type_codigo, disconnect_type_rotulo, disconnect_type_status,
            duracao_s, flag_duracao_zero, flag_outlier_duracao, flag_tempo_invalido,
            dna_soa_original, qtd_passos_original, dna_soa_sem_repeticao_consecutiva,
            recepcao_fila, fila_atend, flag_filas_divergentes,
            eh_retencao_fila, eh_assunto_retencao, flag_encaminhamento_retencao,
            flag_retencao_protocolo, desfecho_retencao,
            agente_original, supervisor_original,
            nota_original, status_nota, nota, respondeu_pesquisa, flag_nota_ruim,
            protocolo_original, formato_protocolo, protocolo_padrao_cs,
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, qtd_niveis_tab, modalidade_tab,
            modalidade_codigo, modalidade_rotulo, modalidade_status, modalidade_cadastro_grupo, flag_divergencia_modalidade,
            categoria_aluno_codigo, categoria_aluno_rotulo, categoria_aluno_status,
            instituicao_codigo, instituicao_rotulo, instituicao_status, flag_dominio_inconsistente
        ) VALUES
        (
            'cc_01', 'call_center', 'arq.xlsx', 'Analitico call center', 2,
            'CPF_SECRETO_1', 'hash_aluno_a', DATE '2026-09-05', TIMESTAMP '2026-09-05 10:00:00',
            1, '1 - Cliente identificado por CPF', 'ok',
            1, '1 = SIDEA', 'ok',
            300, FALSE, FALSE, FALSE,
            'Passo1|Passo1|Passo1|99', 4, 'Passo1|99',
            'cra_retencao', 'cra_retencao', FALSE,
            TRUE, TRUE, FALSE,
            FALSE, 'pedido_cancelamento',
            'Nome Agente Secreto CC 1', 'Supervisor Secreto 1',
            '2', 'respondida', 2, TRUE, TRUE,
            'CS00000001', 'cs', TRUE,
            '1. Graduação EAD > Registro de atendimento - EAD > Atendimento de Retenção > Pedido de Cancelamento',
            '1. Graduação EAD', 'Registro de atendimento - EAD', 'Atendimento de Retenção', 4, 'EAD',
            5, '5 - EAD Campus', 'ok', 'EAD', FALSE,
            1, '1 - Calouro', 'ok',
            2, '2 - Anhanguera', 'ok', FALSE
        ),
        (
            'cc_02', 'call_center', 'arq.xlsx', 'Analitico call center', 3,
            'CPF_SECRETO_1', 'hash_aluno_a', DATE '2026-09-05', TIMESTAMP '2026-09-05 11:00:00',
            1, '1 - Cliente identificado por CPF', 'ok',
            1, '1 = SIDEA', 'ok',
            200, FALSE, FALSE, FALSE,
            'Passo1|Passo1|Passo1', 3, 'Passo1',
            'cra_ath_pool', 'cra_ath_pool', FALSE,
            FALSE, FALSE, FALSE,
            FALSE, NULL,
            'Nome Agente Secreto CC 2', 'Supervisor Secreto 1',
            '4', 'respondida', 4, TRUE, FALSE,
            'CS00000002', 'cs', TRUE,
            '1. Graduação EAD > Registro de atendimento - EAD > Acadêmico',
            '1. Graduação EAD', 'Registro de atendimento - EAD', 'Acadêmico', 3, 'EAD',
            5, '5 - EAD Campus', 'ok', 'EAD', FALSE,
            1, '1 - Calouro', 'ok',
            2, '2 - Anhanguera', 'ok', FALSE
        )
    """)
    # insere 1 contato no WhatsApp no mesmo dia 05/09 (12:00) para hash_aluno_a
    con.execute("""
        INSERT INTO silver_whatsapp (
            contato_id, canal, origem_arquivo, origem_aba, origem_linha,
            aluno_id_original, aluno_hash, data_hora_contato,
            id_type_codigo, id_type_rotulo, id_type_status,
            disconnect_type_codigo, disconnect_type_rotulo, disconnect_type_status,
            after_hour_codigo, after_hour_rotulo, after_hour_status,
            duracao_s, tme_s, flag_duracao_zero, flag_outlier_duracao, flag_outlier_tme,
            flag_tme_maior_duracao, flag_tempo_invalido,
            dna_soa_original, qtd_passos_original, codigo_unidade_original,
            agente_original, nota_original, status_nota, nota, respondeu_pesquisa, flag_nota_ruim,
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, qtd_niveis_tab, modalidade_tab,
            eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao,
            modalidade_codigo, modalidade_rotulo, modalidade_status, modalidade_cadastro_grupo, flag_divergencia_modalidade,
            categoria_aluno_codigo, categoria_aluno_rotulo, categoria_aluno_status,
            instituicao_codigo, instituicao_rotulo, instituicao_status, flag_dominio_inconsistente
        ) VALUES (
            'wa_01', 'whatsapp', 'arq.xlsx', 'Analitico Whatsapp', 2,
            'CPF_SECRETO_1', 'hash_aluno_a', TIMESTAMP '2026-09-05 12:00:00',
            1, '1 - Cliente identificado por CPF ou CNPJ, etc', 'ok',
            3, '3 - ATH', 'ok',
            0, NULL, 'conflito_dicionario',
            600, 30, FALSE, FALSE, FALSE, FALSE, FALSE,
            'Identificacao|0', 2, '10',
            'Nome Agente Secreto WA 1', '1', 'respondida', 1, TRUE, TRUE,
            '1. Graduação Presencial > Registro de atendimento - Presencial > Acadêmico',
            '1. Graduação Presencial', 'Registro de atendimento - Presencial', 'Acadêmico', 3, 'Presencial',
            FALSE, FALSE, NULL,
            1, '1 - Presencial Campus', 'ok', 'Presencial', FALSE,
            1, '1 - Calouro', 'ok',
            2, '2 - Anhanguera', 'ok', TRUE
        )
    """)
    # insere 1 contato no Video no feriado 07/09 (segunda-feira) e 1 no Totem em 08/09 (terca-feira, dia util)
    con.execute("""
        INSERT INTO silver_video_chamada (
            contato_id, canal, origem_arquivo, origem_aba, origem_linha,
            aluno_id_original, aluno_hash, calldate_original, calldate_sem_ms_original,
            data_hora_contato, flag_calldate_sem_ms_diverge,
            duracao_s, tme_s, flag_duracao_zero, flag_outlier_duracao, flag_outlier_tme,
            flag_tme_maior_duracao, flag_tempo_invalido,
            agente_original, protocolo_original, formato_protocolo, protocolo_padrao_cs, flag_retencao_protocolo,
            nota_original, status_nota, nota, respondeu_pesquisa, flag_nota_ruim,
            tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, qtd_niveis_tab, modalidade_tab,
            eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao
        ) VALUES (
            'vid_01', 'video_chamada', 'arq.xlsx', 'Analitico_video_chamada', 2,
            'CPF_SECRETO_1', 'hash_aluno_a', '07/09/2026 14:00:00.500', '07/09/2026 14:00:00',
            TIMESTAMP '2026-09-07 14:00:00.500', FALSE,
            400, 10, FALSE, FALSE, FALSE, FALSE, FALSE,
            'Nome Agente Secreto Video 1', 'CS00000003', 'cs', TRUE, FALSE,
            '5', 'respondida', 5, TRUE, FALSE,
            '1. Graduação EAD > Registro de atendimento - EAD > Acadêmico',
            '1. Graduação EAD', 'Registro de atendimento - EAD', 'Acadêmico', 3, 'EAD',
            FALSE, FALSE, NULL
        )
    """)
    con.execute("""
        INSERT INTO silver_totem (
            contato_id, canal, origem_arquivo, origem_aba, origem_linha,
            aluno_id_original, aluno_hash, data_hora_contato, duracao_s,
            flag_duracao_zero, flag_outlier_duracao, flag_tempo_invalido,
            instituicao_original, flag_instituicao_nao_identificada,
            mdc_original, flag_mdc_nao_identificado,
            navegacao_original, qtd_passos_original,
            nota_original, status_nota, nota, respondeu_pesquisa, flag_nota_ruim
        ) VALUES (
            'tot_01', 'totem', 'arq.xlsx', 'Analitico_Totem', 2,
            'CPF_SECRETO_1', 'hash_aluno_a', TIMESTAMP '2026-09-08 09:00:00', 45,
            FALSE, FALSE, FALSE,
            'Anhanguera', FALSE,
            'JA_SOU_ALUNO', FALSE,
            'saudacao|menu', 2,
            '0', 'sem_resposta_zero', NULL, FALSE, FALSE
        )
    """)


# --- 1. Testes Sinteticos ---


def test_sintetico_dim_calendario_feriado_fim_semana_dia_util() -> None:
    """Valida a classificacao de Fim de Semana, Feriado Nacional (07/09) e Dia Util."""
    con = duckdb.connect()
    criar_silver_sintetica(con)
    rodar_modelo_gold(con)
    validar_modelo_gold(con, exigir_5991=False)

    datas = {
        r[0]: (r[1], r[2], r[3], r[4])
        for r in con.execute(
            "SELECT data, dia_semana_num, dia_semana_nome, tipo_dia, dia_util FROM dim_calendario"
        ).fetchall()
    }
    # intervalo dinamico de 2026-09-05 a 2026-09-08 = 4 dias
    assert len(datas) == 4
    # 05/09/2026 = sabado (isodow 6) -> Fim de Semana, dia_util = 0
    assert datas[dt.date(2026, 9, 5)] == (6, "sáb", "Fim de Semana", 0)
    # 06/09/2026 = domingo (isodow 7) -> Fim de Semana, dia_util = 0
    assert datas[dt.date(2026, 9, 6)] == (7, "dom", "Fim de Semana", 0)
    # 07/09/2026 = segunda (isodow 1), Feriado da Independencia -> Feriado Nacional, dia_util = 0
    assert datas[dt.date(2026, 9, 7)] == (1, "seg", "Feriado Nacional", 0)
    # 08/09/2026 = terca (isodow 2) -> Dia Util, dia_util = 1
    assert datas[dt.date(2026, 9, 8)] == (2, "ter", "Dia Útil", 1)


def test_sintetico_fato_jornada_atribuicao_recontato_agente_anterior() -> None:
    """Valida que o recontato no mesmo dia e atribuido ao agente do atendimento anterior."""
    con = duckdb.connect()
    criar_silver_sintetica(con)
    rodar_modelo_gold(con)

    rows = con.execute("""
        SELECT j.contato_id, j.ordem_contato_aluno, c.agente_id AS agente_atual,
               j.agente_id_anterior, j.flag_recontato_mesmo_dia,
               j.flag_recontato_mesmo_dia_mesmo_canal,
               j.agente_id_atribuido_recontato,
               j.flag_recontato_intracanal_mesmo_dia,
               j.agente_id_atribuido_recontato_intracanal
        FROM fato_jornada j
        JOIN fato_contato c ON c.contato_id = j.contato_id
        ORDER BY j.ordem_contato_aluno
    """).fetchall()

    # contato 1 (cc_01, 10:00): primeiro do dia, sem recontato
    assert rows[0][0] == "cc_01"
    assert rows[0][4] is False
    assert rows[0][6] is None

    # contato 2 (cc_02, 11:00): recontato no mesmo dia e mesmo canal, atribuido ao agente de cc_01
    ag_cc_01 = rows[0][2]
    ag_cc_02 = rows[1][2]
    assert rows[1][0] == "cc_02"
    assert rows[1][4] is True
    assert rows[1][5] is True
    assert rows[1][6] == ag_cc_01
    assert rows[1][7] is True
    assert rows[1][8] == ag_cc_01

    # contato 3 (wa_01, 12:00): recontato no mesmo dia em outro canal, atribuido ao agente de cc_02 na visao global
    assert rows[2][0] == "wa_01"
    assert rows[2][4] is True
    assert rows[2][5] is False
    assert rows[2][6] == ag_cc_02
    # na visao intracanal pura, wa_01 e o primeiro contato no WhatsApp, logo nao tem recontato intracanal
    assert rows[2][7] is False
    assert rows[2][8] is None


def test_sintetico_fato_navegacao_sem_multiplicar_nota() -> None:
    """Confirma que Passo1 repetido 3x no mesmo contato nao multiplica a nota na agregacao por presenca."""
    con = duckdb.connect()
    criar_silver_sintetica(con)
    rodar_modelo_gold(con)

    # cc_01 tem 'Passo1|Passo1|Passo1|99' (nota 2) e cc_02 tem 'Passo1|Passo1|Passo1' (nota 4)
    # no grao de passo bruto, Passo1 aparece 6 vezes (soma errada = 2*3 + 4*3 = 18)
    passos_brutos = con.execute("""
        SELECT count(*) FROM fato_navegacao
        WHERE canal = 'call_center' AND tipo_sequencia = 'original' AND ponto_navegacao = 'Passo1'
    """).fetchone()[0]
    assert passos_brutos == 6

    # na query Q8 (presenca unica por contato), Passo1 tem 2 contatos distintos, soma_notas = 6 e media = 3.0
    q8_res = executar_analytics(con)["q08_dnasoa_influencia_nota"]
    passo1_row = next(
        r
        for r in q8_res
        if r["secao_ordem"] == 1 and r["categoria_analisada"] == "Passo1"
    )
    assert passo1_row["contatos_totais"] == 2
    assert passo1_row["contatos_com_nota"] == 2
    assert passo1_row["soma_notas"] == 6
    assert passo1_row["nota_media"] == 3.0


def test_sintetico_validacao_detecta_vazamento_lgpd_e_fk_quebrada() -> None:
    """Garante que validar_modelo_gold falha se houver aluno_id_original ou FK quebrada."""
    con = duckdb.connect()
    criar_silver_sintetica(con)
    rodar_modelo_gold(con)
    validar_modelo_gold(con, exigir_5991=False)

    # injeta coluna proibida aluno_id_original em dim_aluno
    con.execute("ALTER TABLE dim_aluno ADD COLUMN aluno_id_original VARCHAR")
    with pytest.raises(ValidacaoGoldError, match="coluna sensivel exposta"):
        validar_modelo_gold(con, exigir_5991=False)

    # restaura modelo e quebra uma FK em fato_contato
    rodar_modelo_gold(con)
    con.execute(
        "UPDATE fato_contato SET agente_id = 'AG-INEXISTENTE' WHERE contato_id = 'cc_01'"
    )
    with pytest.raises(ValidacaoGoldError, match="FK quebrada"):
        validar_modelo_gold(con, exigir_5991=False)


# --- 2. Testes de Integracao e Reconciliacao no Dataset Real ---


@pytest.mark.integration
def test_integracao_modelo_estrela_contagens_lgpd_e_chaves() -> None:
    """Valida as 11 tabelas da Gold geradas a partir da Silver real."""
    con = duckdb.connect()
    for tbl in SCHEMA_SILVER:
        con.execute(
            f"CREATE VIEW {tbl} AS SELECT * FROM read_parquet('data/silver/{tbl}.parquet')"
        )
    rodar_modelo_gold(con)
    validar_modelo_gold(con, exigir_5991=True)

    esperados = {
        "dim_calendario": 12,
        "dim_hora": 24,
        "dim_canal": 4,
        "dim_aluno": 173,
        "dim_agente": 171,
        "dim_fila": 33,
        "dim_perfil_aluno": 53,
        "dim_motivo": 591,
        "fato_contato": 5991,
        "fato_navegacao": 81189,
        "fato_jornada": 5991,
    }
    for tabela, qtd_esp in esperados.items():
        qtd = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
        assert qtd == qtd_esp, f"{tabela}: esperado {qtd_esp}, obtido {qtd}"


@pytest.mark.integration
def test_integracao_reconciliacao_satisfacao_retencao_jornada() -> None:
    """Reconcilia metricas de satisfacao, retencao e sobreposicao na Gold com o referencia oficial."""
    con = duckdb.connect()
    for tbl in CHAVES_PK:
        con.execute(
            f"CREATE VIEW {tbl} AS SELECT * FROM read_parquet('data/gold/{tbl}.parquet')"
        )

    # satisfacao global: 1945 validas, soma 8643, 154 ruins, 3208 zeros, 838 nulas
    sat = con.execute("""
        SELECT count(*), count(nota), sum(nota),
               count(*) FILTER (WHERE flag_nota_ruim),
               count(*) FILTER (WHERE status_nota = 'sem_resposta_zero'),
               count(*) FILTER (WHERE status_nota = 'sem_resposta_nula')
        FROM fato_contato
    """).fetchone()
    assert sat == (5991, 1945, 8643, 154, 3208, 838)

    # retencao no Call Center: 270 fila, 266 assunto, 156 ambos, 229 cra_retencao exata, 114 pedido_cancelamento
    ret = con.execute("""
        SELECT count(*) FILTER (WHERE eh_retencao_fila),
               count(*) FILTER (WHERE eh_assunto_retencao),
               count(*) FILTER (WHERE eh_retencao_fila AND eh_assunto_retencao),
               count(*) FILTER (WHERE fila_atend = 'cra_retencao'),
               count(*) FILTER (WHERE desfecho_retencao = 'pedido_cancelamento')
        FROM fato_contato
        WHERE canal = 'call_center'
    """).fetchone()
    assert ret == (270, 266, 156, 229, 114)

    # sobreposicao estimada na fato_jornada: 308 intracanal, 576 intercanal (total 884)
    ov = dict(
        con.execute("""
            SELECT flag_sobreposicao_estimada, count(*)
            FROM fato_jornada GROUP BY 1
        """).fetchall()
    )
    assert ov["intracanal"] == 308
    assert ov["intercanal"] == 576
    assert ov["sem_sobreposicao"] == 5107


@pytest.mark.integration
def test_integracao_queries_q01_a_q09_resultados_chave() -> None:
    """Confere a execucao sem erro de q01..q09 e valida os numeros principais de negocio."""
    con = duckdb.connect()
    for tbl in CHAVES_PK:
        con.execute(
            f"CREATE VIEW {tbl} AS SELECT * FROM read_parquet('data/gold/{tbl}.parquet')"
        )
    res = executar_analytics(con)
    assert len(res) == len(SQL_ANALYTICS) == 9

    # Q1: 173 alunos com WA posterior (1403 contatos CC), 340 transicoes imediatas (160 alunos), 96 sem WA posterior
    q1 = {r["recorte"]: r for r in res["q01_cc_para_whatsapp"]}
    assert q1["1_qualquer_wa_posterior_no_periodo"]["alunos_distintos"] == 173
    assert q1["1_qualquer_wa_posterior_no_periodo"]["contatos_cc"] == 1403
    assert q1["2_transicao_imediata_cc_para_wa"]["contatos_cc"] == 340
    assert q1["2_transicao_imediata_cc_para_wa"]["alunos_distintos"] == 160
    assert q1["3_transicao_com_canais_intermediarios"]["contatos_cc"] == 1063
    assert q1["4_sem_wa_posterior"]["contatos_cc"] == 96

    # Q2: consecutivas exceto WA = 138 alunos (251 trincas); qualquer 4 canais = 157 alunos (325 trincas)
    q2 = {
        (r["tipo_sequencia"], r["terceiro_canal"]): r
        for r in res["q02_cc_wa_outro_canal"]
    }
    assert (
        q2[("a_estritamente_consecutiva", "TODOS_EXCETO_WHATSAPP")]["alunos_distintos"]
        == 138
    )
    assert (
        q2[("a_estritamente_consecutiva", "TODOS_EXCETO_WHATSAPP")]["qtd_ocorrencias"]
        == 251
    )
    assert (
        q2[("a_estritamente_consecutiva", "QUALQUER_UM_DOS_4_CANAIS")][
            "alunos_distintos"
        ]
        == 157
    )
    assert (
        q2[("b_com_contatos_intermediarios", "TODOS_EXCETO_WHATSAPP")][
            "alunos_distintos"
        ]
        == 173
    )

    # Q6: WhatsApp pior nota media (3.89) e maior % nota ruim (17.07% = 84/492)
    q6 = {r["canal"]: r for r in res["q06_canal_pior_nota"]}
    assert q6["whatsapp"]["ranking_pior_nota"] == 1
    assert q6["whatsapp"]["nota_media"] == 3.89
    assert q6["whatsapp"]["pct_notas_ruins"] == 17.07
    assert q6["totem"]["notas_validas"] == 24
    assert q6["totem"]["taxa_resposta_pct"] == 1.60
    assert q6["TOTAL_GERAL"]["nota_media"] == 4.44

    # Q9: Top 1 Visao A Omnichannel = AG-008 (200 recontatos em 204 atendimentos); Top 1 Visao B Intracanal = AG-001 (173 em 185)
    q9 = {
        (r["visao_ordem"], r["ranking"]): r
        for r in res["q09_agente_recontato_mesmo_dia"]
    }
    assert q9[(1, 1)]["agente_id"] == "AG-008"
    assert q9[(1, 1)]["volume_recontatos_mesmo_dia"] == 200
    assert q9[(3, 1)]["agente_id"] == "AG-001"
    assert q9[(3, 1)]["volume_recontatos_mesmo_dia"] == 173

    # verifica que todos os 9 arquivos .sql possuem cabecalho de comentarios documentado
    for arq in SQL_ANALYTICS:
        texto = (SQL_ANALYTICS_DIR / arq).read_text(encoding="utf-8")
        assert "-- Populacao analisada:" in texto
        assert "-- Denominador:" in texto
        assert "-- Premissas aplicadas" in texto
        assert "-- Limitacoes" in texto


@pytest.mark.integration
def test_integracao_exportacao_csv_bom_e_idempotencia() -> None:
    """Executa run_gold duas vezes e verifica idempotencia de Parquet, CSV (UTF-8 BOM) e JSON."""
    res1 = run_gold()
    hashes1 = {}
    for tbl in CHAVES_PK:
        csv_path = Path("data/gold") / f"{tbl}.csv"
        raw_bytes = csv_path.read_bytes()
        # verifica BOM UTF-8 (\xef\xbb\xbf) e delimitador ';'
        assert raw_bytes.startswith(b"\xef\xbb\xbf"), f"{tbl}.csv sem BOM UTF-8"
        primeira_linha = raw_bytes.decode("utf-8-sig").splitlines()[0]
        assert ";" in primeira_linha
        assert "aluno_id_original" not in primeira_linha
        hashes1[tbl] = hashlib.sha256(raw_bytes).hexdigest()

    json1 = Path("data/gold/analytics_results.json").read_text(encoding="utf-8")
    dados_json = json.loads(json1)
    assert len(dados_json) == 9

    # segunda execucao para provar idempotencia
    res2 = run_gold()
    assert res1 == res2
    for tbl in CHAVES_PK:
        csv_path = Path("data/gold") / f"{tbl}.csv"
        assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == hashes1[tbl]
    assert Path("data/gold/analytics_results.json").read_text(encoding="utf-8") == json1
