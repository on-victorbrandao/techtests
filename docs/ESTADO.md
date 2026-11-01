# ESTADO DO PROJETO — Teste Técnico Cogna Educação

- **Data de Atualização:** 01/11/2026
- **Fase Atual Concluída:** Fase 0 (Setup e Inventário)
- **Próxima Fase:** Fase 1 (Normalização de Formato — Local / Bronze)

---

## 1. Visão Geral das Fases

| Fase | Descrição | Status | Entregável Principal |
| :--- | :--- | :---: | :--- |
| **Fase 0** | Setup de ambiente, repositório, inventário e reconciliação | **CONCLUÍDA** | `docs/fase0.md` |
| **Fase 1** | Normalização de formato (Bronze, dicionários JSON, integridade) | PENDENTE | `docs/fase1.md` |
| **Fase 2** | Profiling e diagnóstico de qualidade dos dados | PENDENTE | `docs/fase2_qualidade.md` |
| **Fase 3** | Transformação Silver em DuckDB SQL (Parquet limpo e tipado) | PENDENTE | `docs/fase3.md` |
| **Fase 4** | Modelagem estrela Gold e consultas Q1–Q9 em DuckDB SQL | PENDENTE | `docs/fase4.md` |
| **Fase 5** | Camada semântica Power BI (Power Query M enxuto + DAX) | PENDENTE | `docs/fase5.md` |
| **Fase 6** | Validação cruzada (SQL vs DAX) | PENDENTE | `docs/fase6_reconciliacao.md` |
| **Fase 7** | UX, design, storytelling e construção do dashboard | PENDENTE | `docs/fase7.md` |
| **Fase 8** | Revisão final, documentação executiva e empacotamento | PENDENTE | `docs/fase8_entrega.md` |

---

## 2. Resumo da Fase 0 (Setup e Inventário)

- Ambiente `.venv` configurado com Python 3.13, `pandas`, `pyarrow`, `duckdb`, `openpyxl`, `pytest` e `ruff`.
- Arquivos originais copiados para `data/raw/` em modo somente leitura.
- Reconciliação das 8 tabelas brutas (4 analíticas + 4 dicionários) entre CSV e XLSX validada por 9 testes automatizados (`pytest`).
