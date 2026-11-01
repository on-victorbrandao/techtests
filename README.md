# Cogna Educacao — Teste Tecnico (Analista de Dados Senior)

Projeto de engenharia de dados e analytics desenvolvido para o teste tecnico de Analista de Dados Senior da Cogna Educacao. A solucao integra dados de quatro canais de atendimento (Call Center, WhatsApp, Video Chamada e Totem), executa limpeza, padronizacao e modelagem dimensional em DuckDB SQL, responde as nove perguntas de negocio do case e estrutura a camada semantica para consumo no Power BI.

---

## 1. Arquitetura da Solucao

O pipeline segue a arquitetura Medallion local em quatro camadas:

- **Raw (`data/raw/`)**: arquivos originais preservados em modo somente leitura.
- **Bronze (`data/bronze/`)**: CSVs com cabecalhos normalizados em `snake_case`, mantendo os valores brutos exportados, e dicionarios estruturados em JSON (`data/dictionaries/`).
- **Silver (`data/silver/`)**: tabelas lidas diretamente das abas da planilha `analytical_database_callcenter.xlsx` via DuckDB SQL (`read_xlsx`) para preservar os segundos dos timestamps e os valores originais de protocolo, com tipagem explicita, flags de qualidade e pseudonimizacao LGPD (`aluno_hash`).
- **Gold (`data/gold/`)**: modelo estrela relacional (8 dimensoes e 3 tabelas fato) e consultas analiticas (`Q1` a `Q9`) construidos em DuckDB SQL e exportados em Parquet (`SNAPPY`) e CSV (`;`, UTF-8 com BOM).
- **Power BI (`powerbi/`)**: integracao enxuta sobre a camada Gold, medidas DAX organizadas por pastas e dashboard analitico.

---

## 2. Estrutura de Pastas

```text
cogna/
├── .env.example              # Exemplo de configuracao local (salt de pseudonimizacao)
├── .gitignore                # Regras de exclusao de dados, segredos e caches locais
├── README.md                 # Visao geral e guia de execucao do projeto
├── pyproject.toml            # Metadados do pacote e configuracao do Ruff e Pytest
├── requirements.txt          # Dependencias fixadas do ambiente Python
├── data/                     # Armazenamento local de dados (nao versionado)
│   ├── raw/                  # Arquivos originais em modo somente leitura
│   ├── bronze/               # CSVs com cabecalhos padronizados em snake_case
│   ├── dictionaries/         # Dicionarios de dados em JSON por canal
│   ├── silver/               # Tabelas tratadas e tipadas por canal em Parquet
│   └── gold/                 # Tabelas fato e dimensao em Parquet e CSV + resultados JSON
├── docs/                     # Documentacao tecnica e analitica
│   ├── PLANO_MESTRE.md       # Arquitetura, etapas do projeto e premissas de negocio
│   ├── ESTADO.md             # Acompanhamento das entregas concluidas
│   ├── decisoes.md           # Registro de decisoes arquiteturais e de negocio (ADR)
│   ├── mapeamento_colunas.md # De-para de colunas entre Raw e Bronze
│   ├── inconsistencias_dicionario.md # Diagnostico dos dicionarios de dados
│   ├── fase0.md              # Setup, inventario e reconciliacao inicial
│   ├── fase1.md              # Normalizacao Bronze, dicionarios JSON e integridade
│   ├── fase2_qualidade.md    # Profiling e diagnostico de qualidade dos dados
│   ├── fase3.md              # Camada Silver em DuckDB SQL e reconciliacao
│   └── fase4.md              # Modelo estrela Gold e respostas analiticas Q1-Q9
├── powerbi/                  # Artefatos de integracao M, DAX e tema visual
├── sql/                      # Scripts DuckDB SQL
│   ├── staging/              # Macros, leitura do XLSX, dominios e camada Silver
│   ├── model/                # Dimensoes e tabelas fato do modelo estrela Gold
│   └── analytics/            # Consultas analiticas das 9 perguntas (q01..q09)
├── src/                      # Pacote Python de orquestracao e validacao
│   └── cogna_etl/
│       ├── __init__.py
│       ├── __main__.py
│       ├── inventory.py
│       ├── bronze.py
│       ├── dictionaries.py
│       ├── integrity.py
│       ├── profiling.py
│       ├── silver.py
│       └── gold.py
└── tests/                    # Suite de testes unitarios, sinteticos e de integracao
    ├── test_setup.py
    ├── test_fase1.py
    ├── test_fase2.py
    ├── test_fase3.py
    └── test_fase4.py
```

---

## 3. Como Executar

### 3.1. Requisitos
- Python 3.11 ou superior
- Git

### 3.2. Configuracao do Ambiente
```powershell
# 1. Criar e ativar o ambiente virtual (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar as dependencias e o pacote em modo editavel
pip install -r requirements.txt
pip install -e .

# 3. Configurar o arquivo local .env com o salt de pseudonimizacao
Copy-Item .env.example .env
# Preencher ALUNO_HASH_SALT no arquivo .env antes de rodar as camadas Silver e Gold
```

### 3.3. Execucao do Pipeline e Testes
```powershell
# Executar todas as etapas do pipeline (inventario, bronze, dicionarios, integridade, profiling, silver e gold)
python -m cogna_etl all

# Ou executar etapas individuais
python -m cogna_etl inventory
python -m cogna_etl bronze
python -m cogna_etl dictionaries
python -m cogna_etl integrity
python -m cogna_etl profiling
python -m cogna_etl silver
python -m cogna_etl gold

# Executar a suite completa de testes e verificacao de lint/formatacao
pytest -q
ruff check src tests
ruff format --check src tests
```
