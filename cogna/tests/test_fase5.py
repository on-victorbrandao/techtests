"""Testes automatizados da camada semantica Power BI (Power Query M e DAX).

Valida os 12 scripts .pq em powerbi/m/, os 6 arquivos .dax em powerbi/dax/
e a documentacao tecnica em docs/camada_semantica_powerbi.md contra os
schemas reais de data/gold/*.parquet.
"""

import re
from pathlib import Path

import duckdb

M_DIR = Path("powerbi/m")
DAX_DIR = Path("powerbi/dax")
GOLD_DIR = Path("data/gold")
DOC_PATH = Path("docs/camada_semantica_powerbi.md")

TABELAS_GOLD = [
    "dim_calendario",
    "dim_hora",
    "dim_canal",
    "dim_aluno",
    "dim_agente",
    "dim_fila",
    "dim_perfil_aluno",
    "dim_motivo",
    "fato_contato",
    "fato_navegacao",
    "fato_jornada",
]

ARQUIVOS_DAX = [
    "01_base_volumetria.dax",
    "02_satisfacao_pesquisa.dax",
    "03_tempo_operacional.dax",
    "04_retencao_e_cancelamento.dax",
    "05_jornada_e_recontato_q1_q2_q9.dax",
    "06_navegacao_ura_q8.dax",
]

# transformacoes de negocio ou chamadas externas proibidas nos scripts Power Query M
TRANSFORMACOES_PROIBIDAS_M = [
    "Table.SelectRows",
    "Table.AddColumn",
    "Table.NestedJoin",
    "Table.Join",
    "Table.Combine",
    "Table.Group",
    "Table.RemoveColumns",
    "Table.RenameColumns",
    "Table.ReplaceValue",
    "Table.Filter",
    "Web.Contents",
    "Json.Document",
    "Excel.Workbook",
]

# mapeamento esperado entre tipos fisicos do DuckDB/Parquet e tipos do Power Query M
MAPA_TIPOS_DUCKDB_PARA_M = {
    "VARCHAR": "type text",
    "INTEGER": "Int64.Type",
    "BIGINT": "Int64.Type",
    "DOUBLE": "type number",
    "BOOLEAN": "type logical",
    "DATE": "type date",
    "TIMESTAMP": "type datetime",
}


def _carregar_schema_gold() -> dict[str, dict[str, str]]:
    """Retorna {tabela: {coluna: tipo_duckdb}} lendo os Parquets reais de data/gold/."""
    con = duckdb.connect()
    try:
        schemas: dict[str, dict[str, str]] = {}
        for tabela in TABELAS_GOLD:
            pq = (GOLD_DIR / f"{tabela}.parquet").as_posix()
            rows = con.execute(
                f"DESCRIBE SELECT * FROM read_parquet('{pq}')"
            ).fetchall()
            schemas[tabela] = {r[0]: r[1] for r in rows}
        return schemas
    finally:
        con.close()


def _remover_comentarios_dax(texto: str) -> str:
    """Remove linhas de comentario iniciadas por -- em arquivos DAX."""
    return "\n".join(
        linha for linha in texto.splitlines() if not linha.strip().startswith("--")
    )


def _extrair_blocos_medidas(texto: str) -> list[tuple[str, str]]:
    """Extrai lista de (nome_medida, corpo_expressao) de um arquivo .dax."""
    linhas = _remover_comentarios_dax(texto).splitlines()
    medidas: list[tuple[str, str]] = []
    nome_atual: str | None = None
    buffer: list[str] = []
    for linha in linhas:
        if not linha.strip():
            continue
        # inicio de medida: linha na coluna 0 sem VAR/RETURN e terminando com '='
        eh_cabecalho = (
            not linha.startswith(" ")
            and linha.rstrip().endswith("=")
            and not linha.lstrip().upper().startswith(("VAR ", "RETURN"))
        )
        if eh_cabecalho:
            if nome_atual is not None:
                medidas.append((nome_atual, "\n".join(buffer)))
            nome_atual = linha.rstrip()[:-1].strip()
            buffer = []
        elif nome_atual is not None:
            buffer.append(linha)
    if nome_atual is not None:
        medidas.append((nome_atual, "\n".join(buffer)))
    return medidas


def _extrair_argumentos_funcao(corpo: str, nome_funcao: str) -> list[list[str]]:
    """Extrai os argumentos de cada chamada de funcao respeitando parenteses."""
    padrao = re.compile(rf"\b{nome_funcao}\s*\(")
    chamadas: list[list[str]] = []
    for match in padrao.finditer(corpo):
        idx = match.end()
        nivel = 1
        em_aspas = False
        atual: list[str] = []
        args: list[str] = []
        while idx < len(corpo) and nivel > 0:
            ch = corpo[idx]
            if ch == '"':
                em_aspas = not em_aspas
                atual.append(ch)
            elif not em_aspas:
                if ch == "(":
                    nivel += 1
                    atual.append(ch)
                elif ch == ")":
                    nivel -= 1
                    if nivel == 0:
                        args.append("".join(atual).strip())
                        break
                    atual.append(ch)
                elif ch == "," and nivel == 1:
                    args.append("".join(atual).strip())
                    atual = []
                else:
                    atual.append(ch)
            else:
                atual.append(ch)
            idx += 1
        chamadas.append(args)
    return chamadas


def test_scripts_powerquery_m_existem_e_sao_enxutos() -> None:
    """Verifica os 12 arquivos .pq em powerbi/m/ e regras de codigo enxuto."""
    arquivos_esperados = {"pDataPath.pq"} | {f"{t}.pq" for t in TABELAS_GOLD}
    arquivos_encontrados = {p.name for p in M_DIR.glob("*.pq")}
    assert arquivos_encontrados == arquivos_esperados

    # valida o parametro pDataPath.pq
    texto_param = (M_DIR / "pDataPath.pq").read_text(encoding="utf-8")
    assert "IsParameterQuery = true" in texto_param
    assert 'Type = "Text"' in texto_param
    assert "data\\gold" in texto_param

    # valida cada uma das 11 tabelas da Gold
    for tabela in TABELAS_GOLD:
        texto = (M_DIR / f"{tabela}.pq").read_text(encoding="utf-8")
        # corpo ativo sem os comentarios
        codigo_ativo = "\n".join(
            ln for ln in texto.splitlines() if not ln.strip().startswith("//")
        )
        assert (
            f'Parquet.Document(File.Contents(pDataPath & "\\{tabela}.parquet"))'
            in codigo_ativo
        )
        assert "Table.TransformColumnTypes" in codigo_ativo
        for proibido in TRANSFORMACOES_PROIBIDAS_M:
            assert proibido not in codigo_ativo, (
                f"{tabela}.pq contem transformacao proibida: {proibido}"
            )


def test_scripts_powerquery_m_batem_exatamente_com_schema_gold() -> None:
    """Confere se as colunas e tipos em M batem 1:1 com os Parquets da Gold."""
    schemas_gold = _carregar_schema_gold()
    padrao_par = re.compile(r'\{\s*"([^"]+)"\s*,\s*([A-Za-z0-9_. ]+?)\s*\}')

    for tabela, cols_esperadas in schemas_gold.items():
        texto = (M_DIR / f"{tabela}.pq").read_text(encoding="utf-8")
        codigo_ativo = "\n".join(
            ln for ln in texto.splitlines() if not ln.strip().startswith("//")
        )
        pares = padrao_par.findall(codigo_ativo)
        cols_m = {col: tipo.strip() for col, tipo in pares}

        # mesma lista e mesma ordem de colunas do Parquet
        assert list(cols_m.keys()) == list(cols_esperadas.keys()), (
            f"Colunas divergentes em {tabela}.pq"
        )
        for col, tipo_duck in cols_esperadas.items():
            tipo_m_esperado = MAPA_TIPOS_DUCKDB_PARA_M[tipo_duck]
            assert cols_m[col] == tipo_m_esperado, (
                f"{tabela}.{col}: esperado {tipo_m_esperado}, obtido {cols_m[col]}"
            )


def test_arquivos_dax_sintaxe_balanceada_var_return_e_divide_seguro() -> None:
    """Valida os 6 arquivos .dax, parenteses/aspas, VAR/RETURN e DIVIDE(3 args)."""
    encontrados = sorted(p.name for p in DAX_DIR.glob("*.dax"))
    assert encontrados == ARQUIVOS_DAX

    total_medidas = 0
    for nome_arq in ARQUIVOS_DAX:
        texto = (DAX_DIR / nome_arq).read_text(encoding="utf-8")
        assert "Display Folder:" in texto
        assert "Format String:" in texto

        sem_coment = _remover_comentarios_dax(texto)
        # parenteses e chaves balanceados e aspas duplas em numero par
        assert sem_coment.count("(") == sem_coment.count(")"), (
            f"Parenteses desbalanceados em {nome_arq}"
        )
        assert sem_coment.count("{") == sem_coment.count("}"), (
            f"Chaves desbalanceadas em {nome_arq}"
        )
        assert sem_coment.count('"') % 2 == 0, f"Aspas desbalanceadas em {nome_arq}"

        medidas = _extrair_blocos_medidas(texto)
        assert len(medidas) >= 6, f"Poucas medidas em {nome_arq}: {len(medidas)}"
        total_medidas += len(medidas)

        for nome_medida, corpo in medidas:
            if re.search(r"\bvar\b|\bVAR\b", corpo):
                assert re.search(r"\breturn\b|\bRETURN\b", corpo), (
                    f"Medida '{nome_medida}' sem RETURN"
                )
            assert corpo.count("(") == corpo.count(")"), (
                f"Parenteses desbalanceados na medida '{nome_medida}'"
            )
            for args_divide in _extrair_argumentos_funcao(corpo, "DIVIDE"):
                assert len(args_divide) == 3, (
                    f"DIVIDE sem 3o argumento em '{nome_medida}': {args_divide}"
                )

    assert total_medidas >= 55


def test_arquivos_dax_referenciam_apenas_tabelas_e_colunas_reais_da_gold() -> None:
    """Garante que toda referencia tabela[coluna] nos .dax existe no schema da Gold."""
    schemas_gold = _carregar_schema_gold()
    padrao_ref = re.compile(r"\b([a-z_][a-z0-9_]*)\[([a-z0-9_]+)\]")

    for nome_arq in ARQUIVOS_DAX:
        texto = _remover_comentarios_dax(
            (DAX_DIR / nome_arq).read_text(encoding="utf-8")
        )
        for tabela, coluna in padrao_ref.findall(texto):
            assert tabela in schemas_gold, f"{nome_arq}: tabela inexistente '{tabela}'"
            assert coluna in schemas_gold[tabela], (
                f"{nome_arq}: coluna inexistente '{tabela}[{coluna}]'"
            )


def test_cobertura_metricas_q1_a_q9_e_documentacao_semantica() -> None:
    """Confere a presenca das medidas de Q1 a Q9 e a documentacao da camada."""
    conteudo_dax = "\n".join(
        (DAX_DIR / arq).read_text(encoding="utf-8") for arq in ARQUIVOS_DAX
    )
    medidas_obrigatorias = [
        "#01_Total_Contatos =",
        "#02_Alunos_Distintos =",
        "#03_Media_Contatos_Por_Aluno =",
        "#09_Contatos_Motivo_Preenchido =",
        "#10_%_Preenchimento_Motivo =",
        "#01_Contatos_Pesquisa_Respondida =",
        "#02_Taxa_Resposta_Pesquisa =",
        "#03_Soma_Notas_Validas =",
        "#04_Nota_Media_Satisfacao =",
        "#05_Contatos_Nota_Ruim =",
        "#06_%_Notas_Ruins =",
        "#10_Guardrail_Cobertura_Amostral =",
        "#01_Duracao_Media_s =",
        "#02_Duracao_Mediana_s =",
        "#03_TME_Medio_s =",
        "#04_TME_Mediano_s =",
        "#06_Contatos_TME_Maior_Duracao =",
        "#08_Contatos_Duracao_Zero =",
        "#01_Contatos_Fila_Retencao =",
        "#02_Contatos_Fila_CRA_Retencao =",
        "#03_Contatos_Assunto_Retencao =",
        "#09_Pedidos_Cancelamento =",
        "#11_Alunos_Mantidos_Retencao =",
        "#13_Pedidos_Transferencia =",
        "#15_Pedidos_Trancamento =",
        "#17_Pedidos_Cancelamento_CC_Com_Outro_Canal_Anterior =",
        "#21_Media_Contatos_Previos_Fila_Retencao =",
        "#22_Mediana_Contatos_Previos_Fila_Retencao =",
        "#23_Tempo_Mediano_Desde_Ultimo_Contato_Ate_Retencao_h =",
        "#01_Q1_Alunos_Call_Center_WhatsApp_Posterior =",
        "#03_Q1_Contatos_Call_Center_WhatsApp_Posterior =",
        "#05_Q1_Contatos_CC_Transicao_Imediata_WhatsApp =",
        "#09_Q1_Contatos_Call_Center_WhatsApp_24h =",
        "#10_Q1_Contatos_Call_Center_WhatsApp_7d =",
        "#11_Q2_Alunos_Trinca_CC_WA_Outro_Canal =",
        "#12_Q2_Trincas_CC_WA_Outro_Canal =",
        "#13_Q2_Alunos_Trinca_CC_WA_Video_Totem =",
        "#15_Q2_Alunos_Trinca_CC_WA_Qualquer_Canal =",
        "#17_Q2_Alunos_Sequencia_Intermediarios_CC_WA_Outro_Canal =",
        "#19_Q9_Atendimentos_Agente_Humano =",
        "#20_Q9_Recontatos_Mesmo_Dia_Omnichannel =",
        "#21_Q9_Taxa_Recontato_Mesmo_Dia_Omnichannel =",
        "#22_Q9_Recontatos_Mesmo_Dia_Intracanal =",
        "#23_Q9_Taxa_Recontato_Mesmo_Dia_Intracanal =",
        "#24_Contatos_Sobreposicao_Intracanal =",
        "#25_Contatos_Sobreposicao_Intercanal =",
        "#01_Q8_Contatos_Distintos_Ponto_Navegacao =",
        "#04_Q8_Nota_Media_Ponto_Navegacao =",
        "#06_Q8_%_Notas_Ruins_Ponto_Navegacao =",
    ]
    for assinatura in medidas_obrigatorias:
        assert assinatura in conteudo_dax, f"Medida obrigatoria ausente: {assinatura}"

    # verifica USERELATIONSHIP nas duas visoes da Q9
    rel_visao_a = (
        "USERELATIONSHIP ( "
        "fato_jornada[agente_id_atribuido_recontato], "
        "dim_agente[agente_id] )"
    )
    rel_visao_b = (
        "USERELATIONSHIP ( "
        "fato_jornada[agente_id_atribuido_recontato_intracanal], "
        "dim_agente[agente_id] )"
    )
    assert rel_visao_a in conteudo_dax
    assert rel_visao_b in conteudo_dax

    # verifica documentacao em docs/camada_semantica_powerbi.md
    assert DOC_PATH.exists()
    doc_txt = DOC_PATH.read_text(encoding="utf-8")
    assert "USERELATIONSHIP" in doc_txt
    assert "Sort By Column" in doc_txt
    for q in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9"):
        assert q in doc_txt
