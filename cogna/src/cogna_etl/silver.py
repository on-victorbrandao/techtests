"""Executor fino da Silver: roda os SQLs em ordem e grava os Parquets.

Nenhuma regra de negocio fica aqui, tudo esta em sql/staging.
"""

import os
import shutil
import tempfile
from pathlib import Path

import duckdb

SQL_DIR = Path("sql/staging")
XLSX_PADRAO = Path("data/raw/analytical_database_callcenter.xlsx")
DIC_DIR_PADRAO = Path("data/dictionaries")
SILVER_DIR_PADRAO = Path("data/silver")

# nome da variavel de ambiente com o salt do hash do aluno
VAR_SALT = "ALUNO_HASH_SALT"

# ordem dos scripts: macros, entradas lidas do XLSX/JSON e a Silver propriamente dita
SQL_ENTRADAS = ["01_raw_xlsx.sql", "02_dic_dominio.sql"]
SQL_TRANSFORMACAO = [
    "00_macros.sql",
    "03_guarda_salt.sql",
    "04_dominio_canonico.sql",
    "05_silver_callcenter.sql",
    "06_silver_whatsapp.sql",
    "07_silver_video_chamada.sql",
    "08_silver_totem.sql",
]

# tabela de saida de cada canal e a tabela de entrada correspondente
TABELAS = {
    "silver_callcenter": "raw_cc",
    "silver_whatsapp": "raw_wa",
    "silver_video_chamada": "raw_video",
    "silver_totem": "raw_totem",
}


class SaltAusenteError(RuntimeError):
    """Salt do hash do aluno nao foi configurado."""


class ValidacaoSilverError(RuntimeError):
    """A saida da Silver nao passou na validacao antes de ser gravada."""


def ler_salt(env_path: Path = Path(".env")) -> str:
    """Le o salt do ambiente ou do .env; falha se nao existir."""
    salt = os.environ.get(VAR_SALT, "").strip()
    if not salt and env_path.exists():
        for linha in env_path.read_text(encoding="utf-8").splitlines():
            chave, _, valor = linha.partition("=")
            if chave.strip() == VAR_SALT:
                salt = valor.strip().strip('"').strip("'")
    if not salt:
        raise SaltAusenteError(
            f"{VAR_SALT} ausente. Copie .env.example para .env e preencha "
            f"{VAR_SALT} com o salt do projeto antes de rodar a silver."
        )
    return salt


def abrir_conexao(salt: str) -> duckdb.DuckDBPyConnection:
    """Abre o DuckDB em memoria, carrega a extensao excel e passa o salt."""
    con = duckdb.connect()
    # a extensao excel e core e so baixa na primeira vez
    con.execute("INSTALL excel")
    con.execute("LOAD excel")
    con.execute("SET VARIABLE salt = ?", [salt])
    return con


def rodar_sql(con: duckdb.DuckDBPyConnection, arquivos: list[str]) -> None:
    """Executa os scripts SQL na ordem informada."""
    for nome in arquivos:
        con.execute((SQL_DIR / nome).read_text(encoding="utf-8"))


def contar_tabelas(con: duckdb.DuckDBPyConnection) -> dict[str, tuple[int, int]]:
    """Retorna (linhas de entrada, linhas de saida) por tabela da Silver."""
    res = {}
    for saida, entrada in TABELAS.items():
        qtd_in = con.execute(f"SELECT count(*) FROM {entrada}").fetchone()[0]
        qtd_out = con.execute(f"SELECT count(*) FROM {saida}").fetchone()[0]
        res[saida] = (qtd_in, qtd_out)
    return res


def validar_tabelas(con: duckdb.DuckDBPyConnection) -> None:
    """Confere se nenhuma linha sumiu e se contato_id e unico por tabela."""
    for saida, (qtd_in, qtd_out) in contar_tabelas(con).items():
        if qtd_in != qtd_out:
            raise ValidacaoSilverError(f"{saida}: entrada {qtd_in}, saida {qtd_out}")
        unicos = con.execute(f"SELECT count(DISTINCT contato_id) FROM {saida}")
        if unicos.fetchone()[0] != qtd_out:
            raise ValidacaoSilverError(f"{saida}: contato_id duplicado")


def gravar_parquets(con: duckdb.DuckDBPyConnection, silver_dir: Path) -> list[Path]:
    """Grava em pasta temporaria, valida e so depois troca a saida anterior."""
    silver_dir.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=".tmp_silver_", dir=silver_dir))
    try:
        for tabela in TABELAS:
            destino = (tmp / f"{tabela}.parquet").as_posix()
            con.execute(f"COPY {tabela} TO '{destino}' (FORMAT parquet)")
            _validar_parquet(con, tabela, destino)
        finais = []
        for tabela in TABELAS:
            final = silver_dir / f"{tabela}.parquet"
            os.replace(tmp / f"{tabela}.parquet", final)
            finais.append(final)
        return finais
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _validar_parquet(con: duckdb.DuckDBPyConnection, tabela: str, arq: str) -> None:
    """Compara contagem e schema do Parquet gravado com a tabela de origem."""
    qtd_pq = con.execute(f"SELECT count(*) FROM read_parquet('{arq}')").fetchone()[0]
    qtd_tb = con.execute(f"SELECT count(*) FROM {tabela}").fetchone()[0]
    if qtd_pq != qtd_tb:
        raise ValidacaoSilverError(f"{tabela}: parquet com {qtd_pq} de {qtd_tb}")
    schema_pq = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{arq}')").fetchall()
    schema_tb = con.execute(f"DESCRIBE {tabela}").fetchall()
    if [(c[0], c[1]) for c in schema_pq] != [(c[0], c[1]) for c in schema_tb]:
        raise ValidacaoSilverError(f"{tabela}: schema do parquet diferente")


def run_silver(
    xlsx_path: Path = XLSX_PADRAO,
    dic_dir: Path = DIC_DIR_PADRAO,
    silver_dir: Path = SILVER_DIR_PADRAO,
    env_path: Path = Path(".env"),
) -> dict[str, tuple[int, int]]:
    """Roda a Silver completa e retorna (entrada, saida) por tabela."""
    salt = ler_salt(env_path)
    con = abrir_conexao(salt)
    try:
        con.execute("SET VARIABLE xlsx_path = ?", [Path(xlsx_path).as_posix()])
        con.execute("SET VARIABLE dic_dir = ?", [Path(dic_dir).as_posix()])
        rodar_sql(con, ["00_macros.sql"] + SQL_ENTRADAS)
        rodar_sql(con, SQL_TRANSFORMACAO)
        validar_tabelas(con)
        gravar_parquets(con, Path(silver_dir))
        return contar_tabelas(con)
    finally:
        con.close()
