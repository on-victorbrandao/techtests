"""Testes unitarios e de comportamento para o modulo de profiling."""

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from cogna_etl.profiling import (
    aggregate_ratings,
    classify_callcenter_protocols,
    format_ratings_markdown_table,
    profile_callcenter_queues_and_retention,
    profile_consecutive_overlaps,
    profile_dictionary_anomalies,
    profile_dna_soa_callcenter,
    profile_durations,
    profile_journeys_cc_wa,
    profile_ratings,
    profile_tme_vs_duration,
    run_full_profiling,
    strip_accents,
)


def test_strip_accents_behavior():
    """Garante remocao correta de acentos e conversao para minusculo."""
    assert strip_accents("Retenção") == "retencao"
    assert strip_accents("GRADUAÇÃO EAD") == "graduacao ead"
    assert strip_accents(None) == ""
    assert strip_accents(123) == ""


def test_profile_ratings_synthetic_behavior():
    """Valida calculo de notas com texto invalido, fracionarios e zeros."""
    sample = pd.Series([None, 0, 0, 1, 2, 5, "9", -1, "invalido", 2.5])
    res = profile_ratings(sample)

    assert res["null_count"] == 1
    assert res["zero_count"] == 2
    assert res["unanswered_total"] == 3
    assert res["valid_count"] == 3
    assert res["non_numeric_text_count"] == 1
    assert res["out_of_scale_fractional_count"] == 3
    assert res["bad_ratings_count"] == 2
    assert res["average_answered_score"] == pytest.approx(2.67, abs=0.01)
    assert res["bad_ratings_pct"] == pytest.approx(66.67, abs=0.01)


def test_profile_ratings_empty_and_no_responses():
    """Verifica que ausencia de respostas resulta em media e percentual nulos."""
    empty_series = pd.Series([], dtype=object)
    res_empty = profile_ratings(empty_series)
    assert res_empty["valid_count"] == 0
    assert res_empty["average_answered_score"] is None
    assert res_empty["bad_ratings_pct"] is None
    assert res_empty["response_rate_pct"] is None

    unanswered_series = pd.Series([0, None, "texto", -5])
    res_un = profile_ratings(unanswered_series)
    assert res_un["valid_count"] == 0
    assert res_un["average_answered_score"] is None
    assert res_un["bad_ratings_pct"] is None


def test_ratings_classes_sum_and_channel_aggregation():
    """Garante que as classes de notas somam o total e que o agregado soma os canais."""
    s1 = pd.Series([None, 0, 5, 4, "invalido", 2.5])
    s2 = pd.Series([0, 0, 1, 2, 5])
    ch_map = {
        "call_center": profile_ratings(s1),
        "whatsapp": profile_ratings(s2),
        "video_chamada": profile_ratings(pd.Series([0, 3], dtype=object)),
        "totem": profile_ratings(pd.Series([None, 0], dtype=object)),
    }
    ch_map["total"] = aggregate_ratings(ch_map)

    for r in ch_map.values():
        classes_sum = (
            r["null_count"]
            + r["zero_count"]
            + r["valid_count"]
            + r["non_numeric_text_count"]
            + r["out_of_scale_fractional_count"]
        )
        assert classes_sum == r["total_rows"]

    tot = ch_map["total"]
    chs = [v for k, v in ch_map.items() if k != "total"]
    assert tot["total_rows"] == sum(c["total_rows"] for c in chs)
    assert tot["null_count"] == sum(c["null_count"] for c in chs)
    assert tot["zero_count"] == sum(c["zero_count"] for c in chs)
    assert tot["valid_count"] == sum(c["valid_count"] for c in chs)
    assert tot["sum_valid_scores"] == sum(c["sum_valid_scores"] for c in chs)
    assert tot["bad_ratings_count"] == sum(c["bad_ratings_count"] for c in chs)
    assert tot["average_answered_score"] == round(20 / 6, 2)
    md = format_ratings_markdown_table(ch_map)
    assert "| **Total** |" in md


def test_classify_protocols_synthetic_behavior():
    """Verifica deteccao de formatos padrao, notacao cientifica e anomalias."""
    sample = pd.Series(
        [
            "CS12345678",
            "1,44496E+18",
            "1.44496e+18",
            "cra_retencao_ura",
            "EDU_TEST_1",
            "98765432",
            "S12345678",
            None,
        ]
    )
    res = classify_callcenter_protocols(sample)
    assert res["total_null"] == 1
    assert res["total_filled"] == 7
    assert res["standard_cs"] == 1
    assert res["sci_notation"] == 2
    assert res["cra_retencao_text"] == 1
    assert res["edu_pattern"] == 1
    assert res["pure_numeric"] == 1
    assert res["s_prefix"] == 1


def test_profile_durations_and_outliers():
    """Testa calculo de quartis, limites de outlier e contagem de negativos."""
    sample = pd.Series([0, 10, 20, 30, 40, 50, -5, 1000])
    res = profile_durations(sample)
    assert res["zeros_count"] == 1
    assert res["negative_count"] == 1
    assert res["min"] == -5.0
    assert res["max"] == 1000.0
    assert res["outliers_iqr_count"] >= 1


def test_profile_tme_vs_duration_comparison():
    """Garante classificacao de relacao temporal sem preencher ausencias com zero."""
    df_sample = pd.DataFrame(
        {
            "dur": [100, 50, 200, None, 120, -10],
            "tme": [150, 50, 50, 80, None, 30],
        }
    )
    res = profile_tme_vs_duration(df_sample, "dur", "tme")
    assert res["total_rows"] == 6
    assert res["valid_comparable_pairs"] == 3
    assert res["missing_duration"] == 1
    assert res["missing_tme"] == 1
    assert res["negative_duration"] == 1
    assert res["tme_greater_than_duration"] == 1
    assert res["tme_equal_to_duration"] == 1
    assert res["tme_less_than_duration"] == 1


def test_profile_dna_soa_exact_tokens_and_union():
    """Verifica tokens exatos 98/99 e calculo correto de uniao e intersecao."""
    sample = pd.Series(
        [
            "A|A|A|B|B|B",
            "A|B|C",
            "A|A|A|98",
            "A|A|A|99|99|99",
            "A|A|A|98|99",
            "A|A|A|198|990",
            None,
        ]
    )
    res = profile_dna_soa_callcenter(sample)
    assert res["null_count"] == 1
    assert res["valid_count"] == 6
    assert res["rows_with_token_98"] == 2
    assert res["rows_with_token_99"] == 2
    assert res["rows_with_both_tokens_98_and_99"] == 1
    assert res["rows_with_token_98_or_99_union"] == 3
    assert res["strictly_triplets_count"] == 2


def test_consecutive_pairs_estimated_overlap():
    """Testa identificacao de sobreposicao estimada entre contatos consecutivos."""
    df_cc = pd.DataFrame(
        {
            "identificador aluno": ["100", "100"],
            "Calldate": [
                datetime(2026, 9, 1, 10, 0, 0),
                datetime(2026, 9, 1, 10, 2, 0),
            ],
            "DurationCallcenter": [300, 90],
        }
    )
    df_wa = pd.DataFrame(
        {
            "identificador aluno": ["100"],
            "calldate": [datetime(2026, 9, 1, 10, 3, 0)],
            "DurationCallCenter": [120],
        }
    )
    dfs = {
        "call_center": df_cc,
        "whatsapp": df_wa,
        "video_chamada": pd.DataFrame(
            {"identificador aluno": [], "CallDate": [], "Durao": []}
        ),
        "totem": pd.DataFrame(
            {"identificador aluno": [], "DATA_INICIO": [], "DURACAO": []}
        ),
    }
    res = profile_consecutive_overlaps(dfs)
    assert res["total_consecutive_pairs"] == 2
    assert res["consecutive_pairs_with_estimated_overlap"] == 2
    assert "call_center->call_center" in res["overlaps_by_channel_pair"]
    assert "call_center->whatsapp" in res["overlaps_by_channel_pair"]


def test_queue_and_retention_crosstab_and_outcomes():
    """Valida separacao de assunto vs encaminhamento e desfechos da arvore."""
    df_cc = pd.DataFrame(
        {
            "recepcao_fila": ["f1", "f1", "f_retencao", "f_retencao", "f1"],
            "fila_atend": ["f1", "f2", "f_retencao", "f_retencao", "f1"],
            "tabulacao": [
                "1. Geral > Info",
                "2. Geral > Atendimento de Retenção > Aluno mantido",
                "3. Geral > Atendimento de Retenção > Solicitação de cancelamento",
                "4. Geral > Transferência para retenção",
                "5. Geral > Atendimento de Retenção > Outro motivo indefinido",
            ],
        }
    )
    res = profile_callcenter_queues_and_retention(df_cc)
    assert res["fila_retencao_total"] == 2
    assert res["tabulacao_assunto_retencao_total"] == 3
    assert res["tabulacao_encaminhamento_retencao_total"] == 1
    assert res["crosstab_fila_vs_assunto"]["ambos_retencao"] == 1
    assert res["crosstab_fila_vs_assunto"]["apenas_fila_retencao"] == 1
    assert res["crosstab_fila_vs_assunto"]["apenas_assunto_retencao"] == 2
    assert res["desfechos_mutuamente_exclusivos_arvore"]["Aluno mantido"] == 1
    assert (
        res["desfechos_mutuamente_exclusivos_arvore"]["Solicitacao de cancelamento"]
        == 1
    )
    assert res["desfechos_mutuamente_exclusivos_arvore"]["Nao identificado"] == 1


def test_journeys_cc_wa_synthetic():
    """Valida contagem de jornadas diretas, com intermediarios e alunos distintos."""
    dfs = {
        "call_center": pd.DataFrame(
            {
                "identificador aluno": ["1", "1", "2"],
                "Calldate": [
                    datetime(2026, 9, 1, 10, 0),
                    datetime(2026, 9, 1, 12, 0),
                    datetime(2026, 9, 1, 15, 0),
                ],
            }
        ),
        "totem": pd.DataFrame(
            {
                "identificador aluno": ["1"],
                "DATA_INICIO": [datetime(2026, 9, 1, 11, 0)],
                "DURACAO": [60],
            }
        ),
        "whatsapp": pd.DataFrame(
            {
                "identificador aluno": ["1"],
                "calldate": [datetime(2026, 9, 1, 13, 0)],
            }
        ),
        "video_chamada": pd.DataFrame({"identificador aluno": [], "CallDate": []}),
    }
    res = profile_journeys_cc_wa(dfs)
    assert res["cc_contacts_with_direct_wa_posterior"] == 1
    assert res["cc_contacts_with_intermediate_wa_posterior"] == 1
    assert res["cc_contacts_without_wa_posterior"] == 1
    assert res["distinct_students_with_cc_before_wa"] == 1


def test_profile_dictionary_duplicate_detection(tmp_path):
    """Valida captura de codigos duplicados em arquivos JSON de dicionario."""
    import json

    dict_content = {
        "AfterHour": {
            "campo_bronze": "after_hour",
            "dominio": [
                {"codigo": "0", "rotulo": "0 = Nao"},
                {"codigo": "1", "rotulo": "1 = Sim"},
                {"codigo": "0", "rotulo": "Condicional 1"},
            ],
        }
    }
    d_file = tmp_path / "test_dicionario.json"
    with open(d_file, "w", encoding="utf-8") as f:
        json.dump(dict_content, f)

    res = profile_dictionary_anomalies(tmp_path)
    assert "test_dicionario" in res
    assert "AfterHour" in res["test_dicionario"]
    assert res["test_dicionario"]["AfterHour"]["duplicate_codes"] == {"0": 2}


@pytest.mark.integration
def test_full_profiling_real_dataset_integrity():
    """Executa o profiling completo no dataset real e valida invariantes."""
    res = run_full_profiling()
    assert res["total_rows"] == 5991
    assert res["row_counts"]["call_center"] == 1499
    assert res["row_counts"]["whatsapp"] == 1494
    assert res["row_counts"]["video_chamada"] == 1499
    assert res["row_counts"]["totem"] == 1499

    assert res["students"]["total_unique_students"] == 173
    assert res["students"]["in_all_4_channels"] == 173

    # validacoes das formulas e celulas de erro
    for ch, struct in res["sheet_structure"].items():
        assert struct["error_cells"] == 0, f"Canal {ch} possui celulas com erro"
        assert struct["formulas_with_missing_stored_result"] == 0

    # retencao segregada
    assert res["queues"]["tabulacao_assunto_retencao_total"] == 266
    assert res["queues"]["tabulacao_encaminhamento_retencao_total"] == 6
    assert res["queues"]["fila_retencao_total"] == 270

    # tokens dna_soa
    assert res["dna_soa"]["rows_with_token_98"] == 5
    assert res["dna_soa"]["rows_with_token_99"] == 410
    assert res["dna_soa"]["rows_with_token_98_or_99_union"] == 415

    # deteccao da anomalia de AfterHour
    assert "whatsapp_dicionario" in res["dictionary_anomalies"]
    wa_anom = res["dictionary_anomalies"]["whatsapp_dicionario"]
    assert "AfterHour" in wa_anom
    assert wa_anom["AfterHour"]["duplicate_codes"]["0"] == 3

    # reconciliacao da tabela de satisfacao e linha total
    tot_r = res["ratings"]["total"]
    assert tot_r["total_rows"] == 5991
    assert tot_r["null_count"] == 838
    assert tot_r["zero_count"] == 3208
    assert tot_r["valid_count"] == 1945
    assert tot_r["sum_valid_scores"] == 8643
    assert tot_r["bad_ratings_count"] == 154
    assert tot_r["average_answered_score"] == 4.44
    assert tot_r["bad_ratings_pct"] == 7.92
    assert tot_r["response_rate_pct"] == 32.47
    doc_text = Path("docs/qualidade_dados.md").read_text(encoding="utf-8")
    assert res["ratings_markdown_table"] in doc_text
