# ESTADO DO PROJETO — Teste Técnico Cogna Educação

- **Data de Atualização:** 01/11/2026
- **Fase Atual Concluída:** Fase 1 (Normalização de Formato — Local / Bronze)
- **Próxima Fase:** Fase 2 (Profiling e Diagnóstico de Qualidade)

---

## 1. Visão Geral das Fases

| Fase | Descrição | Status | Entregável Principal |
| :--- | :--- | :---: | :--- |
| **Fase 0** | Setup de ambiente, repositório, inventário e reconciliação | **CONCLUÍDA** | `docs/fase0.md` |
| **Fase 1** | Normalização de formato (Bronze, dicionários JSON, integridade) | **CONCLUÍDA** | `docs/fase1.md` |
| **Fase 2** | Profiling e diagnóstico de qualidade dos dados | PENDENTE | `docs/fase2_qualidade.md` |
| **Fase 3** | Transformação Silver em DuckDB SQL (Parquet limpo e tipado) | PENDENTE | `docs/fase3.md` |
| **Fase 4** | Modelagem estrela Gold e consultas Q1–Q9 em DuckDB SQL | PENDENTE | `docs/fase4.md` |
| **Fase 5** | Camada semântica Power BI (Power Query M enxuto + DAX) | PENDENTE | `docs/fase5.md` |
| **Fase 6** | Validação cruzada (SQL vs DAX) | PENDENTE | `docs/fase6_reconciliacao.md` |
| **Fase 7** | UX, design, storytelling e construção do dashboard | PENDENTE | `docs/fase7.md` |
| **Fase 8** | Revisão final, documentação executiva e empacotamento | PENDENTE | `docs/fase8_entrega.md` |

---

## 2. Resumo da Fase 1 (Normalização Bronze e Dicionários)

- Geração dos 4 CSVs normalizados em `data/bronze/` com cabeçalhos em `snake_case` e paridade integral de células (5.991 linhas de dados).
- Estruturação dos 4 dicionários em JSON em `data/dictionaries/` e documentação de inconsistências (`docs/inconsistencias_dicionario.md`) e mapeamento (`docs/mapeamento_colunas.md`).
- Prova de integridade CSV vs XLSX via SHA-256 e definição do XLSX como fonte oficial da Silver (`DEC-004`).
- Suíte de testes expandida para 30 testes passando no Pytest.
