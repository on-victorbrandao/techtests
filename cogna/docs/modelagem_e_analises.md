# Modelagem dimensional Gold e análises de negócio (Q1 a Q9)

Este documento descreve o modelo estrela da camada Gold (`sql/model/01_dim_calendario.sql` a `11_fato_jornada.sql`) e consolida as respostas das nove perguntas de negócio do case (`sql/analytics/q01_*.sql` a `q09_*.sql`) executadas em DuckDB SQL sobre `data/silver/`.

---

## 1. Arquitetura do modelo estrela Gold

Todas as tabelas são exportadas em formato `.parquet` (`SNAPPY`) e `.csv` (`;`, UTF-8 com BOM) em `data/gold/`, mantendo os 5.991 atendimentos sem exposição de dados pessoais (LGPD).

| Tabela | Script SQL | Tipo | Grão | Chave primária (PK) | Linhas | Colunas |
| :--- | :--- | :---: | :--- | :--- | ---: | ---: |
| `dim_calendario` | `sql/model/01_dim_calendario.sql` | Dimensão | 1 linha por dia no intervalo de contatos (01/09/2026 a 12/09/2026) | `data` (`DATE`) | 12 | 15 |
| `dim_hora` | `sql/model/02_dim_hora.sql` | Dimensão | 1 linha por hora inteira do dia (0 a 23) | `hora_inteira` (`INTEGER`) | 24 | 6 |
| `dim_canal` | `sql/model/03_dim_canal.sql` | Dimensão | 1 linha por canal de atendimento | `canal_id` (`INTEGER`) | 4 | 10 |
| `dim_aluno` | `sql/model/04_dim_aluno.sql` | Dimensão | 1 linha por aluno pseudonimizado (`AL-001..AL-173`) | `aluno_hash` (`VARCHAR`) | 173 | 10 |
| `dim_agente` | `sql/model/05_dim_agente.sql` | Dimensão | 1 linha por `(canal, agente)` mascarado (`AG-001..AG-170`) + `AG-000` (autoatendimento) | `agente_id` (`VARCHAR`) | 171 | 8 |
| `dim_fila` | `sql/model/06_dim_fila.sql` | Dimensão | 1 linha por combinação `(recepcao_fila, fila_atend)` no CC (`FL-01..FL-32`) + `FL-00` (sem fila) | `fila_id` (`VARCHAR`) | 33 | 7 |
| `dim_perfil_aluno` | `sql/model/07_dim_perfil_aluno.sql` | Dimensão | 1 linha por combinação de perfil observada no contato (`PF-001..PF-053`) | `perfil_id` (`VARCHAR`) | 53 | 16 |
| `dim_motivo` | `sql/model/08_dim_motivo.sql` | Dimensão | 1 linha por combinação de tabulação (`tab_nivel1..7`) ou `mdc_original` (`MOT-001..MOT-591`) | `motivo_id` (`VARCHAR`) | 591 | 18 |
| `fato_contato` | `sql/model/09_fato_contato.sql` | Fato | 1 linha por atendimento (`UNION ALL` dos 4 canais) | `contato_id` (`VARCHAR`) | 5.991 | 38 |
| `fato_navegacao` | `sql/model/10_fato_navegacao.sql` | Fato | 1 linha por passo de navegação (`contato_id` + `tipo_sequencia` + `ordem_passo`) | `(contato_id, tipo_sequencia, ordem_passo)` | 81.189 | 8 |
| `fato_jornada` | `sql/model/11_fato_jornada.sql` | Fato | 1 linha por atendimento ordenada por `(aluno_hash, data_hora_contato, canal, contato_id)` | `contato_id` (`VARCHAR`) | 5.991 | 28 |

### Regras de modelagem aplicadas
1. **Proteção LGPD:** `aluno_id_original`, `agente_original` e `supervisor_original` não são exportados para a camada Gold. Os agentes humanos recebem código determinístico `AG-001`..`AG-170` (ordenado por `canal` e `sha256(agente_original)`) e o hash curto `agente_hash` (`substr(sha256(agente_original), 1, 12)`), permitindo auditar qualquer agente na pergunta 9 sem expor nomes.
2. **Perfil vinculado ao atendimento (`dim_perfil_aluno` -> `fato_contato`):** `modalidade`, `categoria_aluno`, `instituicao` e `id_type` refletem o estado do aluno no momento do contato, sem forçar um único cadastro em `dim_aluno` e sem imputar modalidade nos canais que não possuem a coluna (vídeo chamada e totem ficam como `Não Informado no Canal`).
3. **Calendário em SQL (`dim_calendario`):** gerado dinamicamente em DuckDB SQL entre a menor e a maior data de contato, com semana ISO (`1 = segunda .. 7 = domingo`), rótulos em português (`seg`..`dom`, `jan`..`dez`), `ano_mes_ordem` (`ano * 100 + mes`) e feriados nacionais de 2026 declarados em SQL (incluindo `2026-09-07`).

---

## 2. Respostas das 9 perguntas de negócio (Q1 a Q9)

### Q1 — Quantidade de alunos que entraram em contato com o Call Center e posteriormente com o WhatsApp (`q01_cc_para_whatsapp.sql`)

- **Resposta:** **173 alunos distintos** (100,00% dos 173 alunos que acionaram o Call Center) tiveram ao menos um atendimento no WhatsApp em horário posterior (`data_hora_contato_wa > data_hora_contato_cc`).
- Em nível de atendimentos do Call Center, dos **1.499 contatos**, **1.403 (93,60%)** tiveram algum contato de WhatsApp posterior no período e **96 (6,40%, distribuídos em 58 alunos)** ocorreram após o último WhatsApp registrado para aquele aluno.

| Ordem | Recorte analítico | Alunos distintos | % alunos CC (`/173`) | Contatos CC | % contatos CC (`/1.499`) |
| :---: | :--- | ---: | ---: | ---: | ---: |
| 1 | **Qualquer WhatsApp posterior no período (`> ts_cc`)** | **173** | **100,00%** | **1.403** | **93,60%** |
| 2 | Transição imediata (`contato k = CC` e `k+1 = WhatsApp` na jornada global) | 160 | 92,49% | 340 | 22,68% |
| 3 | Transição com canais intermediários (`teve WA posterior, mas k+1 <> WA`) | 173 | 100,00% | 1.063 | 70,91% |
| 4 | Sem WhatsApp posterior no período | 58 | 33,53% | 96 | 6,40% |
| 5 | Sensibilidade: WhatsApp em até **24 horas** (`<= 86.400 s`) após o CC | 173 | 100,00% | 860 | 57,37% |
| 6 | Sensibilidade: WhatsApp em até **7 dias** (`<= 604.800 s`) após o CC | 173 | 100,00% | 1.403 | 93,60% |

---

### Q2 — Alunos que passaram pelo Call Center, depois pelo WhatsApp e depois por qualquer outro canal (`q02_cc_wa_outro_canal.sql`)

- **Resposta:** **Sim.**
  - Na leitura **(a) estritamente consecutiva** (`contato k = Call Center`, `k+1 = WhatsApp`, `k+2 = 3º canal`), **138 alunos distintos (79,77%)** passaram em seguida por um canal diferente de WhatsApp (251 trincas consecutivas), e **157 alunos distintos (90,75%)** tiveram qualquer terceiro contato consecutivo (325 trincas). Considerando apenas **vídeo chamada ou totem** como terceiro canal, são **104 alunos distintos (60,12%)** em 145 trincas.
  - Na leitura **(b) com contatos intermediários** (`t_cc < t_wa < t_terceiro`), **todos os 173 alunos (100,00%)** tiveram atendimento posterior em outro canal após passarem por Call Center e WhatsApp (sendo **172 alunos / 99,42%** se restringirmos o terceiro canal a vídeo chamada ou totem).

| Leitura da sequência | Escopo do terceiro canal | Alunos distintos | % sobre a base (`/173`) | Ocorrências (trincas / contatos) |
| :--- | :--- | ---: | ---: | ---: |
| **(a) Estritamente consecutiva (`k, k+1, k+2`)** | **Consolidado: qualquer canal exceto WhatsApp** | **138** | **79,77%** | **251** |
| (a) Estritamente consecutiva (`k, k+1, k+2`) | Consolidado: qualquer um dos 4 canais | 157 | 90,75% | 325 |
| (a) Estritamente consecutiva (`k, k+1, k+2`) | Consolidado: apenas vídeo chamada ou totem | 104 | 60,12% | 145 |
| (a) Estritamente consecutiva — detalhe | `call_center` | 83 | 47,98% | 106 |
| (a) Estritamente consecutiva — detalhe | `whatsapp` | 66 | 38,15% | 74 |
| (a) Estritamente consecutiva — detalhe | `video_chamada` | 61 | 35,26% | 74 |
| (a) Estritamente consecutiva — detalhe | `totem` | 65 | 37,57% | 71 |
| **(b) Com contatos intermediários (`t_cc < t_wa < t_3º`)** | **Consolidado: qualquer canal exceto WhatsApp** | **173** | **100,00%** | **3.313** |
| (b) Com contatos intermediários (`t_cc < t_wa < t_3º`) | Consolidado: qualquer um dos 4 canais | 173 | 100,00% | 4.414 |
| (b) Com contatos intermediários (`t_cc < t_wa < t_3º`) | Consolidado: apenas vídeo chamada ou totem | 172 | 99,42% | 2.198 |
| (b) Com intermediários — detalhe | `call_center` | 173 | 100,00% | 1.115 |
| (b) Com intermediários — detalhe | `whatsapp` | 173 | 100,00% | 1.101 |
| (b) Com intermediários — detalhe | `totem` | 172 | 99,42% | 1.202 |
| (b) Com intermediários — detalhe | `video_chamada` | 167 | 96,53% | 996 |

---

### Q3 — Principais motivos de contato em todos os canais (`q03_principais_motivos.sql`)

#### 3.1. Cobertura de preenchimento por canal
- Nos canais com atendimento humano (**Call Center, WhatsApp e vídeo chamada**), o motivo vem da árvore `tabulacao_original` (`tab_nivel1..7`). No **Call Center**, **530 de 1.499 contatos (35,36%)** estão com tabulação nula (`NULL`). WhatsApp (1.494) e vídeo chamada (1.499) têm 100% de preenchimento.
- No **totem** (1.499 contatos), o motivo vem do campo `mdc_original`, com 100% de preenchimento físico, mas incluindo 231 registros (`15,41%`) classificados na origem como `Nao identificado`.

#### 3.2. Principais motivos por canal (`tab_nivel2 > tab_nivel3` ou `mdc_original`)

| Canal | Motivo (`tab_nivel2 > tab_nivel3` ou `mdc_original`) | Contatos | % no total do canal | % nos preenchidos do canal |
| :--- | :--- | ---: | ---: | ---: |
| **call_center** | `Sem Tabulação (Nulo)` | 530 | 35,36% | — |
| **call_center** | `Registro de atendimento - EAD > Atendimento de Retenção` | 194 | 12,94% | 20,02% |
| **call_center** | `Registro de atendimento - EAD > Acadêmico` | 193 | 12,88% | 19,92% |
| **call_center** | `Registro de atendimento - Presencial > Acadêmico` | 115 | 7,67% | 11,87% |
| **call_center** | `Registro de atendimento - Presencial > Boleto Mensalidade ou Rematrícula` | 75 | 5,00% | 7,74% |
| **call_center** | `Registro de atendimento - Presencial > Atendimento de Retenção` | 72 | 4,80% | 7,43% |
| **call_center** | `Registro de atendimento - EAD > Boleto Mensalidade ou Rematrícula` | 60 | 4,00% | 6,19% |
| **whatsapp** | `Registro de atendimento - Presencial > Acadêmico` | 637 | 42,64% | 42,64% |
| **whatsapp** | `Registro de atendimento - Presencial > Boleto Mensalidade ou Rematrícula` | 412 | 27,58% | 27,58% |
| **whatsapp** | `Registro de atendimento - Presencial > Atendimento de Retenção` | 402 | 26,91% | 26,91% |
| **whatsapp** | `Ambiente Virtual De Apredinzagem (Ava) > Atividades Virtuais` | 24 | 1,61% | 1,61% |
| **video_chamada** | `Registro de atendimento - EAD > Acadêmico` | 273 | 18,21% | 18,21% |
| **video_chamada** | `Registro de atendimento - Presencial > Acadêmico` | 234 | 15,61% | 15,61% |
| **video_chamada** | `Registro de atendimento - Presencial > Boleto Mensalidade ou Rematrícula` | 203 | 13,54% | 13,54% |
| **video_chamada** | `Registro de atendimento - EAD > Boleto Mensalidade ou Rematrícula` | 120 | 8,01% | 8,01% |
| **video_chamada** | `Registro de atendimento - Presencial > Bolsas` | 64 | 4,27% | 4,27% |
| **video_chamada** | `Registro de atendimento - Presencial > Boleto Serviço` | 56 | 3,74% | 3,74% |
| **video_chamada** | `Registro de atendimento - EAD > Atendimento de Retenção` | 49 | 3,27% | 3,27% |
| **totem** | `JA_SOU_ALUNO` | 765 | 51,03% | 51,03% |
| **totem** | `Nao identificado` | 231 | 15,41% | 15,41% |
| **totem** | `QUERO_SER_ALUNO` | 214 | 14,28% | 14,28% |
| **totem** | `OUTROS_ASSUNTOS` | 133 | 8,87% | 8,87% |
| **totem** | `EX-ALUNO` | 120 | 8,01% | 8,01% |
| **totem** | `TermoQuitacaoDebitos` | 26 | 1,73% | 1,73% |

#### 3.3. Visão consolidada por macrotema (5.991 contatos)

| Macrotema consolidado | Contatos | % sobre o total (`5.991`) | % sobre os preenchidos (`5.461`) |
| :--- | ---: | ---: | ---: |
| **Acadêmico / secretaria** | 1.458 | 24,34% | 26,70% |
| **Financeiro / boletos / bolsas** | 1.296 | 21,63% | 23,73% |
| **Menu inicial / triagem de autoatendimento (MDC totem)** | 1.238 | 20,66% | 22,67% |
| **Não identificado / sem tabulação** (530 nulos CC + 231 MDC não identificado) | 761 | 12,70% | — |
| **Retenção (cancelamento / trancamento / manutenção)** | 743 | 12,40% | 13,61% |
| **Outros assuntos / triagem** | 420 | 7,01% | 7,69% |
| **Portal / AVA / acesso** | 45 | 0,75% | 0,82% |
| **Financeiro / negociação (totem termo de quitação)** | 26 | 0,43% | 0,48% |
| **Acadêmico / documentos (totem matriz e histórico)** | 4 | 0,07% | 0,07% |

---

### Q4 — Perfil do aluno na retenção do Call Center e contato anterior ao pedido de cancelamento (`q04_perfil_retencao_e_contato_anterior.sql`)

#### 4.1. Perfil do aluno que procura a retenção no Call Center
- **Perfil predominante nas três visões:** aluno de **EAD Campus** (63,32% na fila exata `cra_retencao`, 57,04% nas 4 filas de retenção e 70,30% no assunto de retenção), **calouro** (72,05% em `cra_retencao`, 65,56% nas 4 filas e 71,80% no assunto), da instituição **Anhanguera** (93,01% em `cra_retencao`, 86,67% nas 4 filas e 92,48% no assunto) e **identificado por CPF** (> 99,5%).
- Ao considerar todas as 4 filas contendo `retenc` (`cra_retencao`, `cra_retencao_calouro`, `cra_retencao_ptk` e `cra_ptk_retencao` = 270 contatos), entram também alunos de **7 - EAD Campus PTK** (30 contatos, 11,11%) e **9 - Ampli PTC** (20 contatos, 7,41%).

| Dimensão | Categoria de perfil | (1) Fila exata `cra_retencao` (`229` cont. / `144` al.) | (2) 4 filas `eh_retencao_fila` (`270` cont. / `171` al.) | (3) Assunto `eh_assunto_retencao` CC (`266` cont. / `143` al.) |
| :--- | :--- | :--- | :--- | :--- |
| **Modalidade** | `5 - EAD Campus` | **145 (63,32%)** · 109 al. | **154 (57,04%)** · 114 al. | **187 (70,30%)** · 125 al. |
| **Modalidade** | `1 - Presencial Campus` | 77 (33,62%) · 71 al. | 81 (30,00%) · 75 al. | 71 (26,69%) · 66 al. |
| **Modalidade** | `7 - EAD Campus PTK` | 2 (0,87%) · 2 al. | 30 (11,11%) · 29 al. | 0 (0,00%) |
| **Modalidade** | `6 - EAD Parceiros` | 5 (2,18%) · 5 al. | 5 (1,85%) · 5 al. | 8 (3,01%) · 8 al. |
| **Categoria** | `1 - Calouro` | **165 (72,05%)** · 121 al. | **177 (65,56%)** · 128 al. | **191 (71,80%)** · 129 al. |
| **Categoria** | `2 - Veterano` | 64 (27,95%) · 57 al. | 93 (34,44%) · 82 al. | 75 (28,20%) · 66 al. |
| **Instituição** | `2 - Anhanguera` | **213 (93,01%)** · 139 al. | **234 (86,67%)** · 154 al. | **246 (92,48%)** · 138 al. |
| **Instituição** | `9 - Ampli PTC` | 1 (0,44%) · 1 al. | 20 (7,41%) · 20 al. | 0 (0,00%) |
| **Instituição** | `7 - Unime` | 5 (2,18%) · 5 al. | 5 (1,85%) · 5 al. | 8 (3,01%) · 8 al. |
| **Instituição** | `6 - Uniderp` | 4 (1,75%) · 4 al. | 4 (1,48%) · 4 al. | 4 (1,50%) · 4 al. |
| **Instituição** | `1 - Unopar` | 3 (1,31%) · 3 al. | 3 (1,11%) · 3 al. | 5 (1,88%) · 5 al. |
| **Instituição** | Outras (`Pitágoras`, `Unic`, `Ampli legado`) | 3 (1,32%) | 4 (1,48%) | 3 (1,13%) |
| **Identificação** | `1 - Cliente identificado por CPF` | **228 (99,56%)** · 144 al. | **269 (99,63%)** · 171 al. | **265 (99,62%)** · 142 al. |
| **Identificação** | `2 - Cliente NAO identificado por CPF` | 1 (0,44%) · 1 al. | 1 (0,37%) · 1 al. | 1 (0,38%) · 1 al. |

#### 4.2. Contato anterior (`< data_hora_contato`) em outro canal (`<> 'call_center'`) antes do pedido de cancelamento
- **Resposta:** **Sim, quase todos contataram outro canal antes.**
  - Entre os **114 pedidos de cancelamento no Call Center** (`desfecho_retencao = 'pedido_cancelamento'`, correspondentes a **90 alunos distintos**), **110 atendimentos (96,49%)** e **88 alunos (97,78%)** tiveram contato anterior em **outro canal fora do Call Center**: **90,35%** passaram antes pelo **WhatsApp** (103 atendimentos / 83 alunos), **87,72%** pela **vídeo chamada** (100 atendimentos / 79 alunos) e **75,44%** pelo **totem** (86 atendimentos / 71 alunos).
  - No recorte restrito aos **66 pedidos de cancelamento atendidos na fila `cra_retencao`** (61 alunos), **62 atendimentos (93,94%)** e **59 alunos (96,72%)** tiveram contato anterior em outro canal.

| Escopo analisado no Call Center | Total atend. (alunos) | Com outro canal anterior (`<> CC`) | Com `whatsapp` anterior | Com `video_chamada` anterior | Com `totem` anterior | Com `call_center` anterior |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Pedido de cancelamento no CC (`114`)** | 114 (90 al.) | **110 (96,49%)** · 88 al. (97,78%) | 103 (90,35%) · 83 al. | 100 (87,72%) · 79 al. | 86 (75,44%) · 71 al. | 81 (71,05%) · 67 al. |
| **Fila `cra_retencao` + pedido de cancelamento (`66`)** | 66 (61 al.) | **62 (93,94%)** · 59 al. (96,72%) | 55 (83,33%) · 54 al. | 52 (78,79%) · 49 al. | 41 (62,12%) · 41 al. | 35 (53,03%) · 35 al. |
| **Fila exata `cra_retencao` (`229`)** | 229 (144 al.) | **214 (93,45%)** · 143 al. (99,31%) | 193 (84,28%) · 138 al. | 188 (82,10%) · 138 al. | 152 (66,38%) · 127 al. | 139 (60,70%) · 121 al. |
| **Todas as 4 filas de retenção (`270`)** | 270 (171 al.) | **255 (94,44%)** · 171 al. (100,00%) | 234 (86,67%) · 168 al. | 228 (84,44%) · 169 al. | 192 (71,11%) · 158 al. | 168 (62,22%) · 147 al. |
| **Assunto retenção no CC (`266`)** | 266 (143 al.) | **257 (96,62%)** · 142 al. (99,30%) | 245 (92,11%) · 136 al. | 233 (87,59%) · 135 al. | 208 (78,20%) · 127 al. | 196 (73,68%) · 127 al. |

---

### Q5 — Comportamento dos alunos que entram em contato em qualquer canal e depois passam pela retenção (`q05_comportamento_antes_retencao.sql`)

#### 5.1. Volume de contatos prévios e tempo até a retenção

| Visão de retenção | Eventos de retenção | Alunos distintos | % eventos com contato prévio | Média de contatos prévios | Mediana de contatos prévios | Tempo médio desde o último prévio (h) | Tempo mediano desde o último prévio (h) |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1. Retenção por fila no CC (`270`)** | 270 | 171 | **95,56%** (258/270) | **13,41** | **11,0** | **6,09 h** | **1,55 h** (~93 min) |
| **2. Retenção por assunto no CC (`266`)** | 266 | 143 | **97,37%** (259/266) | **16,05** | **15,0** | **5,50 h** | **1,58 h** (~95 min) |
| **3. Sensibilidade: assunto em todos os canais (`743`)** | 743 | 173 | **95,56%** (710/743) | **17,36** | **18,0** | **9,30 h** | **2,12 h** (~127 min) |

- **Padrão observado:** antes de chegar à retenção do Call Center, o aluno acumula mediana de **11 a 15 atendimentos anteriores**, e o último contato prévio ocorre com mediana de **1,55 a 1,58 hora** antes da retenção.

#### 5.2. Canais prévios mais acionados antes da retenção

| Canal prévio | Antes da fila de retenção CC (`270`) — contatos prévios distintos (`3.152`) | Antes do assunto de retenção CC (`266`) — contatos prévios distintos (`2.925`) | Antes do assunto de retenção em todos os canais (`743`) — contatos prévios distintos (`4.938`) |
| :--- | :--- | :--- | :--- |
| `video_chamada` | **1.062 (33,69%)** · 169 al. | **909 (31,08%)** · 135 al. | **1.410 (28,55%)** · 173 al. |
| `whatsapp` | **753 (23,89%)** · 168 al. | **699 (23,90%)** · 136 al. | **1.117 (22,62%)** · 173 al. |
| `totem` | **714 (22,65%)** · 158 al. | **673 (23,01%)** · 127 al. | **1.195 (24,20%)** · 173 al. |
| `call_center` | **623 (19,77%)** · 147 al. | **644 (22,02%)** · 127 al. | **1.216 (24,63%)** · 173 al. |

#### 5.3. Principais motivos prévios antes da retenção
1. `Registro de atendimento - Presencial > Acadêmico` (17,89% dos contatos prévios à fila de retenção no CC; 17,30% antes do assunto de retenção no CC).
2. `Registro de atendimento - Presencial > Boleto Mensalidade ou Rematrícula` (11,68% antes da fila no CC; 11,18% antes do assunto no CC).
3. `Totem MDC: JA_SOU_ALUNO` (11,36% antes da fila no CC; 11,45% antes do assunto no CC).
4. `Registro de atendimento - EAD > Acadêmico` (9,04% antes da fila no CC; 8,65% antes do assunto no CC).
5. `Sem Tabulação (Nulo)` no Call Center (7,52% antes da fila no CC; 8,24% antes do assunto no CC).
6. `Registro de atendimento - Presencial > Atendimento de Retenção` (7,01% antes da fila no CC — indicando passagens prévias por retenção via WhatsApp antes da ligação no Call Center).

#### 5.4. Desfechos registrados na retenção

| Desfecho na tabulação (`desfecho_retencao`) | (1) Fila retenção CC (`270`) | (2) Assunto retenção CC (`266`) | (3) Assunto retenção todos os canais (`743`) |
| :--- | :--- | :--- | :--- |
| `pedido_cancelamento` | 69 (25,56%) · 63 al. | **114 (42,86%)** · 90 al. | 210 (28,26%) · 125 al. |
| `aluno_mantido` | 42 (15,56%) · 39 al. | **61 (22,93%)** · 56 al. | **262 (35,26%)** · 157 al. |
| `pedido_transferencia` | 20 (7,41%) · 20 al. | **45 (16,92%)** · 43 al. | 167 (22,48%) · 119 al. |
| `pedido_trancamento` | 18 (6,67%) · 17 al. | **37 (13,91%)** · 35 al. | 93 (12,52%) · 74 al. |
| `rematricula` (vai ou não vai pagar) | 7 (2,59%) · 7 al. | **9 (3,38%)** · 9 al. | 10 (1,35%) · 10 al. |
| `nao_classificado` (em vídeo chamada) | 0 (0,00%) | 0 (0,00%) | 1 (0,13%) · 1 al. |
| Sem assunto de retenção / tabulação nula na fila | 114 (42,22%) · 84 al. | 0 (0,00%) | 0 (0,00%) |

---

### Q6 — Canal de atendimento com a pior nota de pesquisa (`q06_canal_pior_nota.sql`)

- **Resposta:** O **WhatsApp** é o canal com a **pior nota média (`3,89`)** e o **maior percentual de notas ruins (`17,07%` = 84 notas 1 ou 2 em 492 avaliações válidas)**.
- **Observação sobre cobertura amostral:** O **totem** tem apenas **24 respostas válidas em 1.499 contatos (`1,60%` de taxa de resposta)**, com média `4,42` e 2 notas ruins (`8,33%`), amostra reduzida para comparações isoladas.

| Posição (pior nota) | Canal | Total de contatos | Notas válidas (`1–5`) | Sem resposta (`0`) | Sem resposta (`Nula`) | Taxa de resposta (%) | Soma das notas | **Nota média (`SUM/COUNT`)** | Notas ruins (`1–2`) | **% notas ruins** | Distribuição (`N1 / N2 / N3 / N4 / N5`) |
| :---: | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| **1º** | **`whatsapp`** | 1.494 | 492 | 1.002 | 0 | 32,93% | 1.914 | **3,89** | **84** | **17,07%** | 58 / 26 / 38 / 160 / 210 |
| 2º | `totem` | 1.499 | 24 | 1.475 | 0 | **1,60%** | 106 | **4,42** | 2 | 8,33% | 1 / 1 / 3 / 1 / 18 |
| 3º | `call_center` | 1.499 | 661 | 0 | 838 | 44,10% | 3.011 | **4,56** | 48 | 7,26% | 40 / 8 / 25 / 60 / 528 |
| 4º | `video_chamada` | 1.499 | 768 | 731 | 0 | 51,23% | 3.612 | **4,70** | 20 | 2,60% | 14 / 6 / 22 / 110 / 616 |
| — | **Total geral** | **5.991** | **1.945** | **3.208** | **838** | **32,47%** | **8.643** | **4,44** | **154** | **7,92%** | 113 / 41 / 88 / 331 / 1.372 |

---

### Q7 — Perfil de aluno associado a nota de satisfação ruim (`q07_perfil_nota_ruim.sql`)

- **Leitura unidimensional (Call Center + WhatsApp):**
  - **Modalidade:** `1 - Presencial Campus` concentra **98 das 132 notas ruins** dos dois canais cadastrais, com **13,24% de notas ruins** (98/740 válidas) e média **4,14**, contra **8,42% de notas ruins** (32/380) e média **4,53** em `5 - EAD Campus`.
  - **Categoria do aluno:** **calouros (`1 - Calouro`)** e **veteranos (`2 - Veterano`)** apresentam taxas próximas no agregado (calouro **11,80%** = 61/517, média 4,29; veterano **11,16%** = 71/636, média 4,26).
  - **Instituição:** `2 - Anhanguera` concentra o volume com **127 notas ruins em 1.045 respostas válidas (12,15%)** somando Call Center e WhatsApp (no WhatsApp isolado atinge **18,41%** = 81/440, média **3,85**; no Call Center é **7,60%** = 46/605, média **4,55**).
- **Cruzamento completo (`canal` + `modalidade` + `categoria_aluno` + `instituicao`, amostras $\ge 10$ respostas):** mostra que a concentração de notas ruins no perfil presencial da Anhanguera é puxada pelo canal **WhatsApp** (efeito de composição com o canal, já que no WhatsApp o presencial representa 94% dos atendimentos):

| Canal | Modalidade | Categoria | Instituição | Contatos | Respostas válidas | Taxa resp. (%) | Nota média | Notas ruins (`1–2`) | **% notas ruins** | Amostra $\ge 30$? |
| :--- | :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | :---: |
| `whatsapp` | `5 - EAD Campus` | `1 - Calouro` | `2 - Anhanguera` | 26 | 12 | 46,15% | 3,58 | 4 | **33,33%** | Não (`n=12`) |
| **`whatsapp`** | **`1 - Presencial Campus`** | **`1 - Calouro`** | **`2 - Anhanguera`** | **560** | **159** | **28,39%** | **3,78** | **32** | **20,13%** | **Sim** |
| **`whatsapp`** | **`1 - Presencial Campus`** | **`2 - Veterano`** | **`2 - Anhanguera`** | **685** | **262** | **38,25%** | **3,92** | **43** | **16,41%** | **Sim** |
| `call_center` | `1 - Presencial Campus` | `2 - Veterano` | `2 - Anhanguera` | 364 | 145 | 39,84% | 4,48 | 13 | **8,97%** | Sim |
| `call_center` | `5 - EAD Campus` | `1 - Calouro` | `2 - Anhanguera` | 419 | 209 | 49,88% | 4,58 | 17 | **8,13%** | Sim |
| `call_center` | `5 - EAD Campus` | `2 - Veterano` | `2 - Anhanguera` | 321 | 146 | 45,48% | 4,58 | 10 | **6,85%** | Sim |
| `whatsapp` | `1 - Presencial Campus` | `1 - Calouro` | `5 - Unic` | 35 | 17 | 48,57% | 4,29 | 1 | **5,88%** | Não (`n=17`) |
| `call_center` | `1 - Presencial Campus` | `1 - Calouro` | `2 - Anhanguera` | 167 | 90 | 53,89% | 4,64 | 5 | **5,56%** | Sim |
| `call_center` | `7 - EAD Campus PTK` | `2 - Veterano` | `9 - Ampli PTC` | 68 | 13 | 19,12% | 4,62 | 0 | **0,00%** | Não (`n=13`) |

---

### Q8 — Relação entre os pontos da árvore de navegação (`dna_soa`) do Call Center e a nota da pesquisa (`q08_dnasoa_influencia_nota.sql`)

- **Escopo metodológico (associação vs. causalidade):** a análise avalia a **associação estatística** entre a passagem por cada nó da URA (`dna_soa`) e a nota de satisfação no **grão de presença única por contato** (`COUNT(DISTINCT contato_id)` por nó, evitando triplicar o peso de chamadas com passos repetidos). Como os dados são observacionais e a nota é atribuída após o atendimento humano, não se infere relação causal direta da URA sobre a nota.
- **Resultado nos dados:** a nota média varia pouco entre os nós da árvore (entre `4,55` e `4,64`, com notas ruins entre `5,69%` e `7,52%`). A diferença mais visível ocorre na **taxa de resposta à pesquisa**, que cai de **46,40%** nas trilhas padrão em trios para **38,54%** quando há passagem pelo token `99` (e **0,00%** nos 5 contatos com token `98`), além de recuar para **36,04%** nas trilhas muito longas (10 a 14 passos distintos sem repetição consecutiva), faixa em que as notas ruins chegam a **8,75%**.

#### 8.1. Presença única por ponto de navegação no Call Center

| Ponto de navegação (`dna_soa`) | Contatos totais | Contatos com nota | Taxa resp. (%) | Soma das notas | Nota média | Notas ruins (`1–2`) | % notas ruins |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `1 - Identificação via Mailing` | 1.497 | 660 | 44,09% | 3.006 | **4,55** | 48 | **7,27%** |
| `2 - Verifica Chute Ativo` | 1.497 | 660 | 44,09% | 3.006 | **4,55** | 48 | **7,27%** |
| `3 - Verifica Campanha ativa` | 1.497 | 660 | 44,09% | 3.006 | **4,55** | 48 | **7,27%** |
| `4 - Verifica Recencia` | 620 | 281 | 45,32% | 1.303 | **4,64** | 16 | **5,69%** |
| `2 - Identificação Ficeira` | 614 | 266 | 43,32% | 1.209 | **4,55** | 20 | **7,52%** |
| `5 - Cadastra Recencia` | 450 | 210 | 46,67% | 956 | **4,55** | 15 | **7,14%** |
| Token `99` | 410 | 158 | **38,54%** | 720 | **4,56** | 11 | **6,96%** |
| Token `98` | 5 | 0 | **0,00%** | — | — | 0 | — |

#### 8.2. Extensão da trilha (passos sem repetição consecutiva) vs. nota

| Faixa de passos (`dna_soa_sem_repeticao_consecutiva`) | Contatos totais | Contatos com nota | Taxa resp. (%) | Nota média | Notas ruins (`1–2`) | % notas ruins |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| `00 passos (DNA_SOA nulo)` | 2 | 1 | 50,00% | 5,00 | 0 | 0,00% |
| `01_curta (3 passos sem repetição; 9–15 brutos)` | 527 | 241 | 45,73% | **4,48** | 20 | **8,30%** |
| `02_media (4 a 6 passos sem repetição; 12–30 brutos)` | 471 | 219 | 46,50% | **4,62** | 15 | **6,85%** |
| `03_longa (7 a 9 passos sem repetição; 15–36 brutos)` | 277 | 120 | 43,32% | **4,68** | 6 | **5,00%** |
| `04_muito_longa (10 a 14 passos sem repetição; 18–42 brutos)` | 222 | 80 | **36,04%** | **4,44** | 7 | **8,75%** |

---

### Q9 — Agente que gera o maior volume de recontatos do mesmo CPF no mesmo dia (`q09_agente_recontato_mesmo_dia.sql`)

- **Regra de atribuição:** quando o mesmo aluno (`aluno_hash`) realiza um atendimento $k$ e retorna para um novo atendimento $k+1$ no **mesmo dia calendário** (`data_contato`), o recontato é atribuído ao **agente do atendimento $k$ (imediatamente anterior)**.
- **Resultado:**
  - Na **visão A (omnichannel — jornada global, em que o atendimento anterior teve agente humano e o aluno retornou no mesmo dia em qualquer canal)**, o maior volume é do agente **`AG-008`** (`call_center`, hash `bdc0c3eb12fc`, supervisor `SUP-05`), com **200 recontatos no mesmo dia** em 204 atendimentos (**98,04%**), seguido por **`AG-004`** (`192` recontatos em 235 atendimentos, **81,70%**) e **`AG-001`** (`185` recontatos em 185 atendimentos, **100,00%**). *(Filtrando apenas os 3 canais humanos antes do `LAG` — visão A2 —, **`AG-008`** permanece em 1º lugar com **190 recontatos** / 93,14%, seguido por **`AG-001`** com **182** / 98,38%).*
  - Na **visão B (intracanal — retorno ao mesmo canal no mesmo dia)**, o maior volume é do agente **`AG-001`** (`call_center`, hash `26e0082b2d88`, supervisor `SUP-02`), com **173 recontatos intracanal no mesmo dia** em 185 atendimentos (**93,51%**), seguido por **`AG-008`** com **129 recontatos** em 204 atendimentos (**63,24%**).

#### 9.1. Top 10 agentes — visão A (omnichannel: atendimento anterior com agente humano)

| Posição | `agente_id` | `agente_hash` | Canal | Supervisor | Total de atendimentos | **Volume de recontatos no mesmo dia (visão A)** | **Taxa de recontato (%)** | Sub: próximo canal humano | Sub: sequência nos 3 canais humanos (visão A2) | Ref.: recontatos intracanal (visão B) |
| :---: | :---: | :---: | :--- | :---: | ---: | ---: | ---: | ---: | ---: | ---: |
| **1º** | **`AG-008`** | `bdc0c3eb12fc` | `call_center` | `SUP-05` | 204 | **200** | **98,04%** | 174 | 190 (1º na A2) | 129 |
| **2º** | **`AG-004`** | `4550edbbee54` | `call_center` | `SUP-03` | 235 | **192** | **81,70%** | 114 | 127 (4º na A2) | 49 |
| **3º** | **`AG-001`** | `26e0082b2d88` | `call_center` | `SUP-02` | 185 | **185** | **100,00%** | 174 | 182 (2º na A2) | 173 |
| 4º | `AG-002` | `3998c8cb457e` | `call_center` | `SUP-01` | 194 | **184** | 94,85% | 146 | 165 (3º na A2) | 86 |
| 5º | `AG-007` | `99bc73181991` | `call_center` | `SUP-07` | 153 | **128** | 83,66% | 93 | 101 (6º na A2) | 56 |
| 6º | `AG-005` | `5638e1e5f442` | `call_center` | `SUP-04` | 125 | **116** | 92,80% | 85 | 104 (5º na A2) | 60 |
| 7º | `AG-011` | `f36587212293` | `call_center` | `SUP-03` | 153 | **110** | 71,90% | 58 | 64 (9º na A2) | 26 |
| 8º | `AG-121` | `5ce3bc77a2a3` | `whatsapp` | `SUP-NA` | 96 | **87** | 90,63% | 80 | 86 (7º na A2) | 34 |
| 9º | `AG-012` | `fe8d1813f4af` | `call_center` | `SUP-00` | 80 | **79** | 98,75% | 75 | 79 (8º na A2) | 79 |
| 10º | `AG-125` | `6aba04901471` | `whatsapp` | `SUP-NA` | 78 | **70** | 89,74% | 60 | 62 (10º na A2) | 33 |

#### 9.2. Top 10 agentes — visão B (intracanal: retorno ao mesmo canal no mesmo dia)

| Posição | `agente_id` | `agente_hash` | Canal | Supervisor | Total de atendimentos | **Volume de recontatos intracanal (visão B)** | **Taxa de recontato intracanal (%)** | Sub: consecutivo global no mesmo canal |
| :---: | :---: | :---: | :--- | :---: | ---: | ---: | ---: | ---: |
| **1º** | **`AG-001`** | `26e0082b2d88` | `call_center` | `SUP-02` | 185 | **173** | **93,51%** | 134 |
| **2º** | **`AG-008`** | `bdc0c3eb12fc` | `call_center` | `SUP-05` | 204 | **129** | **63,24%** | 57 |
| **3º** | **`AG-002`** | `3998c8cb457e` | `call_center` | `SUP-01` | 194 | **86** | **44,33%** | 42 |
| 4º | `AG-012` | `fe8d1813f4af` | `call_center` | `SUP-00` | 80 | **79** | 98,75% | 44 |
| 5º | `AG-005` | `5638e1e5f442` | `call_center` | `SUP-04` | 125 | **60** | 48,00% | 20 |
| 6º | `AG-007` | `99bc73181991` | `call_center` | `SUP-07` | 153 | **56** | 36,60% | 41 |
| 7º | `AG-004` | `4550edbbee54` | `call_center` | `SUP-03` | 235 | **49** | 20,85% | 35 |
| 8º | `AG-121` | `5ce3bc77a2a3` | `whatsapp` | `SUP-NA` | 96 | **34** | 35,42% | 22 |
| 9º | `AG-003` | `424102217b0e` | `call_center` | `SUP-08` | 64 | **34** | 53,13% | 19 |
| 10º | `AG-125` | `6aba04901471` | `whatsapp` | `SUP-NA` | 78 | **33** | 42,31% | 18 |

---

## 3. Verificações de integridade do modelo Gold

| Verificação | Esperado | Obtido | Status |
| :--- | :--- | :--- | :---: |
| Linhas em `fato_contato` e `fato_jornada` | 5.991 | 5.991 | OK |
| Alunos distintos em `dim_aluno` | 173 | 173 | OK |
| Colunas `aluno_id_original`, `agente_original` e `supervisor_original` na Gold | 0 tabelas | 0 tabelas | OK |
| Unicidade de chave primária nas 11 tabelas Gold (`COUNT(*) == COUNT(DISTINCT pk)`) | 11 / 11 | 11 / 11 | OK |
| Integridade referencial de chaves estrangeiras (`0` órfãos em todos os relacionamentos) | 0 órfãos | 0 órfãos | OK |
| Satisfação global reconciliada (válidas / soma / ruins / zeros / nulas) | 1.945 / 8.643 / 154 / 3.208 / 838 | 1.945 / 8.643 / 154 / 3.208 / 838 | OK |
| Retenção CC reconciliada (fila / assunto / ambos / `cra_retencao` / cancelamento) | 270 / 266 / 156 / 229 / 114 | 270 / 266 / 156 / 229 / 114 | OK |
| Sobreposição estimada em `fato_jornada` (intracanal / intercanal / sem sobreposição) | 308 / 576 / 5.107 | 308 / 576 / 5.107 | OK |
