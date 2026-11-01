# Mapeamento de Colunas — Camada Raw para Bronze

Este documento registra a padronização formal de todos os nomes de colunas dos 4 conjuntos analíticos de atendimento. As colunas foram convertidas para `snake_case` minúsculo, sem caracteres especiais ou acentos, garantindo unicidade, legibilidade técnica e interoperabilidade com DuckDB SQL, Python e Power BI.

---

## 1. Diretrizes de Padronização e Premissas

1. **Snake Case:** Nomes em caixa baixa, sem espaços ou símbolos (ex.: `Duração da Chamada` → `duracao_da_chamada`).
2. **Coluna Sem Nome (Vídeo Chamada):** A coluna de índice 2 estava vazia no cabeçalho original e contém data e hora sem os milissegundos. Foi nomeada explicitamente como `calldate_sem_ms`.
3. **Diferenciação entre Fila de Entrada e Fila de Atendimento:** A distinção funcional entre `recepcao_fila` e `fila_atend` no Call Center permanece como **hipótese técnica pendente de confirmação da Cogna** (hipótese: `recepcao_fila` representa a fila receptora inicial da URA e `fila_atend` representa a fila efetiva onde o operador atendeu a ligação).
4. **Horário de Atendimento (`after_hour`):** O campo indica atendimento fora do horário de expediente da operação, não necessariamente fora do horário comercial geral.
5. **Premissas de Unidades de Tempo:** Campos de duração e espera (`duration_callcenter`, `duracao`, `duracao_da_chamada`, `tme`) são assumidos sob a **premissa de unidade em segundos**, pendente de validação formal.
6. **Nota de Pesquisa:** Resposta `0` é tratada sob a **premissa de ausência de resposta**, pendente de validação formal pela Cogna.
7. **Isolamento de Dados:** Este documento contém apenas metadados e definições de colunas, em estrita conformidade com as diretrizes de governança e LGPD.

---

## 2. Tabelas Analíticas

### 2.1. Call Center (`analitico_callcenter.csv`)
- **Arquivo Raw:** `data/raw/analytical_database_callcenter.analitico_callcenter.csv`
- **Arquivo Bronze:** `data/bronze/analitico_callcenter.csv`
- **Total de Colunas:** 22

| Índice | Nome Original (Raw) | Nome Normalizado (Bronze) | Descrição / Hipótese / Premissa |
| :---: | :--- | :--- | :--- |
| 0 | `identificador aluno` | `identificador_aluno` | ID de identificação cadastral do aluno |
| 1 | `Date` | `date` | Data da chamada no formato DD/MM/AAAA |
| 2 | `Calldate` | `calldate` | Data e hora de início da chamada |
| 3 | `IdType` | `id_type` | Código do tipo de identificação feita na URA |
| 4 | `IdType - desc` | `id_type_desc` | Rótulo do tipo de identificação na URA |
| 5 | `DisconnectType` | `disconnect_type` | Código do tipo de desconexão da chamada |
| 6 | `DisconnectType_DESC` | `disconnect_type_desc` | Descrição do encerramento da chamada |
| 7 | `DurationCallcenter` | `duration_callcenter` | Premissa: tempo de chamada em curso no DAC/ATH em segundos |
| 8 | `DnaSoa` | `dna_soa` | Sequência dos pontos e serviços navegados na URA |
| 9 | `recepcao_fila` | `recepcao_fila` | Hipótese: fila de recepção inicial na entrada da chamada |
| 10 | `fila_atend` | `fila_atend` | Hipótese: fila final onde ocorreu o atendimento pelo operador |
| 11 | `Agent` | `agent` | Nome do agente que realizou o atendimento |
| 12 | `Supervisor` | `supervisor` | Nome do supervisor responsável |
| 13 | `Pesquisa_1` | `pesquisa_1` | Premissa: nota de satisfação de 1 a 5 (0 = sem resposta) |
| 14 | `Protocolo` | `protocolo` | Identificador do protocolo gerado no sistema |
| 15 | `tabulacao` | `tabulacao` | Classificação hierárquica do motivo do contato |
| 16 | `Modalidade_nova` | `modalidade_nova` | Código da modalidade de ensino do aluno |
| 17 | `Modalidade_nova_DESC` | `modalidade_nova_desc` | Descrição textual da modalidade de ensino |
| 18 | `Categoria_Aluno` | `categoria_aluno` | Código da categoria do aluno (Calouro/Veterano) |
| 19 | `Categoria_Aluno_DESC` | `categoria_aluno_desc` | Descrição textual da categoria do aluno |
| 20 | `Instituicao` | `instituicao` | Código da instituição de ensino |
| 21 | `Instituicao_DESC` | `instituicao_desc` | Nome da instituição de ensino |

---

### 2.2. WhatsApp (`analitico_whatsapp.csv`)
- **Arquivo Raw:** `data/raw/analytical_database_callcenter.analitico_whatsapp.csv`
- **Arquivo Bronze:** `data/bronze/analitico_whatsapp.csv`
- **Total de Colunas:** 19

| Índice | Nome Original (Raw) | Nome Normalizado (Bronze) | Descrição / Hipótese / Premissa |
| :---: | :--- | :--- | :--- |
| 0 | `identificador aluno` | `identificador_aluno` | ID de identificação cadastral do aluno |
| 1 | `calldate` | `calldate` | Data e hora de abertura do chamado via WhatsApp |
| 2 | `IdType` | `id_type` | Código do tipo de identificação do cliente |
| 3 | `DisconnectType` | `disconnect_type` | Código do motivo de desconexão |
| 4 | `DisconnectType_DESC` | `disconnect_type_desc` | Descrição do motivo de desconexão |
| 5 | `Modalidade` | `modalidade` | Código da modalidade de ensino |
| 6 | `Modalidade_DESC` | `modalidade_desc` | Descrição textual da modalidade de ensino |
| 7 | `DurationCallCenter` | `duration_callcenter` | Premissa: duração do atendimento com operador em segundos |
| 8 | `AfterHour` | `after_hour` | Indicador de atendimento fora do horário de atendimento da operação |
| 9 | `Categoria_aluno` | `categoria_aluno` | Código da categoria do aluno |
| 10 | `Categoria_aluno_DESC` | `categoria_aluno_desc` | Descrição textual da categoria do aluno |
| 11 | `Instituicao` | `instituicao` | Código da instituição de ensino |
| 12 | `Instituicao_DESC` | `instituicao_desc` | Nome da instituição de ensino |
| 13 | `DnaSoa` | `dna_soa` | Sequência dos nós de navegação no bot |
| 14 | `TME` | `tme` | Premissa: tempo de espera até o início do atendimento em segundos |
| 15 | `codigo_unidade` | `codigo_unidade` | Hipótese: código do polo ou unidade física de vínculo |
| 16 | `Pesquisa_1` | `pesquisa_1` | Premissa: nota de satisfação de 1 a 5 (0 = sem resposta) |
| 17 | `AGENTE` | `agente` | Usuário ou nome do agente de atendimento |
| 18 | `Tabulacao` | `tabulacao` | Motivo de encerramento tabulado |

---

### 2.3. Vídeo Chamada (`analitico_video_chamada.csv`)
- **Arquivo Raw:** `data/raw/analytical_database_callcenter.analitico_video_chamada.csv`
- **Arquivo Bronze:** `data/bronze/analitico_video_chamada.csv`
- **Total de Colunas:** 9

| Índice | Nome Original (Raw) | Nome Normalizado (Bronze) | Descrição / Hipótese / Premissa |
| :---: | :--- | :--- | :--- |
| 0 | `identificador aluno` | `identificador_aluno` | ID de identificação cadastral do aluno |
| 1 | `CallDate` | `calldate` | Data e hora com milissegundos (`DD/MM/AAAA HH:MM:SS.mmm`) |
| 2 | *(vazio / sem nome)* | `calldate_sem_ms` | Coluna sem nome no arquivo bruto. Contém data e hora truncada sem fração de segundo |
| 3 | `TME` | `tme` | Premissa: tempo de espera na fila da chamada de vídeo em segundos |
| 4 | `Duração da Chamada` | `duracao_da_chamada` | Premissa: duração da videochamada em segundos |
| 5 | `Agente` | `agente` | Nome do operador que realizou a chamada de vídeo |
| 6 | `Protocolo` | `protocolo` | Código do protocolo de atendimento |
| 7 | `Nota Pergunta1` | `nota_pergunta1` | Premissa: nota avaliativa de 1 a 5 (0 = sem resposta) |
| 8 | `tabulacao` | `tabulacao` | Motivo tabulado para a chamada de vídeo |

---

### 2.4. Totem Presencial (`analitico_totem.csv`)
- **Arquivo Raw:** `data/raw/analytical_database_callcenter.analitico_totem.csv`
- **Arquivo Bronze:** `data/bronze/analitico_totem.csv`
- **Total de Colunas:** 7

| Índice | Nome Original (Raw) | Nome Normalizado (Bronze) | Descrição / Hipótese / Premissa |
| :---: | :--- | :--- | :--- |
| 0 | `identificador aluno` | `identificador_aluno` | ID de identificação cadastral do aluno |
| 1 | `DATA_INICIO` | `data_inicio` | Data e hora de início da sessão de autoatendimento no totem |
| 2 | `DURACAO` | `duracao` | Premissa: tempo de permanência da sessão no totem em segundos |
| 3 | `INSTITUICAO` | `instituicao` | Nome ou código da instituição onde o totem está instalado |
| 4 | `MDC` | `mdc` | Hipótese: motivo do contato selecionado na tela inicial |
| 5 | `NAVEGACAO` | `navegacao` | Trilha de telas acessadas no autoatendimento |
| 6 | `Nota Pergunta1` | `nota_pergunta1` | Premissa: avaliação registrada no totem de 1 a 5 (0 = sem resposta) |
