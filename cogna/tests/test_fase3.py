"""Testes da camada Silver em SQL (DuckDB).

Os testes sinteticos injetam relacoes raw_* falsas e rodam o mesmo SQL da Silver.
Os testes de integracao usam o XLSX real e comparam com o openpyxl.
"""

import datetime as dt
import hashlib
import re
from pathlib import Path

import duckdb
import openpyxl
import pytest

from cogna_etl import silver
from cogna_etl.silver import (
    SaltAusenteError,
    ValidacaoSilverError,
    abrir_conexao,
    gravar_parquets,
    ler_salt,
    rodar_sql,
    run_silver,
)

SALT_TESTE = "salt-de-teste-nao-usar-em-producao"

# colunas das relacoes raw_* (tipo VARCHAR quando nao informado)
COLUNAS_RAW = {
    "raw_cc": (
        "origem_arquivo origem_aba origem_linha:INTEGER identificador_aluno "
        "date:DATE calldate:TIMESTAMP id_type id_type_desc disconnect_type "
        "disconnect_type_desc duration_callcenter dna_soa recepcao_fila "
        "fila_atend agent supervisor pesquisa_1 protocolo tabulacao "
        "modalidade_nova modalidade_nova_desc categoria_aluno "
        "categoria_aluno_desc instituicao instituicao_desc"
    ),
    "raw_wa": (
        "origem_arquivo origem_aba origem_linha:INTEGER identificador_aluno "
        "calldate:TIMESTAMP id_type disconnect_type disconnect_type_desc "
        "modalidade modalidade_desc duration_callcenter after_hour "
        "categoria_aluno categoria_aluno_desc instituicao instituicao_desc "
        "dna_soa tme codigo_unidade pesquisa_1 agente tabulacao"
    ),
    "raw_video": (
        "origem_arquivo origem_aba origem_linha:INTEGER identificador_aluno "
        "calldate calldate_sem_ms tme duracao_da_chamada agente protocolo "
        "nota_pergunta1 tabulacao"
    ),
    "raw_totem": (
        "origem_arquivo origem_aba origem_linha:INTEGER identificador_aluno "
        "data_inicio:TIMESTAMP duracao instituicao mdc navegacao nota_pergunta1"
    ),
}

ABAS = {
    "raw_cc": "Analitico call center",
    "raw_wa": "Analitico Whatsapp",
    "raw_video": "Analitico_video_chamada",
    "raw_totem": "Analitico_Totem",
}

TAB_OK = "1. Graduação Presencial > Financeiro > Boleto"

PADRAO = {
    "raw_cc": {
        "identificador_aluno": "1001",
        "date": dt.date(2026, 9, 1),
        "calldate": dt.datetime(2026, 9, 1, 8, 0, 5),
        "id_type": "1",
        "id_type_desc": "1 - Cliente identificado por CPF",
        "disconnect_type": "1",
        "disconnect_type_desc": "1 = SIDEA (Desconexão por parte da origem - Cliente)",
        "duration_callcenter": "100",
        "dna_soa": "a|a|a",
        "recepcao_fila": "cra_ath_x",
        "fila_atend": "cra_ath_x",
        "agent": "Agente Um",
        "supervisor": "Supervisor Um",
        "pesquisa_1": "5",
        "protocolo": "CS12345678",
        "tabulacao": TAB_OK,
        "modalidade_nova": "1",
        "modalidade_nova_desc": "1 - Presencial Campus",
        "categoria_aluno": "1",
        "categoria_aluno_desc": "1 - Calouro",
        "instituicao": "2",
        "instituicao_desc": "2 - Anhanguera",
    },
    "raw_wa": {
        "identificador_aluno": "1001",
        "calldate": dt.datetime(2026, 9, 1, 9, 0, 0),
        "id_type": "1",
        "disconnect_type": "3",
        "disconnect_type_desc": "3 - ATH (Transfer com sucesso)",
        "modalidade": "1",
        "modalidade_desc": "1 - Presencial Campus",
        "duration_callcenter": "600",
        "after_hour": "1",
        "categoria_aluno": "1",
        "categoria_aluno_desc": "1 - Calouro",
        "instituicao": "2",
        "instituicao_desc": "2- Anhanguera",
        "dna_soa": "Identificacao|0|Busca|0",
        "tme": "60",
        "codigo_unidade": "10",
        "pesquisa_1": "4",
        "agente": "Agente Dois",
        "tabulacao": TAB_OK,
    },
    "raw_video": {
        "identificador_aluno": "1001",
        "calldate": "06/09/2026 19:01:56.662",
        "calldate_sem_ms": "06/09/2026 19:01:56",
        "tme": "5",
        "duracao_da_chamada": "300",
        "agente": "Agente Tres",
        "protocolo": "CS87654321",
        "nota_pergunta1": "3",
        "tabulacao": TAB_OK,
    },
    "raw_totem": {
        "identificador_aluno": "1001",
        "data_inicio": dt.datetime(2026, 9, 4, 13, 55, 37),
        "duracao": "40",
        "instituicao": "Anhanguera",
        "mdc": "JA_SOU_ALUNO",
        "navegacao": "saudacao -> perfil|identificacao -> fim",
        "nota_pergunta1": "5",
    },
}

DIC_PADRAO = [
    ("call_center", "id_type", "1", "1 - Cliente identificado por CPF"),
    (
        "call_center",
        "disconnect_type",
        "1",
        "1 = SIDEA (Desconexão por parte da origem - Cliente)",
    ),
    ("call_center", "modalidade_nova", "1", "1 - Presencial Campus"),
    ("call_center", "modalidade_nova", "5", "5 - EAD Campus"),
    ("call_center", "categoria_aluno", "1", "1 - Calouro"),
    ("call_center", "instituicao", "2", "2 - Anhanguera"),
    ("whatsapp", "id_type", "1", "1 - Cliente identificado por CPF"),
    ("whatsapp", "disconnect_type", "3", "3 - ATH (Transfer com sucesso)"),
    ("whatsapp", "modalidade", "1", "1 - Presencial Campus"),
    ("whatsapp", "categoria_aluno", "1", "1 - Calouro"),
    ("whatsapp", "categoria_aluno", "5", "4 - Calouro Presencial e Veterano EAD"),
    ("whatsapp", "instituicao", "2", "2- Anhanguera"),
    ("whatsapp", "instituicao", "2", "2 - Anhanguera"),
    ("whatsapp", "instituicao", "12", "12- Unopar + Anhanguera"),
    ("whatsapp", "instituicao", "12", "12- Unopar + Anhanguera"),
    ("whatsapp", "after_hour", "0", "0 = Não"),
    ("whatsapp", "after_hour", "1", "1 = Sim"),
    ("whatsapp", "after_hour", "0", "Se Sigla_FuncionalGroup == 'FHA' então 1"),
    ("whatsapp", "after_hour", "0", "Se Sigla_FuncionalGroup <> 'FHA' então 1"),
]


def _criar_raw(con, nome: str, linhas: list[dict]) -> None:
    """Cria a relacao raw_* com os dados falsos, completando com o padrao."""
    cols = [c.split(":") for c in COLUNAS_RAW[nome].split()]
    ddl = ", ".join(f'"{c[0]}" {c[1] if len(c) > 1 else "VARCHAR"}' for c in cols)
    con.execute(f"CREATE OR REPLACE TABLE {nome} ({ddl})")
    nomes = [c[0] for c in cols]
    for i, over in enumerate(linhas):
        valores = {"origem_arquivo": "teste.xlsx", "origem_aba": ABAS[nome]}
        valores["origem_linha"] = i + 2
        valores.update(PADRAO[nome])
        valores.update(over)
        marcas = ", ".join("?" for _ in nomes)
        lista = ", ".join(f'"{n}"' for n in nomes)
        con.execute(
            f"INSERT INTO {nome} ({lista}) VALUES ({marcas})",
            [valores[n] for n in nomes],
        )


def montar(cc=(), wa=(), video=(), totem=(), dic=DIC_PADRAO, salt=SALT_TESTE):
    """Monta uma conexao com raw_* falsos e roda o SQL da Silver."""
    con = duckdb.connect()
    if salt is not None:
        con.execute("SET VARIABLE salt = ?", [salt])
    for nome, linhas in (
        ("raw_cc", cc),
        ("raw_wa", wa),
        ("raw_video", video),
        ("raw_totem", totem),
    ):
        _criar_raw(con, nome, list(linhas))
    con.execute(
        "CREATE TABLE dic_dominio (canal VARCHAR, campo VARCHAR, codigo VARCHAR, rotulo VARCHAR)"
    )
    con.executemany("INSERT INTO dic_dominio VALUES (?, ?, ?, ?)", list(dic))
    rodar_sql(con, silver.SQL_TRANSFORMACAO)
    return con


def consulta(con, sql: str):
    return con.execute(sql).fetchall()


# ---------------------------------------------------------------- sinteticos


def test_id_ausente_vira_nulo_sem_hash_compartilhado():
    ids = [None, "", "nan", "None", "  ", "0012345"]
    con = montar(cc=[{"identificador_aluno": i} for i in ids])
    res = consulta(
        con,
        "SELECT aluno_id_original, aluno_hash FROM silver_callcenter ORDER BY origem_linha",
    )
    assert len(res) == 6
    # ausencias viram NULL, nunca texto nan/None nem hash de aluno compartilhado
    assert all(r == (None, None) for r in res[:5])
    # id textual fica intacto, sem zero-fill nem remocao de zero
    assert res[5][0] == "0012345" and len(res[5][1]) == 64


def test_aluno_hash_igual_entre_canais_e_depende_do_salt():
    con = montar(cc=[{}], wa=[{}], video=[{}], totem=[{}])
    hashes = {
        t: consulta(con, f"SELECT aluno_hash FROM {t}")[0][0]
        for t in (
            "silver_callcenter",
            "silver_whatsapp",
            "silver_video_chamada",
            "silver_totem",
        )
    }
    assert len(set(hashes.values())) == 1
    esperado = hashlib.sha256(f"{SALT_TESTE}|1001".encode()).hexdigest()
    assert hashes["silver_totem"] == esperado
    outro = montar(cc=[{}], salt="outro-salt")
    assert consulta(outro, "SELECT aluno_hash FROM silver_callcenter")[0][0] != esperado


def test_contato_id_deterministico_e_unico_por_origem():
    a = montar(cc=[{}, {}], wa=[{}, {}], video=[{}], totem=[{}])
    b = montar(cc=[{}, {}], wa=[{}, {}], video=[{}], totem=[{}])
    sql = (
        "SELECT contato_id FROM silver_callcenter UNION ALL SELECT contato_id FROM silver_whatsapp "
        "UNION ALL SELECT contato_id FROM silver_video_chamada UNION ALL SELECT contato_id FROM silver_totem"
    )
    ids_a = [r[0] for r in consulta(a, sql)]
    assert len(ids_a) == len(set(ids_a)) == 6
    assert ids_a == [r[0] for r in consulta(b, sql)]


def test_nota_invalida_zero_e_nula_nao_somem_nem_viram_nota():
    notas = ["6", "2.5", "texto", "0", None, "3", "1", "4.0", "-1"]
    con = montar(cc=[{"pesquisa_1": n} for n in notas])
    res = consulta(
        con,
        "SELECT nota_original, status_nota, nota, respondeu_pesquisa, flag_nota_ruim "
        "FROM silver_callcenter ORDER BY origem_linha",
    )
    assert len(res) == len(notas)
    esperado = [
        ("6", "invalida", None, False, False),
        ("2.5", "invalida", None, False, False),
        ("texto", "invalida", None, False, False),
        ("0", "sem_resposta_zero", None, False, False),
        (None, "sem_resposta_nula", None, False, False),
        ("3", "respondida", 3, True, False),
        ("1", "respondida", 1, True, True),
        ("4.0", "respondida", 4, True, False),
        ("-1", "invalida", None, False, False),
    ]
    assert res == esperado


def test_dominio_conflitante_desconhecido_e_sem_multiplicar_linhas():
    wa = [
        {"after_hour": "0"},
        {"instituicao": "12", "instituicao_desc": "12- Unopar + Anhanguera"},
        {"instituicao": "99", "instituicao_desc": "99- Qualquer"},
        {
            "categoria_aluno": "5",
            "categoria_aluno_desc": "4 - Calouro Presencial e Veterano EAD",
        },
        {"instituicao": None, "instituicao_desc": None},
        {"instituicao": "2", "instituicao_desc": "2 - Anhanguera"},
    ]
    con = montar(wa=wa)
    res = consulta(
        con,
        "SELECT after_hour_status, instituicao_status, instituicao_rotulo, categoria_aluno_status, "
        "flag_dominio_inconsistente FROM silver_whatsapp ORDER BY origem_linha",
    )
    # uma linha de saida para cada linha de entrada, mesmo com codigo 0 e 12 repetidos no dicionario
    assert len(res) == 6
    assert res[0][0] == "conflito_dicionario"
    # instituicao 12 duplicada com o mesmo rotulo e consolidada
    assert res[1][1:3] == ("ok", "12 - Unopar + Anhanguera")
    assert res[2][1] == "sem_dicionario" and res[2][2] is None
    # categoria 5 com rotulo comecando em 4 fica marcada
    assert res[3][3] == "rotulo_diverge_codigo"
    assert res[4][1] == "nulo"
    # os dois formatos do rotulo da instituicao 2 viram um so
    assert res[5][1:3] == ("ok", "2 - Anhanguera")
    # so conflito, desconhecido e rotulo divergente marcam a linha como inconsistente
    assert [r[4] for r in res] == [True, False, True, True, False, False]


def test_dominio_nao_cruza_codigos_entre_canais():
    dic = DIC_PADRAO + [("whatsapp", "modalidade", "5", "5 - EAD Polo errado")]
    con = montar(
        cc=[{"modalidade_nova": "5", "modalidade_nova_desc": "5 - EAD Campus"}], dic=dic
    )
    res = consulta(
        con, "SELECT modalidade_rotulo, modalidade_status FROM silver_callcenter"
    )
    assert res == [("5 - EAD Campus", "ok")]


def test_milissegundos_do_video_e_segundos_do_cc():
    video = [
        {
            "calldate": "06/09/2026 19:01:56.662",
            "calldate_sem_ms": "06/09/2026 19:01:56",
        },
        {
            "calldate": "07/09/2026 10:00:00.005",
            "calldate_sem_ms": "07/09/2026 10:00:01",
        },
        {"calldate": "texto invalido", "calldate_sem_ms": None},
    ]
    con = montar(video=video, cc=[{"calldate": dt.datetime(2026, 9, 1, 8, 7, 17)}])
    res = consulta(
        con,
        "SELECT data_hora_contato, flag_calldate_sem_ms_diverge, calldate_original "
        "FROM silver_video_chamada ORDER BY origem_linha",
    )
    assert res[0][0] == dt.datetime(2026, 9, 6, 19, 1, 56, 662000)
    assert res[1][0] == dt.datetime(2026, 9, 7, 10, 0, 0, 5000)
    # a coluna sem ms que diverge do campo com ms fica sinalizada
    assert (res[0][1], res[1][1]) == (False, True)
    # data ilegivel vira NULL, a linha continua na saida e o texto original e mantido
    assert res[2][0] is None and res[2][2] == "texto invalido"
    assert consulta(con, "SELECT data_hora_contato FROM silver_callcenter")[0][
        0
    ] == dt.datetime(2026, 9, 1, 8, 7, 17)


def test_formatos_de_protocolo():
    protocolos = [
        "CS12345678",
        "EDU-79415-20240305-N4Z6",
        "Ocorrência·OcorrênciaEDU-85868-20240311-H3Q3",
        "1.4449560103202401E+18",
        "123456789012",
        "CRA_RETENÇÃO",
        "cra_retenção",
        "S29510335",
        "XYZ-1",
        None,
    ]
    con = montar(cc=[{"protocolo": p} for p in protocolos])
    res = consulta(
        con,
        "SELECT protocolo_original, formato_protocolo, protocolo_padrao_cs, flag_retencao_protocolo, "
        "eh_retencao_fila FROM silver_callcenter ORDER BY origem_linha",
    )
    formatos = [r[1] for r in res]
    assert formatos == [
        "cs", "edu", "edu", "notacao_cientifica", "numerico",
        "cra_retencao", "cra_retencao", "prefixo_s", "outro", "nulo",
    ]  # fmt: skip
    # o texto original nunca e alterado, nem a notacao cientifica
    assert res[3][0] == "1.4449560103202401E+18"
    assert [r[2] for r in res] == [True] + [False] * 9
    assert [r[3] for r in res] == [False] * 5 + [True, True] + [False] * 3
    # protocolo CRA_RETENCAO nao prova fila de retencao
    assert not any(r[4] for r in res)


def test_tabulacao_com_niveis_variados():
    tabs = [
        None,
        "1. Graduação Presencial",
        "2. Graduação EAD > B > C > D > E > F > G",
        "1. Graduação Presencial > > C",
        "  ",
    ]
    con = montar(cc=[{"tabulacao": t} for t in tabs])
    res = consulta(
        con,
        "SELECT tabulacao_original, tab_nivel1, tab_nivel2, tab_nivel3, tab_nivel7, qtd_niveis_tab, "
        "modalidade_tab FROM silver_callcenter ORDER BY origem_linha",
    )
    assert res[0] == (None, None, None, None, None, 0, None)
    assert res[1][1:] == ("1. Graduação Presencial", None, None, None, 1, "Presencial")
    assert res[2][1:] == ("2. Graduação EAD", "B", "C", "G", 7, "EAD")
    # nivel do meio vazio fica NULL e nao entra na contagem
    assert res[3][1:4] == ("1. Graduação Presencial", None, "C") and res[3][5] == 2
    assert res[4][0] is None and res[4][5] == 0


def test_tabulacao_com_mais_de_sete_niveis_falha_explicitamente():
    oito = " > ".join("n" + str(i) for i in range(8))
    with pytest.raises(duckdb.Error, match="mais de 7 niveis"):
        montar(cc=[{"tabulacao": oito}])


def test_divergencia_de_modalidade_nao_corrige_cadastro():
    cc = [
        {
            "tabulacao": "2. Graduação EAD > x",
            "modalidade_nova": "1",
            "modalidade_nova_desc": "1 - Presencial Campus",
        },
        {
            "tabulacao": "1. Graduação Presencial > Prova Presencial",
            "modalidade_nova": "1",
        },
        {
            "tabulacao": "2. Graduação EAD > Portal digital",
            "modalidade_nova": "5",
            "modalidade_nova_desc": "5 - EAD Campus",
        },
        {"tabulacao": None},
    ]
    con = montar(cc=cc)
    res = consulta(
        con,
        "SELECT modalidade_tab, modalidade_cadastro_grupo, modalidade_codigo, flag_divergencia_modalidade "
        "FROM silver_callcenter ORDER BY origem_linha",
    )
    assert res == [
        ("EAD", "Presencial", 1, True),
        ("Presencial", "Presencial", 1, False),
        ("EAD", "EAD", 5, False),
        (None, "Presencial", 1, False),
    ]


def test_retencao_fila_assunto_encaminhamento_e_desfecho():
    ret = "1. Graduação Presencial > Atendimento de Retenção > "
    cc = [
        {
            "fila_atend": "cra_retenção_calouro",
            "tabulacao": ret + "Solicitação de cancelamento",
        },
        {"fila_atend": "cra_ath_x", "tabulacao": ret + "Aluno mantido"},
        {
            "fila_atend": "cra_ath_x",
            "tabulacao": ret + "Solicitação de transferência > mesma unidade",
        },
        {"fila_atend": "cra_ath_x", "tabulacao": ret + "Solicitação de trancamento"},
        {"fila_atend": "cra_ath_x", "tabulacao": ret + "Vai pagar rematrícula"},
        {"fila_atend": "cra_ath_x", "tabulacao": ret + "Outro assunto"},
        {"fila_atend": "CRA_RETENCAO", "tabulacao": TAB_OK},
        {
            "fila_atend": "cra_ath_x",
            "tabulacao": "1. Graduação Presencial > Transferência para retenção",
        },
        {"fila_atend": None, "recepcao_fila": "cra_ath_x", "tabulacao": None},
    ]
    con = montar(cc=cc)
    res = consulta(
        con,
        "SELECT eh_retencao_fila, eh_assunto_retencao, flag_encaminhamento_retencao, desfecho_retencao, "
        "flag_filas_divergentes FROM silver_callcenter ORDER BY origem_linha",
    )
    assert [r[3] for r in res] == [
        "pedido_cancelamento", "aluno_mantido", "pedido_transferencia", "pedido_trancamento",
        "rematricula", "nao_classificado", None, None, None,
    ]  # fmt: skip
    assert [r[0] for r in res] == [True] + [False] * 5 + [True, False, False]
    assert [r[1] for r in res] == [True] * 6 + [False] * 3
    assert [r[2] for r in res] == [False] * 7 + [True, False]
    # desfecho so existe quando o assunto e retencao; a fila sozinha nao gera desfecho
    assert res[6][3] is None
    # filas diferentes ou ausentes ficam marcadas, sem apagar nenhuma das duas colunas
    assert res[8][4] is True and res[1][4] is False


def test_dna_com_trios_e_tokens_98_99():
    dnas = [
        "a|a|a|b|b|b|c|c|c",
        "98|99|99",
        "a|b|a",
        None,
    ]
    con = montar(cc=[{"dna_soa": d} for d in dnas])
    res = consulta(
        con,
        "SELECT dna_soa_original, qtd_passos_original, dna_soa_sem_repeticao_consecutiva "
        "FROM silver_callcenter ORDER BY origem_linha",
    )
    assert res[0] == (dnas[0], 9, "a|b|c")
    # original intacto e passos 98 e 99 preservados na versao derivada
    assert res[1] == (dnas[1], 3, "98|99")
    # repeticao nao consecutiva nao e removida
    assert res[2] == (dnas[2], 3, "a|b|a")
    assert res[3] == (None, None, None)
    tokens = consulta(
        con,
        "SELECT count(*) FILTER (WHERE list_contains(string_split(dna_soa_original, '|'), '98')) FROM silver_callcenter",
    )
    assert tokens[0][0] == 1


def test_tempo_zero_nulo_invalido_e_tme_maior_que_duracao():
    wa = [
        {"duration_callcenter": "0", "tme": "10"},
        {"duration_callcenter": None, "tme": None},
        {"duration_callcenter": "12.5", "tme": "-3"},
        {"duration_callcenter": "50", "tme": "100"},
        {"duration_callcenter": "50", "tme": "50"},
        {"duration_callcenter": "60.0", "tme": "20"},
    ]
    con = montar(wa=wa)
    res = consulta(
        con,
        "SELECT duracao_s, tme_s, flag_duracao_zero, flag_tme_maior_duracao, flag_tempo_invalido "
        "FROM silver_whatsapp ORDER BY origem_linha",
    )
    assert len(res) == 6
    # zero de origem e mantido como zero; ausencia vira NULL
    assert res[0] == (0, 10, True, True, False)
    assert res[1] == (None, None, False, False, False)
    # fracao e negativo viram NULL com flag de tempo invalido, sem descartar a linha
    assert res[2] == (None, None, False, False, True)
    assert res[3] == (50, 100, False, True, False)
    assert res[4] == (50, 50, False, False, False)
    assert res[5][:2] == (60, 20)


def test_outlier_iqr_por_canal():
    video = [
        {"duracao_da_chamada": str(v), "tme": "5"} for v in (10, 11, 12, 13, 14, 1000)
    ]
    totem = [{"duracao": str(v)} for v in (1000, 1001, 1002, 1003)]
    con = montar(video=video, totem=totem)
    out = consulta(
        con,
        "SELECT flag_outlier_duracao FROM silver_video_chamada ORDER BY origem_linha",
    )
    assert [r[0] for r in out] == [False] * 5 + [True]
    # a regra e calculada dentro de cada canal, entao o totem nao herda os limites do video
    assert not any(
        r[0] for r in consulta(con, "SELECT flag_outlier_duracao FROM silver_totem")
    )


def test_totem_sem_agente_e_nota_do_totem():
    totem = [
        {
            "nota_pergunta1": "0",
            "instituicao": "Nao identificado",
            "mdc": "Nao identificado",
        },
        {"nota_pergunta1": "2"},
        {"nota_pergunta1": None, "navegacao": None},
    ]
    con = montar(totem=totem)
    cols = [c[0] for c in con.execute("DESCRIBE silver_totem").fetchall()]
    assert not any("agente" in c or "protocolo" in c or "tab" in c for c in cols)
    res = consulta(
        con,
        "SELECT status_nota, nota, flag_nota_ruim, flag_instituicao_nao_identificada, "
        "flag_mdc_nao_identificado, qtd_passos_original FROM silver_totem ORDER BY origem_linha",
    )
    assert res[0] == ("sem_resposta_zero", None, False, True, True, 2)
    assert res[1] == ("respondida", 2, True, False, False, 2)
    assert res[2] == ("sem_resposta_nula", None, False, False, False, None)


def test_schema_explicito_nas_quatro_tabelas():
    con = montar(cc=[{}], wa=[{}], video=[{}], totem=[{}])
    tipos = {
        "contato_id": "VARCHAR",
        "origem_linha": "INTEGER",
        "data_hora_contato": "TIMESTAMP",
        "duracao_s": "INTEGER",
        "nota": "INTEGER",
        "respondeu_pesquisa": "BOOLEAN",
    }
    for tabela in silver.TABELAS:
        schema = dict(
            (c[0], c[1]) for c in con.execute(f"DESCRIBE {tabela}").fetchall()
        )
        for col, tipo in tipos.items():
            assert schema[col] == tipo, f"{tabela}.{col}"
        assert not [
            c for c, t in schema.items() if t == "JSON" or t.startswith("DECIMAL")
        ]


def test_salt_ausente_falha_com_mensagem_clara_no_sql(monkeypatch):
    with pytest.raises(duckdb.Error, match="ALUNO_HASH_SALT ausente"):
        montar(cc=[{}], salt=None)


def test_salt_ausente_falha_com_mensagem_clara_no_python(tmp_path, monkeypatch):
    monkeypatch.delenv(silver.VAR_SALT, raising=False)
    with pytest.raises(SaltAusenteError, match=r"\.env\.example"):
        ler_salt(tmp_path / "nao_existe.env")
    vazio = tmp_path / "vazio.env"
    vazio.write_text(f"{silver.VAR_SALT}=\n", encoding="utf-8")
    with pytest.raises(SaltAusenteError):
        ler_salt(vazio)
    ok = tmp_path / "ok.env"
    ok.write_text(f'# comentario\n{silver.VAR_SALT}="abc"\n', encoding="utf-8")
    assert ler_salt(ok) == "abc"


def test_run_silver_nao_gera_saida_sem_salt(tmp_path, monkeypatch):
    monkeypatch.delenv(silver.VAR_SALT, raising=False)
    saida = tmp_path / "silver"
    with pytest.raises(SaltAusenteError):
        run_silver(silver_dir=saida, env_path=tmp_path / "sem.env")
    assert not saida.exists()


def test_gravacao_so_troca_a_saida_se_a_validacao_passar(tmp_path, monkeypatch):
    con = montar(cc=[{}], wa=[{}], video=[{}], totem=[{}])
    saida = tmp_path / "silver"
    saida.mkdir()
    antigo = saida / "silver_totem.parquet"
    antigo.write_bytes(b"saida anterior")
    outro = saida / "arquivo_de_outra_origem.txt"
    outro.write_text("nao e meu", encoding="utf-8")

    def falha(*args, **kwargs):
        raise ValidacaoSilverError("falha simulada")

    monkeypatch.setattr(silver, "_validar_parquet", falha)
    with pytest.raises(ValidacaoSilverError):
        gravar_parquets(con, saida)
    # a saida anterior continua igual e a pasta temporaria foi removida
    assert antigo.read_bytes() == b"saida anterior"
    assert sorted(p.name for p in saida.iterdir()) == [
        "arquivo_de_outra_origem.txt",
        "silver_totem.parquet",
    ]
    monkeypatch.undo()
    gravar_parquets(con, saida)
    assert outro.exists()
    assert len(list(saida.glob("silver_*.parquet"))) == 4


def test_validacao_detecta_linha_perdida():
    con = montar(cc=[{}, {}], wa=[{}], video=[{}], totem=[{}])
    silver.validar_tabelas(con)
    con.execute("DELETE FROM silver_callcenter WHERE origem_linha = 3")
    with pytest.raises(ValidacaoSilverError, match="silver_callcenter"):
        silver.validar_tabelas(con)


# ---------------------------------------------------------------- integracao

XLSX = Path("data/raw/analytical_database_callcenter.xlsx")
DIC_DIR = Path("data/dictionaries")

pytestmark_real = pytest.mark.skipif(
    not (XLSX.exists() and DIC_DIR.exists()), reason="dados reais ausentes"
)


def _salt_real() -> str:
    try:
        return ler_salt()
    except SaltAusenteError:
        pytest.skip("ALUNO_HASH_SALT nao configurado")


@pytest.fixture(scope="module")
def con_raw():
    """Conexao com as relacoes raw_* lidas do XLSX real pelo read_xlsx."""
    con = abrir_conexao(_salt_real())
    con.execute("SET VARIABLE xlsx_path = ?", [XLSX.as_posix()])
    rodar_sql(con, ["00_macros.sql", "01_raw_xlsx.sql"])
    yield con
    con.close()


@pytest.fixture(scope="module")
def silver_real(tmp_path_factory):
    """Roda a Silver real duas vezes em pastas separadas."""
    pasta = tmp_path_factory.mktemp("silver")
    a, b = pasta / "a", pasta / "b"
    res = run_silver(silver_dir=a)
    run_silver(silver_dir=b)
    return {"a": a, "b": b, "res": res}


def _pq(pasta: Path, nome: str) -> str:
    return f"read_parquet('{(pasta / (nome + '.parquet')).as_posix()}')"


def _norm(v):
    """Representacao comparavel de uma celula entre openpyxl e DuckDB."""
    if v is None:
        return None
    if isinstance(v, dt.datetime):
        return v.isoformat(sep=" ", timespec="milliseconds")
    if isinstance(v, dt.date):
        return _norm(dt.datetime.combine(v, dt.time()))
    if isinstance(v, float):
        return repr(v)
    if isinstance(v, str) and re.fullmatch(r"[0-9]+(\.[0-9]+)?[Ee][+-]?[0-9]+", v):
        return repr(float(v))
    return str(v)


def _hash_linha(valores) -> str:
    texto = "\x1f".join("\x00" if v is None else v for v in map(_norm, valores))
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


COLUNAS_ABA = {
    "raw_cc": 22,
    "raw_wa": 19,
    "raw_video": 9,
    "raw_totem": 7,
}
LINHAS_ESPERADAS = {
    "raw_cc": 1499,
    "raw_wa": 1494,
    "raw_video": 1499,
    "raw_totem": 1499,
}


@pytest.mark.integration
@pytestmark_real
@pytest.mark.parametrize("nome", list(COLUNAS_ABA))
def test_passo0_read_xlsx_igual_ao_openpyxl(con_raw, nome):
    wb = openpyxl.load_workbook(XLSX, read_only=True, data_only=True)
    n = COLUNAS_ABA[nome]
    ws = wb[ABAS[nome]]
    originais = [
        (i, r[:n])
        for i, r in enumerate(ws.iter_rows(values_only=True), start=1)
        if i > 1 and any(c is not None for c in r)
    ]
    wb.close()
    cols = con_raw.execute(f"DESCRIBE {nome}").fetchall()
    nomes = [c[0] for c in cols][3:]
    lidas = con_raw.execute(
        f"SELECT origem_linha, {', '.join(chr(34) + c + chr(34) for c in nomes)} FROM {nome} ORDER BY origem_linha"
    ).fetchall()
    assert len(lidas) == len(originais) == LINHAS_ESPERADAS[nome]
    # a linha de origem aponta para a linha real da aba, sem deslocamento
    assert [r[0] for r in lidas] == [o[0] for o in originais]
    # hash de linha de todas as linhas: openpyxl x DuckDB (inclui protocolo longo e datas)
    hash_duck = [_hash_linha(r[1:]) for r in lidas]
    hash_opx = [_hash_linha(o[1]) for o in originais]
    assert hash_duck == hash_opx


@pytest.mark.integration
@pytestmark_real
def test_passo0_ids_datas_e_cabecalho_do_video(con_raw):
    for nome in COLUNAS_ABA:
        # id inteiro vira texto sem .0 e sem zero-fill; todos tem 13 ou 14 digitos
        fora = con_raw.execute(
            f"SELECT count(*) FROM {nome} WHERE identificador_aluno IS NOT NULL "
            "AND NOT regexp_matches(identificador_aluno, '^[1-9][0-9]{12,13}$')"
        ).fetchone()[0]
        assert fora == 0
    cols = [c[0] for c in con_raw.execute("DESCRIBE raw_video").fetchall()]
    assert cols[5] == "calldate_sem_ms" and "duracao_da_chamada" in cols
    # video: texto com milissegundos preservado na entrada
    sem_ms = con_raw.execute(
        "SELECT count(*) FROM raw_video WHERE NOT regexp_matches(calldate, "
        "'^[0-9]{2}/[0-9]{2}/[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}[.][0-9]{3}$')"
    ).fetchone()[0]
    assert sem_ms == 0
    # cc, wa e totem: nenhum timestamp perdido e segundos preservados
    for nome, col in (
        ("raw_cc", "calldate"),
        ("raw_wa", "calldate"),
        ("raw_totem", "data_inicio"),
    ):
        nulos = con_raw.execute(
            f"SELECT count(*) FILTER (WHERE {col} IS NULL) FROM {nome}"
        ).fetchone()[0]
        segundos = con_raw.execute(
            f"SELECT count(DISTINCT date_part('second', {col})) FROM {nome}"
        ).fetchone()[0]
        assert nulos == 0 and segundos > 1


@pytest.mark.integration
@pytestmark_real
def test_reconciliacao_linhas_chaves_e_alunos(silver_real):
    assert all(a == b for a, b in silver_real["res"].values())
    assert sum(b for _, b in silver_real["res"].values()) == 5991
    pasta = silver_real["a"]
    con = duckdb.connect()
    uniao = " UNION ALL ".join(
        f"SELECT contato_id, aluno_hash, aluno_id_original, '{t}' AS t FROM {_pq(pasta, t)}"
        for t in silver.TABELAS
    )
    tot, ids, nulos, ids_alunos, hashes, pares = con.execute(
        f"SELECT count(*), count(DISTINCT contato_id), count(*) FILTER (WHERE aluno_hash IS NULL), "
        f"count(DISTINCT aluno_id_original), count(DISTINCT aluno_hash), "
        f"count(DISTINCT (aluno_id_original, aluno_hash)) FROM ({uniao})"
    ).fetchone()
    assert (tot, ids, nulos) == (5991, 5991, 0)
    # 173 alunos, cada um com um unico hash, igual entre canais
    assert (ids_alunos, hashes, pares) == (173, 173, 173)
    em_4 = con.execute(
        f"SELECT count(*) FROM (SELECT aluno_hash FROM ({uniao}) GROUP BY 1 HAVING count(DISTINCT t) = 4)"
    ).fetchone()[0]
    assert em_4 == 173


@pytest.mark.integration
@pytestmark_real
def test_reconciliacao_satisfacao(silver_real):
    pasta = silver_real["a"]
    con = duckdb.connect()
    esperado = {
        "silver_callcenter": (661, 3011, 48),
        "silver_whatsapp": (492, 1914, 84),
        "silver_video_chamada": (768, 3612, 20),
        "silver_totem": (24, 106, 2),
    }
    total = [0, 0, 0]
    for tabela, exp in esperado.items():
        obtido = con.execute(
            f"SELECT count(*) FILTER (WHERE status_nota = 'respondida'), sum(nota), "
            f"count(*) FILTER (WHERE flag_nota_ruim) FROM {_pq(pasta, tabela)}"
        ).fetchone()
        assert obtido == exp, tabela
        total = [t + o for t, o in zip(total, obtido)]
    assert total == [1945, 8643, 154]
    status = con.execute(
        f"SELECT status_nota, count(*) FROM {_pq(pasta, 'silver_callcenter')} GROUP BY 1"
    ).fetchall()
    assert dict(status) == {"respondida": 661, "sem_resposta_nula": 838}
    assert (
        con.execute(
            f"SELECT count(*) FROM {_pq(pasta, 'silver_totem')} WHERE status_nota = 'sem_resposta_zero'"
        ).fetchone()[0]
        == 1475
    )


@pytest.mark.integration
@pytestmark_real
def test_reconciliacao_retencao_filas_e_protocolo(silver_real):
    cc = _pq(silver_real["a"], "silver_callcenter")
    con = duckdb.connect()
    r = con.execute(
        f"SELECT count(*) FILTER (WHERE eh_retencao_fila), count(*) FILTER (WHERE eh_assunto_retencao), "
        f"count(*) FILTER (WHERE flag_encaminhamento_retencao), "
        f"count(*) FILTER (WHERE eh_retencao_fila AND eh_assunto_retencao), "
        f"count(*) FILTER (WHERE eh_retencao_fila AND NOT eh_assunto_retencao), "
        f"count(*) FILTER (WHERE NOT eh_retencao_fila AND eh_assunto_retencao), "
        f"count(*) FILTER (WHERE NOT eh_retencao_fila AND NOT eh_assunto_retencao), "
        f"count(*) FILTER (WHERE NOT flag_filas_divergentes), count(*) FILTER (WHERE flag_filas_divergentes) FROM {cc}"
    ).fetchone()
    assert r == (270, 266, 6, 156, 114, 110, 1119, 1295, 204)
    desfecho = dict(
        con.execute(
            f"SELECT desfecho_retencao, count(*) FROM {cc} WHERE eh_assunto_retencao GROUP BY 1"
        ).fetchall()
    )
    assert desfecho == {
        "pedido_cancelamento": 114, "aluno_mantido": 61, "pedido_transferencia": 45,
        "pedido_trancamento": 37, "rematricula": 9,
    }  # fmt: skip
    fmt = dict(
        con.execute(
            f"SELECT formato_protocolo, count(*) FROM {cc} GROUP BY 1"
        ).fetchall()
    )
    assert fmt == {
        "nulo": 469, "cs": 971, "edu": 32, "notacao_cientifica": 12,
        "numerico": 9, "cra_retencao": 5, "prefixo_s": 1,
    }  # fmt: skip
    assert (
        con.execute(
            f"SELECT count(*) FILTER (WHERE flag_retencao_protocolo) FROM {cc}"
        ).fetchone()[0]
        == 5
    )
    video = _pq(silver_real["a"], "silver_video_chamada")
    assert (
        con.execute(
            f"SELECT count(*) FROM {video} WHERE protocolo_padrao_cs"
        ).fetchone()[0]
        == 1499
    )
    # modalidade pelo primeiro nivel da tabulacao contra o cadastro
    div_cc = con.execute(
        f"SELECT count(*) FILTER (WHERE flag_divergencia_modalidade) FROM {cc}"
    ).fetchone()[0]
    wa = _pq(silver_real["a"], "silver_whatsapp")
    div_wa = con.execute(
        f"SELECT count(*) FILTER (WHERE flag_divergencia_modalidade) FROM {wa}"
    ).fetchone()[0]
    assert (div_cc, div_wa) == (19, 46)


@pytest.mark.integration
@pytestmark_real
def test_reconciliacao_dna_tempos_e_dominios(silver_real):
    pasta = silver_real["a"]
    cc = _pq(pasta, "silver_callcenter")
    con = duckdb.connect()
    dna = con.execute(
        f"SELECT count(*) FILTER (WHERE dna_soa_original IS NULL), "
        f"count(*) FILTER (WHERE dna_soa_original IS NOT NULL), "
        f"count(*) FILTER (WHERE list_contains(string_split(dna_soa_original, '|'), '98')), "
        f"count(*) FILTER (WHERE list_contains(string_split(dna_soa_original, '|'), '99')), "
        f"count(*) FILTER (WHERE list_contains(string_split(dna_soa_original, '|'), '98') "
        f"AND list_contains(string_split(dna_soa_original, '|'), '99')), "
        f"count(*) FILTER (WHERE qtd_passos_original % 3 = 0 AND list_bool_and("
        f"[string_split(dna_soa_original, '|')[3 * k + 1] = string_split(dna_soa_original, '|')[3 * k + 2] "
        f"AND string_split(dna_soa_original, '|')[3 * k + 2] = string_split(dna_soa_original, '|')[3 * k + 3] "
        f"FOR k IN range(qtd_passos_original // 3)])) FROM {cc}"
    ).fetchone()
    assert dna == (2, 1497, 5, 410, 0, 1082)
    # datas: sem nulos e extremos iguais ao profiling
    assert con.execute(
        f"SELECT min(data_hora_contato), max(data_hora_contato) FROM {cc}"
    ).fetchone() == (
        dt.datetime(2026, 9, 1, 8, 7, 17),
        dt.datetime(2026, 9, 11, 19, 56, 12),
    )
    video = _pq(pasta, "silver_video_chamada")
    assert con.execute(
        f"SELECT min(data_hora_contato), max(data_hora_contato) FROM {video}"
    ).fetchone() == (
        dt.datetime(2026, 9, 1, 10, 0, 54, 242000),
        dt.datetime(2026, 9, 11, 20, 44, 12, 716000),
    )
    wa = _pq(pasta, "silver_whatsapp")
    tme_dur = con.execute(
        f"SELECT count(*) FILTER (WHERE flag_tme_maior_duracao) FROM {wa}"
    ).fetchone()[0]
    assert tme_dur == 64
    assert (
        con.execute(
            f"SELECT count(*) FILTER (WHERE flag_tme_maior_duracao) FROM {video}"
        ).fetchone()[0]
        == 4
    )
    totem = _pq(pasta, "silver_totem")
    assert (
        con.execute(
            f"SELECT count(*) FILTER (WHERE flag_duracao_zero) FROM {totem}"
        ).fetchone()[0]
        == 183
    )
    # nenhum tempo ilegivel e nenhuma data nula nos canais reais
    for tabela in silver.TABELAS:
        pq = _pq(pasta, tabela)
        assert (
            con.execute(
                f"SELECT count(*) FILTER (WHERE flag_tempo_invalido OR data_hora_contato IS NULL) FROM {pq}"
            ).fetchone()[0]
            == 0
        )
    # whatsapp: so o AfterHour 0 e conflitante; o resto do dominio esta ok
    status = dict(
        con.execute(
            f"SELECT after_hour_status, count(*) FROM {wa} GROUP BY 1"
        ).fetchall()
    )
    assert status == {"conflito_dicionario": 1494}
    assert (
        con.execute(
            f"SELECT count(*) FROM {cc} WHERE flag_dominio_inconsistente"
        ).fetchone()[0]
        == 0
    )


@pytest.mark.integration
@pytestmark_real
def test_idempotencia_duas_execucoes_mesmo_conteudo(silver_real):
    con = duckdb.connect()
    for tabela in silver.TABELAS:
        hashes = []
        for chave in ("a", "b"):
            pq = _pq(silver_real[chave], tabela)
            hashes.append(
                con.execute(
                    f"SELECT sha256(string_agg(CAST(t AS VARCHAR), '|' ORDER BY contato_id)) FROM {pq} AS t"
                ).fetchone()[0]
            )
        assert hashes[0] == hashes[1], tabela
        schemas = [
            con.execute(
                f"DESCRIBE SELECT * FROM {_pq(silver_real[k], tabela)}"
            ).fetchall()
            for k in ("a", "b")
        ]
        assert schemas[0] == schemas[1]
        ids = [
            con.execute(
                f"SELECT sha256(string_agg(contato_id || coalesce(aluno_hash, ''), '|' ORDER BY contato_id)) "
                f"FROM {_pq(silver_real[k], tabela)}"
            ).fetchone()[0]
            for k in ("a", "b")
        ]
        assert ids[0] == ids[1]
