"""Normalizacao da camada Bronze para os CSVs analiticos."""

import csv
from pathlib import Path

COLUMN_MAPPINGS = {
    "analytical_database_callcenter.analitico_callcenter.csv": {
        "output_name": "analitico_callcenter.csv",
        "mapping": [
            ("identificador aluno", "identificador_aluno"),
            ("Date", "date"),
            ("Calldate", "calldate"),
            ("IdType", "id_type"),
            ("IdType - desc", "id_type_desc"),
            ("DisconnectType", "disconnect_type"),
            ("DisconnectType_DESC", "disconnect_type_desc"),
            ("DurationCallcenter", "duration_callcenter"),
            ("DnaSoa", "dna_soa"),
            ("recepcao_fila", "recepcao_fila"),
            ("fila_atend", "fila_atend"),
            ("Agent", "agent"),
            ("Supervisor", "supervisor"),
            ("Pesquisa_1", "pesquisa_1"),
            ("Protocolo", "protocolo"),
            ("tabulacao", "tabulacao"),
            ("Modalidade_nova", "modalidade_nova"),
            ("Modalidade_nova_DESC", "modalidade_nova_desc"),
            ("Categoria_Aluno", "categoria_aluno"),
            ("Categoria_Aluno_DESC", "categoria_aluno_desc"),
            ("Instituicao", "instituicao"),
            ("Instituicao_DESC", "instituicao_desc"),
        ],
    },
    "analytical_database_callcenter.analitico_whatsapp.csv": {
        "output_name": "analitico_whatsapp.csv",
        "mapping": [
            ("identificador aluno", "identificador_aluno"),
            ("calldate", "calldate"),
            ("IdType", "id_type"),
            ("DisconnectType", "disconnect_type"),
            ("DisconnectType_DESC", "disconnect_type_desc"),
            ("Modalidade", "modalidade"),
            ("Modalidade_DESC", "modalidade_desc"),
            ("DurationCallCenter", "duration_callcenter"),
            ("AfterHour", "after_hour"),
            ("Categoria_aluno", "categoria_aluno"),
            ("Categoria_aluno_DESC", "categoria_aluno_desc"),
            ("Instituicao", "instituicao"),
            ("Instituicao_DESC", "instituicao_desc"),
            ("DnaSoa", "dna_soa"),
            ("TME", "tme"),
            ("codigo_unidade", "codigo_unidade"),
            ("Pesquisa_1", "pesquisa_1"),
            ("AGENTE", "agente"),
            ("Tabulacao", "tabulacao"),
        ],
    },
    "analytical_database_callcenter.analitico_video_chamada.csv": {
        "output_name": "analitico_video_chamada.csv",
        "mapping": [
            ("identificador aluno", "identificador_aluno"),
            ("CallDate", "calldate"),
            ("", "calldate_sem_ms"),
            ("TME", "tme"),
            ("Dura\u00e7\u00e3o da Chamada", "duracao_da_chamada"),
            ("Agente", "agente"),
            ("Protocolo", "protocolo"),
            ("Nota Pergunta1", "nota_pergunta1"),
            ("tabulacao", "tabulacao"),
        ],
    },
    "analytical_database_callcenter.analitico_totem.csv": {
        "output_name": "analitico_totem.csv",
        "mapping": [
            ("identificador aluno", "identificador_aluno"),
            ("DATA_INICIO", "data_inicio"),
            ("DURACAO", "duracao"),
            ("INSTITUICAO", "instituicao"),
            ("MDC", "mdc"),
            ("NAVEGACAO", "navegacao"),
            ("Nota Pergunta1", "nota_pergunta1"),
        ],
    },
}


def validate_table_structure(
    raw_header: list[str],
    raw_rows: list[list[str]],
    mapping: list[tuple[str, str]],
    file_label: str,
) -> list[str]:
    # valida se a lista de colunas esperadas bate na ordem exata
    expected_raw = [orig for orig, _ in mapping]
    if raw_header != expected_raw:
        raise ValueError(
            f"Cabecalho raw diverge do mapeamento em {file_label}: "
            f"esperado={expected_raw}, recebido={raw_header}"
        )

    # garante que os nomes normalizados de saida sao unicos
    new_header = [new_col for _, new_col in mapping]
    if len(new_header) != len(set(new_header)):
        raise ValueError(
            f"Colunas de saida duplicadas no mapeamento de {file_label}: {new_header}"
        )

    # confere se cada linha de dados possui a mesma quantidade de colunas
    expected_cols = len(new_header)
    for line_idx, row in enumerate(raw_rows, start=2):
        if len(row) != expected_cols:
            raise ValueError(
                f"Linha {line_idx} de {file_label} tem {len(row)} campos, "
                f"esperado {expected_cols}"
            )

    return new_header


def normalize_bronze(
    raw_dir: str = "data/raw", bronze_dir: str = "data/bronze"
) -> dict:
    # cria a pasta de destino caso ainda nao exista
    raw_path = Path(raw_dir)
    bronze_path = Path(bronze_dir)
    bronze_path.mkdir(parents=True, exist_ok=True)

    summary = {}

    for raw_filename, meta in COLUMN_MAPPINGS.items():
        src_file = raw_path / raw_filename
        dst_file = bronze_path / meta["output_name"]

        # confere a existencia do arquivo de entrada
        if not src_file.exists():
            raise FileNotFoundError(f"Arquivo nao encontrado: {src_file}")

        # le os dados originais preservando cada caractere
        with open(src_file, "r", encoding="utf-8-sig", newline="") as f_in:
            reader = csv.reader(f_in, delimiter=";")
            raw_header = next(reader)
            raw_rows = list(reader)

        # aplica as validacoes de cabecalho, unicidade e quantidade de colunas
        new_header = validate_table_structure(
            raw_header=raw_header,
            raw_rows=raw_rows,
            mapping=meta["mapping"],
            file_label=raw_filename,
        )

        # grava a tabela normalizada em utf-8 com bom e delimitador ponto e virgula
        with open(dst_file, "w", encoding="utf-8-sig", newline="") as f_out:
            writer = csv.writer(f_out, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(new_header)
            writer.writerows(raw_rows)

        # monta o resumo da tabela processada
        summary[meta["output_name"]] = {
            "raw_file": raw_filename,
            "bronze_file": meta["output_name"],
            "raw_lines": len(raw_rows) + 1,
            "bronze_lines": len(raw_rows) + 1,
            "data_rows": len(raw_rows),
            "cols_count": len(new_header),
            "headers": new_header,
        }

    return summary


if __name__ == "__main__":
    # executa o processo para as quatro tabelas
    res = normalize_bronze()
    for name, s in res.items():
        print(
            f"Bronze gerado: {name} ({s['data_rows']} linhas, "
            f"{s['cols_count']} colunas)"
        )
