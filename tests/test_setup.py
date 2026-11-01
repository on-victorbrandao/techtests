"""Testes automatizados de setup, inventario e reconciliacao da Fase 0."""

from pathlib import Path

import openpyxl
import pytest

from cogna_etl.inventory import (
    get_csv_metrics,
    get_xlsx_sheet_metrics,
)


@pytest.fixture(scope="module")
def raw_path() -> Path:
    p = Path("data/raw")
    assert p.exists(), "Diretorio data/raw deve existir."
    return p


def test_raw_files_exist_and_readonly(raw_path: Path):
    expected_files = [
        "analytical_database_callcenter.analitico_callcenter.csv",
        "analytical_database_callcenter.dicionario_callcenter.csv",
        "analytical_database_callcenter.analitico_whatsapp.csv",
        "analytical_database_callcenter.dicionario_whatsapp.csv",
        "analytical_database_callcenter.analitico_video_chamada.csv",
        "analytical_database_callcenter.dicionario_video_chamado.csv",
        "analytical_database_callcenter.analitico_totem.csv",
        "analytical_database_callcenter.dicionario_totem.csv",
        "analytical_database_callcenter.xlsx",
    ]
    for filename in expected_files:
        file_path = raw_path / filename
        assert file_path.exists(), f"Arquivo bruto {filename} ausente."


@pytest.mark.parametrize(
    "csv_name,sheet_name,expected_cols,expected_rows",
    [
        (
            "analytical_database_callcenter.analitico_callcenter.csv",
            "Analitico call center",
            22,
            1500,
        ),
        (
            "analytical_database_callcenter.dicionario_callcenter.csv",
            "Dicionario call center",
            4,
            35,
        ),
        (
            "analytical_database_callcenter.analitico_whatsapp.csv",
            "Analitico Whatsapp",
            19,
            1495,
        ),
        (
            "analytical_database_callcenter.dicionario_whatsapp.csv",
            "Dicionario_whatsapp",
            4,
            81,
        ),
        (
            "analytical_database_callcenter.analitico_video_chamada.csv",
            "Analitico_video_chamada",
            9,
            1500,
        ),
        (
            "analytical_database_callcenter.dicionario_video_chamado.csv",
            "Dicionario_video",
            2,
            10,
        ),
        (
            "analytical_database_callcenter.analitico_totem.csv",
            "Analitico_Totem",
            7,
            1500,
        ),
        (
            "analytical_database_callcenter.dicionario_totem.csv",
            "Dicionario_Totem",
            2,
            7,
        ),
    ],
)
def test_csv_reconciliation_with_xlsx(
    raw_path: Path,
    csv_name: str,
    sheet_name: str,
    expected_cols: int,
    expected_rows: int,
):
    csv_file = raw_path / csv_name
    xlsx_file = raw_path / "analytical_database_callcenter.xlsx"

    csv_m = get_csv_metrics(csv_file)
    assert csv_m["header_cols_count"] == expected_cols
    assert csv_m["parsed_records"] == expected_rows
    assert csv_m["encoding"] == "utf-8-sig"
    assert csv_m["delimiter"] == ";"

    wb = openpyxl.load_workbook(xlsx_file, read_only=True, data_only=True)
    xlsx_m = get_xlsx_sheet_metrics(wb, sheet_name)
    wb.close()

    assert xlsx_m["cols_count"] == expected_cols
    assert xlsx_m["total_rows"] == expected_rows
