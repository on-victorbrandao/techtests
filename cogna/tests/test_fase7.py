"""Testes automatizados do Dashboard Executivo HTML Content (Fase 7).

Valida a integridade da medida DAX #01_HTML_Dashboard_Executivo_Cogna, a sintaxe
balanceada, a presenca das respostas obrigatorias Q1 a Q9 e os tokens de design
system oficial da Cogna Educacao.
"""

from pathlib import Path

from cogna_etl.dashboard import (
    get_dashboard_dax,
    get_dashboard_expression,
    validate_dashboard_dax_syntax,
)

DASHBOARD_DAX_FILE = Path("powerbi/dashboard/07_dashboard_html_content.dax")


def test_dax_arquivo_existe_e_carrega() -> None:
    """Verifica presenca do arquivo e delimitador padrao."""
    assert DASHBOARD_DAX_FILE.exists()
    dax_code = get_dashboard_dax()
    assert "#01_HTML_Dashboard_Executivo_Cogna =" in dax_code
    assert "Display Folder: 07. Dashboard HTML Content" in dax_code


def test_dax_medida_sintaxe_balanceada() -> None:
    """Valida delimitadores balanceados na expressao DAX gerada."""
    contagens = validate_dashboard_dax_syntax()
    assert contagens["parenteses_abre"] == contagens["parenteses_fecha"]
    assert contagens["colchetes_abre"] == contagens["colchetes_fecha"]
    assert contagens["chaves_abre"] == contagens["chaves_fecha"]
    assert contagens["aspas_duplas"] % 2 == 0

    expr = get_dashboard_expression()
    assert len(expr) > 20000


def test_dax_respostas_negocio_q1_a_q9() -> None:
    """Garante respostas categoricas de Q1 a Q9 no HTML do dashboard."""
    dax_code = get_dashboard_dax()

    # Q1: 100% migracao, 1403 contatos, 340 imediatos, 860 em 24h
    assert "100,0% dos alunos" in dax_code
    assert "1.403 contatos" in dax_code
    assert "340 imediatos" in dax_code
    assert "860 em até 24h" in dax_code

    # Q2: trincas consecutivas e intermediarios
    assert "138 Alunos" in dax_code
    assert "251 ocorrências" in dax_code
    assert "104 Alunos" in dax_code
    assert "145 ocorrências" in dax_code
    assert "173 Alunos" in dax_code

    # Q3: principais motivos por canal
    assert "Solicitação de Documentos" in dax_code
    assert "47,4%" in dax_code
    assert "Dúvidas Acadêmicas" in dax_code
    assert "26,1%" in dax_code
    assert "Suporte AVA / Plataforma" in dax_code
    assert "37,2%" in dax_code
    assert "Matrícula / Rematrícula" in dax_code
    assert "45,9%" in dax_code

    # Q4 e Q5: retencao e cancelamento com outro canal anterior
    assert "96,5% dos Cancelamentos" in dax_code
    assert "1,55 horas" in dax_code
    assert "11 atendimentos" in dax_code

    # Q6: pior nota e guardrail
    assert "2,96" in dax_code
    assert "37,5%" in dax_code
    assert "Guardrail" in dax_code

    # Q7: perfil com nota ruim
    assert "68,1% das notas ruins" in dax_code
    assert "Polos Leste e Sul" in dax_code

    # Q8: nos URA vs satisfacao
    assert "3,82" in dax_code
    assert "19,4%" in dax_code

    # Q9: recontatos por agente
    assert "374 Recontatos (6,24%)" in dax_code
    assert "142 Recontatos (2,37%)" in dax_code
    assert "AG-012" in dax_code
    assert "AG-008" in dax_code
    assert "AG-001" in dax_code


def test_dax_tokens_design_system_oficial() -> None:
    """Verifica tokens visuais, paleta de cores e estrutura semantica."""
    dax_code = get_dashboard_dax()

    # cores oficiais da Cogna
    assert "#5219A1" in dax_code
    assert "#7433DA" in dax_code
    assert "#FFAD01" in dax_code
    assert "#151D48" in dax_code
    assert "#737791" in dax_code
    assert "#FAFBFC" in dax_code
    assert "#0BB783" in dax_code
    assert "#EF4444" in dax_code

    # estrutura semantica e navegacao
    assert "<style>" in dax_code
    assert "<nav class='cogna-sidebar'>" in dax_code
    assert "<header class='cogna-topbar'>" in dax_code
    assert "<section class='cogna-kpi-grid'>" in dax_code
    assert "<script>" in dax_code

    # perfil do usuario Victor Brandao
    assert "Victor Brandão | Admin" in dax_code
    assert "Engenheiro de Analytics Sênior" in dax_code


def test_dax_logo_oficial_heroicons_e_timestamp() -> None:
    """Verifica logo oficial vetorizada, icones Heroicons e timestamp dinamico."""
    dax_code = get_dashboard_dax()

    # logo oficial da Cogna (viewBox oficial e classes de estilo)
    assert "viewBox='0 0 1524 542'" in dax_code
    assert ".s0 { fill: #5219A1; } .s1 { fill: #151D48; }" in dax_code

    # icones solidos Heroicons (24x24) na barra de navegacao
    assert dax_code.count("viewBox='0 0 24 24'") >= 6

    # timestamp dinamico de atualizacao do modelo
    assert 'var _data_atualizacao = FORMAT ( NOW(), "dd/mm/yyyy" )' in dax_code
    assert 'Atualizado: " & _data_atualizacao' in dax_code


def test_dax_graficos_colunas_e_rosca_e_sem_emojis() -> None:
    """Valida graficos de colunas verticais, rosca e ausencia de emojis."""
    dax_code = get_dashboard_dax()

    # Grafico de colunas verticais de picos horarios
    assert "Picos de Atendimento por Horário" in dax_code
    assert "512 (Pico)" in dax_code
    assert "rx='6'" in dax_code

    # Grafico de rosca (Donut) CSAT
    assert "MÉDIA CSAT" in dax_code
    assert "stroke-dasharray='320.6 87.8'" in dax_code

    # Ausencia de emojis de Android nos titulos de cards
    assert "🔀" not in dax_code
    assert "🛡️" not in dax_code
    assert "⭐" not in dax_code
    assert "🎧" not in dax_code
    assert "📊" not in dax_code
    assert "📌" not in dax_code
    assert "🔄" not in dax_code
