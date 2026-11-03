"""Testes automatizados da validacao cruzada SQL vs. DAX e modelo semantico.

Valida a execucao do modulo cogna_etl.validation, os Parquets da camada Gold,
o catalogo de 88 medidas DAX e a documentacao tecnica em docs/.
"""

import json
import subprocess
import sys
from pathlib import Path

from cogna_etl.validation import (
    ARQUIVOS_DAX_ESPERADOS,
    TABELAS_GOLD_ESPERADAS,
    run_validation,
)

GOLD_DIR = Path("data/gold")
DOCS_DIR = Path("docs")


def test_run_validation_executa_sem_divergencias() -> None:
    """Garante que run_validation roda sobre a Gold e retorna zero divergencias."""
    res = run_validation()
    assert res["status"] == "ok"
    assert res["total_divergencias"] == 0
    assert res["total_tabelas_gold"] == 11
    assert res["total_medidas_dax"] == 88

    # confere a contagem exata de medidas por arquivo
    for arq, qtd_esp in ARQUIVOS_DAX_ESPERADOS.items():
        assert res["medidas_por_arquivo"][arq] == qtd_esp

    # verifica o arquivo de relatorio gerado
    rep_path = GOLD_DIR / "validation_report.json"
    assert rep_path.exists()
    conteudo_rep = json.loads(rep_path.read_text(encoding="utf-8"))
    assert conteudo_rep["status"] == "ok"
    assert conteudo_rep["total_divergencias"] == 0


def test_metricas_volumetria_e_satisfacao_gold() -> None:
    """Valida volumetria geral (5.991) e indicadores de satisfacao (Q6/Q7)."""
    res = run_validation()
    vol = res["metricas_sql_gold"]["volumetria"]
    sat = res["metricas_sql_gold"]["satisfacao"]
    ops = res["metricas_sql_gold"]["tempo_operacional"]

    # volumetria por canal e alunos
    assert vol["total_contatos"] == 5991
    assert vol["alunos_distintos"] == 173
    assert vol["media_contatos_aluno"] == 34.63
    assert vol["contatos_cc"] == 1499
    assert vol["contatos_wa"] == 1494
    assert vol["contatos_video"] == 1499
    assert vol["contatos_totem"] == 1499

    # cobertura de motivo
    assert vol["motivo_preenchido"] == 5461
    assert vol["motivo_nulo"] == 530
    assert vol["pct_motivo_preenchido"] == 91.15
    assert vol["motivo_identificado"] == 5230
    assert vol["pct_motivo_identificado"] == 87.30

    # satisfacao geral e canais
    assert sat["pesquisa_respondida"] == 1945
    assert sat["taxa_resposta_pct"] == 32.47
    assert sat["soma_notas_validas"] == 8643
    assert sat["nota_media_global"] == 4.44
    assert sat["nota_media_cc"] == 4.56
    assert sat["nota_media_wa"] == 3.89
    assert sat["nota_media_video"] == 4.70
    assert sat["nota_media_totem"] == 4.42
    assert sat["respondidos_totem"] == 24
    assert sat["notas_ruins_global"] == 154
    assert sat["pct_notas_ruins_global"] == 7.92
    assert sat["notas_ruins_wa"] == 84
    assert sat["pct_notas_ruins_wa"] == 17.07

    # indicadores operacionais de tempo
    assert ops["contatos_com_tme"] == 2993
    assert ops["tme_maior_duracao"] == 68
    assert ops["tme_maior_duracao_wa"] == 64
    assert ops["tme_maior_duracao_video"] == 4
    assert ops["pct_tme_maior_duracao"] == 2.27
    assert ops["duracao_zero"] == 183
    assert ops["duracao_zero_totem"] == 183


def test_metricas_jornada_q1_q2_q9() -> None:
    """Valida as perguntas de transicao de canal, trincas e recontato no mesmo dia."""
    res = run_validation()
    jor = res["metricas_sql_gold"]["jornada_q1_q2_q9"]
    ops = res["metricas_sql_gold"]["tempo_operacional"]

    # Q1 Call Center para WhatsApp
    assert jor["q1_alunos_cc_wa_posterior"] == 173
    assert jor["q1_contatos_cc_wa_posterior"] == 1403
    assert jor["q1_pct_contatos_cc_wa_posterior"] == 93.60
    assert jor["q1_transicao_imediata"] == 340
    assert jor["q1_pct_transicao_imediata"] == 22.68
    assert jor["q1_wa_com_intermediarios"] == 1063
    assert jor["q1_sem_wa_posterior"] == 96
    assert jor["q1_wa_ate_24h"] == 860
    assert jor["q1_wa_ate_7d"] == 1403

    # Q2 trincas consecutivas e intermediarios
    assert jor["q2_alunos_consec_exceto_wa"] == 138
    assert jor["q2_trincas_consec_exceto_wa"] == 251
    assert jor["q2_alunos_consec_video_totem"] == 104
    assert jor["q2_trincas_consec_video_totem"] == 145
    assert jor["q2_alunos_consec_qualquer"] == 157
    assert jor["q2_trincas_consec_qualquer"] == 325
    assert jor["q2_alunos_interm_exceto_wa"] == 173
    assert jor["q2_alunos_interm_video_totem"] == 172

    # Q9 agentes e recontatos
    assert ops["atendimentos_humanos"] == 4492
    assert ops["atendimentos_autoatendimento"] == 1499
    assert jor["q9_top1_visao_a"]["agente_id"] == "AG-008"
    assert jor["q9_top1_visao_a"]["recontatos_mesmo_dia"] == 200
    assert jor["q9_top1_visao_a"]["total_atendimentos"] == 204
    assert jor["q9_top1_visao_a"]["taxa_pct"] == 98.04

    assert jor["q9_top1_visao_b"]["agente_id"] == "AG-001"
    assert jor["q9_top1_visao_b"]["recontatos_mesmo_dia_intracanal"] == 173
    assert jor["q9_top1_visao_b"]["total_atendimentos"] == 185
    assert jor["q9_top1_visao_b"]["taxa_pct"] == 93.51

    # sobreposicoes de horario estimadas
    assert jor["sobreposicao_intracanal"] == 308
    assert jor["sobreposicao_intercanal"] == 576
    assert jor["sobreposicao_total"] == 884


def test_metricas_retencao_q4_q5_e_ura_q8() -> None:
    """Valida retencao, desfechos de cancelamento e pontos de navegacao da URA."""
    res = run_validation()
    ret = res["metricas_sql_gold"]["retencao_q4_q5"]
    nav = res["metricas_sql_gold"]["navegacao_q8"]

    # Q4 e Q5 retencao
    assert ret["fila_retencao"] == 270
    assert ret["alunos_fila_retencao"] == 171
    assert ret["contatos_cra_retencao"] == 229
    assert ret["alunos_cra_retencao"] == 144
    assert ret["assunto_retencao"] == 743
    assert ret["alunos_assunto_retencao"] == 173
    assert ret["assunto_retencao_cc"] == 266
    assert ret["alunos_assunto_retencao_cc"] == 143

    # desfechos de retencao
    assert ret["pedidos_cancelamento"] == 210
    assert ret["pedidos_cancelamento_cc"] == 114
    assert ret["alunos_mantidos"] == 262
    assert ret["pedidos_transferencia"] == 167
    assert ret["pedidos_trancamento"] == 93

    # contato previo antes da retencao
    assert ret["cancel_cc_com_outro_canal"] == 110
    assert ret["pct_cancel_cc_com_outro_canal"] == 96.49
    assert ret["fila_ret_com_outro_canal"] == 255
    assert ret["pct_fila_ret_com_outro_canal"] == 94.44
    assert ret["media_contatos_previos_ret"] == 13.41
    assert ret["mediana_contatos_previos_ret"] == 11.00
    assert ret["mediana_horas_desde_ultimo_contato"] == 1.55

    # Q8 pontos de navegacao URA
    assert nav["q8_contatos_98_99"] == 415
    assert nav["q8_contatos_98"] == 5
    assert nav["q8_contatos_99"] == 410
    assert nav["q8_respondidos_99"] == 158
    assert nav["q8_nota_media_99"] == 4.56
    assert nav["q8_contatos_no_1"] == 1497
    assert nav["q8_respondidos_no_1"] == 660
    assert nav["q8_nota_media_no_1"] == 4.55


def test_consistencia_documentacao_semantica() -> None:
    """Verifica se a documentacao em docs/ reflete exatamente as contagens da Gold."""
    doc_sem = (DOCS_DIR / "camada_semantica_powerbi.md").read_text(encoding="utf-8")
    doc_mod = (DOCS_DIR / "modelagem_e_analises.md").read_text(encoding="utf-8")

    # verifica se a secao 5 de validacao cruzada esta documentada
    assert "## 5. Validação cruzada entre DuckDB SQL e motor VertiPaq DAX" in doc_sem
    assert "8.643" in doc_sem
    assert "8.643" in doc_mod

    # confere todas as 11 tabelas da Gold com PKs e contagens
    for tab, (linhas, cols) in TABELAS_GOLD_ESPERADAS.items():
        assert f"`powerbi/m/{tab}.pq`" in doc_sem
        assert f"`{linhas}`" in doc_sem or f"{linhas:,}".replace(",", ".") in doc_sem


def test_cli_validate_executa_com_sucesso() -> None:
    """Testa a chamada do CLI python -m cogna_etl validate."""
    cmd = [sys.executable, "-m", "cogna_etl", "validate"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    assert "[Validate] status=ok" in proc.stdout
    assert "medidas_dax=88" in proc.stdout
    assert "divergencias=0" in proc.stdout
