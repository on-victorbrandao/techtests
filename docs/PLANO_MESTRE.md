# PLANO MESTRE — Teste Técnico Cogna (Analista de Dados Sênior)

Este documento descreve o contexto, os objetivos de negócio, a arquitetura de engenharia de dados, o roteiro técnico das etapas e as premissas adotadas no projeto.

## 1. Contexto e Fontes de Dados
- **Objetivo:** Solução de engenharia de dados e analytics para o teste técnico de Analista de Dados Sênior (Cogna Educação).
- **Fontes originais (`data/raw/`):** Planilha principal `analytical_database_callcenter.xlsx` e 8 arquivos CSV exportados das abas correspondentes:
  - Abas analíticas: `Analitico call center`, `Analitico Whatsapp`, `Analitico_video_chamada` e `Analitico_Totem`.
  - Abas de dicionário: `Dicionario call center`, `Dicionario_whatsapp`, `Dicionario_video` e `Dicionario_Totem`.
- **Características técnicas das fontes:**
  - Os CSVs utilizam delimitador `;`, cabeçalho na primeira linha e codificação `utf-8-sig`. Nos dicionários, a primeira coluna (`Campos`) vem de células mescladas no Excel e requer preenchimento contextual (`forward-fill`).
  - A leitura inicial é feita como texto para preservar identificadores longos e protocolos numéricos.
  - A planilha `analytical_database_callcenter.xlsx` armazena os timestamps completos com precisão de segundos (omitidos nos CSVs de Call Center, WhatsApp e Totem) e os valores numéricos de protocolo sem a formatação truncada `1,44496E+18` gerada na exportação em locale `pt-BR`.

## 2. Objetivos de Negócio (9 Perguntas Obrigatórias + Indicadores Operacionais)
1. Qual a quantidade de alunos que entraram em contato com o Call Center e posteriormente com o WhatsApp?
2. Algum aluno entrou em contato com o Call Center, depois no WhatsApp e depois em qualquer outro canal?
3. Quais são os principais motivos de contato em todos os canais?
4. Qual o perfil de aluno que procura a fila de retenção (`CRA_Retenção`) do Call Center? Esse aluno contatou anteriormente algum outro canal antes de pedir o cancelamento?
5. Algum comportamento de aluno que entra em contato em qualquer um dos canais e depois na retenção?
6. Qual o canal de atendimento com a pior nota de pesquisa?
7. Existe algum perfil de aluno que dá nota de satisfação ruim?
8. Usando a coluna `DnaSoa` do Call Center, é possível avaliar se os pontos de navegação influenciaram a nota do atendimento? (Diferenciando associação/correlação observacional de causalidade).
9. Qual agente gera o maior volume de recontatos do mesmo CPF no mesmo dia?

**Indicadores complementares:** desconexão por tipo, TME e duração de atendimento por canal/fila, contatos fora de horário, taxa de recontato no mesmo dia, volume por hora/dia, navegação em autoatendimento (Totem e URA) e taxa de resposta da pesquisa de satisfação.

## 3. Arquitetura (Medallion Local)
```text
cogna/
├─ data/                      # Armazenamento local (não versionado no Git)
│  ├─ raw/                    # Cópia somente leitura dos arquivos originais
│  ├─ bronze/                 # CSVs normalizados (cabeçalhos em snake_case)
│  ├─ dictionaries/           # Dicionários estruturados em JSON por canal
│  ├─ silver/                 # Parquet tipado e padronizado via DuckDB SQL sobre o XLSX
│  └─ gold/                   # Modelo estrela em Parquet e CSV + resultados das 9 perguntas
├─ src/cogna_etl/             # Orquestrador e CLI Python (python -m cogna_etl <comando>)
├─ sql/{staging,model,analytics}/
├─ tests/                     # Suíte de testes unitários, sintéticos e de integração
├─ docs/                      # Documentação técnica, decisões e relatórios por etapa
└─ powerbi/                   # Projeto Power BI (PBIP/TMDL, scripts M, DAX e tema JSON)
```
**Stack principal:** Python 3.11+, DuckDB SQL, Pandas, PyArrow, OpenPyXL, Pytest e Ruff.

## 4. Etapas de Desenvolvimento

### Fase 0 — Setup e Inventário
Configuração do ambiente virtual, `requirements.txt`, estrutura de diretórios, `.gitignore` e repositório Git. Cópia dos arquivos brutos para `data/raw/` em modo somente leitura, inventário físico/lógico (tamanho, linhas, encoding, delimitador) e reconciliação dimensional entre os CSVs e as abas do XLSX.
- **Documentação:** `docs/fase0.md` e `docs/ESTADO.md`.

### Fase 1 — Normalização Bronze e Dicionários JSON
- Padronização dos cabeçalhos dos CSVs analíticos em `snake_case` minúsculo, sem acentos ou símbolos, documentada em `docs/mapeamento_colunas.md`.
- Estruturação dos dicionários em JSON (`data/dictionaries/`) com `forward-fill` do nome do campo, remoção de linhas vazias, preservação explícita de conflitos de domínio e mapeamento por canal, documentada em `docs/inconsistencias_dicionario.md`.
- Gravação em `data/bronze/` sem alteração dos valores originais e verificação de integridade via hash SHA-256 contra o XLSX.
- **Documentação:** `docs/fase1.md`.

### Fase 2 — Profiling e Diagnóstico de Qualidade
Diagnóstico completo sobre as 4 abas analíticas do XLSX: volumetria, nulos, cardinalidade, duplicatas exatas, fórmulas e cache do Excel, faixas temporais, cobertura e distribuição das notas de pesquisa, comparação `recepcao_fila` vs `fila_atend`, matriz cruzada de retenção (fila vs assunto vs encaminhamento), formatos de protocolo, divergências entre modalidade cadastral e tabulação, durações/TME, trilhas `dna_soa` (trios repetidos e tokens `98`/`99`), fluxos do Totem e sobreposições temporais na jornada do aluno.
- **Documentação:** `docs/fase2_qualidade.md`.

### Fase 3 — Camada Silver em SQL (DuckDB)
Conforme `DEC-006`, toda a transformação de negócio da camada Silver é executada em DuckDB SQL (`sql/staging/00..08_*.sql`), com Python atuando apenas como executor fino em `src/cogna_etl/silver.py`:
- Leitura direta das abas analíticas do `analytical_database_callcenter.xlsx` via `read_xlsx` do DuckDB, preservando segundos nos timestamps, milissegundos na Vídeo Chamada e valores originais de protocolo, com linhagem de origem (`origem_arquivo`, `origem_aba`, `origem_linha`).
- Geração de `contato_id` determinístico por origem e pseudonimização de `identificador_aluno` em `aluno_hash` (SHA-256 com salt de `.env`).
- Padronização de timestamps (`data_hora_contato`), durações e TME em segundos com flags de zero, inválido, outlier por IQR 1,5 e `TME > duração`.
- Classificação estrita das notas de pesquisa (`status_nota`, `nota` inteira de 1 a 5, `respondeu_pesquisa`, `flag_nota_ruim`).
- Decomposição hierárquica da tabulação (`tab_nivel1..7`), flags separadas de retenção (`eh_retencao_fila`, `eh_assunto_retencao`, `flag_encaminhamento_retencao`, `flag_retencao_protocolo`), `desfecho_retencao`, `modalidade_tab` pelo 1º nível e `flag_divergencia_modalidade`.
- Padronização de domínios por canal e campo a partir dos JSONs locais, sinalizando conflitos sem multiplicar registros.
- Persistência em `data/silver/silver_*.parquet` com schema explícito e validação atômica.
- **Documentação:** `docs/fase3.md`.

### Fase 4 — Modelo Estrela Gold e Consultas Analíticas em SQL (DuckDB)
Modelagem dimensional em `sql/model/01..11_*.sql` e consultas analíticas em `sql/analytics/q01..q09_*.sql`:
- **Fatos:** `fato_contato` (5.991 atendimentos unificados), `fato_navegacao` (passos de navegação explodidos com posição e flag de repetição) e `fato_jornada` (sequência cronológica por aluno com `ROW_NUMBER`, `LAG`, `LEAD`, intervalos, sobreposições e atribuição de recontato no mesmo dia ao agente anterior).
- **Dimensões:** `dim_calendario` (dinâmica em SQL com feriados nacionais estáticos), `dim_hora`, `dim_canal`, `dim_aluno`, `dim_agente`, `dim_fila`, `dim_perfil_aluno` e `dim_motivo`.
- **Proteção LGPD:** remoção integral de `aluno_id_original` e nomes pessoais de agentes/supervisores nas tabelas exportadas da Gold.
- Exportação em `data/gold/*.parquet` (`SNAPPY`) e `data/gold/*.csv` (`;`, UTF-8 com BOM).
- **Documentação:** `docs/fase4.md`.

### Fase 5 — Integração com Power BI
- Scripts Power Query M enxutos em `powerbi/m/`, restritos à leitura parametrizada (`pDataPath` apontando para `data/gold/`), sem transformações de negócio em M.
- Estruturação do modelo estrela com relacionamentos 1:N unidirecionais, tabela de calendário marcada e chaves técnicas ocultas em formato de projeto Power BI (PBIP/TMDL).
- **Documentação:** `docs/fase5.md`.

### Fase 6 — Medidas DAX
Catálogo de medidas DAX em `powerbi/dax/medidas.dax` e no modelo semântico, organizadas por pastas de exibição: volumes, taxa de resposta, nota média ponderada dos respondidos, % de notas ruins, tempos de atendimento e espera, recontato no mesmo dia, ranking de agentes, transições de jornada (CC→WA e CC→WA→outro canal), retenção e navegação vs satisfação, reconciliadas com os resultados SQL da Fase 4.
- **Documentação:** `docs/fase6.md`.

### Fase 7 — Design, UX/UI e Construção do Dashboard
Estruturação visual com 1 capa de navegação e até 3 páginas analíticas (Visão Geral & Jornada · Motivos & Retenção · Qualidade & Agentes), grid alinhado, hierarquia tipográfica, paleta sóbria, acessibilidade, tooltips de contexto e tema JSON em `powerbi/theme/`.

### Fase 8 — Documentação Final e Empacotamento da Entrega
Consolidação do `README.md`, documentação de arquitetura, linhagem, dicionário e qualidade de dados, e montagem do pacote local `entrega/` (fora do Git) contendo a base analítica Gold, códigos SQL/Python e arquivo do Power BI.

## 5. Premissas de Negócio Adotadas (Registradas em `docs/decisoes.md`)
- **Identificador do aluno e LGPD:** `identificador_aluno` tratado como texto exato (sem zero-fill) e pseudonimizado em `aluno_hash` via SHA-256 com salt local. Nas tabelas Gold e visuais, utiliza-se apenas `aluno_hash` e códigos pseudonimizados de agente (`AG-001..AG-170`).
- **Contato posterior:** qualquer atendimento do mesmo aluno com timestamp estritamente superior (`>`) dentro do período analisado, acompanhado de análises de sensibilidade para janelas de 24 horas e 7 dias.
- **Retenção:** avaliada de forma transparente sob duas ópticas complementares — fila de atendimento contendo `"retenc"` (`eh_retencao_fila`) e tabulação contendo `"Atendimento de Retenção"` (`eh_assunto_retencao`), reportadas lado a lado nas questões Q4 e Q5.
- **Pesquisa de satisfação:** nota `0` e valores nulos representam ausência de resposta (`respondeu_pesquisa = FALSE`) e não entram no denominador da nota média; notas `1` e `2` compõem o indicador de nota ruim (`flag_nota_ruim = TRUE`); a taxa de resposta é sempre informada junto à média.
- **Recontato no mesmo dia (Q9):** retorno do mesmo aluno no mesmo dia calendário (`data_contato`), atribuído ao agente que realizou o atendimento imediatamente anterior, reportado nas visões Omnichannel (canais com agente humano) e Intracanal (mesmo canal).
- **Modalidade cadastral vs tabulação:** prevalece o atributo cadastral registrado no contato, sinalizando divergências contra o 1º nível da tabulação por meio de `flag_divergencia_modalidade`.
- **Unidade de duração e TME:** valores tratados em segundos inteiros (`duracao_s`, `tme_s`).
