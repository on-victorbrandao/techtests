"""Ponto de entrada da CLI cogna_etl."""

import sys


def main() -> None:
    # CLI simples para execucao dos modulos do pipeline
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "inventory":
        from cogna_etl.inventory import run_inventory

        run_inventory()
    else:
        print("Uso: python -m cogna_etl [inventory]")


if __name__ == "__main__":
    main()
