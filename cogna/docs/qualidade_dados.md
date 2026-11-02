# Diagnóstico de qualidade dos dados e tratamento da camada Silver

Este documento apresenta o diagnóstico das quatro bases analíticas (`data/raw/analytical_database_callcenter.xlsx` e arquivos CSV correspondentes) e as regras de limpeza e tipagem aplicadas na camada Silver em DuckDB SQL (`sql/staging/00_macros.sql` a `08_silver_totem.sql`).

---

## 1. Inventário das fontes brutas e paridade entre CSV e XLSX

Todos os arquivos CSV foram recebidos em codificação `UTF-8 com BOM` (`utf-8-sig`) e delimitador `;`.

| Arquivo bruto (`data/raw`) | Tamanho | Colunas | Linhas totais | Cabeçalho | Linhas de dados | Aba correspondente no Excel | Status |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- | :---: |
| `analitico_callcenter.csv` | 1.164,8 KB | 22 | 1.500 | 1 | 1.499 | `Analitico call center` | Reconciliado |
| `dicionario_callcenter.csv` | 1,7 KB | 4 | 35 | 1 | 34 | `Dicionario call center` | Reconciliado |
| `analitico_whatsapp.csv` | 828,8 KB | 19 | 1.495 | 1 | 1.494 | `Analitico Whatsapp` | Reconciliado |
| `dicionario_whatsapp.csv` | 6,9 KB | 4 | 81 | 1 | 80 | `Dicionario_whatsapp` | Reconciliado |
| `analitico_video_chamada.csv` | 340,6 KB | 9 | 1.500 | 1 | 1.499 | `Analitico_video_chamada` | Reconciliado |
| `dicionario_video_chamado.csv` | 0,4 KB | 2 | 10 | 1 | 5 (+4 vazias) | `Dicionario_video` | Reconciliado |
| `analitico_totem.csv` | 227,1 KB | 7 | 1.500 | 1 | 1.499 | `Analitico_Totem` | Reconciliado |
| `dicionario_totem.csv` | 0,2 KB | 2 | 7 | 1 | 6 | `Dicionario_Totem` | Reconciliado |

Na comparação célula a célula via hash SHA-256 entre os CSVs exportados e as abas da planilha `.xlsx`:
- **Vídeo chamada:** 1.499 linhas idênticas nas 9 colunas.
- **WhatsApp e totem:** divergência restrita às colunas de data e hora (`calldate` e `DATA_INICIO`), pois os CSVs foram exportados sem os segundos.
- **Call Center:** divergência nas colunas de data (`Date` e `Calldate`) e em 16 linhas da coluna `Protocolo`, nas quais números inteiros longos foram exportados em notação científica (`1,44496E+18`).

Por esse motivo, a camada Bronze mantém a cópia normalizada dos CSVs e a camada Silver lê diretamente as abas da planilha `.xlsx` via `read_xlsx` do DuckDB.

---

## 2. Volumetria de entrada e fórmulas na planilha original

| Canal / aba | Linhas analíticas (XLSX) | Colunas de conteúdo | Fórmulas no XLSX | Fórmulas sem valor em cache | Células com erro | Duplicatas exatas |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Call Center** (`Analitico call center`) | 1.499 | 22 | 7.495 | 0 | 0 | 0 |
| **WhatsApp** (`Analitico Whatsapp`) | 1.494 | 19 | 5.976 | 0 | 0 | 0 |
| **Vídeo chamada** (`Analitico_video_chamada`) | 1.499 | 9 | 1.499 | 0 | 0 | 0 |
| **Totem** (`Analitico_Totem`) | 1.499 | 7 | 0 | 0 | 0 | 0 |
| **Total** | **5.991** | — | **14.970** | **0** | **0** | **0** |

- As colunas descritivas de Call Center (5 colunas) e WhatsApp (4 colunas) contêm fórmulas `=VLOOKUP(...)` apontando para as abas de dicionário.
- Na aba de vídeo chamada, a coluna de índice 2 (`calldate_sem_ms`, sem nome no cabeçalho original) usa a fórmula `=SUBSTITUTE(LEFT(B2,SEARCH(".",B2)-1),"-","/")` para remover os milissegundos.
- Todas as 14.970 células com fórmula possuem valor armazenado em cache e zero erros (`#N/A`, `#VALUE!`, `#REF!`).

---

## 3. Diagnóstico de qualidade por tema

### 3.1. Identificadores de alunos e `IdType`
- O conjunto completo possui **173 alunos únicos**, e todos os 173 aparecem nos quatro canais.
- O campo `identificador_aluno` tem 13 ou 14 dígitos em todos os registros (texto numérico tratado sem *zero-fill* e pseudonimizado em `aluno_hash` via SHA-256 com salt).
- No Call Center, 1.475 registros têm `id_type = 1` (`1 - Cliente identificado por CPF`) e 24 registros têm `id_type = 2` (`2 - Cliente NAO identificado por CPF`), distribuídos em 21 alunos que tiveram atendimentos com e sem identificação por CPF na URA. No WhatsApp, 100% dos 1.494 registros têm `id_type = 1`.

### 3.2. Retenção no Call Center: fila, assunto e encaminhamento
A presença do termo de retenção ocorre em três campos distintos:
1. **Fila de retenção (`eh_retencao_fila`):** `fila_atend` contendo `retenc` = **270 chamadas** (sendo **229** na fila exata `cra_retencao`).
2. **Assunto de retenção (`eh_assunto_retencao`):** `tabulacao` contendo `Atendimento de Retenção` = **266 chamadas**.
3. **Encaminhamento para retenção (`flag_encaminhamento_retencao`):** `tabulacao` contendo `para retenção` = **6 chamadas** (todas atendidas em filas regulares).

Cruzamento entre fila e assunto no Call Center (1.499 chamadas):
- **Ambos (fila = sim e assunto = sim):** 156 atendimentos.
- **Apenas fila de retenção (fila = sim e assunto = não):** 114 atendimentos (todos com tabulação nula na origem).
- **Apenas assunto de retenção (fila = não e assunto = sim):** 110 atendimentos.
- **Nenhum dos dois:** 1.119 atendimentos.

Distribuição dos desfechos nas **266 tabulações com assunto de retenção** no Call Center:
- Solicitação de cancelamento (`pedido_cancelamento`): **114** (42,86%)
- Aluno mantido (`aluno_mantido`): **61** (22,93%)
- Solicitação de transferência (`pedido_transferencia`): **45** (16,92%)
- Solicitação de trancamento (`pedido_trancamento`): **37** (13,91%)
- Não vai pagar rematrícula (`rematricula`): **6** (2,26%)
- Vai pagar rematrícula (`rematricula`): **3** (1,13%)

### 3.3. Formatos de protocolo
- **Call Center:** 469 protocolos nulos (31,29%) e 1.030 preenchidos:
  - Padrão `CS########` (`cs`): **971**
  - Padrão `EDU` (`edu`): **32**
  - Ponto flutuante / notação científica no XLSX (`notacao_cientifica`): **12**
  - Inteiros numéricos no XLSX (`numerico`): **9**
  - Texto `"CRA_RETENÇÃO"` (`cra_retencao`): **5** (marcados em `flag_retencao_protocolo`)
  - Prefixo `S########` (`prefixo_s`): **1**
- **Vídeo chamada:** 1.499 protocolos (100%) no padrão `CS########`.
- **WhatsApp e totem:** não possuem coluna de protocolo.

### 3.4. Pesquisas de satisfação

| Canal | Total de linhas | Nulos na origem | Zeros (premissa) | Notas válidas {1..5} | Texto não numérico | Fora de escala ou fração | Média dos respondidos | % notas ruins {1, 2} | Taxa de resposta |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **Call Center** | 1.499 | 838 | 0 | 661 | 0 | 0 | 4,56 | 7,26% (48) | 44,10% |
| **WhatsApp** | 1.494 | 0 | 1.002 | 492 | 0 | 0 | 3,89 | 17,07% (84) | 32,93% |
| **Vídeo chamada** | 1.499 | 0 | 731 | 768 | 0 | 0 | 4,70 | 2,60% (20) | 51,23% |
| **Totem** | 1.499 | 0 | 1.475 | 24 | 0 | 0 | 4,42 | 8,33% (2) | 1,60% |
| **Total** | **5.991** | **838** | **3.208** | **1.945** | **0** | **0** | **4,44** | **7,92% (154)** | **32,47%** |

- A média geral (**4,44**) corresponde à soma global das notas válidas (`8.643` = `3.011 + 1.914 + 3.612 + 106`) dividida pelo total de respostas válidas (`1.945`).
- O percentual de notas ruins (**7,92%**) equivale a `154 / 1.945`, e a taxa geral de resposta (**32,47%**) equivale a `1.945 / 5.991`.

### 3.5. Tempos operacionais (TME vs. duração) e outliers (IQR 1,5)
- **WhatsApp:** 1.494 registros válidos. Duração média de `7.089,6 s` (mediana `6.285,0 s`, mín. `586,0 s`, máx. `26.286,0 s`) e TME médio de `2.938,3 s` (mediana `1.808,0 s`, mín. `1,0 s`, máx. `14.870,0 s`). Em **64 atendimentos** (4,28%), o TME supera a duração registrada (`flag_tme_maior_duracao`).
- **Vídeo chamada:** 1.499 registros válidos. Duração média de `824,3 s` (mediana `677,0 s`, mín. `45,0 s`, máx. `4.524,0 s`) e TME médio de `37,3 s` (mediana `4,0 s`, mín. `1,0 s`, máx. `3.812,0 s`). Em **4 chamadas** (0,27%), o TME supera a duração.
- **Call Center:** 1.499 registros de duração (média `831,9 s`, mediana `700,0 s`, mín. `3,0 s`, máx. `4.073,0 s`), sem coluna de TME.
- **Totem:** 1.499 registros de duração (média `37,0 s`, mediana `32,0 s`, mín. `0,0 s`, máx. `222,0 s`, sendo **183** com duração igual a zero), sem coluna de TME.

Limites superiores de outlier pelo critério de Tukey ($Q_3 + 1{,}5 \times \text{IQR}$) calculados na Silver:

| Canal e métrica | Q1 | Q3 | Limite superior | Registros sinalizados (`flag_outlier_*`) |
| :--- | ---: | ---: | ---: | ---: |
| Call Center — duração | 374,50 | 1.118,00 | 2.233,25 | 55 |
| WhatsApp — duração | 3.937,25 | 9.514,50 | 17.880,38 | 18 |
| WhatsApp — TME | 11,75 | 4.882,25 | 12.188,00 | 5 |
| Vídeo chamada — duração | 464,00 | 1.016,50 | 1.845,25 | 81 |
| Vídeo chamada — TME | 3,00 | 9,00 | 18,00 | 338 |
| Totem — duração | 9,00 | 54,50 | 122,75 | 26 |

### 3.6. Trilha de navegação (`dna_soa`) e sobreposição temporal
- No Call Center, `dna_soa` tem 2 registros nulos e 1.497 preenchidos (68 caminhos distintos). Em 100% dos preenchidos há repetição consecutiva de passos, sendo **1.082** (72,28%) compostos por trios consecutivos idênticos. O token exato `98` aparece em **5** contatos e o token `99` em **410** contatos (união = **415** contatos, interseção = 0).
- Avaliando os 5.818 pares consecutivos de atendimentos do mesmo aluno no tempo, **884 pares** (15,20%) apresentam sobreposição estimada entre início + duração do atendimento $k$ e o início do atendimento $k+1$ (sendo **308** no mesmo canal e **576** entre canais diferentes).

---

## 4. Reconciliação da camada Silver (`data/silver/silver_*.parquet`)

Nenhuma linha é descartada na camada Silver: todas as anomalias são tratadas por tipagem segura e colunas de sinalização.

| Indicador de reconciliação | Esperado (XLSX / profiling) | Obtido na Silver |
| :--- | :--- | :--- |
| Linhas por canal (CC / WA / vídeo / totem / total) | 1.499 / 1.494 / 1.499 / 1.499 / 5.991 | 1.499 / 1.494 / 1.499 / 1.499 / 5.991 |
| `contato_id` únicos | 5.991 | 5.991 |
| `aluno_hash` distintos (presentes nos 4 canais) | 173 | 173 |
| Notas válidas 1–5 (CC / WA / vídeo / totem / total) | 661 / 492 / 768 / 24 (1.945) | 661 / 492 / 768 / 24 (1.945) |
| Soma das notas válidas (total) | 3.011 / 1.914 / 3.612 / 106 (8.643) | 3.011 / 1.914 / 3.612 / 106 (8.643) |
| Notas ruins 1–2 (total) | 48 / 84 / 20 / 2 (154) | 48 / 84 / 20 / 2 (154) |
| Retenção CC: fila / assunto / encaminhamento | 270 / 266 / 6 | 270 / 266 / 6 |
| Retenção CC: ambos / só fila / só assunto / nenhum | 156 / 114 / 110 / 1.119 | 156 / 114 / 110 / 1.119 |
| Filas CC: coincidentes / divergentes (`recepcao_fila` vs. `fila_atend`) | 1.295 / 204 | 1.295 / 204 |
| Desfechos dos 266 assuntos no CC (cancel. / mantido / transf. / tranc. / rematr.) | 114 / 61 / 45 / 37 / 9 | 114 / 61 / 45 / 37 / 9 |
| Protocolo CC: nulo / CS / EDU / not. científ. / numérico / CRA / prefixo S | 469 / 971 / 32 / 12 / 9 / 5 / 1 | 469 / 971 / 32 / 12 / 9 / 5 / 1 |
| Divergência de modalidade no 1º nível da tabulação (CC / WA) | 19 / 46 | 19 / 46 |
| Conflito de domínio em `AfterHour` no WhatsApp (`flag_dominio_inconsistente`) | 1.494 | 1.494 |
