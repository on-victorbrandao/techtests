# Relatório de Conclusão — Fase 1: Normalização de Formato (Bronze e Dicionários)

- **Projeto:** Teste Técnico Cogna Educação — Analista de Dados Sênior
- **Data:** 01/11/2026
- **Status:** CONCLUÍDA

---

## 1. Objetivo e O Que Foi Feito

A Fase 1 realizou a padronização estrutural dos dados analíticos e dos metadados de dicionário, gerando a camada **Bronze** em `data/bronze/` e os dicionários em JSON em `data/dictionaries/`, preservando integralmente os valores das fontes.

### Principais ações realizadas:
1. **Preservação Raw:** Arquivos em `data/raw/` mantidos intactos e em modo somente leitura.
2. **Normalização Bronze com Validações Estritas:**
   - Cabeçalhos padronizados para `snake_case` minúsculo, único e sem acentos.
   - Validações antes da gravação: conferência da ordem e nomes exatos de entrada, validação de unicidade das colunas de saída e conferência de quantidade de campos por registro.
   - Uso de exceções explícitas (`ValueError`, `FileNotFoundError`) em substituição a `assert`.
   - Coluna de índice 2 da Vídeo Chamada (sem nome na origem, contendo data sem milissegundos) identificada explicitamente como `calldate_sem_ms`.
   - Valores gravados em UTF-8 com BOM (`utf-8-sig`) e delimitador `;`.
3. **Mapeamento de Colunas Documentado:** Criado [`docs/mapeamento_colunas.md`](file:///C:/Users/victo/OneDrive/Documentos/learning-work/test/cogna/docs/mapeamento_colunas.md), com separação clara entre definições confirmadas, hipóteses funcionais (como a diferença entre `recepcao_fila` e `fila_atend`) e premissas pendentes (como nota 0 e unidades de tempo).
4. **Dicionários Estruturados em JSON:**
   - Módulo `src/cogna_etl/dictionaries.py` com forward-fill da coluna `Campos` e remoção de registros vazios.
   - Preservação integral dos conflitos de código e rótulo (ex.: código 5 com rótulo "4 -", código 12 duplicado em Instituição, regras lógicas em `AfterHour`).
   - Diferenciação entre domínios categóricos discretos e linhas com instruções de formato/metadados.
   - Mapeamento explícito, por canal, entre o campo do dicionário e a respectiva coluna da Bronze.
   - Arquivos JSON salvos localmente em `data/dictionaries/` (protegidos pelo `.gitignore`).
5. **Decisão sobre Fontes (DEC-004):**
   - Os CSVs brutos são a referência exclusiva da Bronze.
   - O arquivo `analytical_database_callcenter.xlsx` é a fonte oficial para a camada Silver, garantindo os segundos dos timestamps e a precisão numérica dos protocolos.
   - Fica vetada a recuperação de horários por join apenas no identificador do aluno, devido a repetições de ID no histórico.
6. **Prova de Integridade de Conteúdo (Hash SHA-256 por Linha):**
   - Comparação linha a linha entre cada CSV e sua aba no XLSX após normalizar o `.0` de inteiros.
   - Vídeo Chamada com paridade binária integral de dados (1.499 linhas iguais).
   - WhatsApp (1.494 linhas) e Totem (1.499 linhas) com divergência restrita às datas por omissão de segundos na exportação do CSV pelo Excel (todas as demais colunas idênticas).
   - Call Center com divergência nas datas e em 16 linhas de `Protocolo` afetadas por notação científica (`1,44496E+18`) na exportação do CSV.
7. **Suíte de Testes Automatizados:** 30 testes implementados no Pytest cobrindo paridade de linhas e colunas, igualdade dos valores, conformidade de `snake_case`, unicidade, nomeação da coluna de vídeo, estrutura dos dicionários e testes negativos para cabeçalhos reordenados, nomes inesperados, nomes duplicados e linhas com quantidade incorreta de campos.

---

## 2. Comandos Executados (Copiáveis)

```powershell
# 1. Ativar o ambiente virtual
.venv\Scripts\Activate.ps1

# 2. Executar o pipeline de normalizacao Bronze
$env:PYTHONPATH="src"
python -m cogna_etl bronze

# 3. Processar os dicionarios em JSON
python -m cogna_etl dictionaries

# 4. Executar a prova de integridade
python -m cogna_etl integrity

# 5. Executar a suite completa de testes
pytest -v

# 6. Validar conformidade de codigo (Ruff)
ruff check .
ruff format --check .
```

---

## 3. Contagens Antes/Depois, Integridade e Testes

### 3.1. Contagens: Raw vs Bronze

| Tabela Analítica | Arquivo Bronze (`data/bronze/`) | Linhas Totais | Cabeçalho | Linhas de Dados | Colunas | Status de Paridade |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Call Center** | `analitico_callcenter.csv` | 1.500 | 1 | 1.499 | 22 | Idêntico |
| **WhatsApp** | `analitico_whatsapp.csv` | 1.495 | 1 | 1.494 | 19 | Idêntico |
| **Vídeo Chamada** | `analitico_video_chamada.csv` | 1.500 | 1 | 1.499 | 9 | Idêntico |
| **Totem** | `analitico_totem.csv` | 1.500 | 1 | 1.499 | 7 | Idêntico |
| **TOTAL** | - | **5.995** | **4** | **5.991** | - | **Idêntico** |

> **Validação de Dados:** O teste automatizado `test_bronze_data_values_identical_to_raw` comparou todas as **5.991 linhas de dados** da camada Bronze contra os arquivos da camada Raw, confirmando igualdade em cada célula.

---

### 3.2. Prova de Integridade de Conteúdo (CSV vs XLSX via Hash SHA-256)

| Tabela / Aba | Linhas de Dados | Linhas Hash Idêntico | Linhas Divergentes | Colunas com Divergência | Causa da Divergência |
| :--- | :---: | :---: | :---: | :--- | :--- |
| **Vídeo Chamada** | 1.499 | 1.499 (100%) | 0 (0%) | Nenhuma | Conteúdo idêntico em todas as 9 colunas. |
| **WhatsApp** | 1.494 | 0 | 1.494 | `calldate` (1.494 linhas) | O CSV bruto foi exportado sem segundos pelo Excel. As outras 18 colunas são idênticas. |
| **Totem** | 1.499 | 0 | 1.499 | `DATA_INICIO` (1.499 linhas) | O CSV bruto foi exportado sem segundos. As outras 6 colunas são idênticas. |
| **Call Center** | 1.499 | 0 | 1.499 | `Date` (1.499 linhas)<br>`Calldate` (1.499 linhas)<br>`Protocolo` (16 linhas) | 1) Datas sem segundos no CSV.<br>2) Em `Protocolo`, 16 linhas foram truncadas em notação científica pt-BR (`1,44496E+18`) na exportação do CSV. As demais 19 colunas são idênticas. |

---

### 3.3. Dicionários em JSON (`data/dictionaries/`)

| Canal | Arquivo JSON | Qtd Campos | Tratamento Aplicado |
| :--- | :--- | :---: | :--- |
| **Call Center** | `callcenter_dicionario.json` | 10 | Forward-fill, mapeamento para Bronze, isolamento de instruções de formato. |
| **WhatsApp** | `whatsapp_dicionario.json` | 14 | Forward-fill, preservação do código 5 rotulado como "4 -", código 12 duplicado e regras lógicas em `AfterHour`. |
| **Vídeo Chamada** | `video_chamada_dicionario.json`| 5 | Descarte de 4 linhas vazias finais, mapeamento de campos descritivos para Bronze. |
| **Totem** | `totem_dicionario.json` | 6 | Mapeamento chave/descrição dos 6 campos documentados. |

---

### 3.4. Resultado dos Testes Automatizados (Pytest)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\victo\OneDrive\Documentos\learning-work\test\cogna
configfile: pyproject.toml
testpaths: tests
collected 30 items

tests/test_fase1.py .....................                                 [ 70%]
tests/test_setup.py .........                                             [100%]

============================== 30 passed in 2.98s ==============================
```

---

## 4. Premissas Aplicadas e Riscos

1. **Fidelidade Bronze aos CSVs:** A Bronze reflete estritamente os CSVs brutos, apenas com cabeçalhos normalizados em `snake_case`.
2. **Resgate de Precisão na Silver (DEC-004):** A camada Silver consumirá diretamente as abas do arquivo `analytical_database_callcenter.xlsx`, recuperando os segundos das datas e os protocolos numéricos inteiros sem notação científica.
3. **Mapeamentos Independentes por Canal:** Fica vetado cruzar códigos de domínio entre canais diferentes sem validação específica de cada dicionário.

---

## 5. Pendências

- Confirmação externa das premissas registradas em `docs/decisoes.md` (distinção entre `recepcao_fila` e `fila_atend`, nota 0 como não respondido e unidades de tempo).
- Próxima etapa: Fase 2 (Profiling e Diagnóstico de Qualidade).

---

## 6. Versionamento e Branch

- **Branch de Integração:** `cogna`
- **Branch de Trabalho:** `feat/fase-1-normalizacao`
- **Mensagem de Commit:** `feat: implementar normalizacao bronze, dicionarios e prova de integridade (fase 1)`
- **Pull Request:** https://github.com/on-victorbrandao/techtests/pull/new/feat/fase-1-normalizacao (`cogna` ← `feat/fase-1-normalizacao`)
