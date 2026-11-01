# Diagnóstico de inconsistências nos dicionários de dados

Este documento registra as inconsistências estruturais, tipográficas e de domínio identificadas nos quatro dicionários de dados da Cogna Educação.

---

## 1. Divergências de nomenclatura (dicionário vs. dados analíticos)

| Canal / tabela | Campo no dicionário | Coluna no dado analítico | Diagnóstico |
| :--- | :--- | :--- | :--- |
| **Call Center** | `Nota_Pesquisa_1` | `Pesquisa_1` | O dicionário adiciona o prefixo `Nota_`, enquanto a tabela bruta de dados utiliza `Pesquisa_1`. |
| **WhatsApp** | `DNASoa` | `DnaSoa` | Variação de caixa (`DNASoa` vs. `DnaSoa`). |
| **WhatsApp** | `DurationCallCenter` | `DurationCallCenter` | No dicionário consta formato de hora, mas no dado analítico o campo é numérico em segundos. |
| **Vídeo chamada** | `DurationCallcenter` | `Duração da Chamada` | O dicionário usa o nome em inglês do Call Center (`DurationCallcenter`), mas a tabela traz o rótulo em português (`Duração da Chamada`). |
| **Vídeo chamada** | *Arquivo físico* | `dicionario_video_chamado.csv` | Erro de grafia no nome do arquivo original (`_video_chamado.csv` em vez de `_video_chamada.csv`). |

---

## 2. Inconsistências de conteúdo e domínio por canal

### 2.1. WhatsApp (`dicionario_whatsapp.csv`)
1. **Divergência no domínio de `Categoria_aluno`:**
   - O código `5` está rotulado como `"4 - Calouro Presencial e Veterano EAD"` (o código cadastrado é `5`, mas o texto do rótulo começa com `4`).
2. **Duplicação de código em `Instituicao`:**
   - O código `12` aparece duplicado em duas linhas consecutivas:
     - Linha 35: `12; 12- Unopar + Anhanguera`
     - Linha 36: `12; 12- Unopar + Anhanguera`
3. **Regras condicionais misturadas no domínio de `AfterHour`:**
   - O domínio mistura códigos binários (`0 = Não`, `1 = Sim`) com expressões condicionais na chave `0`:
     - Código `0`: `"Se Sigla_FuncionalGroup == 'FHA' então 1"`
     - Código `0`: `"Se Sigla_FuncionalGroup <> 'FHA' então 1"`
4. **Quebras de linha embutidas em descrições (`\n`):**
   - Na descrição do campo `Modalidade`, há quebras de linha (`\n\n\n`) dentro do texto entre aspas, fazendo com que o CSV bruto tenha 143 linhas físicas para 81 registros lógicos.
5. **Células mescladas na coluna `Campos`:**
   - A coluna `Campos` vem preenchida apenas na primeira linha de cada bloco de domínio, deixando as linhas seguintes em branco. Tratado com preenchimento progressivo (*forward-fill*).

### 2.2. Call Center (`dicionario_callcenter.csv`)
1. **Omissão de colunas presentes na base analítica:**
   - O dicionário lista 10 campos e não documenta sete colunas da tabela analítica:
     - `fila_atend` (fila de atendimento, usada na identificação de retenção)
     - `Agent` (nome do atendente, usado na análise de recontatos)
     - `Supervisor`
     - `Protocolo`
     - `tabulacao` (árvore de motivos)
     - `Date`
2. **Células mescladas:**
   - A coluna `Campos` exigiu *forward-fill* para associar os códigos aos campos `IdType`, `DisconnectType`, `Categoria_Aluno`, `Modalidade` e `Instituicao`.

### 2.3. Vídeo chamada (`dicionario_video_chamado.csv`)
1. **Cobertura parcial (5 de 9 colunas descritas):**
   - O dicionário documenta apenas `Calldate`, `DurationCallcenter`, `Nota Pergunta1`, `TME` e `Agente`.
   - Não há descrição para `identificador aluno`, `Protocolo`, `tabulacao` nem para a coluna sem nome de índice 2 (`calldate_sem_ms`).
2. **Linhas vazias no final do arquivo:**
   - As linhas 7 a 10 do CSV contêm apenas delimitadores vazios (`;;`) originados da planilha e são descartadas na conversão para JSON.
3. **Estrutura sem tabela de domínio:**
   - Possui apenas duas colunas (`Campos` e `Descrição`), sem códigos discretos.

### 2.4. Totem presencial (`dicionario_totem.csv`)
1. **Omissão de `identificador aluno`:**
   - O dicionário documenta seis campos (`DATA_INICIO`, `DURACAO`, `INSTITUICAO`, `MDC`, `NAVEGACAO` e `Nota Pergunta1`), omitindo o identificador do aluno.
2. **Estrutura sem tabela de domínio:**
   - Possui apenas duas colunas (`Campos` e `Descrição`), sem códigos numéricos mapeados.

---

## 3. Tratamento aplicado no pipeline

1. **Preenchimento progressivo (*forward-fill*):** implementado em `cogna_etl.dictionaries` para propagar o nome do campo pai às linhas de domínio.
2. **Descarte de linhas vazias:** registros compostos apenas por delimitadores vazios são ignorados na leitura.
3. **Exportação em JSON:** dicionários estruturados salvos localmente em `data/dictionaries/` e consumidos pelos scripts SQL da camada Silver (`sql/staging/02_dic_dominio.sql` e `04_dominio_canonico.sql`) sem multiplicação de linhas.
