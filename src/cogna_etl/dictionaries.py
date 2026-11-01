"""Processamento e estruturacao dos dicionarios de dados em JSON."""

import csv
import json
from pathlib import Path

# mapeamento explicito entre o campo do dicionario e a coluna na camada bronze
DICTIONARY_TO_BRONZE_FIELD = {
    "callcenter": {
        "calldate": "calldate",
        "IdType": "id_type",
        "DisconnectType": "disconnect_type",
        "DurationCallcenter": "duration_callcenter",
        "DnaSoa": "dna_soa",
        "Nota_Pesquisa_1": "pesquisa_1",
        "Categoria_Aluno": "categoria_aluno",
        "Modalidade": "modalidade_nova",
        "Instituicao": "instituicao",
        "recepcao_fila": "recepcao_fila",
    },
    "whatsapp": {
        "calldate": "calldate",
        "IdType": "id_type",
        "DisconnectType": "disconnect_type",
        "Modalidade": "modalidade",
        "Categoria_aluno": "categoria_aluno",
        "Instituicao": "instituicao",
        "AfterHour": "after_hour",
        "DNASoa": "dna_soa",
        "DurationCallCenter": "duration_callcenter",
        "TME": "tme",
        "codigo_unidade": "codigo_unidade",
        "Pesquisa_1": "pesquisa_1",
        "AGENTE": "agente",
        "Tabulacao": "tabulacao",
    },
    "video_chamada": {
        "Calldate": "calldate",
        "DurationCallcenter": "duracao_da_chamada",
        "Nota Pergunta1": "nota_pergunta1",
        "TME": "tme",
        "Agente": "agente",
    },
    "totem": {
        "DATA_INICIO": "data_inicio",
        "DURACAO": "duracao",
        "INSTITUICAO": "instituicao",
        "MDC": "mdc",
        "NAVEGACAO": "navegacao",
        "Nota Pergunta1": "nota_pergunta1",
    },
}

# campos que representam dominios categoricos reais com codigos discretos
CATEGORICAL_FIELDS = {
    "IdType",
    "DisconnectType",
    "Categoria_Aluno",
    "Categoria_aluno",
    "Modalidade",
    "Instituicao",
    "AfterHour",
}


def process_channel_dictionary(file_path: Path, channel_key: str) -> dict:
    # le todas as linhas do csv em formato texto
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = list(csv.reader(f, delimiter=";"))

    if not reader:
        return {}

    raw_header = [c.strip() for c in reader[0]]
    rows = reader[1:]
    has_domain_cols = len(raw_header) >= 4

    channel_mapping = DICTIONARY_TO_BRONZE_FIELD.get(channel_key, {})
    result = {}
    current_field = None

    for row in rows:
        # ignora linhas totalmente em branco ou sem qualquer caractere
        if not any(c.strip() != "" for c in row):
            continue

        field = row[0].strip() if len(row) > 0 else ""
        if field:
            current_field = field

        if not current_field:
            continue

        # inicializa o campo na estrutura de saida
        if current_field not in result:
            bronze_col = channel_mapping.get(current_field, current_field.lower())
            is_cat = current_field in CATEGORICAL_FIELDS
            result[current_field] = {
                "campo_origem": current_field,
                "campo_bronze": bronze_col,
                "tipo_campo": "categorico" if is_cat else "escalar_ou_metadado",
                "descricao": "",
                "instrucao_formato": "",
                "dominio": [],
                "metadados_extras": [],
            }

        # processa campos com 4 colunas de dicionario
        if has_domain_cols:
            code = row[1].strip() if len(row) > 1 else ""
            label = row[2].strip() if len(row) > 2 else ""
            desc = row[3].strip() if len(row) > 3 else ""

            # guarda a descricao do campo se informada
            if desc and not result[current_field]["descricao"]:
                result[current_field]["descricao"] = desc

            # diferencia dominio discreto de instrucao de formato com codigo zero
            if current_field in CATEGORICAL_FIELDS:
                if code != "" or label != "":
                    # preserva o codigo e rotulo originais sem alterar conflitos
                    result[current_field]["dominio"].append(
                        {"codigo": code, "rotulo": label}
                    )
            else:
                # em campos escalares o campo dominio e apenas instrucao ou formato
                if label and not result[current_field]["instrucao_formato"]:
                    result[current_field]["instrucao_formato"] = label
                elif label:
                    result[current_field]["metadados_extras"].append(label)
        else:
            # dicionarios de 2 colunas apenas guardam a descricao
            desc = row[1].strip() if len(row) > 1 else ""
            if desc:
                result[current_field]["descricao"] = desc

    return result


def generate_all_dictionaries(
    raw_dir: str = "data/raw", dict_dir: str = "data/dictionaries"
) -> dict:
    # prepara o diretorio local de dicionarios json
    raw_path = Path(raw_dir)
    target_dir = Path(dict_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    dict_files = {
        "callcenter": "analytical_database_callcenter.dicionario_callcenter.csv",
        "whatsapp": "analytical_database_callcenter.dicionario_whatsapp.csv",
        "video_chamada": "analytical_database_callcenter.dicionario_video_chamado.csv",
        "totem": "analytical_database_callcenter.dicionario_totem.csv",
    }

    outputs = {}
    for key, filename in dict_files.items():
        src_path = raw_path / filename
        processed = process_channel_dictionary(src_path, key)

        out_json_path = target_dir / f"{key}_dicionario.json"
        # grava o arquivo em json formatado localmente
        with open(out_json_path, "w", encoding="utf-8") as f_out:
            json.dump(processed, f_out, indent=2, ensure_ascii=False)

        outputs[key] = {
            "source": filename,
            "json_file": out_json_path.name,
            "fields_count": len(processed),
            "fields": list(processed.keys()),
        }

    return outputs


if __name__ == "__main__":
    # executa a geracao dos dicionarios estruturados
    res = generate_all_dictionaries()
    for k, v in res.items():
        print(f"Dicionario gerado: {v['json_file']} ({v['fields_count']} campos)")
