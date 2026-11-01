"""Prova de integridade de conteudo entre os CSVs brutos e as abas do XLSX."""

import csv
import hashlib
from pathlib import Path

import openpyxl


def normalize_cell_value(val) -> str:
    # normaliza valores nulos e remove o sufixo ponto zero de inteiros
    if val is None:
        return ""
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        return s[:-2]
    return s


def compute_row_hash(row: list) -> str:
    # gera o hash sha256 dos valores concatenados por barra vertical
    norm_row = [normalize_cell_value(c) for c in row]
    row_str = "|".join(norm_row)
    return hashlib.sha256(row_str.encode("utf-8")).hexdigest()


def verify_content_integrity(raw_dir: str = "data/raw") -> dict:
    # aponta para a pasta e arquivo excel original
    raw_path = Path(raw_dir)
    xlsx_path = raw_path / "analytical_database_callcenter.xlsx"

    csv_to_sheet = {
        "analytical_database_callcenter.analitico_callcenter.csv": (
            "Analitico call center"
        ),
        "analytical_database_callcenter.analitico_whatsapp.csv": ("Analitico Whatsapp"),
        "analytical_database_callcenter.analitico_video_chamada.csv": (
            "Analitico_video_chamada"
        ),
        "analytical_database_callcenter.analitico_totem.csv": ("Analitico_Totem"),
    }

    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    report = {}

    for csv_name, sheet_name in csv_to_sheet.items():
        csv_file = raw_path / csv_name
        # carrega os registros do csv bruto
        with open(csv_file, "r", encoding="utf-8-sig", newline="") as f:
            csv_rows = list(csv.reader(f, delimiter=";"))

        # carrega as linhas da aba correspondente do excel
        sheet = wb[sheet_name]
        xlsx_rows = list(sheet.iter_rows(values_only=True))

        total_rows = len(csv_rows)
        header_csv = csv_rows[0]
        identical_rows_hash = 0
        divergent_rows_hash = 0

        # inicializa os contadores de divergencia por coluna e categoria
        col_divergence_count = {i: 0 for i in range(len(header_csv))}
        divergence_categories = {
            "date_format_or_seconds_truncation": 0,
            "protocol_scientific_notation": 0,
            "other": 0,
        }

        # compara linha a linha ignorando o cabecalho
        for idx in range(1, total_rows):
            c_row = csv_rows[idx]
            x_row = xlsx_rows[idx]

            c_hash = compute_row_hash(c_row)
            x_hash = compute_row_hash(x_row)

            if c_hash == x_hash:
                identical_rows_hash += 1
            else:
                divergent_rows_hash += 1
                has_date_diff = False
                has_proto_diff = False
                has_other_diff = False

                # identifica quais colunas apresentaram divergencia de valor
                for col_idx in range(len(header_csv)):
                    c_val = normalize_cell_value(c_row[col_idx])
                    x_val = normalize_cell_value(x_row[col_idx])
                    if c_val != x_val:
                        col_divergence_count[col_idx] += 1
                        col_name = header_csv[col_idx].lower()
                        if "date" in col_name or "data" in col_name or col_idx == 2:
                            has_date_diff = True
                        elif "protocolo" in col_name:
                            has_proto_diff = True
                        else:
                            has_other_diff = True

                # classifica o motivo principal da diferenca na linha
                if has_date_diff:
                    divergence_categories["date_format_or_seconds_truncation"] += 1
                if has_proto_diff:
                    divergence_categories["protocol_scientific_notation"] += 1
                if has_other_diff:
                    divergence_categories["other"] += 1

        # monta o diagnostico final da tabela
        report[sheet_name] = {
            "csv_file": csv_name,
            "total_rows": total_rows,
            "data_rows": total_rows - 1,
            "cols_count": len(header_csv),
            "identical_hash_rows": identical_rows_hash,
            "divergent_hash_rows": divergent_rows_hash,
            "divergent_cols": {
                header_csv[k]: v for k, v in col_divergence_count.items() if v > 0
            },
            "divergence_categories": divergence_categories,
        }

    wb.close()
    return report


if __name__ == "__main__":
    # executa a conferencia de integridade e exibe o resumo
    res = verify_content_integrity()
    for sheet, info in res.items():
        print(
            f"{sheet}: dados={info['data_rows']}, "
            f"iguais={info['identical_hash_rows']}, "
            f"divergentes={info['divergent_hash_rows']}"
        )
        if info["divergent_cols"]:
            print(f"  colunas divergentes: {info['divergent_cols']}")
