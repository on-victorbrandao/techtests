"""Testes da camada Bronze e dicionarios da Fase 1."""

import csv
import json
import re
from pathlib import Path

import pytest

from cogna_etl.bronze import (
    COLUMN_MAPPINGS,
    normalize_bronze,
    validate_table_structure,
)
from cogna_etl.dictionaries import generate_all_dictionaries


@pytest.fixture(scope="module")
def run_setup():
    # executa a normalizacao e geracao dos dicionarios uma vez para a suite
    normalize_bronze()
    generate_all_dictionaries()


@pytest.mark.parametrize(
    "raw_name,meta",
    list(COLUMN_MAPPINGS.items()),
)
def test_bronze_row_and_col_counts_match_raw(run_setup, raw_name, meta):
    # compara contagens totais de linhas e colunas entre raw e bronze
    raw_path = Path("data/raw") / raw_name
    bronze_path = Path("data/bronze") / meta["output_name"]

    assert bronze_path.exists(), f"Arquivo bronze {bronze_path} ausente."

    with open(raw_path, "r", encoding="utf-8-sig", newline="") as f_raw:
        raw_rows = list(csv.reader(f_raw, delimiter=";"))

    with open(bronze_path, "r", encoding="utf-8-sig", newline="") as f_brz:
        brz_rows = list(csv.reader(f_brz, delimiter=";"))

    assert len(brz_rows) == len(raw_rows)
    assert len(brz_rows[0]) == len(raw_rows[0])


@pytest.mark.parametrize(
    "raw_name,meta",
    list(COLUMN_MAPPINGS.items()),
)
def test_bronze_data_values_identical_to_raw(run_setup, raw_name, meta):
    # confere se cada celula de dados da bronze e exatamente igual a raw
    raw_path = Path("data/raw") / raw_name
    bronze_path = Path("data/bronze") / meta["output_name"]

    with open(raw_path, "r", encoding="utf-8-sig", newline="") as f_raw:
        raw_rows = list(csv.reader(f_raw, delimiter=";"))

    with open(bronze_path, "r", encoding="utf-8-sig", newline="") as f_brz:
        brz_rows = list(csv.reader(f_brz, delimiter=";"))

    for idx in range(1, len(raw_rows)):
        assert brz_rows[idx] == raw_rows[idx]


@pytest.mark.parametrize(
    "raw_name,meta",
    list(COLUMN_MAPPINGS.items()),
)
def test_bronze_headers_snake_case_and_unique(run_setup, raw_name, meta):
    # valida se todas as colunas de saida sao unicas e estao em snake_case
    bronze_path = Path("data/bronze") / meta["output_name"]
    with open(bronze_path, "r", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f, delimiter=";"))

    assert len(header) == len(set(header))
    pattern = re.compile(r"^[a-z0-9_]+$")
    for col in header:
        assert pattern.match(col)


def test_video_unnamed_column_explicitly_named(run_setup):
    # verifica se a coluna que veio sem nome recebeu o rotulo explicito
    video_path = Path("data/bronze/analitico_video_chamada.csv")
    with open(video_path, "r", encoding="utf-8-sig", newline="") as f:
        header = next(csv.reader(f, delimiter=";"))

    assert header[2] == "calldate_sem_ms"


@pytest.mark.parametrize(
    "dict_key,expected_min_fields",
    [
        ("callcenter", 10),
        ("whatsapp", 14),
        ("video_chamada", 5),
        ("totem", 6),
    ],
)
def test_dictionaries_json_structure_and_forward_fill(
    run_setup, dict_key, expected_min_fields
):
    # checa se o json foi gerado com estrutura valida e campos preenchidos
    json_path = Path(f"data/dictionaries/{dict_key}_dicionario.json")
    assert json_path.exists()

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert len(data) >= expected_min_fields
    assert "" not in data
    for field, content in data.items():
        assert "descricao" in content
        assert "dominio" in content
        assert "campo_bronze" in content


def test_validation_reordered_columns_raises_error():
    # garante que colunas fora de ordem geram erro explicito
    mapping = [("col_a", "col_a_norm"), ("col_b", "col_b_norm")]
    reordered_header = ["col_b", "col_a"]
    rows = [["1", "2"]]

    with pytest.raises(ValueError, match="Cabecalho raw diverge"):
        validate_table_structure(reordered_header, rows, mapping, "teste_reord")


def test_validation_unexpected_column_name_raises_error():
    # garante que coluna com nome inesperado gera erro explicito
    mapping = [("col_a", "col_a_norm"), ("col_b", "col_b_norm")]
    wrong_header = ["col_a", "col_inesperada"]
    rows = [["1", "2"]]

    with pytest.raises(ValueError, match="Cabecalho raw diverge"):
        validate_table_structure(wrong_header, rows, mapping, "teste_nome")


def test_validation_duplicate_output_names_raises_error():
    # garante que colunas de saida duplicadas geram erro explicito
    dup_mapping = [("col_a", "mesmo_nome"), ("col_b", "mesmo_nome")]
    header = ["col_a", "col_b"]
    rows = [["1", "2"]]

    with pytest.raises(ValueError, match="Colunas de saida duplicadas"):
        validate_table_structure(header, rows, dup_mapping, "teste_duplicados")


def test_validation_incorrect_record_field_count_raises_error():
    # garante que linha com quantidade incorreta de colunas gera erro explicito
    mapping = [("col_a", "col_a_norm"), ("col_b", "col_b_norm")]
    header = ["col_a", "col_b"]
    bad_rows = [["1", "2"], ["apenas_uma_coluna"]]

    with pytest.raises(ValueError, match="Linha 3.*tem 1 campos, esperado 2"):
        validate_table_structure(header, bad_rows, mapping, "teste_tamanho")
