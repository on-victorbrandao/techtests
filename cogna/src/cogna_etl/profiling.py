"""Modulo de profiling e diagnostico de qualidade de dados."""

import json
import unicodedata
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import openpyxl
import pandas as pd


def strip_accents(text: Any) -> str:
    """Remove acentos e converte texto para minusculo."""
    if not isinstance(text, str):
        return ""
    # decompoe caracteres acentuados e remove marcas nao espacadas
    nfd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfd if unicodedata.category(c) != "Mn").lower()


def load_raw_xlsx_sheets(xlsx_path: Path) -> Dict[str, pd.DataFrame]:
    """Carrega as quatro abas analiticas do XLSX com rastreabilidade de linha."""
    wb = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    sheets_map = {
        "call_center": "Analitico call center",
        "whatsapp": "Analitico Whatsapp",
        "video_chamada": "Analitico_video_chamada",
        "totem": "Analitico_Totem",
    }
    dfs = {}
    for ch, sheet_name in sheets_map.items():
        ws = wb[sheet_name]
        raw_rows = list(ws.iter_rows(values_only=True))
        # substitui cabecalho nulo por nome padrao mantendo rastreabilidade
        header = [
            f"col_{i}" if h is None else str(h).strip()
            for i, h in enumerate(raw_rows[0])
        ]
        records = []
        for line_idx, row_vals in enumerate(raw_rows[1:], start=2):
            row_dict = dict(zip(header, row_vals))
            row_dict["_origem_arquivo"] = xlsx_path.name
            row_dict["_origem_aba"] = sheet_name
            row_dict["_origem_linha"] = line_idx
            records.append(row_dict)
        dfs[ch] = pd.DataFrame(records)
    wb.close()
    return dfs


def _inspect_single_sheet_formulas(
    f_rows: List[Any], v_rows: List[Any]
) -> Dict[str, Any]:
    """Conta formulas, cache ausente e celulas de erro em uma aba."""
    raw_hdr = [c.value for c in f_rows[0]]
    f_cnt, err_cnt, none_stored, f_cols = 0, 0, 0, set()
    for fr, vr in zip(f_rows[1:], v_rows[1:]):
        for idx, (fc, vc) in enumerate(zip(fr, vr)):
            if fc.data_type == "f" or (
                isinstance(fc.value, str) and fc.value.startswith("=")
            ):
                f_cnt += 1
                f_cols.add(idx)
                if vc.value is None:
                    none_stored += 1
            if vc.data_type == "e" or (
                isinstance(vc.value, str) and vc.value.startswith("#")
            ):
                err_cnt += 1
    return {
        "total_rows": len(f_rows) - 1,
        "formula_cells": f_cnt,
        "formula_columns": [
            {"col_pos_1based": i + 1, "raw_header": raw_hdr[i]} for i in sorted(f_cols)
        ],
        "formulas_with_missing_stored_result": none_stored,
        "error_cells": err_cnt,
    }


def profile_sheet_formulas_and_errors(xlsx_path: Path) -> Dict[str, Any]:
    """Inspeciona formulas, resultados armazenados e erros via tipos de celula."""
    wb_f = openpyxl.load_workbook(xlsx_path, data_only=False, read_only=True)
    wb_v = openpyxl.load_workbook(xlsx_path, data_only=True, read_only=True)
    sheets_map = {
        "call_center": "Analitico call center",
        "whatsapp": "Analitico Whatsapp",
        "video_chamada": "Analitico_video_chamada",
        "totem": "Analitico_Totem",
    }
    res = {
        ch: _inspect_single_sheet_formulas(
            list(wb_f[sname].iter_rows()), list(wb_v[sname].iter_rows())
        )
        for ch, sname in sheets_map.items()
    }
    wb_f.close()
    wb_v.close()
    return res


def profile_identifiers(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Avalia identificadores de alunos e multiplicidade de IdType."""
    id_sets: Dict[str, Set[str]] = {}
    lens_per_ch: Dict[str, List[int]] = {}
    for ch, df in dfs.items():
        col = [c for c in df.columns if "identificador" in c.lower()][0]
        ids = df[col].dropna().astype(str).str.strip()
        id_sets[ch] = set(ids.unique())
        lens_per_ch[ch] = sorted(list({len(x) for x in ids}))

    all_ids = set.union(*id_sets.values())
    common_all = set.intersection(*id_sets.values())

    # conta alunos com mais de um valor de IdType no periodo sem assumir erro
    df_cc = dfs["call_center"]
    id_col = [c for c in df_cc.columns if "identificador" in c.lower()][0]
    type_col = [c for c in df_cc.columns if c.lower() == "idtype"][0]
    desc_col = [
        c for c in df_cc.columns if "desc" in c.lower() and "idtype" in c.lower()
    ][0]
    cc_grouped = df_cc.groupby(id_col)[type_col].nunique()
    multi_id_type_students = int((cc_grouped > 1).sum())

    return {
        "total_unique_students": len(all_ids),
        "in_all_4_channels": len(common_all),
        "lengths_per_channel": lens_per_ch,
        "call_center_id_type_counts": df_cc[type_col].value_counts().to_dict(),
        "call_center_id_type_desc_counts": df_cc[desc_col].value_counts().to_dict(),
        "students_with_multiple_id_types": multi_id_type_students,
    }


def classify_retention_tree_outcome(tabulation_text: str) -> str:
    """Classifica o desfecho categorico da tabulacao de retencao pela arvore."""
    if not isinstance(tabulation_text, str) or not tabulation_text.strip():
        return "Nao identificado"
    parts = [strip_accents(p.strip()) for p in tabulation_text.split(">")]
    for p in reversed(parts):
        if "cancel" in p:
            return "Solicitacao de cancelamento"
        if "mantido" in p:
            return "Aluno mantido"
        if "tranc" in p:
            return "Solicitacao de trancamento"
        if "transf" in p:
            return "Solicitacao de transferencia"
        if "nao vai pagar rematricula" in p:
            return "Nao vai pagar rematricula"
        if "vai pagar rematricula" in p:
            return "Vai pagar rematricula"
    return "Nao identificado"


def profile_callcenter_queues_and_retention(df_cc: pd.DataFrame) -> Dict[str, Any]:
    """Analisa filas e tabulacoes segregando assunto e encaminhamento de retencao."""
    rec_col, fila_col, tab_col = "recepcao_fila", "fila_atend", "tabulacao"
    mask_fila_ret = (
        df_cc[fila_col].apply(strip_accents).str.contains("retenc", na=False)
    )
    norm_tab = df_cc[tab_col].apply(strip_accents)
    mask_assunto = norm_tab.str.contains("atendimento de retencao", na=False)
    mask_encam = norm_tab.str.contains("para retencao", na=False)

    # matriz cruzada usando estritamente o assunto de retencao
    crosstab_assunto = {
        "ambos_retencao": int((mask_fila_ret & mask_assunto).sum()),
        "apenas_fila_retencao": int((mask_fila_ret & ~mask_assunto).sum()),
        "apenas_assunto_retencao": int((~mask_fila_ret & mask_assunto).sum()),
        "nenhum_retencao": int((~mask_fila_ret & ~mask_assunto).sum()),
    }
    norm_assunto = norm_tab[mask_assunto]
    tree_outcomes = df_cc[mask_assunto][tab_col].apply(classify_retention_tree_outcome)

    return {
        "coincident_queues": int((df_cc[rec_col] == df_cc[fila_col]).sum()),
        "divergent_queues": int((df_cc[rec_col] != df_cc[fila_col]).sum()),
        "fila_retencao_total": int(mask_fila_ret.sum()),
        "tabulacao_assunto_retencao_total": int(mask_assunto.sum()),
        "tabulacao_encaminhamento_retencao_total": int(mask_encam.sum()),
        "crosstab_fila_vs_assunto": crosstab_assunto,
        "flags_independentes_assunto": {
            "flag_cancelamento": int(norm_assunto.str.contains("cancel").sum()),
            "flag_aluno_mantido": int(norm_assunto.str.contains("mantido").sum()),
            "flag_trancamento": int(norm_assunto.str.contains("tranc").sum()),
            "flag_transferencia": int(norm_assunto.str.contains("transf").sum()),
            "declaracao_nao_exclusivas": True,
        },
        "desfechos_mutuamente_exclusivos_arvore": (
            tree_outcomes.value_counts().to_dict()
        ),
    }


def classify_callcenter_protocols(series: pd.Series) -> Dict[str, int]:
    """Classifica protocolos do Call Center por formato e anomalia."""
    valid = series.dropna().astype(str).str.strip()
    sci = int(valid.str.contains(r"^[0-9]+,[0-9]+E\+[0-9]+$", regex=True).sum())
    f_sci = int(valid.str.contains(r"^[0-9]+\.[0-9]+e\+[0-9]+$", regex=True).sum())
    cra = int(valid.apply(strip_accents).str.contains("cra_retenc", na=False).sum())
    cs_pat = int(valid.str.contains(r"^CS[0-9]{8}$", regex=True).sum())
    edu = int(valid.str.contains(r"EDU", regex=True).sum())
    pure_num = int(valid.str.contains(r"^[0-9]+$", regex=True).sum())
    s_pref = int(valid.str.contains(r"^S[0-9]{8}$", regex=True).sum())

    return {
        "total_null": int(series.isna().sum()),
        "total_filled": len(valid),
        "sci_notation": sci + f_sci,
        "cra_retencao_text": cra,
        "standard_cs": cs_pat,
        "edu_pattern": edu,
        "pure_numeric": pure_num,
        "s_prefix": s_pref,
    }


def _classify_single_rating(v: Any) -> str:
    """Classifica um valor individual de pesquisa de satisfacao."""
    if v is None or pd.isna(v):
        return "null"
    if isinstance(v, bool):
        return "text"
    if isinstance(v, (int, float, str)):
        try:
            num = float(str(v).strip().replace(",", "."))
        except ValueError:
            return "text"
        if num == 0.0:
            return "zero"
        if num.is_integer() and 1 <= int(num) <= 5:
            return f"valid:{int(num)}"
        return "out_of_scale"
    return "text"


def profile_ratings(series: pd.Series) -> Dict[str, Any]:
    """Analisa notas separando nulos, zeros, validos, texto e fracionarios."""
    n_null, n_zero, text_non_num, out_of_scale_frac = 0, 0, 0, 0
    valid_ratings: List[int] = []

    for v in series:
        cat = _classify_single_rating(v)
        if cat == "null":
            n_null += 1
        elif cat == "zero":
            n_zero += 1
        elif cat.startswith("valid:"):
            valid_ratings.append(int(cat.split(":")[1]))
        elif cat == "out_of_scale":
            out_of_scale_frac += 1
        else:
            text_non_num += 1

    n_val = len(valid_ratings)
    sum_scores = int(sum(valid_ratings))
    bad_count = sum(1 for r in valid_ratings if r in [1, 2])
    return {
        "total_rows": len(series),
        "null_count": n_null,
        "zero_count": n_zero,
        "valid_count": n_val,
        "sum_valid_scores": sum_scores,
        "non_numeric_text_count": text_non_num,
        "out_of_scale_fractional_count": out_of_scale_frac,
        "unanswered_total": n_null + n_zero,
        "bad_ratings_count": bad_count,
        "response_rate_pct": (
            round((n_val / len(series)) * 100, 2) if len(series) > 0 else None
        ),
        "bad_ratings_pct": round((bad_count / n_val) * 100, 2) if n_val > 0 else None,
        "average_answered_score": round(sum_scores / n_val, 2) if n_val > 0 else None,
    }


def aggregate_ratings(channel_ratings: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Consolida metricas gerais de satisfacao a partir das somas exatas dos canais."""
    chs = [v for k, v in channel_ratings.items() if k != "total"]
    tot_rows = sum(r["total_rows"] for r in chs)
    n_null = sum(r["null_count"] for r in chs)
    n_zero = sum(r["zero_count"] for r in chs)
    n_val = sum(r["valid_count"] for r in chs)
    sum_scores = sum(r["sum_valid_scores"] for r in chs)
    text_cnt = sum(r["non_numeric_text_count"] for r in chs)
    out_cnt = sum(r["out_of_scale_fractional_count"] for r in chs)
    bad_cnt = sum(r["bad_ratings_count"] for r in chs)
    return {
        "total_rows": tot_rows,
        "null_count": n_null,
        "zero_count": n_zero,
        "valid_count": n_val,
        "sum_valid_scores": sum_scores,
        "non_numeric_text_count": text_cnt,
        "out_of_scale_fractional_count": out_cnt,
        "unanswered_total": n_null + n_zero,
        "bad_ratings_count": bad_cnt,
        "response_rate_pct": (
            round((n_val / tot_rows) * 100, 2) if tot_rows > 0 else None
        ),
        "bad_ratings_pct": round((bad_cnt / n_val) * 100, 2) if n_val > 0 else None,
        "average_answered_score": round(sum_scores / n_val, 2) if n_val > 0 else None,
    }


def _fmt_pt_int(n: int) -> str:
    """Formata inteiro com separador de milhar por ponto."""
    return f"{n:,}".replace(",", ".")


def _fmt_pt_dec(val: Optional[float]) -> str:
    """Formata decimal com duas casas e virgula."""
    return f"{val:.2f}".replace(".", ",") if val is not None else "—"


def format_ratings_markdown_table(ratings: Dict[str, Dict[str, Any]]) -> str:
    """Gera a tabela Markdown de satisfacao diretamente do resultado do profiling."""
    labels = [
        ("call_center", "**Call Center**", False),
        ("whatsapp", "**WhatsApp**", False),
        ("video_chamada", "**Vídeo chamada**", False),
        ("totem", "**Totem**", False),
        ("total", "**Total**", True),
    ]
    sep = "| :--- |" + " :---: |" * 9
    lines = [
        "| Canal | Total de linhas | Nulos na origem | Zeros (premissa) "
        "| Notas válidas {1..5} | Texto não numérico "
        "| Fora de escala ou fração | Média dos respondidos "
        "| % notas ruins {1, 2} | Taxa de resposta |",
        sep,
    ]
    for key, label, is_bold in labels:
        r = ratings[key]
        b = "**" if is_bold else ""
        bad_str = (
            f"{_fmt_pt_dec(r['bad_ratings_pct'])}% "
            f"({_fmt_pt_int(r['bad_ratings_count'])})"
        )
        cells = [
            f"{b}{_fmt_pt_int(r['total_rows'])}{b}",
            f"{b}{_fmt_pt_int(r['null_count'])}{b}",
            f"{b}{_fmt_pt_int(r['zero_count'])}{b}",
            f"{b}{_fmt_pt_int(r['valid_count'])}{b}",
            f"{b}{_fmt_pt_int(r['non_numeric_text_count'])}{b}",
            f"{b}{_fmt_pt_int(r['out_of_scale_fractional_count'])}{b}",
            f"{b}{_fmt_pt_dec(r['average_answered_score'])}{b}",
            f"{b}{bad_str}{b}",
            f"{b}{_fmt_pt_dec(r['response_rate_pct'])}%{b}",
        ]
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    return "\n".join(lines)


def profile_durations(series: pd.Series) -> Dict[str, Any]:
    """Calcula estatisticas descritivas e outliers para metricas de tempo."""
    s = pd.to_numeric(series, errors="coerce").dropna()
    q25 = float(s.quantile(0.25)) if len(s) > 0 else 0.0
    q50 = float(s.median()) if len(s) > 0 else 0.0
    q75 = float(s.quantile(0.75)) if len(s) > 0 else 0.0
    p95 = float(s.quantile(0.95)) if len(s) > 0 else 0.0
    p99 = float(s.quantile(0.99)) if len(s) > 0 else 0.0
    iqr = q75 - q25
    upper_fence = q75 + 1.5 * iqr

    return {
        "count": len(s),
        "min": float(s.min()) if len(s) > 0 else 0.0,
        "max": float(s.max()) if len(s) > 0 else 0.0,
        "mean": round(float(s.mean()), 1) if len(s) > 0 else 0.0,
        "median": round(q50, 1),
        "p25": round(q25, 1),
        "p75": round(q75, 1),
        "p95": round(p95, 1),
        "p99": round(p99, 1),
        "zeros_count": int((s == 0).sum()),
        "negative_count": int((s < 0).sum()),
        "outliers_iqr_count": int((s > upper_fence).sum()),
        "outliers_p99_count": int((s > p99).sum()),
    }


def _classify_tme_duration_pair(d: Any, t: Any) -> str:
    """Classifica um par de duracao e TME quanto a preenchimento e sinal."""
    d_none, t_none = (d is None or pd.isna(d)), (t is None or pd.isna(t))
    if d_none and t_none:
        return "miss_both"
    if d_none:
        return "miss_dur"
    if t_none:
        return "miss_tme"
    try:
        d_val, t_val = float(d), float(t)
    except (ValueError, TypeError):
        return "non_num"
    if d_val < 0 and t_val < 0:
        return "neg_both"
    if d_val < 0:
        return "neg_dur"
    if t_val < 0:
        return "neg_tme"
    return f"ok:{d_val}:{t_val}"


def profile_tme_vs_duration(
    df: pd.DataFrame, dur_col: str, tme_col: str
) -> Dict[str, Any]:
    """Compara espera e duracao estritamente sobre pares preenchidos e validos."""
    valid_pairs = []
    counts = Counter(
        _classify_tme_duration_pair(d, t) for d, t in zip(df[dur_col], df[tme_col])
    )
    for k, c in counts.items():
        if k.startswith("ok:"):
            _, dv, tv = k.split(":")
            valid_pairs.extend([(float(dv), float(tv))] * c)
    n_val = len(valid_pairs)
    tme_gt = sum(1 for d, t in valid_pairs if t > d)
    return {
        "total_rows": len(df),
        "valid_comparable_pairs": n_val,
        "missing_duration": counts["miss_dur"],
        "missing_tme": counts["miss_tme"],
        "missing_both": counts["miss_both"],
        "negative_duration": counts["neg_dur"] + counts["neg_both"],
        "negative_tme": counts["neg_tme"] + counts["neg_both"],
        "non_numeric_pairs": counts["non_num"],
        "tme_greater_than_duration": tme_gt,
        "tme_equal_to_duration": sum(1 for d, t in valid_pairs if t == d),
        "tme_less_than_duration": sum(1 for d, t in valid_pairs if t < d),
        "pct_tme_greater_than_duration": (
            round((tme_gt / n_val) * 100, 2) if n_val > 0 else None
        ),
    }


def profile_dna_soa_callcenter(series: pd.Series) -> Dict[str, Any]:
    """Analisa a estrutura da trilha dna_soa com contagem exata de tokens 98 e 99."""
    valid = series.dropna().astype(str)
    triplets, with_reps, tok_98, tok_99, tok_both, tok_union = 0, 0, 0, 0, 0, 0
    for row in valid:
        tokens = [t.strip() for t in row.split("|")]
        if any(tokens[i] == tokens[i + 1] for i in range(len(tokens) - 1)):
            with_reps += 1
        if len(tokens) % 3 == 0 and all(
            tokens[i] == tokens[i + 1] == tokens[i + 2]
            for i in range(0, len(tokens), 3)
        ):
            triplets += 1
        h98, h99 = ("98" in tokens), ("99" in tokens)
        tok_98 += int(h98)
        tok_99 += int(h99)
        tok_both += int(h98 and h99)
        tok_union += int(h98 or h99)
    return {
        "null_count": int(series.isna().sum()),
        "valid_count": len(valid),
        "consecutive_repetitions": with_reps,
        "strictly_triplets_count": triplets,
        "triplets_pct": (
            round((triplets / len(valid)) * 100, 2) if len(valid) > 0 else 0.0
        ),
        "rows_with_token_98": tok_98,
        "rows_with_token_99": tok_99,
        "rows_with_both_tokens_98_and_99": tok_both,
        "rows_with_token_98_or_99_union": tok_union,
    }


def parse_timestamp_preserve_ms(raw_dt: Any) -> datetime:
    """Decodifica timestamp preservando milissegundos quando presentes."""
    if isinstance(raw_dt, datetime):
        return raw_dt
    raw_str = str(raw_dt).strip()
    if "." in raw_str:
        return datetime.strptime(raw_str, "%d/%m/%Y %H:%M:%S.%f")
    return datetime.strptime(raw_str, "%d/%m/%Y %H:%M:%S")


def _build_timeline_records(
    dfs: Dict[str, pd.DataFrame], include_duration: bool = False
) -> pd.DataFrame:
    """Constroi linha do tempo unificada de contatos ordenada por aluno e horario."""
    records = []
    for ch, df in dfs.items():
        id_col = [c for c in df.columns if "identificador" in c.lower()][0]
        dt_col = [
            c
            for c in df.columns
            if any(k in c.lower() for k in ["calldate", "data_inicio"])
        ][0]
        dur_cols = [c for c in df.columns if "dura" in c.lower()]
        for _, row in df.iterrows():
            rec: Dict[str, Any] = {
                "aluno": str(row[id_col]),
                "canal": ch,
                "dt": parse_timestamp_preserve_ms(row[dt_col]),
            }
            if include_duration and dur_cols:
                rec["duracao"] = int(row[dur_cols[0]] or 0)
            records.append(rec)
    return pd.DataFrame(records).sort_values(["aluno", "dt"]).reset_index(drop=True)


def profile_consecutive_overlaps(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Calcula pares consecutivos com sobreposicao estimada por par de canais."""
    all_sorted = _build_timeline_records(dfs, include_duration=True)
    pair_overlaps: List[Dict[str, Any]] = []
    total_consec_pairs = 0
    for _, group in all_sorted.groupby("aluno"):
        grp = group.sort_values("dt").reset_index(drop=True)
        for i in range(len(grp) - 1):
            total_consec_pairs += 1
            c1, c2 = grp.iloc[i], grp.iloc[i + 1]
            c1_end = c1["dt"] + timedelta(seconds=int(c1["duracao"]))
            if c2["dt"] < c1_end:
                pair_overlaps.append({"c1_canal": c1["canal"], "c2_canal": c2["canal"]})
    df_ov = pd.DataFrame(pair_overlaps)
    by_pair = (
        df_ov.groupby(["c1_canal", "c2_canal"]).size().to_dict()
        if len(df_ov) > 0
        else {}
    )
    return {
        "total_consecutive_pairs": total_consec_pairs,
        "consecutive_pairs_with_estimated_overlap": len(pair_overlaps),
        "overlaps_by_channel_pair": {f"{k[0]}->{k[1]}": v for k, v in by_pair.items()},
        "observacao_metodologica": (
            "Horario final estimado pela duracao informada; "
            "depende da definicao e unidade."
        ),
    }


def profile_journeys_cc_wa(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Calcula associacao de contatos de CC a contatos posteriores de WA."""
    df_seq = _build_timeline_records(dfs, include_duration=False)
    df_seq["prev_canal"] = df_seq.groupby("aluno")["canal"].shift(1)
    direct_cc_wa = int(
        (
            (df_seq["prev_canal"] == "call_center") & (df_seq["canal"] == "whatsapp")
        ).sum()
    )
    cc_direct, cc_interm, cc_no_wa, students_cc_wa = 0, 0, 0, set()
    for aluno, grp in df_seq.groupby("aluno"):
        chs = grp["canal"].tolist()
        has_cc = False
        for i, ch in enumerate(chs):
            if ch == "call_center":
                has_cc = True
                wa_idxs = [j for j in range(i + 1, len(chs)) if chs[j] == "whatsapp"]
                if not wa_idxs:
                    cc_no_wa += 1
                elif wa_idxs[0] == i + 1:
                    cc_direct += 1
                else:
                    cc_interm += 1
            elif ch == "whatsapp" and has_cc:
                students_cc_wa.add(aluno)
    df_seq["dt_trunc_sec"] = df_seq["dt"].apply(lambda x: x.replace(microsecond=0))
    return {
        "direct_consecutive_cc_to_wa_transitions": direct_cc_wa,
        "cc_contacts_with_direct_wa_posterior": cc_direct,
        "cc_contacts_with_intermediate_wa_posterior": cc_interm,
        "cc_contacts_without_wa_posterior": cc_no_wa,
        "distinct_students_with_cc_before_wa": len(students_cc_wa),
        "exact_ties_at_second_level": int(
            (df_seq.groupby(["aluno", "dt_trunc_sec"]).size() > 1).sum()
        ),
    }


def _compute_modality_divergence(
    content_df: pd.DataFrame, mod_col: str, tab_col: str
) -> Dict[str, Any]:
    """Compara modalidade cadastral com busca no texto completo e nivel 1."""
    sub = content_df[[mod_col, tab_col]].dropna()
    cad_p = sub[mod_col].apply(strip_accents).str.contains("presencial")
    cad_e = sub[mod_col].apply(strip_accents).str.contains("ead|digital")
    tab_p = sub[tab_col].apply(strip_accents).str.contains("presencial")
    tab_e = sub[tab_col].apply(strip_accents).str.contains("ead|digital")
    lvl1 = sub[tab_col].apply(lambda x: strip_accents(str(x).split(">")[0]))
    l1_p, l1_e = lvl1.str.contains("presencial"), lvl1.str.contains("ead|digital")
    return {
        "evaluated_rows": len(sub),
        "cadastral_presencial_tab_ead": int((cad_p & tab_e).sum()),
        "cadastral_ead_tab_presencial": int((cad_e & tab_p).sum()),
        "total_divergent": int(((cad_p & tab_e) | (cad_e & tab_p)).sum()),
        "level1_presencial_to_ead": int((cad_p & l1_e).sum()),
        "level1_ead_to_presencial": int((cad_e & l1_p).sum()),
        "level1_total_divergent": int(((cad_p & l1_e) | (cad_e & l1_p)).sum()),
        "classification_label": "possivel divergencia por busca textual",
    }


def profile_channel_basic_metrics(df: pd.DataFrame, channel: str) -> Dict[str, Any]:
    """Calcula nulos por coluna, duplicatas, datas min/max, filas e divergencias."""
    content_cols = [c for c in df.columns if not c.startswith("_origem_")]
    content_df = df[content_cols]
    dt_cols = [
        c for c in content_cols if any(k in c.lower() for k in ["calldate", "data"])
    ]
    date_info = {}
    for dc in dt_cols:
        p_dates = [parse_timestamp_preserve_ms(v) for v in content_df[dc].dropna()]
        date_info[dc] = {
            "min": min(p_dates).isoformat() if p_dates else None,
            "max": max(p_dates).isoformat() if p_dates else None,
            "missing_timestamps": int(content_df[dc].isna().sum()),
        }
    fila_cols = [c for c in content_cols if "fila" in c.lower()]
    mod_cols = [
        c for c in content_cols if "modalidade" in c.lower() and "desc" in c.lower()
    ]
    tab_cols = [c for c in content_cols if "tabulacao" in c.lower()]
    return {
        "channel": channel,
        "nulls_per_column": content_df.isna().sum().to_dict(),
        "exact_duplicates_content": int(content_df.duplicated().sum()),
        "dates_summary": date_info,
        "distinct_queues_count": {
            fc: int(content_df[fc].nunique(dropna=True)) for fc in fila_cols
        },
        "modality_divergence": (
            _compute_modality_divergence(content_df, mod_cols[0], tab_cols[0])
            if mod_cols and tab_cols
            else None
        ),
    }


def profile_dictionary_anomalies(dict_dir: Path) -> Dict[str, Any]:
    """Identifica codigos duplicados e conflitos de chave nos dicionarios JSON."""
    anomalies = {}
    for p in dict_dir.glob("*.json"):
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        chan_anom = {}
        for field, meta in d.items():
            dom = meta.get("dominio", [])
            counts = Counter(item.get("codigo") for item in dom if "codigo" in item)
            dups = {k: v for k, v in counts.items() if v > 1}
            if dups:
                chan_anom[field] = {
                    "duplicate_codes": dups,
                    "entries": [i for i in dom if i.get("codigo") in dups],
                }
        if chan_anom:
            anomalies[p.stem] = chan_anom
    return anomalies


def _profile_all_durations_and_tme(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Agrupa estatisticas de duracao e comparacoes de TME de todos os canais."""
    vc_dur_col = [c for c in dfs["video_chamada"].columns if "dura" in c.lower()][0]
    durations = {
        "call_center_duracao": profile_durations(
            dfs["call_center"]["DurationCallcenter"]
        ),
        "whatsapp_duracao": profile_durations(dfs["whatsapp"]["DurationCallCenter"]),
        "whatsapp_tme": profile_durations(dfs["whatsapp"]["TME"]),
        "video_chamada_duracao": profile_durations(dfs["video_chamada"][vc_dur_col]),
        "video_chamada_tme": profile_durations(dfs["video_chamada"]["TME"]),
        "totem_duracao": profile_durations(dfs["totem"]["DURACAO"]),
    }
    tme_comp = {
        "whatsapp": profile_tme_vs_duration(
            dfs["whatsapp"], "DurationCallCenter", "TME"
        ),
        "video_chamada": profile_tme_vs_duration(
            dfs["video_chamada"], vc_dur_col, "TME"
        ),
    }
    return {"durations": durations, "tme_comparison": tme_comp}


def _profile_all_ratings(dfs: Dict[str, pd.DataFrame]) -> Dict[str, Dict[str, Any]]:
    """Calcula distribuicao de satisfacao por canal e consolidado total."""
    ratings = {
        "call_center": profile_ratings(dfs["call_center"]["Pesquisa_1"]),
        "whatsapp": profile_ratings(dfs["whatsapp"]["Pesquisa_1"]),
        "video_chamada": profile_ratings(dfs["video_chamada"]["Nota Pergunta1"]),
        "totem": profile_ratings(dfs["totem"]["Nota Pergunta1"]),
    }
    ratings["total"] = aggregate_ratings(ratings)
    return ratings


def run_full_profiling(
    raw_xlsx_path: Path = Path("data/raw/analytical_database_callcenter.xlsx"),
    dict_dir: Path = Path("data/dictionaries"),
    output_json_path: Optional[Path] = Path("data/profiling_results.json"),
) -> Dict[str, Any]:
    """Executa o diagnostico completo e grava os resultados detalhados localmente."""
    dfs = load_raw_xlsx_sheets(raw_xlsx_path)
    ratings = _profile_all_ratings(dfs)
    dur_tme = _profile_all_durations_and_tme(dfs)
    vc_cs = dfs["video_chamada"]["Protocolo"].dropna().str.contains(r"^CS[0-9]{8}$")
    result = {
        "row_counts": {k: len(v) for k, v in dfs.items()},
        "total_rows": sum(len(v) for v in dfs.values()),
        "sheet_structure": profile_sheet_formulas_and_errors(raw_xlsx_path),
        "basic_per_channel": {
            ch: profile_channel_basic_metrics(df, ch) for ch, df in dfs.items()
        },
        "students": profile_identifiers(dfs),
        "queues": profile_callcenter_queues_and_retention(dfs["call_center"]),
        "protocols": {
            "call_center": classify_callcenter_protocols(
                dfs["call_center"]["Protocolo"]
            ),
            "video_chamada_standard_cs": int(vc_cs.sum()),
        },
        "ratings": ratings,
        "ratings_markdown_table": format_ratings_markdown_table(ratings),
        "durations": dur_tme["durations"],
        "tme_comparison": dur_tme["tme_comparison"],
        "dna_soa": profile_dna_soa_callcenter(dfs["call_center"]["DnaSoa"]),
        "consecutive_overlaps": profile_consecutive_overlaps(dfs),
        "journeys_cc_wa": profile_journeys_cc_wa(dfs),
        "dictionary_anomalies": profile_dictionary_anomalies(dict_dir),
    }
    if output_json_path:
        output_json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_json_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    return result
