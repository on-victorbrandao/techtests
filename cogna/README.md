# Cogna Educação — teste técnico de analista de dados sênior

Projeto de engenharia de dados e analytics desenvolvido para o teste técnico de analista de dados sênior da Cogna Educação. A solução integra as bases de atendimento de quatro canais (Call Center, WhatsApp, vídeo chamada e totem), executa padronização, limpeza e modelagem dimensional em DuckDB SQL, responde às nove perguntas de negócio do case e prepara a camada semântica para o Power BI.

---

## 1. Objetivos de negócio (9 perguntas obrigatórias e indicadores operacionais)

1. Qual a quantidade de alunos que entraram em contato com o Call Center e posteriormente com o WhatsApp?
2. Algum aluno entrou em contato com o Call Center, depois no WhatsApp e depois em qualquer outro canal?
3. Quais são os principais motivos de contato em todos os canais?
4. Qual o perfil do aluno que procura a fila de retenção (`cra_retencao`) do Call Center? Esse aluno contatou anteriormente algum outro canal antes de pedir o cancelamento?
5. Qual o comportamento dos alunos que entram em contato em qualquer canal de atendimento e depois passam pela retenção?
6. Qual o canal de atendimento que tem a pior nota de pesquisa?
7. Existe algum perfil de aluno associado a uma nota de satisfação ruim?
8. Os pontos pelos quais os alunos passam na árvore de atendimento (`dna_soa`) do Call Center influenciam na nota obtida na pesquisa de satisfação?
9. Qual agente gera o maior volume de recontatos do mesmo CPF no mesmo dia?

Além das nove perguntas, o projeto acompanha volumetria de atendimentos, alunos únicos, taxa de resposta da pesquisa, nota média ponderada, proporção de notas ruins (1 e 2), tempos de espera e atendimento (TME e duração), transições entre canais e taxas de recontato.

---

## 2. Arquitetura e fluxo de dados

O pipeline segue a arquitetura medallion local em quatro camadas:

- **Raw (`data/raw/`)**: planilha original `analytical_database_callcenter.xlsx` e os 8 arquivos CSV exportados das abas correspondentes, preservados em modo somente leitura.
- **Bronze (`data/bronze/`)**: arquivos CSV com cabeçalhos padronizados em `snake_case` (mantendo os valores brutos originais) e dicionários de dados estruturados em JSON (`data/dictionaries/`).
- **Silver (`data/silver/`)**: tabelas lidas diretamente das abas da planilha `analytical_database_callcenter.xlsx` via DuckDB SQL (`read_xlsx`) para preservar os segundos dos timestamps e os valores numéricos de protocolo, aplicando tipagem explícita, flags de qualidade e pseudonimização em conformidade com a LGPD (`aluno_hash`).
- **Gold (`data/gold/`)**: modelo estrela relacional (8 dimensões e 3 tabelas fato) e consultas analíticas (`q01` a `q09`) em DuckDB SQL, exportados em Parquet (`SNAPPY`) e CSV (`;`, UTF-8 com BOM).
- **Power BI (`powerbi/`)**: integração enxuta sobre a camada Gold, medidas DAX e dashboard analítico.

---

## 3. Premissas de negócio e tratamento

As premissas abaixo foram adotadas para pontos não especificados nos dicionários originais:

- **Pseudonimização (LGPD):** o identificador do aluno é convertido em hash SHA-256 com salt local (`ALUNO_HASH_SALT` configurado via `.env`). Nenhum identificador original de aluno, nome de agente ou supervisor é exposto na camada Gold ou versionado no Git.
- **Fonte da camada Silver:** a exportação original dos CSVs truncou os segundos dos timestamps em três canais e converteu 16 protocolos longos em notação científica (`1,44496E+18`). Por isso, a Bronze espelha estritamente os CSVs recebidos e a Silver consome diretamente as abas do arquivo `.xlsx`.
- **Conceito de recontato posterior:** qualquer atendimento do mesmo aluno em timestamp estritamente posterior no período analisado, com recortes adicionais de transição imediata (`k -> k+1`) e janelas de 24 horas e 7 dias.
- **Identificação de retenção:** avaliada tanto pela fila de atendimento (`fila_atend` contendo `retenc` e recorte específico de `cra_retencao`) quanto pelo assunto registrado na tabulação (`Atendimento de Retenção`), apresentando as visões lado a lado.
- **Pesquisa de satisfação:** notas de `1` a `5` são tratadas como respostas válidas (`1` e `2` classificadas como nota ruim). Valores `0` ou nulos são classificados como ausência de resposta (`respondeu_pesquisa = false`) e não entram no denominador da nota média, mantendo a taxa de resposta visível em paralelo.
- **Tempos operacionais:** `duration_callcenter`, `duracao`, `duracao_da_chamada` e `tme` são tratados em segundos (`INTEGER`). Registros com `tme > duracao` são preservados e sinalizados por flag (`flag_tme_maior_duracao`).
- **Divergência de modalidade:** quando o primeiro nível da árvore de tabulação diverge da modalidade cadastral (presencial vs. EAD), prevalece o dado cadastral do contato e a ocorrência é marcada em `flag_divergencia_modalidade`.
- **Atribuição de recontato no mesmo dia (Q9):** quando o mesmo aluno realiza novo contato no mesmo dia calendário, o recontato é atribuído ao agente do atendimento imediatamente anterior, reportando tanto a visão omnichannel (retorno em qualquer canal) quanto a visão intracanal (retorno ao mesmo canal).

---

## 4. Estrutura do repositório

```text
cogna/
├── .env.example              # Exemplo de configuração local (salt de pseudonimização)
├── .gitignore                # Regras de exclusão de dados, segredos e artefatos locais
├── README.md                 # Visão geral, arquitetura, premissas e guia de execução
├── pyproject.toml            # Configuração do projeto, Ruff e Pytest
├── requirements.txt          # Dependências do ambiente Python
├── data/                     # Armazenamento local de dados (não versionado)
│   ├── raw/                  # Arquivos originais em modo somente leitura
│   ├── bronze/               # CSVs com cabeçalhos padronizados em snake_case
│   ├── dictionaries/         # Dicionários de dados em JSON por canal
│   ├── silver/               # Tabelas tratadas e tipadas por canal em Parquet
│   └── gold/                 # Modelo estrela em Parquet e CSV + resultados analíticos
├── docs/                     # Documentação técnica e analítica
│   ├── mapeamento_colunas.md         # De-para de colunas e definições por canal
│   ├── inconsistencias_dicionario.md # Diagnóstico dos dicionários de dados
│   ├── qualidade_dados.md            # Profiling das bases, limpeza Silver e reconciliação
│   └── modelagem_e_analises.md       # Modelo estrela Gold e respostas das perguntas Q1 a Q9
├── powerbi/                  # Artefatos de integração M, DAX e tema visual
├── sql/                      # Scripts DuckDB SQL
│   ├── staging/              # Macros, leitura do XLSX, domínios e camada Silver
│   ├── model/                # Dimensões e tabelas fato do modelo estrela Gold
│   └── analytics/            # Consultas analíticas das 9 perguntas (q01..q09)
├── src/                      # Pacote Python de orquestração e validação
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
└── tests/                    # Testes unitários, sintéticos e de integração
    ├── test_setup.py
    ├── test_fase1.py
    ├── test_fase2.py
    ├── test_fase3.py
    └── test_fase4.py
```

---

## 5. Como executar

### 5.1. Requisitos
- Python 3.11 ou superior
- Git

### 5.2. Configuração do ambiente
```powershell
# 1. Criar e ativar o ambiente virtual (Windows PowerShell)
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Instalar as dependências e o pacote em modo editável
pip install -r requirements.txt
pip install -e .

# 3. Configurar o arquivo local .env com o salt de pseudonimização
Copy-Item .env.example .env
# Preencher ALUNO_HASH_SALT no arquivo .env antes de executar as camadas Silver e Gold
```

### 5.3. Execução do pipeline e testes
```powershell
# Executar todas as etapas do pipeline (inventário, bronze, dicionários, integridade, profiling, silver e gold)
python -m cogna_etl all

# Ou executar etapas individuais
python -m cogna_etl inventory
python -m cogna_etl bronze
python -m cogna_etl dictionaries
python -m cogna_etl integrity
python -m cogna_etl profiling
python -m cogna_etl silver
python -m cogna_etl gold

# Executar a suíte de testes e verificação de código
pytest -q
ruff check src tests
ruff format --check src tests
```
