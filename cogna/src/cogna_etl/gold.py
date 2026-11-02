"""Executor fino da Gold: roda os SQLs do modelo estrela e queries analiticas.

Nenhuma regra de negocio fica em Python; tudo esta em sql/model e sql/analytics.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path

import duckdb

SQL_MACROS = Path("sql/staging/00_macros.sql")
SQL_MODEL_DIR = Path("sql/model")
SQL_ANALYTICS_DIR = Path("sql/analytics")
SILVER_DIR_PADRAO = Path("data/silver")
GOLD_DIR_PADRAO = Path("data/gold")

TABELAS_SILVER = [
    "silver_callcenter",
    "silver_whatsapp",
    "silver_video_chamada",
    "silver_totem",
]

SQL_MODEL = [
    "01_dim_calendario.sql",
    "02_dim_hora.sql",
    "03_dim_canal.sql",
    "04_dim_aluno.sql",
    "05_dim_agente.sql",
    "06_dim_fila.sql",
    "07_dim_perfil_aluno.sql",
    "08_dim_motivo.sql",
    "09_fato_contato.sql",
    "10_fato_navegacao.sql",
    "11_fato_jornada.sql",
]

SQL_ANALYTICS = [
    "q01_cc_para_whatsapp.sql",
    "q02_cc_wa_outro_canal.sql",
    "q03_principais_motivos.sql",
    "q04_perfil_retencao_e_contato_anterior.sql",
    "q05_comportamento_antes_retencao.sql",
    "q06_canal_pior_nota.sql",
    "q07_perfil_nota_ruim.sql",
    "q08_dnasoa_influencia_nota.sql",
    "q09_agente_recontato_mesmo_dia.sql",
]

# chave primaria (expressao SQL) de cada tabela da Gold para checar unicidade
CHAVES_PK = {
    "dim_calendario": "data",
    "dim_hora": "hora_inteira",
    "dim_canal": "canal_id",
    "dim_aluno": "aluno_hash",
    "dim_agente": "agente_id",
    "dim_fila": "fila_id",
    "dim_perfil_aluno": "perfil_id",
    "dim_motivo": "motivo_id",
    "fato_contato": "contato_id",
    "fato_navegacao": (
        "contato_id || '|' || tipo_sequencia || '|' || CAST(ordem_passo AS VARCHAR)"
    ),
    "fato_jornada": "contato_id",
}

# relacionamentos (tabela_filha, coluna_fk, tabela_pai, coluna_pk)
CHAVES_FK = [
    ("fato_contato", "aluno_hash", "dim_aluno", "aluno_hash"),
    ("fato_contato", "canal_id", "dim_canal", "canal_id"),
    ("fato_contato", "canal", "dim_canal", "canal"),
    ("fato_contato", "data_contato", "dim_calendario", "data"),
    ("fato_contato", "hora_inteira", "dim_hora", "hora_inteira"),
    ("fato_contato", "agente_id", "dim_agente", "agente_id"),
    ("fato_contato", "fila_id", "dim_fila", "fila_id"),
    ("fato_contato", "perfil_id", "dim_perfil_aluno", "perfil_id"),
    ("fato_contato", "motivo_id", "dim_motivo", "motivo_id"),
    ("fato_navegacao", "contato_id", "fato_contato", "contato_id"),
    ("fato_jornada", "contato_id", "fato_contato", "contato_id"),
]

COLUNAS_PROIBIDAS_LGPD = {
    "aluno_id_original",
    "agente_original",
    "supervisor_original",
}


class ValidacaoGoldError(RuntimeError):
    """A camada Gold nao passou nas validacoes de integridade ou LGPD."""


def carregar_views_silver(con: duckdb.DuckDBPyConnection, silver_dir: Path) -> None:
    """Registra os 4 Parquets da Silver como views na conexao DuckDB."""
    for nome in TABELAS_SILVER:
        arq = (Path(silver_dir) / f"{nome}.parquet").as_posix()
        if not Path(arq).exists():
            raise ValidacaoGoldError(f"Parquet da Silver ausente: {arq}")
        sql = f"CREATE OR REPLACE VIEW {nome} AS SELECT * FROM read_parquet('{arq}')"
        con.execute(sql)


def rodar_modelo_gold(con: duckdb.DuckDBPyConnection) -> None:
    """Executa as macros e os scripts SQL do modelo estrela em ordem."""
    con.execute(SQL_MACROS.read_text(encoding="utf-8"))
    for arq in SQL_MODEL:
        con.execute((SQL_MODEL_DIR / arq).read_text(encoding="utf-8"))


def contar_tabelas_gold(con: duckdb.DuckDBPyConnection) -> dict[str, int]:
    """Retorna a contagem de linhas de cada tabela do modelo estrela."""
    res = {}
    for tabela in CHAVES_PK:
        res[tabela] = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    return res


def validar_modelo_gold(
    con: duckdb.DuckDBPyConnection, exigir_5991: bool = True
) -> None:
    """Valida LGPD, contagem da fato_contato, unicidade de PK e integridade de FK."""
    soma_silver = sum(
        con.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in TABELAS_SILVER
    )
    qtd_fato = con.execute("SELECT count(*) FROM fato_contato").fetchone()[0]
    if qtd_fato != soma_silver:
        raise ValidacaoGoldError(f"fato_contato ({qtd_fato}) != silver ({soma_silver})")
    if exigir_5991 and qtd_fato != 5991:
        raise ValidacaoGoldError(f"fato_contato esperado 5991, obtido {qtd_fato}")
    _validar_lgpd_e_pks(con)
    _validar_fks(con)


def _validar_lgpd_e_pks(con: duckdb.DuckDBPyConnection) -> None:
    """Verifica ausencia de colunas sensiveis e unicidade de chave primaria."""
    for tabela, expr_pk in CHAVES_PK.items():
        cols = {c[0] for c in con.execute(f"DESCRIBE {tabela}").fetchall()}
        vazadas = cols.intersection(COLUNAS_PROIBIDAS_LGPD)
        if vazadas:
            raise ValidacaoGoldError(f"{tabela}: coluna sensivel exposta {vazadas}")
        total, distintos = con.execute(
            f"SELECT count(*), count(DISTINCT ({expr_pk})) FROM {tabela}"
        ).fetchone()
        if total != distintos:
            raise ValidacaoGoldError(f"{tabela}: PK duplicada ({distintos} de {total})")


def _validar_fks(con: duckdb.DuckDBPyConnection) -> None:
    """Verifica integridade referencial de todas as chaves estrangeiras."""
    for filha, fk, pai, pk in CHAVES_FK:
        orfaos = con.execute(
            f"SELECT count(*) FROM {filha} f "
            f"LEFT JOIN {pai} p ON p.{pk} = f.{fk} "
            f"WHERE f.{fk} IS NULL OR p.{pk} IS NULL"
        ).fetchone()[0]
        if orfaos > 0:
            msg = f"FK quebrada: {filha}.{fk} -> {pai}.{pk} ({orfaos})"
            raise ValidacaoGoldError(msg)


def exportar_tabelas_gold(con: duckdb.DuckDBPyConnection, gold_dir: Path) -> list[Path]:
    """Grava Parquet (SNAPPY) e CSV (; UTF-8 com BOM) de forma atomica."""
    gold_dir = Path(gold_dir)
    gold_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp_gold_", dir=gold_dir))
    try:
        for tabela in CHAVES_PK:
            _gravar_parquet_e_csv_tmp(con, tabela, tmp)
        finais = []
        for tabela in CHAVES_PK:
            for ext in (".parquet", ".csv"):
                final = gold_dir / f"{tabela}{ext}"
                os.replace(tmp / f"{tabela}{ext}", final)
                finais.append(final)
        return finais
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _gravar_parquet_e_csv_tmp(
    con: duckdb.DuckDBPyConnection, tabela: str, tmp: Path
) -> None:
    """Grava Parquet SNAPPY e CSV com BOM na pasta temporaria e confere linhas."""
    pq_path = (tmp / f"{tabela}.parquet").as_posix()
    csv_raw = tmp / f"{tabela}.raw.csv"
    csv_final = tmp / f"{tabela}.csv"
    con.execute(f"COPY {tabela} TO '{pq_path}' (FORMAT parquet, COMPRESSION snappy)")
    raw_posix = csv_raw.as_posix()
    con.execute(
        f"COPY {tabela} TO '{raw_posix}' (FORMAT csv, DELIMITER ';', HEADER true)"
    )
    # adiciona BOM UTF-8 no inicio do CSV para leitura direta no Excel/Power BI
    conteudo = csv_raw.read_bytes()
    csv_final.write_bytes(b"\xef\xbb\xbf" + conteudo)
    csv_raw.unlink()
    qtd_tb = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    sql_pq = f"SELECT count(*) FROM read_parquet('{pq_path}')"
    qtd_pq = con.execute(sql_pq).fetchone()[0]
    if qtd_pq != qtd_tb:
        raise ValidacaoGoldError(f"{tabela}: parquet gravado com {qtd_pq} de {qtd_tb}")


def executar_analytics(con: duckdb.DuckDBPyConnection) -> dict[str, list[dict]]:
    """Executa q01..q09 sobre o modelo estrela e devolve dicionario serializavel."""
    resultados: dict[str, list[dict]] = {}
    for arq in SQL_ANALYTICS:
        chave = arq.removesuffix(".sql")
        sql = (SQL_ANALYTICS_DIR / arq).read_text(encoding="utf-8")
        cur = con.execute(sql)
        colunas = [d[0] for d in cur.description]
        linhas = cur.fetchall()
        resultados[chave] = [dict(zip(colunas, linha)) for linha in linhas]
    return resultados


def salvar_analytics_json(resultados: dict[str, list[dict]], gold_dir: Path) -> Path:
    """Salva o JSON de resultados analiticos em data/gold/analytics_results.json."""
    destino = Path(gold_dir) / "analytics_results.json"
    destino.write_text(
        json.dumps(resultados, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return destino


def run_gold(
    silver_dir: Path = SILVER_DIR_PADRAO,
    gold_dir: Path = GOLD_DIR_PADRAO,
    exigir_5991: bool = True,
) -> dict[str, int]:
    """Executa a camada Gold (modelo estrela, exportacao e queries Q1-Q9)."""
    con = duckdb.connect()
    try:
        carregar_views_silver(con, silver_dir)
        rodar_modelo_gold(con)
        validar_modelo_gold(con, exigir_5991=exigir_5991)
        exportar_tabelas_gold(con, gold_dir)
        resultados = executar_analytics(con)
        salvar_analytics_json(resultados, gold_dir)
        return contar_tabelas_gold(con)
    finally:
        con.close()
