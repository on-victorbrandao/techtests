"""Ponto de entrada da linha de comando do pacote cogna_etl."""

import sys


def main() -> None:
    # executa o comando informado como primeiro argumento
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "inventory":
        from cogna_etl.inventory import run_inventory

        run_inventory()
    elif cmd == "bronze":
        from cogna_etl.bronze import normalize_bronze

        res = normalize_bronze()
        for name, s in res.items():
            print(
                f"[Bronze] {name}: {s['data_rows']} linhas de dados, "
                f"{s['cols_count']} colunas"
            )
    elif cmd == "dictionaries":
        from cogna_etl.dictionaries import generate_all_dictionaries

        res = generate_all_dictionaries()
        for k, v in res.items():
            print(f"[Dicionarios] {v['json_file']}: {v['fields_count']} campos")
    elif cmd == "integrity":
        from cogna_etl.integrity import verify_content_integrity

        res = verify_content_integrity()
        for sheet, info in res.items():
            print(f"[Integridade] {sheet}:")
            print(f"  linhas com hash identico: {info['identical_hash_rows']}")
            print(f"  linhas com hash divergente: {info['divergent_hash_rows']}")
            print(f"  colunas divergentes: {info['divergent_cols']}")
    elif cmd == "all":
        from cogna_etl.bronze import normalize_bronze
        from cogna_etl.dictionaries import generate_all_dictionaries
        from cogna_etl.integrity import verify_content_integrity
        from cogna_etl.inventory import run_inventory

        run_inventory()
        normalize_bronze()
        generate_all_dictionaries()
        verify_content_integrity()
    else:
        print("Uso: python -m cogna_etl [inventory|bronze|dictionaries|integrity|all]")


if __name__ == "__main__":
    main()
