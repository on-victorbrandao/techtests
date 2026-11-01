"""Modulo de inventario e reconciliacao inicial dos arquivos brutos."""

import csv
from pathlib import Path

import openpyxl


def detect_encoding(file_path: Path) -> str:
    # Testar codificacoes comuns para identificar compatibilidade
    for enc in ["utf-8-sig", "utf-8", "cp1252", "latin-1"]:
        try:
            with open(file_path, "r", encoding=enc) as f:
                f.read(1024 * 1024)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def get_csv_metrics(file_path: Path) -> dict:
    enc = detect_encoding(file_path)
    size_bytes = file_path.stat().st_size

    with open(file_path, "r", encoding=enc, newline="") as f:
        # Linhas de texto brutas (quebras de linha fisicas)
        raw_lines = sum(1 for _ in f)

        # Registros logicos via csv.reader (respeitando aspas e multilinhas)
        f.seek(0)
        reader = list(csv.reader(f, delimiter=";"))
        parsed_records = len(reader)
        header = reader[0] if reader else []

        # Contagem de linhas nao vazias
        non_empty_records = [r for r in reader if any(cell.strip() != "" for cell in r)]

    return {
        "file_name": file_path.name,
        "size_bytes": size_bytes,
        "encoding": enc,
        "delimiter": ";",
        "header_cols_count": len(header),
        "raw_lines": raw_lines,
        "parsed_records": parsed_records,
        "non_empty_records": len(non_empty_records),
        "data_records": len(non_empty_records) - 1,
        "headers": header,
    }


def get_xlsx_sheet_metrics(wb: openpyxl.Workbook, sheet_name: str) -> dict:
    sheet = wb[sheet_name]
    rows = list(sheet.iter_rows(values_only=True))
    total_rows = len(rows)
    header = [str(c) if c is not None else "" for c in rows[0]] if rows else []

    non_empty_rows = [
        r for r in rows if any(c is not None and str(c).strip() != "" for c in r)
    ]

    return {
        "sheet_name": sheet_name,
        "total_rows": total_rows,
        "non_empty_rows": len(non_empty_rows),
        "data_rows": len(non_empty_rows) - 1,
        "cols_count": len(header),
        "headers": header,
    }


def run_inventory(raw_dir_path: str = "data/raw") -> dict:
    raw_dir = Path(raw_dir_path)
    xlsx_path = raw_dir / "analytical_database_callcenter.xlsx"

    csv_to_sheet = {
        "analytical_database_callcenter.analitico_callcenter.csv": (
            "Analitico call center"
        ),
        "analytical_database_callcenter.dicionario_callcenter.csv": (
            "Dicionario call center"
        ),
        "analytical_database_callcenter.analitico_whatsapp.csv": ("Analitico Whatsapp"),
        "analytical_database_callcenter.dicionario_whatsapp.csv": (
            "Dicionario_whatsapp"
        ),
        "analytical_database_callcenter.analitico_video_chamada.csv": (
            "Analitico_video_chamada"
        ),
        "analytical_database_callcenter.dicionario_video_chamado.csv": (
            "Dicionario_video"
        ),
        "analytical_database_callcenter.analitico_totem.csv": ("Analitico_Totem"),
        "analytical_database_callcenter.dicionario_totem.csv": ("Dicionario_Totem"),
    }

    wb = openpyxl.load_workbook(xlsx_path, read_only=True, data_only=True)
    results = []

    print("=" * 110)
    print(
        f"{'Tabela / Arquivo':<42} | {'Tam (KB)':<8} | {'Cols':<4} | "
        f"{'Linhas CSV':<10} | {'Linhas XLSX':<11} | {'Status':<10}"
    )
    print("=" * 110)

    for csv_name, sheet_name in csv_to_sheet.items():
        csv_file = raw_dir / csv_name
        csv_m = get_csv_metrics(csv_file)
        xlsx_m = get_xlsx_sheet_metrics(wb, sheet_name)

        rows_match = csv_m["parsed_records"] == xlsx_m["total_rows"]
        cols_match = csv_m["header_cols_count"] == xlsx_m["cols_count"]
        status = "RECONCILIADO" if rows_match and cols_match else "DIVERGENTE"

        results.append(
            {
                "csv_name": csv_name,
                "sheet_name": sheet_name,
                "csv_metrics": csv_m,
                "xlsx_metrics": xlsx_m,
                "status": status,
            }
        )

        kb = csv_m["size_bytes"] / 1024
        print(
            f"{csv_name:<42} | {kb:8.1f} | {csv_m['header_cols_count']:4} | "
            f"{csv_m['parsed_records']:10} | {xlsx_m['total_rows']:11} | {status:<10}"
        )

    wb.close()
    print("=" * 110)
    return results
