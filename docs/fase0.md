# Relatório de Conclusão — Fase 0: Setup e Inventário

- **Projeto:** Teste Técnico Cogna Educação — Analista de Dados Sênior
- **Data:** 01/11/2026
- **Status:** CONCLUÍDA

---

## 1. Objetivo e O Que Foi Feito

O objetivo desta fase foi estruturar a fundação do projeto com rastreabilidade, isolamento de ambiente, segurança de dados (LGPD) e validação da integridade das fontes originais.

### Principais ações realizadas:
1. **Estrutura de Pastas:** Provisionamento da arquitetura Medallion local (`data/raw`, `data/bronze`, `data/dictionaries`, `data/silver`, `data/gold`), códigos de engenharia (`src/cogna_etl`), modelagem SQL (`sql/staging`, `sql/model`, `sql/analytics`), testes automatizados (`tests`), documentação (`docs`) e artefatos Power BI (`powerbi/m`, `powerbi/dax`, `powerbi/theme`).
2. **Ambiente Virtual e Dependências:** Criação do `.venv` com Python 3.13 e fixação das dependências no `requirements.txt` (`pandas`, `pyarrow`, `duckdb`, `openpyxl`, `pytest`, `ruff`).
3. **Segurança e Versionamento:** Configuração estrita de `.gitignore` garantindo que nenhum dado bruto, tratado ou intermediário seja versionado no Git. Criação do `.env.example` para suporte ao salt LGPD.
4. **Isolamento de Originais:** Cópia dos 8 CSVs brutos e do arquivo `analytical_database_callcenter.xlsx` para `data/raw/` e bloqueio com atributo de somente leitura (`ReadOnly`).
5. **Inventário e Reconciliação:** Desenvolvimento do módulo `cogna_etl.inventory` e de suíte com 9 testes automatizados no Pytest, comparando linha a linha e coluna a coluna cada CSV contra sua aba correspondente no Excel.
6. **Governança Git:** Inicialização do repositório local, apontamento para o remote `origin` (`https://github.com/on-victorbrandao/techtests`) e branch de trabalho `feat/fase-0-setup`.

---

## 2. Comandos Executados (Copiáveis)

```powershell
# 1. Provisionar estrutura de pastas
New-Item -ItemType Directory -Force -Path `
  "data/raw", "data/bronze", "data/dictionaries", "data/silver", "data/gold", `
  "src/cogna_etl", "sql/staging", "sql/model", "sql/analytics", `
  "tests", "docs", "powerbi/m", "powerbi/dax", "powerbi/theme"

# 2. Copiar arquivos brutos e aplicar modo somente-leitura
Copy-Item "analytical_database_callcenter*.csv" -Destination "data/raw/"
Copy-Item "analytical_database_callcenter.xlsx" -Destination "data/raw/"
Get-ChildItem -Path "data/raw" | ForEach-Object { Set-ItemProperty -Path $_.FullName -Name IsReadOnly -Value $true }

# 3. Criar e ativar ambiente virtual
python -m venv .venv
.venv\Scripts\Activate.ps1

# 4. Instalar bibliotecas da stack e fixar versoes
pip install pandas pyarrow duckdb openpyxl pytest ruff
pip freeze > requirements.txt

# 5. Executar o inventario de dados e reconciliacao com o Excel
$env:PYTHONPATH="src"
python -m cogna_etl inventory

# 6. Rodar testes automatizados de paridade
pytest -v

# 7. Validar linting e formatacao
ruff check .
ruff format --check .
```

---

## 3. Contagens Antes/Depois e Testes com Resultado

### 3.1. Tabela de Reconciliação dos Arquivos Brutos

Todos os arquivos foram identificados com codificação `UTF-8 com BOM` (`utf-8-sig`) e delimitador `;`.

> **Nota sobre contagem de linhas:** Os totais de linhas incluem exatamente 1 linha de cabeçalho. A coluna **Linhas de Dados** detalha os registros reais em cada fonte.

| Arquivo Bruto (`data/raw`) | Tamanho | Cols | Linhas Totais | Cabeçalho | Linhas de Dados | Aba Excel Equivalente | Status de Paridade |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| `analitico_callcenter.csv` | 1.164,8 KB | 22 | 1.500 | 1 | 1.499 | `Analitico call center` | Reconciliado |
| `dicionario_callcenter.csv` | 1,7 KB | 4 | 35 | 1 | 34 | `Dicionario call center` | Reconciliado |
| `analitico_whatsapp.csv` | 828,8 KB | 19 | 1.495 | 1 | 1.494 | `Analitico Whatsapp` | Reconciliado |
| `dicionario_whatsapp.csv` | 6,9 KB | 4 | 81* | 1 | 80 | `Dicionario_whatsapp` | Reconciliado |
| `analitico_video_chamada.csv`| 340,6 KB | 9 | 1.500 | 1 | 1.499 | `Analitico_video_chamada` | Reconciliado |
| `dicionario_video_chamado.csv`| 0,4 KB | 2 | 10** | 1 | 5 (+4 vazias) | `Dicionario_video` | Reconciliado |
| `analitico_totem.csv` | 227,1 KB | 7 | 1.500 | 1 | 1.499 | `Analitico_Totem` | Reconciliado |
| `dicionario_totem.csv` | 0,2 KB | 2 | 7 | 1 | 6 | `Dicionario_Totem` | Reconciliado |

> **Notas de Diagnóstico da Reconciliação:**
> - `*` `dicionario_whatsapp.csv`: Apresenta 143 linhas físicas de texto porque descrições textuais contêm quebras de linha (`\n`) envolvidas por aspas. O parser de CSV padrão computa exatamente 81 registros lógicos (1 cabeçalho + 80 linhas de dados), correspondendo exatamente às 81 linhas da aba no Excel.
> - `**` `dicionario_video_chamado.csv`: Possui 10 registros tanto no CSV quanto na planilha Excel (1 cabeçalho + 5 registros com descrição + 4 linhas em branco finais preservadas da planilha original).

### 3.2. Resultado da Suíte de Testes Automatizados (Pytest)

```text
============================= test session starts =============================
platform win32 -- Python 3.13.2, pytest-9.2.0, pluggy-1.7.0
rootdir: C:\Users\victo\OneDrive\Documentos\learning-work\test\cogna
configfile: pyproject.toml
testpaths: tests
collected 9 items

tests\test_setup.py .........                                            [100%]

============================== 9 passed in 2.46s ==============================
```

---

## 4. Premissas Aplicadas e Riscos

1. **Premissa de Imutabilidade Raw:** Nenhum arquivo original sofreu qualquer alteração. Todos foram preservados intactos em `data/raw/` com flag de somente leitura.
2. **Premissa de Parsing e Leitura Segura:** O tratamento de CSV exige `csv.reader` com suporte a campos entre aspas contendo `\n`, e leitura inicial de todos os atributos como string (`dtype=str`) para evitar corrupção de IDs decimais ou perda de notação científica.
3. **Riscos Mitigados:** Risco de vazamento de dados em commits mitigado pelo `.gitignore` estrito; risco de divergência de versões eliminado com `requirements.txt` fixado.

---

## 5. Pendências

- Nenhuma pendência técnica para a Fase 0.
- Próxima etapa: Fase 1 (Normalização de Formato Bronze e conversão dos dicionários para JSON estruturado).

---

## 6. Versionamento e Branch

- **Branch de Integração:** `cogna`
- **Branch de Trabalho:** `feat/fase-0-setup`
- **Mensagem de Commit:** `feat: setup de ambiente, inventario e reconciliacao de dados (fase 0)`
- **Pull Request:** https://github.com/on-victorbrandao/techtests/pull/new/feat/fase-0-setup (`cogna` ← `feat/fase-0-setup`)
