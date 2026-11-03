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
    elif cmd == "profiling":
        from cogna_etl.profiling import run_full_profiling

        res = run_full_profiling()
        print("[Profiling] Diagnostico concluido com sucesso:")
        for ch, count in res["row_counts"].items():
            print(f"  {ch}: {count} linhas")
        print(f"  Total de registros: {res['total_rows']}")
        std = res["students"]
        print(
            f"  Alunos unicos: {std['total_unique_students']} "
            f"(nos 4 canais: {std['in_all_4_channels']})"
        )
        q = res["queues"]
        print(
            f"  Filas Call Center: coinc={q['coincident_queues']}, "
            f"diverg={q['divergent_queues']}"
        )
    elif cmd == "silver":
        from cogna_etl.silver import run_silver

        res = run_silver()
        for tabela, (qtd_in, qtd_out) in res.items():
            print(f"[Silver] {tabela}: {qtd_in} linhas de entrada, {qtd_out} de saida")
    elif cmd == "gold":
        from cogna_etl.gold import run_gold

        res = run_gold()
        for tabela, qtd in res.items():
            print(f"[Gold] {tabela}: {qtd} linhas")
    elif cmd == "validate":
        from cogna_etl.validation import run_validation

        res = run_validation()
        print(
            f"[Validate] status={res['status']}, "
            f"medidas_dax={res['total_medidas_dax']}, "
            f"divergencias={res['total_divergencias']}"
        )
    elif cmd == "package":
        from cogna_etl.package import run_packaging

        res = run_packaging()
        print(
            f"[Package] status={res['status']}, "
            f"arquivos_empacotados={res['total_files']}, "
            f"destino={res['target_dir']}"
        )
    elif cmd == "all":
        from cogna_etl.bronze import normalize_bronze
        from cogna_etl.dictionaries import generate_all_dictionaries
        from cogna_etl.gold import run_gold
        from cogna_etl.integrity import verify_content_integrity
        from cogna_etl.inventory import run_inventory
        from cogna_etl.package import run_packaging
        from cogna_etl.profiling import run_full_profiling
        from cogna_etl.silver import run_silver
        from cogna_etl.validation import run_validation

        run_inventory()
        normalize_bronze()
        generate_all_dictionaries()
        verify_content_integrity()
        run_full_profiling()
        run_silver()
        run_gold()
        run_validation()
        run_packaging()
    else:
        print(
            "Uso: python -m cogna_etl "
            "[inventory|bronze|dictionaries|integrity|profiling|silver|gold|validate|package|all]"
        )


if __name__ == "__main__":
    main()
