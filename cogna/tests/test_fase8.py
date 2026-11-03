"""Testes automatizados da Fase 8: empacotamento local da entrega final."""

import subprocess
import sys
from pathlib import Path

from cogna_etl.package import copy_files, generate_manifest, run_packaging


def test_copy_files_helper(tmp_path: Path) -> None:
    # cria diretorio de origem com arquivos dummy
    src = tmp_path / "src_test"
    dst = tmp_path / "dst_test"
    src.mkdir()
    (src / "arquivo1.sql").write_text("SELECT 1;", encoding="utf-8")
    (src / "arquivo2.sql").write_text("SELECT 2;", encoding="utf-8")
    (src / "outro.txt").write_text("ignore", encoding="utf-8")

    copied = copy_files(src, dst, "*.sql")
    assert len(copied) == 2
    assert "arquivo1.sql" in copied
    assert "arquivo2.sql" in copied
    assert (dst / "arquivo1.sql").exists()
    assert (dst / "arquivo2.sql").exists()
    assert not (dst / "outro.txt").exists()


def test_generate_manifest_content(tmp_path: Path) -> None:
    # valida criacao e secoes essenciais do manifesto
    dst = tmp_path / "entrega_manifesto"
    dst.mkdir()
    summary = {
        "gold_parquet": ["fato_contato.parquet"],
        "sql_analytics": ["q01_cc_para_whatsapp.sql"],
    }
    manifest_path = generate_manifest(dst, summary)
    assert manifest_path.exists()
    content = manifest_path.read_text(encoding="utf-8")

    # checa presenca dos topicos obrigatorios
    assert "# Manifesto de entrega" in content
    assert "Q1 (Call Center -> WhatsApp)" in content
    assert "Q9 (Recontatos no mesmo dia)" in content
    assert "100,0%" in content
    assert "pDataPath" in content
    assert "DuckDB SQL" in content


def test_run_packaging_isolated(tmp_path: Path) -> None:
    # cria estrutura minima simulada da raiz do projeto
    fake_root = tmp_path / "fake_project"
    (fake_root / "data" / "gold").mkdir(parents=True)
    (fake_root / "sql" / "model").mkdir(parents=True)
    (fake_root / "sql" / "analytics").mkdir(parents=True)
    (fake_root / "powerbi" / "m").mkdir(parents=True)
    (fake_root / "powerbi" / "dax").mkdir(parents=True)
    (fake_root / "powerbi" / "dashboard").mkdir(parents=True)
    (fake_root / "powerbi" / "ux").mkdir(parents=True)

    # cria arquivos de teste
    (fake_root / "data" / "gold" / "fato_contato.parquet").write_bytes(b"PAR1")
    (fake_root / "data" / "gold" / "fato_contato.csv").write_text(
        "id;val", encoding="utf-8"
    )
    (fake_root / "sql" / "model" / "01_dim.sql").write_text(
        "SELECT 1;", encoding="utf-8"
    )
    (fake_root / "sql" / "analytics" / "q01.sql").write_text(
        "SELECT 1;", encoding="utf-8"
    )
    (fake_root / "powerbi" / "m" / "dim.pq").write_text(
        "let Source = 1 in Source", encoding="utf-8"
    )
    (fake_root / "powerbi" / "dax" / "01.dax").write_text("[M] = 1", encoding="utf-8")
    (fake_root / "powerbi" / "dashboard" / "dash.dax").write_text(
        "[Dash] = 1", encoding="utf-8"
    )
    (fake_root / "powerbi" / "ux" / "cogna_theme_pbi.json").write_text(
        "{}", encoding="utf-8"
    )

    dest = tmp_path / "pacote_entrega"
    res = run_packaging(base_dir=fake_root, target_dir=dest)

    assert res["status"] == "ok"
    assert (dest / "MANIFESTO.md").exists()
    assert (dest / "data" / "gold" / "fato_contato.parquet").exists()
    assert (dest / "sql" / "model" / "01_dim.sql").exists()
    assert (dest / "powerbi" / "dashboard" / "dash.dax").exists()
    assert (dest / "powerbi" / "ux" / "cogna_theme_pbi.json").exists()


def test_gitignore_security_rules() -> None:
    # assegura que a pasta entrega esta estritamente no gitignore
    gitignore_path = Path(__file__).resolve().parent.parent / ".gitignore"
    assert gitignore_path.exists()
    content = gitignore_path.read_text(encoding="utf-8")
    assert "entrega/" in content
    assert "data/" in content


def test_package_cli_execution() -> None:
    # executa comando package pela CLI oficial
    project_root = Path(__file__).resolve().parent.parent
    cmd = [sys.executable, "-m", "cogna_etl", "package"]
    proc = subprocess.run(
        cmd,
        cwd=project_root,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    assert "[Package] status=ok" in proc.stdout
    assert "arquivos_empacotados=" in proc.stdout
