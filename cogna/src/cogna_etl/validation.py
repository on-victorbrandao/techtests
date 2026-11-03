"""Validacao cruzada entre SQL/DuckDB (camada Gold), medidas DAX e documentacao."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import duckdb

GOLD_DIR_PADRAO = Path("data/gold")
DAX_DIR_PADRAO = Path("powerbi/dax")
DOCS_DIR_PADRAO = Path("docs")

TABELAS_GOLD_ESPERADAS: dict[str, tuple[int, int]] = {
    "dim_calendario": (12, 15),
    "dim_hora": (24, 6),
    "dim_canal": (4, 10),
    "dim_aluno": (173, 10),
    "dim_agente": (171, 8),
    "dim_fila": (33, 7),
    "dim_perfil_aluno": (53, 16),
    "dim_motivo": (591, 18),
    "fato_contato": (5991, 38),
    "fato_navegacao": (81189, 8),
    "fato_jornada": (5991, 28),
}

ARQUIVOS_DAX_ESPERADOS: dict[str, int] = {
    "01_base_volumetria.dax": 12,
    "02_satisfacao_pesquisa.dax": 10,
    "03_tempo_operacional.dax": 11,
    "04_retencao_e_cancelamento.dax": 23,
    "05_jornada_e_recontato_q1_q2_q9.dax": 26,
    "06_navegacao_ura_q8.dax": 6,
}


def _extrair_medidas_dax(dax_dir: Path) -> dict[str, dict[str, str]]:
    """Extrai o catalogo de medidas DAX com pasta, formato e expressao."""
    catalogo: dict[str, dict[str, str]] = {}
    for nome_arq in sorted(ARQUIVOS_DAX_ESPERADOS):
        caminho = dax_dir / nome_arq
        linhas = caminho.read_text(encoding="utf-8").splitlines()
        desc = ""
        folder = ""
        fmt = ""
        nome_atual: str | None = None
        corpo: list[str] = []

        for linha in linhas:
            s = linha.strip()
            if s.startswith("--"):
                meta = s[2:].strip()
                if meta.startswith("Display Folder:"):
                    partes = [p.strip() for p in meta.split("|")]
                    folder = partes[0].replace("Display Folder:", "").strip()
                    if len(partes) > 1 and "Format String:" in partes[1]:
                        fmt = partes[1].replace("Format String:", "").strip()
                else:
                    desc = meta
                continue
            if not s:
                continue
            eh_cabecalho = (
                not linha.startswith(" ")
                and linha.rstrip().endswith("=")
                and not linha.lstrip().upper().startswith(("VAR ", "RETURN"))
            )
            if eh_cabecalho:
                if nome_atual is not None:
                    catalogo[nome_atual] = {
                        "arquivo": nome_arq,
                        "pasta": folder,
                        "formato": fmt,
                        "descricao": desc,
                        "expressao": "\n".join(corpo),
                    }
                nome_atual = linha.rstrip()[:-1].strip()
                corpo = []
            elif nome_atual is not None:
                corpo.append(linha)

        if nome_atual is not None:
            catalogo[nome_atual] = {
                "arquivo": nome_arq,
                "pasta": folder,
                "formato": fmt,
                "descricao": desc,
                "expressao": "\n".join(corpo),
            }
    return catalogo


def _registrar_views_gold(con: duckdb.DuckDBPyConnection, gold_dir: Path) -> None:
    """Registra as 11 tabelas Parquet da camada Gold como views no DuckDB."""
    for tabela in TABELAS_GOLD_ESPERADAS:
        pq = (gold_dir / f"{tabela}.parquet").as_posix()
        con.execute(
            f"CREATE OR REPLACE VIEW {tabela} AS SELECT * FROM read_parquet('{pq}')"
        )


def _executar_sql_volumetria(con: duckdb.DuckDBPyConnection) -> Any:
    """Calcula a volumetria e cobertura de motivo."""
    return con.execute(
        """
        SELECT
            COUNT(*) AS total_contatos,
            COUNT(DISTINCT fc.aluno_hash) AS alunos_distintos,
            ROUND(
                COUNT(*) * 1.0 / COUNT(DISTINCT fc.aluno_hash),
                2
            ) AS media_contatos_aluno,
            COUNT(*) FILTER (WHERE fc.canal = 'call_center') AS contatos_cc,
            COUNT(*) FILTER (WHERE fc.canal = 'whatsapp') AS contatos_wa,
            COUNT(*) FILTER (
                WHERE fc.canal = 'video_chamada'
            ) AS contatos_video,
            COUNT(*) FILTER (WHERE fc.canal = 'totem') AS contatos_totem,
            COUNT(*) FILTER (
                WHERE dm.motivo_principal <> 'Sem Tabulação (Nulo)'
            ) AS motivo_preenchido,
            COUNT(*) FILTER (
                WHERE dm.motivo_principal = 'Sem Tabulação (Nulo)'
            ) AS motivo_nulo,
            ROUND(
                COUNT(*) FILTER (
                    WHERE dm.motivo_principal <> 'Sem Tabulação (Nulo)'
                ) * 100.0 / COUNT(*),
                2
            ) AS pct_motivo_preenchido,
            COUNT(*) FILTER (
                WHERE NOT dm.motivo_principal IN (
                    'Sem Tabulação (Nulo)', 'Nao identificado'
                )
            ) AS motivo_identificado,
            ROUND(
                COUNT(*) FILTER (
                    WHERE NOT dm.motivo_principal IN (
                        'Sem Tabulação (Nulo)', 'Nao identificado'
                    )
                ) * 100.0 / COUNT(*),
                2
            ) AS pct_motivo_identificado
        FROM fato_contato fc
        JOIN dim_motivo dm ON fc.motivo_id = dm.motivo_id
        """
    ).fetchone()


def _executar_sql_satisfacao(con: duckdb.DuckDBPyConnection) -> Any:
    """Calcula indicadores de pesquisa e satisfacao."""
    return con.execute(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE fc.respondeu_pesquisa
            ) AS pesquisa_respondida,
            ROUND(
                COUNT(*) FILTER (WHERE fc.respondeu_pesquisa) * 100.0
                / COUNT(*),
                2
            ) AS taxa_resposta_pct,
            SUM(fc.nota) FILTER (
                WHERE fc.respondeu_pesquisa
            ) AS soma_notas_validas,
            ROUND(
                AVG(fc.nota) FILTER (WHERE fc.respondeu_pesquisa),
                2
            ) AS nota_media_global,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE fc.respondeu_pesquisa AND fc.canal = 'call_center'
                ),
                2
            ) AS nota_media_cc,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE fc.respondeu_pesquisa AND fc.canal = 'whatsapp'
                ),
                2
            ) AS nota_media_wa,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE fc.respondeu_pesquisa AND fc.canal = 'video_chamada'
                ),
                2
            ) AS nota_media_video,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE fc.respondeu_pesquisa AND fc.canal = 'totem'
                ),
                2
            ) AS nota_media_totem,
            COUNT(*) FILTER (
                WHERE fc.respondeu_pesquisa AND fc.canal = 'totem'
            ) AS respondidos_totem,
            COUNT(*) FILTER (
                WHERE fc.respondeu_pesquisa AND fc.canal = 'whatsapp'
            ) AS respondidos_wa,
            COUNT(*) FILTER (
                WHERE fc.respondeu_pesquisa AND fc.canal = 'call_center'
            ) AS respondidos_cc,
            COUNT(*) FILTER (
                WHERE fc.respondeu_pesquisa AND fc.canal = 'video_chamada'
            ) AS respondidos_video,
            COUNT(*) FILTER (WHERE fc.flag_nota_ruim) AS notas_ruins_global,
            ROUND(
                COUNT(*) FILTER (WHERE fc.flag_nota_ruim) * 100.0
                / COUNT(*) FILTER (WHERE fc.respondeu_pesquisa),
                2
            ) AS pct_notas_ruins_global,
            COUNT(*) FILTER (
                WHERE fc.flag_nota_ruim AND fc.canal = 'whatsapp'
            ) AS notas_ruins_wa,
            ROUND(
                COUNT(*) FILTER (
                    WHERE fc.flag_nota_ruim AND fc.canal = 'whatsapp'
                ) * 100.0
                / COUNT(*) FILTER (
                    WHERE fc.respondeu_pesquisa AND fc.canal = 'whatsapp'
                ),
                2
            ) AS pct_notas_ruins_wa,
            COUNT(*) FILTER (
                WHERE fc.flag_nota_ruim AND fc.canal = 'call_center'
            ) AS notas_ruins_cc,
            COUNT(*) FILTER (
                WHERE fc.flag_nota_ruim AND fc.canal = 'video_chamada'
            ) AS notas_ruins_video,
            COUNT(*) FILTER (
                WHERE fc.flag_nota_ruim AND fc.canal = 'totem'
            ) AS notas_ruins_totem,
            COUNT(*) FILTER (
                WHERE fc.status_nota = 'sem_resposta_zero'
            ) AS sem_resposta_zero,
            COUNT(*) FILTER (
                WHERE fc.status_nota = 'sem_resposta_nulo'
            ) AS sem_resposta_nulo
        FROM fato_contato fc
        """
    ).fetchone()


def _executar_sql_tempos(con: duckdb.DuckDBPyConnection) -> Any:
    """Calcula indicadores de duracao e tempo de espera."""
    return con.execute(
        """
        SELECT
            ROUND(AVG(fc.duracao_s), 2) AS duracao_media_s,
            ROUND(MEDIAN(fc.duracao_s), 2) AS duracao_mediana_s,
            ROUND(AVG(fc.tme_s), 2) AS tme_medio_s,
            ROUND(MEDIAN(fc.tme_s), 2) AS tme_mediano_s,
            COUNT(*) FILTER (WHERE fc.tme_s IS NOT NULL) AS contatos_com_tme,
            COUNT(*) FILTER (
                WHERE fc.flag_tme_maior_duracao
            ) AS tme_maior_duracao,
            COUNT(*) FILTER (
                WHERE fc.flag_tme_maior_duracao AND fc.canal = 'whatsapp'
            ) AS tme_maior_duracao_wa,
            COUNT(*) FILTER (
                WHERE fc.flag_tme_maior_duracao AND fc.canal = 'video_chamada'
            ) AS tme_maior_duracao_video,
            ROUND(
                COUNT(*) FILTER (WHERE fc.flag_tme_maior_duracao) * 100.0
                / COUNT(*) FILTER (WHERE fc.tme_s IS NOT NULL),
                2
            ) AS pct_tme_maior_duracao,
            COUNT(*) FILTER (WHERE fc.flag_duracao_zero) AS duracao_zero,
            COUNT(*) FILTER (
                WHERE fc.flag_duracao_zero AND fc.canal = 'totem'
            ) AS duracao_zero_totem,
            ROUND(
                COUNT(*) FILTER (WHERE fc.flag_duracao_zero) * 100.0
                / COUNT(*),
                2
            ) AS pct_duracao_zero,
            COUNT(*) FILTER (
                WHERE fc.flag_outlier_duracao
            ) AS outlier_duracao,
            COUNT(*) FILTER (WHERE fc.flag_outlier_tme) AS outlier_tme,
            COUNT(*) FILTER (WHERE fc.agente_id <> 'AG-000') AS atend_humanos,
            COUNT(*) FILTER (WHERE fc.agente_id = 'AG-000') AS atend_auto
        FROM fato_contato fc
        """
    ).fetchone()


def _executar_sql_retencao(con: duckdb.DuckDBPyConnection) -> Any:
    """Calcula volume e desfechos nas filas e assuntos de retencao."""
    return con.execute(
        """
        SELECT
            COUNT(*) FILTER (WHERE fc.eh_retencao_fila) AS fila_retencao,
            COUNT(DISTINCT fc.aluno_hash) FILTER (
                WHERE fc.eh_retencao_fila
            ) AS alunos_fila_retencao,
            COUNT(*) FILTER (WHERE fc.eh_assunto_retencao) AS assunto_retencao,
            COUNT(DISTINCT fc.aluno_hash) FILTER (
                WHERE fc.eh_assunto_retencao
            ) AS alunos_assunto_retencao,
            COUNT(*) FILTER (
                WHERE fc.eh_assunto_retencao AND fc.canal = 'call_center'
            ) AS assunto_retencao_cc,
            COUNT(DISTINCT fc.aluno_hash) FILTER (
                WHERE fc.eh_assunto_retencao AND fc.canal = 'call_center'
            ) AS alunos_assunto_retencao_cc,
            COUNT(*) FILTER (
                WHERE fc.desfecho_retencao = 'pedido_cancelamento'
            ) AS pedidos_cancelamento,
            COUNT(*) FILTER (
                WHERE fc.desfecho_retencao = 'pedido_cancelamento'
                  AND fc.canal = 'call_center'
            ) AS pedidos_cancelamento_cc,
            COUNT(*) FILTER (
                WHERE fc.desfecho_retencao = 'aluno_mantido'
            ) AS alunos_mantidos,
            COUNT(*) FILTER (
                WHERE fc.desfecho_retencao = 'pedido_transferencia'
            ) AS pedidos_transferencia,
            COUNT(*) FILTER (
                WHERE fc.desfecho_retencao = 'pedido_trancamento'
            ) AS pedidos_trancamento
        FROM fato_contato fc
        """
    ).fetchone()


def _executar_sql_q4_q5(con: duckdb.DuckDBPyConnection) -> tuple[Any, Any, Any]:
    """Calcula metricas de cra_retencao, canal anterior e tempo previo."""
    cra_row = con.execute(
        """
        SELECT
            COUNT(*) AS contatos_cra_retencao,
            COUNT(DISTINCT fc.aluno_hash) AS alunos_cra_retencao
        FROM fato_contato fc
        JOIN dim_fila df ON fc.fila_id = df.fila_id
        WHERE df.eh_fila_cra_retencao_exata = TRUE
        """
    ).fetchone()

    ant_row = con.execute(
        """
        WITH ev_cancel_cc AS (
            SELECT fc.contato_id, fc.aluno_hash, fc.data_hora_contato
            FROM fato_contato fc
            WHERE fc.canal = 'call_center'
              AND fc.desfecho_retencao = 'pedido_cancelamento'
        ),
        ant_cancel AS (
            SELECT
                e.contato_id,
                COUNT(a.contato_id) FILTER (
                    WHERE a.canal <> 'call_center'
                ) > 0 AS passou_outro
            FROM ev_cancel_cc e
            LEFT JOIN fato_contato a
                ON a.aluno_hash = e.aluno_hash
               AND a.data_hora_contato < e.data_hora_contato
            GROUP BY e.contato_id
        ),
        ev_fila_ret AS (
            SELECT fc.contato_id, fc.aluno_hash, fc.data_hora_contato
            FROM fato_contato fc
            WHERE fc.canal = 'call_center' AND fc.eh_retencao_fila = TRUE
        ),
        ant_fila AS (
            SELECT
                e.contato_id,
                COUNT(a.contato_id) FILTER (
                    WHERE a.canal <> 'call_center'
                ) > 0 AS passou_outro
            FROM ev_fila_ret e
            LEFT JOIN fato_contato a
                ON a.aluno_hash = e.aluno_hash
               AND a.data_hora_contato < e.data_hora_contato
            GROUP BY e.contato_id
        )
        SELECT
            (
                SELECT COUNT(*) FILTER (WHERE passou_outro)
                FROM ant_cancel
            ) AS cancel_cc_com_outro,
            (
                SELECT ROUND(
                    COUNT(*) FILTER (WHERE passou_outro) * 100.0 / COUNT(*),
                    2
                )
                FROM ant_cancel
            ) AS pct_cancel_cc_com_outro,
            (
                SELECT COUNT(*) FILTER (WHERE passou_outro)
                FROM ant_fila
            ) AS fila_ret_com_outro,
            (
                SELECT ROUND(
                    COUNT(*) FILTER (WHERE passou_outro) * 100.0 / COUNT(*),
                    2
                )
                FROM ant_fila
            ) AS pct_fila_ret_com_outro
        """
    ).fetchone()

    prev_row = con.execute(
        """
        WITH ev_ret AS (
            SELECT fc.contato_id, fc.aluno_hash, fc.data_hora_contato
            FROM fato_contato fc
            WHERE fc.canal = 'call_center' AND fc.eh_retencao_fila = TRUE
        ),
        previos AS (
            SELECT
                e.contato_id,
                COUNT(p.contato_id) AS qtd_previos,
                epoch(
                    e.data_hora_contato - MAX(p.data_hora_contato)
                ) / 3600.0 AS horas_desde_ultimo
            FROM ev_ret e
            LEFT JOIN fato_contato p
                ON p.aluno_hash = e.aluno_hash
               AND p.data_hora_contato < e.data_hora_contato
            GROUP BY e.contato_id, e.data_hora_contato
        )
        SELECT
            ROUND(
                AVG(qtd_previos) FILTER (WHERE qtd_previos > 0),
                2
            ) AS media_contatos_previos,
            ROUND(
                MEDIAN(qtd_previos) FILTER (WHERE qtd_previos > 0),
                2
            ) AS mediana_contatos_previos,
            ROUND(
                MEDIAN(horas_desde_ultimo) FILTER (WHERE qtd_previos > 0),
                2
            ) AS mediana_horas_ultimo
        FROM previos
        """
    ).fetchone()

    return cra_row, ant_row, prev_row


def _executar_sql_jornada(con: duckdb.DuckDBPyConnection) -> tuple[Any, Any]:
    """Calcula transicoes Q1 e trincas Q2."""
    q1_row = con.execute(
        """
        WITH cc AS (
            SELECT
                fc.contato_id,
                fc.aluno_hash,
                fc.data_hora_contato,
                fj.canal_proximo,
                fj.flag_teve_wa_posterior
            FROM fato_contato fc
            JOIN fato_jornada fj ON fc.contato_id = fj.contato_id
            WHERE fc.canal = 'call_center'
        ),
        wa_pos AS (
            SELECT
                cc.contato_id,
                cc.aluno_hash,
                cc.canal_proximo,
                cc.flag_teve_wa_posterior,
                MIN(wa.data_hora_contato) AS min_wa,
                epoch(
                    MIN(wa.data_hora_contato) - cc.data_hora_contato
                ) AS sec_wa
            FROM cc
            LEFT JOIN fato_contato wa
                ON wa.aluno_hash = cc.aluno_hash
               AND wa.canal = 'whatsapp'
               AND wa.data_hora_contato > cc.data_hora_contato
            GROUP BY
                cc.contato_id,
                cc.aluno_hash,
                cc.canal_proximo,
                cc.flag_teve_wa_posterior,
                cc.data_hora_contato
        )
        SELECT
            COUNT(DISTINCT aluno_hash) FILTER (
                WHERE flag_teve_wa_posterior
            ) AS q1_alunos_wa_pos,
            COUNT(*) FILTER (
                WHERE flag_teve_wa_posterior
            ) AS q1_contatos_wa_pos,
            ROUND(
                COUNT(*) FILTER (WHERE flag_teve_wa_posterior) * 100.0
                / COUNT(*),
                2
            ) AS q1_pct_contatos_wa_pos,
            COUNT(*) FILTER (
                WHERE canal_proximo = 'whatsapp'
            ) AS q1_transicao_imediata,
            ROUND(
                COUNT(*) FILTER (WHERE canal_proximo = 'whatsapp') * 100.0
                / COUNT(*),
                2
            ) AS q1_pct_transicao_imediata,
            COUNT(*) FILTER (
                WHERE flag_teve_wa_posterior
                  AND (canal_proximo <> 'whatsapp' OR canal_proximo IS NULL)
            ) AS q1_wa_com_intermediarios,
            COUNT(*) FILTER (
                WHERE NOT flag_teve_wa_posterior
            ) AS q1_sem_wa_posterior,
            COUNT(*) FILTER (
                WHERE sec_wa IS NOT NULL AND sec_wa <= 86400
            ) AS q1_wa_ate_24h,
            COUNT(*) FILTER (
                WHERE sec_wa IS NOT NULL AND sec_wa <= 604800
            ) AS q1_wa_ate_7d
        FROM wa_pos
        """
    ).fetchone()

    q2_row = con.execute(
        """
        WITH trincas AS (
            SELECT
                j1.aluno_hash,
                j1.contato_id,
                j3.canal AS terceiro_canal
            FROM fato_jornada j1
            JOIN fato_jornada j2 ON j2.contato_id = j1.contato_id_proximo
            JOIN fato_jornada j3 ON j3.contato_id = j2.contato_id_proximo
            WHERE j1.canal = 'call_center' AND j2.canal = 'whatsapp'
        ),
        prim_cc AS (
            SELECT aluno_hash, MIN(data_hora_contato) AS min_cc
            FROM fato_contato WHERE canal = 'call_center'
            GROUP BY aluno_hash
        ),
        prim_wa AS (
            SELECT fc.aluno_hash, MIN(fc.data_hora_contato) AS min_wa
            FROM fato_contato fc
            JOIN prim_cc cc
                ON fc.aluno_hash = cc.aluno_hash
               AND fc.data_hora_contato > cc.min_cc
            WHERE fc.canal = 'whatsapp'
            GROUP BY fc.aluno_hash
        ),
        interm AS (
            SELECT fc.aluno_hash, fc.canal AS terceiro_canal
            FROM fato_contato fc
            JOIN prim_wa wa
                ON fc.aluno_hash = wa.aluno_hash
               AND fc.data_hora_contato > wa.min_wa
        )
        SELECT
            (
                SELECT COUNT(DISTINCT aluno_hash)
                FROM trincas
                WHERE terceiro_canal <> 'whatsapp'
            ) AS q2_al_exceto_wa,
            (
                SELECT COUNT(*)
                FROM trincas
                WHERE terceiro_canal <> 'whatsapp'
            ) AS q2_tr_exceto_wa,
            (
                SELECT COUNT(DISTINCT aluno_hash)
                FROM trincas
                WHERE terceiro_canal IN ('video_chamada', 'totem')
            ) AS q2_al_vid_tot,
            (
                SELECT COUNT(*)
                FROM trincas
                WHERE terceiro_canal IN ('video_chamada', 'totem')
            ) AS q2_tr_vid_tot,
            (SELECT COUNT(DISTINCT aluno_hash) FROM trincas) AS q2_al_qualquer,
            (SELECT COUNT(*) FROM trincas) AS q2_tr_qualquer,
            (
                SELECT COUNT(DISTINCT aluno_hash)
                FROM interm
                WHERE terceiro_canal <> 'whatsapp'
            ) AS q2_al_interm_exceto_wa,
            (
                SELECT COUNT(DISTINCT aluno_hash)
                FROM interm
                WHERE terceiro_canal IN ('video_chamada', 'totem')
            ) AS q2_al_interm_vid_tot
        """
    ).fetchone()

    return q1_row, q2_row


def _executar_sql_agentes_e_ura(
    con: duckdb.DuckDBPyConnection,
) -> tuple[Any, Any, Any, Any]:
    """Calcula recontatos Q9, sobreposicoes e pontos de navegacao Q8."""
    q9_sobrep = con.execute(
        """
        SELECT
            COUNT(*) FILTER (
                WHERE flag_sobreposicao_estimada = 'intracanal'
            ) AS sobreposicao_intracanal,
            COUNT(*) FILTER (
                WHERE flag_sobreposicao_estimada = 'intercanal'
            ) AS sobreposicao_intercanal,
            COUNT(*) FILTER (
                WHERE flag_sobreposicao_estimada IN ('intracanal', 'intercanal')
            ) AS sobreposicao_total
        FROM fato_jornada
        """
    ).fetchone()

    top_visao_a = con.execute(
        """
        WITH atend AS (
            SELECT agente_id, COUNT(*) AS total_atendimentos
            FROM fato_contato
            WHERE agente_id <> 'AG-000'
            GROUP BY 1
        ),
        recont AS (
            SELECT
                agente_id_atribuido_recontato AS agente_id,
                COUNT(*) AS recontatos_mesmo_dia
            FROM fato_jornada
            WHERE flag_recontato_mesmo_dia_canal_com_agente = TRUE
              AND agente_id_atribuido_recontato IS NOT NULL
              AND agente_id_atribuido_recontato <> 'AG-000'
            GROUP BY 1
        )
        SELECT
            r.agente_id,
            da.canal_agente AS canal_principal,
            r.recontatos_mesmo_dia,
            a.total_atendimentos,
            ROUND(
                r.recontatos_mesmo_dia * 100.0 / a.total_atendimentos,
                2
            ) AS taxa_pct
        FROM recont r
        JOIN atend a USING (agente_id)
        JOIN dim_agente da USING (agente_id)
        ORDER BY r.recontatos_mesmo_dia DESC, a.total_atendimentos DESC
        LIMIT 1
        """
    ).fetchone()

    top_visao_b = con.execute(
        """
        WITH atend AS (
            SELECT agente_id, COUNT(*) AS total_atendimentos
            FROM fato_contato
            WHERE agente_id <> 'AG-000'
            GROUP BY 1
        ),
        recont AS (
            SELECT
                agente_id_atribuido_recontato_intracanal AS agente_id,
                COUNT(*) AS recontatos_mesmo_dia_intracanal
            FROM fato_jornada
            WHERE flag_recontato_intracanal_mesmo_dia = TRUE
              AND agente_id_atribuido_recontato_intracanal IS NOT NULL
              AND agente_id_atribuido_recontato_intracanal <> 'AG-000'
            GROUP BY 1
        )
        SELECT
            r.agente_id,
            da.canal_agente AS canal_principal,
            r.recontatos_mesmo_dia_intracanal,
            a.total_atendimentos,
            ROUND(
                r.recontatos_mesmo_dia_intracanal * 100.0 / a.total_atendimentos,
                2
            ) AS taxa_pct
        FROM recont r
        JOIN atend a USING (agente_id)
        JOIN dim_agente da USING (agente_id)
        ORDER BY
            r.recontatos_mesmo_dia_intracanal DESC,
            a.total_atendimentos DESC
        LIMIT 1
        """
    ).fetchone()

    q8_row = con.execute(
        """
        WITH nav_dist AS (
            SELECT DISTINCT fn.contato_id, fn.ponto_navegacao
            FROM fato_navegacao fn
            WHERE fn.tipo_sequencia = 'original'
        )
        SELECT
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao IN ('98', '99')
            ) AS q8_contatos_98_99,
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao = '98'
            ) AS q8_contatos_98,
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao = '99'
            ) AS q8_contatos_99,
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao = '99' AND fc.respondeu_pesquisa
            ) AS q8_respondidos_99,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE nd.ponto_navegacao = '99' AND fc.respondeu_pesquisa
                ),
                2
            ) AS q8_nota_media_99,
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao = '1 - Identificação via Mailing'
            ) AS q8_contatos_no_1,
            COUNT(*) FILTER (
                WHERE nd.ponto_navegacao = '1 - Identificação via Mailing'
                  AND fc.respondeu_pesquisa
            ) AS q8_respondidos_no_1,
            ROUND(
                AVG(fc.nota) FILTER (
                    WHERE nd.ponto_navegacao = '1 - Identificação via Mailing'
                      AND fc.respondeu_pesquisa
                ),
                2
            ) AS q8_nota_media_no_1
        FROM nav_dist nd
        JOIN fato_contato fc ON nd.contato_id = fc.contato_id
        """
    ).fetchone()

    return q9_sobrep, top_visao_a, top_visao_b, q8_row


def _calcular_metricas_sql(con: duckdb.DuckDBPyConnection) -> dict[str, Any]:
    """Calcula todas as metricas de Q1 a Q9 e KPIs operacionais direto na Gold."""
    fc_vol = _executar_sql_volumetria(con)
    fc_sat = _executar_sql_satisfacao(con)
    fc_ops = _executar_sql_tempos(con)
    fc_ret = _executar_sql_retencao(con)
    cra_row, ant_row, prev_row = _executar_sql_q4_q5(con)
    q1_row, q2_row = _executar_sql_jornada(con)
    q9_sobrep, top_visao_a, top_visao_b, q8_row = _executar_sql_agentes_e_ura(con)

    assert fc_vol is not None
    assert fc_sat is not None
    assert fc_ops is not None
    assert fc_ret is not None
    assert cra_row is not None
    assert ant_row is not None
    assert prev_row is not None
    assert q1_row is not None
    assert q2_row is not None
    assert q9_sobrep is not None
    assert top_visao_a is not None
    assert top_visao_b is not None
    assert q8_row is not None

    return {
        "volumetria": {
            "total_contatos": int(fc_vol[0]),
            "alunos_distintos": int(fc_vol[1]),
            "media_contatos_aluno": float(fc_vol[2]),
            "contatos_cc": int(fc_vol[3]),
            "contatos_wa": int(fc_vol[4]),
            "contatos_video": int(fc_vol[5]),
            "contatos_totem": int(fc_vol[6]),
            "motivo_preenchido": int(fc_vol[7]),
            "motivo_nulo": int(fc_vol[8]),
            "pct_motivo_preenchido": float(fc_vol[9]),
            "motivo_identificado": int(fc_vol[10]),
            "pct_motivo_identificado": float(fc_vol[11]),
        },
        "satisfacao": {
            "pesquisa_respondida": int(fc_sat[0]),
            "taxa_resposta_pct": float(fc_sat[1]),
            "soma_notas_validas": int(fc_sat[2]),
            "nota_media_global": float(fc_sat[3]),
            "nota_media_cc": float(fc_sat[4]),
            "nota_media_wa": float(fc_sat[5]),
            "nota_media_video": float(fc_sat[6]),
            "nota_media_totem": float(fc_sat[7]),
            "respondidos_totem": int(fc_sat[8]),
            "respondidos_wa": int(fc_sat[9]),
            "respondidos_cc": int(fc_sat[10]),
            "respondidos_video": int(fc_sat[11]),
            "notas_ruins_global": int(fc_sat[12]),
            "pct_notas_ruins_global": float(fc_sat[13]),
            "notas_ruins_wa": int(fc_sat[14]),
            "pct_notas_ruins_wa": float(fc_sat[15]),
            "notas_ruins_cc": int(fc_sat[16]),
            "notas_ruins_video": int(fc_sat[17]),
            "notas_ruins_totem": int(fc_sat[18]),
            "sem_resposta_zero": int(fc_sat[19]),
            "sem_resposta_nulo": int(fc_sat[20]),
        },
        "tempo_operacional": {
            "duracao_media_s": float(fc_ops[0]),
            "duracao_mediana_s": float(fc_ops[1]),
            "tme_medio_s": float(fc_ops[2]),
            "tme_mediano_s": float(fc_ops[3]),
            "contatos_com_tme": int(fc_ops[4]),
            "tme_maior_duracao": int(fc_ops[5]),
            "tme_maior_duracao_wa": int(fc_ops[6]),
            "tme_maior_duracao_video": int(fc_ops[7]),
            "pct_tme_maior_duracao": float(fc_ops[8]),
            "duracao_zero": int(fc_ops[9]),
            "duracao_zero_totem": int(fc_ops[10]),
            "pct_duracao_zero": float(fc_ops[11]),
            "outlier_duracao": int(fc_ops[12]),
            "outlier_tme": int(fc_ops[13]),
            "atendimentos_humanos": int(fc_ops[14]),
            "atendimentos_autoatendimento": int(fc_ops[15]),
        },
        "retencao_q4_q5": {
            "fila_retencao": int(fc_ret[0]),
            "alunos_fila_retencao": int(fc_ret[1]),
            "assunto_retencao": int(fc_ret[2]),
            "alunos_assunto_retencao": int(fc_ret[3]),
            "assunto_retencao_cc": int(fc_ret[4]),
            "alunos_assunto_retencao_cc": int(fc_ret[5]),
            "pedidos_cancelamento": int(fc_ret[6]),
            "pedidos_cancelamento_cc": int(fc_ret[7]),
            "alunos_mantidos": int(fc_ret[8]),
            "pedidos_transferencia": int(fc_ret[9]),
            "pedidos_trancamento": int(fc_ret[10]),
            "contatos_cra_retencao": int(cra_row[0]),
            "alunos_cra_retencao": int(cra_row[1]),
            "cancel_cc_com_outro_canal": int(ant_row[0]),
            "pct_cancel_cc_com_outro_canal": float(ant_row[1]),
            "fila_ret_com_outro_canal": int(ant_row[2]),
            "pct_fila_ret_com_outro_canal": float(ant_row[3]),
            "media_contatos_previos_ret": float(prev_row[0]),
            "mediana_contatos_previos_ret": float(prev_row[1]),
            "mediana_horas_desde_ultimo_contato": float(prev_row[2]),
        },
        "jornada_q1_q2_q9": {
            "q1_alunos_cc_wa_posterior": int(q1_row[0]),
            "q1_contatos_cc_wa_posterior": int(q1_row[1]),
            "q1_pct_contatos_cc_wa_posterior": float(q1_row[2]),
            "q1_transicao_imediata": int(q1_row[3]),
            "q1_pct_transicao_imediata": float(q1_row[4]),
            "q1_wa_com_intermediarios": int(q1_row[5]),
            "q1_sem_wa_posterior": int(q1_row[6]),
            "q1_wa_ate_24h": int(q1_row[7]),
            "q1_wa_ate_7d": int(q1_row[8]),
            "q2_alunos_consec_exceto_wa": int(q2_row[0]),
            "q2_trincas_consec_exceto_wa": int(q2_row[1]),
            "q2_alunos_consec_video_totem": int(q2_row[2]),
            "q2_trincas_consec_video_totem": int(q2_row[3]),
            "q2_alunos_consec_qualquer": int(q2_row[4]),
            "q2_trincas_consec_qualquer": int(q2_row[5]),
            "q2_alunos_interm_exceto_wa": int(q2_row[6]),
            "q2_alunos_interm_video_totem": int(q2_row[7]),
            "sobreposicao_intracanal": int(q9_sobrep[0]),
            "sobreposicao_intercanal": int(q9_sobrep[1]),
            "sobreposicao_total": int(q9_sobrep[2]),
            "q9_top1_visao_a": {
                "agente_id": str(top_visao_a[0]),
                "canal_principal": str(top_visao_a[1]),
                "recontatos_mesmo_dia": int(top_visao_a[2]),
                "total_atendimentos": int(top_visao_a[3]),
                "taxa_pct": float(top_visao_a[4]),
            },
            "q9_top1_visao_b": {
                "agente_id": str(top_visao_b[0]),
                "canal_principal": str(top_visao_b[1]),
                "recontatos_mesmo_dia_intracanal": int(top_visao_b[2]),
                "total_atendimentos": int(top_visao_b[3]),
                "taxa_pct": float(top_visao_b[4]),
            },
        },
        "navegacao_q8": {
            "q8_contatos_98_99": int(q8_row[0]),
            "q8_contatos_98": int(q8_row[1]),
            "q8_contatos_99": int(q8_row[2]),
            "q8_respondidos_99": int(q8_row[3]),
            "q8_nota_media_99": float(q8_row[4]),
            "q8_contatos_no_1": int(q8_row[5]),
            "q8_respondidos_no_1": int(q8_row[6]),
            "q8_nota_media_no_1": float(q8_row[7]),
        },
    }


def _montar_lista_reconciliacao(
    sql_m: dict[str, Any], aj: dict[str, Any]
) -> list[tuple[str, float | int | str, float | int | str, float]]:
    """Gera os pares de comparacao entre SQL e analytics_results.json."""
    q01 = {r["recorte"]: r for r in aj["q01_cc_para_whatsapp"]}
    q02_c = {
        r.get("escopo_terceiro_canal"): r
        for r in aj["q02_cc_wa_outro_canal"]
        if r.get("tipo_sequencia") == "a_estritamente_consecutiva"
    }
    q02_i = {
        r.get("escopo_terceiro_canal"): r
        for r in aj["q02_cc_wa_outro_canal"]
        if r.get("tipo_sequencia") == "b_com_contatos_intermediarios"
    }
    q04 = {
        (r.get("escopo"), r.get("categoria_valor")): r
        for r in aj["q04_perfil_retencao_e_contato_anterior"]
        if r.get("parte") == "PARTE_B_CONTATO_ANTERIOR"
    }
    q05_0 = aj["q05_comportamento_antes_retencao"][0]
    q06 = {r["canal"]: r for r in aj["q06_canal_pior_nota"]}
    q06_tot = q06["TOTAL_GERAL"]
    q09_top_a = aj["q09_agente_recontato_mesmo_dia"][0]

    cand_b = [
        r for r in aj["q09_agente_recontato_mesmo_dia"] if r["agente_id"] == "AG-001"
    ]
    ref_b = cand_b[0]["ref_recontatos_intracanal"] if cand_b else 173

    v = sql_m["volumetria"]
    s = sql_m["satisfacao"]
    j = sql_m["jornada_q1_q2_q9"]
    r = sql_m["retencao_q4_q5"]

    return [
        ("total_contatos", v["total_contatos"], 5991, 0.0),
        ("alunos_distintos", v["alunos_distintos"], 173, 0.0),
        ("media_contatos_aluno", v["media_contatos_aluno"], 34.63, 1e-4),
        (
            "pesquisa_respondida",
            s["pesquisa_respondida"],
            q06_tot["notas_validas"],
            0.0,
        ),
        (
            "taxa_resposta_pct",
            s["taxa_resposta_pct"],
            q06_tot["taxa_resposta_pct"],
            1e-4,
        ),
        ("soma_notas_validas", s["soma_notas_validas"], q06_tot["soma_notas"], 0.0),
        ("nota_media_global", s["nota_media_global"], q06_tot["nota_media"], 1e-4),
        ("nota_media_wa", s["nota_media_wa"], q06["whatsapp"]["nota_media"], 1e-4),
        ("nota_media_cc", s["nota_media_cc"], q06["call_center"]["nota_media"], 1e-4),
        (
            "nota_media_video",
            s["nota_media_video"],
            q06["video_chamada"]["nota_media"],
            1e-4,
        ),
        ("nota_media_totem", s["nota_media_totem"], q06["totem"]["nota_media"], 1e-4),
        (
            "notas_ruins_global",
            s["notas_ruins_global"],
            q06_tot["qtd_notas_ruins"],
            0.0,
        ),
        (
            "notas_ruins_wa",
            s["notas_ruins_wa"],
            q06["whatsapp"]["qtd_notas_ruins"],
            0.0,
        ),
        (
            "q1_alunos_cc_wa_pos",
            j["q1_alunos_cc_wa_posterior"],
            q01["1_qualquer_wa_posterior_no_periodo"]["alunos_distintos"],
            0.0,
        ),
        (
            "q1_contatos_cc_wa_pos",
            j["q1_contatos_cc_wa_posterior"],
            q01["1_qualquer_wa_posterior_no_periodo"]["contatos_cc"],
            0.0,
        ),
        (
            "q1_transicao_imediata",
            j["q1_transicao_imediata"],
            q01["2_transicao_imediata_cc_para_wa"]["contatos_cc"],
            0.0,
        ),
        (
            "q1_wa_ate_24h",
            j["q1_wa_ate_24h"],
            q01["5_sensibilidade_janela_ate_24h"]["contatos_cc"],
            0.0,
        ),
        (
            "q1_wa_ate_7d",
            j["q1_wa_ate_7d"],
            q01["6_sensibilidade_janela_ate_7_dias"]["contatos_cc"],
            0.0,
        ),
        (
            "q2_al_consec_exceto_wa",
            j["q2_alunos_consec_exceto_wa"],
            q02_c["consolidado_exceto_whatsapp"]["alunos_distintos"],
            0.0,
        ),
        (
            "q2_tr_consec_exceto_wa",
            j["q2_trincas_consec_exceto_wa"],
            q02_c["consolidado_exceto_whatsapp"]["qtd_ocorrencias"],
            0.0,
        ),
        (
            "q2_al_consec_vid_tot",
            j["q2_alunos_consec_video_totem"],
            q02_c["consolidado_exceto_wa_e_cc"]["alunos_distintos"],
            0.0,
        ),
        (
            "q2_tr_consec_vid_tot",
            j["q2_trincas_consec_video_totem"],
            q02_c["consolidado_exceto_wa_e_cc"]["qtd_ocorrencias"],
            0.0,
        ),
        (
            "q2_al_consec_qualquer",
            j["q2_alunos_consec_qualquer"],
            q02_c["consolidado_qualquer_4_canais"]["alunos_distintos"],
            0.0,
        ),
        (
            "q2_tr_consec_qualquer",
            j["q2_trincas_consec_qualquer"],
            q02_c["consolidado_qualquer_4_canais"]["qtd_ocorrencias"],
            0.0,
        ),
        (
            "q2_al_interm_exceto_wa",
            j["q2_alunos_interm_exceto_wa"],
            q02_i["consolidado_exceto_whatsapp"]["alunos_distintos"],
            0.0,
        ),
        (
            "q2_al_interm_vid_tot",
            j["q2_alunos_interm_video_totem"],
            q02_i["consolidado_exceto_wa_e_cc"]["alunos_distintos"],
            0.0,
        ),
        ("fila_retencao", r["fila_retencao"], 270, 0.0),
        ("contatos_cra_retencao", r["contatos_cra_retencao"], 229, 0.0),
        ("assunto_retencao", r["assunto_retencao"], 743, 0.0),
        ("assunto_retencao_cc", r["assunto_retencao_cc"], 266, 0.0),
        (
            "cancel_cc_com_outro",
            r["cancel_cc_com_outro_canal"],
            q04[("4_pedido_cancelamento_cc_114", "1_qualquer_outro_canal_exceto_cc")][
                "contatos"
            ],
            0.0,
        ),
        (
            "fila_ret_com_outro",
            r["fila_ret_com_outro_canal"],
            q04[("2_quatro_filas_retencao_270", "1_qualquer_outro_canal_exceto_cc")][
                "contatos"
            ],
            0.0,
        ),
        (
            "media_contatos_previos_ret",
            r["media_contatos_previos_ret"],
            q05_0["media_contatos_previos"],
            1e-4,
        ),
        (
            "mediana_contatos_previos_ret",
            r["mediana_contatos_previos_ret"],
            q05_0["mediana_contatos_previos"],
            1e-4,
        ),
        (
            "mediana_horas_ultimo_contato",
            r["mediana_horas_desde_ultimo_contato"],
            q05_0["mediana_horas_ultimo_previo"],
            1e-4,
        ),
        (
            "q9_top1_visao_a_agente",
            j["q9_top1_visao_a"]["agente_id"],
            q09_top_a["agente_id"],
            0.0,
        ),
        (
            "q9_top1_visao_a_recont",
            j["q9_top1_visao_a"]["recontatos_mesmo_dia"],
            q09_top_a["volume_recontatos_mesmo_dia"],
            0.0,
        ),
        ("q9_top1_visao_b_agente", j["q9_top1_visao_b"]["agente_id"], "AG-001", 0.0),
        (
            "q9_top1_visao_b_recont",
            j["q9_top1_visao_b"]["recontatos_mesmo_dia_intracanal"],
            ref_b,
            0.0,
        ),
        ("sobreposicao_intracanal", j["sobreposicao_intracanal"], 308, 0.0),
        ("sobreposicao_intercanal", j["sobreposicao_intercanal"], 576, 0.0),
    ]


def _reconciliar_sql_vs_analytics_json(
    sql_metrics: dict[str, Any], analytics_json: dict[str, Any]
) -> list[dict[str, Any]]:
    """Compara cada metrica SQL calculada nos Parquets com analytics_results.json."""
    pares = _montar_lista_reconciliacao(sql_metrics, analytics_json)
    resultados: list[dict[str, Any]] = []
    for metrica, val_sql, val_ref, tol in pares:
        if isinstance(val_sql, str) or isinstance(val_ref, str):
            ok = str(val_sql) == str(val_ref)
            diff = 0.0 if ok else 1.0
        else:
            diff = abs(float(val_sql) - float(val_ref))
            ok = diff <= tol
        resultados.append(
            {
                "metrica": metrica,
                "valor_sql_parquet": val_sql,
                "valor_referencia_dax_gold": val_ref,
                "diferenca": round(diff, 6),
                "tolerancia": tol,
                "status": "ok" if ok else "divergente",
            }
        )
    return resultados


def _validar_documentacao_markdown(
    docs_dir: Path, sql_metrics: dict[str, Any]
) -> dict[str, Any]:
    """Confere os numeros documentados em docs/ contra as metricas reais da Gold."""
    doc_semantica = (docs_dir / "camada_semantica_powerbi.md").read_text(
        encoding="utf-8"
    )
    doc_modelagem = (docs_dir / "modelagem_e_analises.md").read_text(encoding="utf-8")

    padrao_tabela = re.compile(
        r"\|\s*`powerbi/m/([a-z_]+)\.pq`\s*\|\s*`[a-z_]+`\s*\|\s*"
        r"(?:Dimensão|Fato)\s*\|\s*([0-9.]+)\s*\|\s*([0-9]+)\s*\|"
    )
    tabelas_doc: dict[str, tuple[int, int]] = {}
    for nome_tab, l_str, c_str in padrao_tabela.findall(doc_semantica):
        linhas_int = int(l_str.replace(".", ""))
        cols_int = int(c_str)
        tabelas_doc[nome_tab] = (linhas_int, cols_int)

    divergencias_doc: list[str] = []
    for tab, esperado in TABELAS_GOLD_ESPERADAS.items():
        if tabelas_doc.get(tab) != esperado:
            divergencias_doc.append(
                f"Tabela {tab}: doc={tabelas_doc.get(tab)} vs gold={esperado}"
            )

    tokens_comuns = [
        "5.991",
        "173",
        "1.499",
        "1.494",
        "1.945",
        "32,47%",
        "8.643",
        "4,44",
        "3,89",
        "154",
        "17,07%",
        "270",
        "229",
        "743",
        "266",
        "110",
        "96,49%",
        "255",
        "94,44%",
        "13,41",
        "1,55",
        "1.403",
        "93,60%",
        "340",
        "22,68%",
        "860",
        "138",
        "251",
        "104",
        "145",
        "157",
        "325",
        "172",
        "AG-008",
        "200",
        "AG-001",
        "173",
        "308",
        "576",
    ]
    for tok in tokens_comuns:
        if tok not in doc_semantica:
            divergencias_doc.append(f"Token '{tok}' ausente em doc semantica")
        if tok not in doc_modelagem:
            divergencias_doc.append(f"Token '{tok}' ausente em doc modelagem")

    if "34,63" not in doc_semantica:
        divergencias_doc.append("Token '34,63' ausente em doc semantica")
    if "11,00" not in doc_semantica:
        divergencias_doc.append("Token '11,00' ausente em doc semantica")
    if "11,0" not in doc_modelagem:
        divergencias_doc.append("Token '11,0' ausente em doc modelagem")

    assert sql_metrics["volumetria"]["total_contatos"] == 5991
    assert sql_metrics["satisfacao"]["pesquisa_respondida"] == 1945

    return {
        "tabelas_verificadas": len(tabelas_doc),
        "tokens_verificados": len(tokens_comuns) + 3,
        "divergencias": divergencias_doc,
        "status": "ok" if not divergencias_doc else "divergente",
    }


def run_validation(
    gold_dir: Path | None = None,
    dax_dir: Path | None = None,
    docs_dir: Path | None = None,
) -> dict[str, Any]:
    """Executa a reconciliacao SQL vs. DAX e valida a documentacao da camada Gold."""
    gold_path = gold_dir or GOLD_DIR_PADRAO
    dax_path = dax_dir or DAX_DIR_PADRAO
    docs_path = docs_dir or DOCS_DIR_PADRAO

    catalogo_dax = _extrair_medidas_dax(dax_path)
    contagem_por_arquivo: dict[str, int] = {}
    for info in catalogo_dax.values():
        arq = info["arquivo"]
        contagem_por_arquivo[arq] = contagem_por_arquivo.get(arq, 0) + 1

    con = duckdb.connect()
    try:
        _registrar_views_gold(con, gold_path)
        tabelas_fisicas: dict[str, dict[str, int]] = {}
        for tab in TABELAS_GOLD_ESPERADAS:
            row_cnt = con.execute(f"SELECT COUNT(*) FROM {tab}").fetchone()
            col_cnt = len(con.execute(f"DESCRIBE SELECT * FROM {tab}").fetchall())
            assert row_cnt is not None
            tabelas_fisicas[tab] = {
                "linhas": int(row_cnt[0]),
                "colunas": int(col_cnt),
            }
        metricas_sql = _calcular_metricas_sql(con)
    finally:
        con.close()

    analytics_json = json.loads(
        (gold_path / "analytics_results.json").read_text(encoding="utf-8")
    )
    reconciliacao = _reconciliar_sql_vs_analytics_json(metricas_sql, analytics_json)
    doc_check = _validar_documentacao_markdown(docs_path, metricas_sql)

    divergencias_reconciliacao = [r for r in reconciliacao if r["status"] != "ok"]
    divergencias_tabelas = [
        tab
        for tab, (l_esp, c_esp) in TABELAS_GOLD_ESPERADAS.items()
        if tabelas_fisicas[tab]["linhas"] != l_esp
        or tabelas_fisicas[tab]["colunas"] != c_esp
    ]
    divergencias_dax = [
        arq
        for arq, qtd_esp in ARQUIVOS_DAX_ESPERADOS.items()
        if contagem_por_arquivo.get(arq, 0) != qtd_esp
    ]

    total_divergencias = (
        len(divergencias_reconciliacao)
        + len(divergencias_tabelas)
        + len(divergencias_dax)
        + len(doc_check["divergencias"])
    )

    relatorio: dict[str, Any] = {
        "status": "ok" if total_divergencias == 0 else "divergente",
        "total_divergencias": total_divergencias,
        "total_tabelas_gold": len(tabelas_fisicas),
        "total_medidas_dax": len(catalogo_dax),
        "medidas_por_arquivo": contagem_por_arquivo,
        "tabelas_gold": tabelas_fisicas,
        "metricas_sql_gold": metricas_sql,
        "reconciliacao_sql_vs_dax": reconciliacao,
        "consistencia_documentacao": doc_check,
    }

    out_path = gold_path / "validation_report.json"
    out_path.write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return relatorio
