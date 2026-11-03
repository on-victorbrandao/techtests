"""Modulo de empacotamento local da entrega final do projeto Cogna.

Reune base analitica Gold, scripts SQL, codigo M, catalogo DAX, tema visual e manifesto.
"""

import shutil
from pathlib import Path
from typing import Any


def copy_files(
    src_dir: Path,
    dst_dir: Path,
    pattern: str,
) -> list[str]:
    """Copia arquivos correspondentes a um padrao para a pasta de destino."""
    dst_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    # itera pelos arquivos correspondentes ao padrao no diretorio de origem
    for src_file in sorted(src_dir.glob(pattern)):
        if src_file.is_file():
            dst_file = dst_dir / src_file.name
            shutil.copy2(src_file, dst_file)
            copied.append(src_file.name)
    return copied


def build_manifest_text(total_files: int) -> str:
    """Monta o texto do manifesto executivo respeitando o limite de colunas."""
    lines = [
        "# Manifesto de entrega — Teste Tecnico Cogna Educacao",
        "",
        (
            "Pacote consolidado para avaliacao tecnica contendo a base "
            "dimensional Gold, scripts SQL em DuckDB, scripts Power Query M, "
            "catalogo de medidas DAX, medida executiva em visual unico "
            "HTML Content e tema institucional."
        ),
        "",
        "---",
        "",
        "## 1. Resumo executivo da solucao",
        "",
        (
            "- **Arquitetura:** modelo medallion em 4 camadas "
            "(Raw -> Bronze -> Silver -> Gold -> Camada Semantica Power BI)."
        ),
        (
            "- **Tratamento Silver:** preservacao de segundos e protocolos longos "
            "via leitura direta do XLSX em DuckDB SQL, padronizacao de dominios e "
            "pseudonimizacao LGPD via hash SHA-256 com salt local."
        ),
        (
            "- **Modelagem Gold:** modelo estrela com 3 tabelas fato "
            "(5.991 atendimentos unificados, navegacao URA e jornada cronologica "
            "por aluno) e 8 dimensoes relacionais, exportados em Parquet (SNAPPY) "
            "e CSV (ponto e virgula com BOM)."
        ),
        (
            "- **Camada Semantica e UX:** 88 medidas analiticas reconciliadas com "
            "zero divergencias contra o SQL e 1 medida executiva em visual unico "
            "HTML Content (`#01_HTML_Dashboard_Executivo_Cogna`) com design system "
            "oficial da Cogna Educacao."
        ),
        f"- **Total de artefatos empacotados:** {total_files} arquivos.",
        "",
        "---",
        "",
        "## 2. Sintese das respostas de negocio (Q1 a Q9)",
        "",
        (
            "| Pergunta | Indicador principal | Resultado validado | "
            "Conclusao analitica e operacional |"
        ),
        "| :--- | :--- | :---: | :--- |",
        (
            "| **Q1 (Call Center -> WhatsApp)** | % Migracao posterior de alunos | "
            "**100,0%** (173 alunos) | 1.403 contatos do CC (93,6%) migraram; "
            "340 imediatos (22,7%) e 860 em ate 24h (57,4%). |"
        ),
        (
            "| **Q2 (Trinca CC -> WA -> Outro)** | Alunos na trinca consecutiva | "
            "**138 alunos** (251 ocorrencias) | 104 alunos foram para video/totem "
            "(145 casos); 173 na sequencia ampla com intermediarios. |"
        ),
        (
            "| **Q3 (Principais motivos por canal)** | Top 1 motivo por canal | "
            "**Documentos no WA (47,4%)** | CC dividido em Dúvidas Acadêmicas (26,1%) "
            "e Financeiro (25,1%), com 35,4% nulos; Vídeo em Suporte AVA (37,2%); "
            "Totem em Matrícula (45,9%). |"
        ),
        (
            "| **Q4 (Perfil da fila retencao)** | % Contato previo em outro canal | "
            "**94,44%** (255 de 270) | 96,49% dos que pediram cancelamento "
            "passaram antes por canal previo; mediana de 1,55 h do contato anterior. |"
        ),
        (
            "| **Q5 (Comportamento pre-retencao)** | Volume previo acumulado | "
            "**11 contatos** (mediana) | Media de 13,41 atendimentos antes da "
            "retencao; alta friccao operacional antecede a intencao de evasao. |"
        ),
        (
            "| **Q6 (Pior canal de atendimento)** | Pior nota media CSAT | "
            "**Totem (nota 2,96)** | Totem tem 37,5% de notas ruins (guardrail n=24, "
            "taxa 1,60%); WA lidera volume absoluto de detratores (84 ruins); "
            "Video tem melhor nota (4,58). |"
        ),
        (
            "| **Q7 (Perfil com notas ruins)** | Segmento mais impactado | "
            "**Calouros (68,1%)** | 182 contatos ruins no total; concentracao em "
            "Presencial Campus (13,24% ruins vs 8,42% EAD), polos Leste/Sul e "
            "inicio da tarde util. |"
        ),
        (
            "| **Q8 (Navegacao URA / Ponto SOA)** | Influencia dos nos financeiros | "
            "**Nota 3,82** (19,4% ruins) | Nos de suporte financeiro e contestacao "
            "geram nota inferior a nos de consulta simples (nota 4,61 e 3,8% ruins). |"
        ),
        (
            "| **Q9 (Recontatos no mesmo dia)** | Taxa e volume de recontatos | "
            "**6,24%** (374 recontatos) | Visao A Omnichannel: 374 recontatos (6,24%); "
            "Visao B Intracanal: 142 (2,37%); ranking liderado por AG-012 (98,8%), "
            "AG-008 (200) e AG-001 (185). |"
        ),
        "",
        "---",
        "",
        "## 3. Estrutura de pastas do pacote",
        "",
        "```text",
        "entrega/",
        "├── MANIFESTO.md              # Resumo executivo e respostas de negocio",
        "├── data/",
        "│   └── gold/                 # Fatos e dimensoes em Parquet e CSV",
        "├── sql/",
        "│   ├── model/                # Scripts DDL/DML do modelo estrela em DuckDB",
        "│   └── analytics/            # Consultas analiticas oficiais Q1 a Q9",
        "└── powerbi/",
        "    ├── m/                    # Scripts Power Query (.pq) parametrizados",
        "    ├── dax/                  # Catalogo de 88 medidas analiticas DAX",
        "    ├── dashboard/            # Dashboard executivo HTML Content",
        "    └── ux/                   # Tema institucional oficial (JSON)",
        "```",
        "",
        "---",
        "",
        "## 4. Guia rapido de reproducao",
        "",
        "### Consumo no Power BI Desktop",
        "1. Abra o arquivo Power BI Desktop do projeto (`tech_test_cogna.pbix`).",
        "2. Acesse `Transformar Dados` -> `Editar Parametros`.",
        (
            "3. Altere o parametro `pDataPath` para o caminho absoluto da pasta "
            "`entrega/data/gold/`."
        ),
        (
            "4. Clique em `Fechar e Aplicar` para recarregar todos os dados a partir "
            "dos arquivos Parquet."
        ),
        "",
        "### Execucao das consultas no DuckDB SQL",
        "1. Inicie uma sessao DuckDB na raiz da pasta `entrega/`.",
        "2. Carregue as tabelas Parquet da pasta `data/gold/`.",
        "3. Execute os scripts analiticos em `sql/analytics/q01..q09_*.sql`.",
    ]
    return "\n".join(lines) + "\n"


def generate_manifest(
    target_dir: Path,
    files_summary: dict[str, list[str]],
) -> Path:
    """Gera o arquivo de manifesto executivo descrevendo os artefatos empacotados."""
    manifest_path = target_dir / "MANIFESTO.md"
    total_files = sum(len(v) for v in files_summary.values())
    content = build_manifest_text(total_files)
    manifest_path.write_text(content, encoding="utf-8")
    return manifest_path


def run_packaging(
    base_dir: Path | None = None,
    target_dir: Path | None = None,
) -> dict[str, Any]:
    """Executa o empacotamento completo dos arquivos da solucao na pasta entrega."""
    # define raiz do projeto e pasta de destino
    root = (
        base_dir
        if base_dir is not None
        else Path(__file__).resolve().parent.parent.parent
    )
    dest = target_dir if target_dir is not None else root / "entrega"

    dest.mkdir(parents=True, exist_ok=True)
    summary: dict[str, list[str]] = {}

    # copia tabelas Gold em Parquet e CSV
    gold_dir = root / "data" / "gold"
    summary["gold_parquet"] = copy_files(gold_dir, dest / "data" / "gold", "*.parquet")
    summary["gold_csv"] = copy_files(gold_dir, dest / "data" / "gold", "*.csv")
    summary["gold_json"] = copy_files(gold_dir, dest / "data" / "gold", "*.json")

    # copia scripts SQL do modelo estrela e consultas analiticas
    summary["sql_model"] = copy_files(
        root / "sql" / "model", dest / "sql" / "model", "*.sql"
    )
    summary["sql_analytics"] = copy_files(
        root / "sql" / "analytics", dest / "sql" / "analytics", "*.sql"
    )

    # copia scripts M do Power Query
    summary["powerbi_m"] = copy_files(
        root / "powerbi" / "m", dest / "powerbi" / "m", "*.pq"
    )

    # copia catalogo de medidas DAX
    summary["powerbi_dax"] = copy_files(
        root / "powerbi" / "dax", dest / "powerbi" / "dax", "*.dax"
    )

    # copia medida do dashboard HTML Content
    summary["powerbi_dashboard"] = copy_files(
        root / "powerbi" / "dashboard", dest / "powerbi" / "dashboard", "*.dax"
    )

    # copia tema institucional do Power BI
    summary["powerbi_ux"] = copy_files(
        root / "powerbi" / "ux", dest / "powerbi" / "ux", "*.json"
    )

    # gera manifesto executivo
    manifest_path = generate_manifest(dest, summary)

    total_files = sum(len(v) for v in summary.values()) + (
        1 if manifest_path.exists() else 0
    )

    return {
        "status": "ok",
        "target_dir": str(dest),
        "total_files": total_files,
        "summary": summary,
        "manifest": str(manifest_path),
    }
