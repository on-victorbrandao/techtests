"""Módulo de gestão da medida DAX do Dashboard Executivo HTML Content.

Carrega a medida de powerbi/dashboard/07_dashboard_html_content.dax e valida
a integridade estrutural e sintática do template para Power BI Desktop.
"""

from pathlib import Path

DASHBOARD_DAX_PATH = Path("powerbi/dashboard/07_dashboard_html_content.dax")


def get_dashboard_dax() -> str:
    """Retorna o código DAX completo da medida do Dashboard Executivo."""
    if not DASHBOARD_DAX_PATH.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {DASHBOARD_DAX_PATH}")
    return DASHBOARD_DAX_PATH.read_text(encoding="utf-8")


def get_dashboard_expression() -> str:
    """Retorna apenas o corpo da expressão DAX (após o cabeçalho)."""
    full_code = get_dashboard_dax()
    delimitador = "#01_HTML_Dashboard_Executivo_Cogna = \n\n"
    if delimitador not in full_code:
        raise ValueError("Cabeçalho padrão da medida DAX não encontrado.")
    return full_code.split(delimitador, 1)[1]


def validate_dashboard_dax_syntax() -> dict[str, int]:
    """Valida o balanceamento de delimitadores na expressão DAX."""
    expr = get_dashboard_expression()
    contagens = {
        "parenteses_abre": expr.count("("),
        "parenteses_fecha": expr.count(")"),
        "colchetes_abre": expr.count("["),
        "colchetes_fecha": expr.count("]"),
        "chaves_abre": expr.count("{"),
        "chaves_fecha": expr.count("}"),
        "aspas_duplas": expr.count('"'),
    }
    if contagens["parenteses_abre"] != contagens["parenteses_fecha"]:
        raise ValueError("Parênteses desbalanceados na medida DAX.")
    if contagens["colchetes_abre"] != contagens["colchetes_fecha"]:
        raise ValueError("Colchetes desbalanceados na medida DAX.")
    if contagens["chaves_abre"] != contagens["chaves_fecha"]:
        raise ValueError("Chaves desbalanceadas na medida DAX.")
    if contagens["aspas_duplas"] % 2 != 0:
        raise ValueError("Aspas duplas desbalanceadas na medida DAX.")
    return contagens
