# Diagnóstico de Inconsistências nos Dicionários de Dados

Este documento registra todas as inconsistências estruturais, tipográficas, conceituais e de integridade identificadas nos 4 dicionários de dados da Cogna Educação durante a Fase 1.

---

## 1. Divergências de Nomenclatura (Dicionário vs Dados Analíticos)

| Canal / Tabela | Campo no Dicionário | Coluna no Dado Analítico | Diagnóstico |
| :--- | :--- | :--- | :--- |
| **Call Center** | `Nota_Pesquisa_1` | `Pesquisa_1` | O dicionário adiciona o prefixo `Nota_`, enquanto a tabela bruta de dados utiliza `Pesquisa_1`. |
| **WhatsApp** | `DNASoa` | `DnaSoa` | Variação de casing (`DNASoa` vs `DnaSoa`). |
| **WhatsApp** | `DurationCallCenter` | `DurationCallCenter` | No dicionário traz formato de hora mas no dado é numérico em segundos. |
| **Vídeo Chamada** | `DurationCallcenter` | `Duração da Chamada` | O dicionário usa o termo técnico em inglês do Call Center (`DurationCallcenter`), mas o dado analítico traz rótulo em português com acento (`Duração da Chamada`). |
| **Vídeo Chamada** | *Arquivo Físico* | `dicionario_video_chamado.csv` | Erro tipográfico no nome do arquivo original (`_video_chamado.csv` com "o" no final, em vez de `_video_chamada.csv`). |

---

## 2. Inconsistências de Conteúdo e Domínio por Canal

### 2.1. WhatsApp (`dicionario_whatsapp.csv`)
1. **Erro de Rotulagem no Domínio de `Categoria_aluno`:**
   - **Código `5`** está rotulado como `"4 - Calouro Presencial e Veterano EAD"`. O código numérico cadastrado é `5`, porém a string do rótulo inicia com o algarismo `4`.
2. **Duplicação de Código em `Instituicao`:**
   - O código **`12`** aparece duplicado exatamente em duas linhas consecutivas:
     - Linha 35: `12; 12- Unopar + Anhanguera`
     - Linha 36: `12; 12- Unopar + Anhanguera`
3. **Regras Lógicas Embutidas no Domínio de `AfterHour`:**
   - O domínio mistura códigos binários (`0 = Não`, `1 = Sim`) com expressões de lógica de banco de dados:
     - Código `0`: `"Se Sigla_FuncionalGroup == 'FHA' então 1"`
     - Código `0`: `"Se Sigla_FuncionalGroup <> 'FHA' então 1"`
4. **Quebras de Linha Embutidas em Descrições (`\n`):**
   - Na descrição do campo `Modalidade`, foram inseridas quebras de linha (`\n\n\n`) dentro do texto entre aspas, fazendo com que o arquivo CSV bruto apresentasse 143 linhas físicas para apenas 81 registros lógicos de dados.
5. **Células Mescladas na Coluna `Campos`:**
   - A coluna `Campos` continha valores preenchidos apenas na primeira ocorrência de cada bloco de domínio, deixando as linhas subsequentes em branco. Corrigido com forward-fill.

### 2.2. Call Center (`dicionario_callcenter.csv`)
1. **Omissão de Campos Críticos da Operação:**
   - O dicionário lista apenas 10 campos, omitindo completamente colunas essenciais presentes na base analítica:
     - `fila_atend` (Fila final de atendimento — coluna central para análise de Retenção).
     - `recepcao_fila` está listada, porém `fila_atend` não possui descrição nem domínio.
     - `Agent` (Nome do atendente — indispensável para a Pergunta 9).
     - `Supervisor`.
     - `Protocolo`.
     - `tabulacao` (Árvore de motivos).
     - `Date`.
2. **Células Mescladas:**
   - A coluna `Campos` demandou forward-fill para associar códigos aos campos `IdType`, `DisconnectType`, `Categoria_Aluno`, `Modalidade` e `Instituicao`.

### 2.3. Vídeo Chamada (`dicionario_video_chamado.csv`)
1. **Cobertura Parcial (apenas 5 de 9 colunas descritas):**
   - O dicionário documenta apenas 5 campos (`Calldate`, `DurationCallcenter`, `Nota Pergunta1`, `TME`, `Agente`).
   - Não há documentação para: `identificador aluno`, `Protocolo`, `tabulacao` e para a coluna extra sem nome (índice 2, contendo data sem milissegundos).
2. **Linhas Vazias Remanescentes no Arquivo Original:**
   - As linhas 7 a 10 do CSV contêm apenas delimitadores vazios (`;;`), derivadas de células mescladas ou formatações vazias do Excel. Foram descartadas na geração do JSON.
3. **Ausência de Estrutura de Domínio:**
   - Possui apenas 2 colunas (`Campos` e `Descrição`), sem códigos discretos.

### 2.4. Totem Presencial (`dicionario_totem.csv`)
1. **Omissão de `identificador aluno`:**
   - O dicionário documenta 6 campos (`DATA_INICIO`, `DURACAO`, `INSTITUICAO`, `MDC`, `NAVEGACAO`, `Nota Pergunta1`), omitindo o campo de identificação cadastral do aluno.
2. **Ausência de Estrutura de Domínio:**
   - Possui apenas 2 colunas (`Campos` e `Descrição`), sem códigos numéricos mapeados.

---

## 3. Ações Corretivas Realizadas no Pipeline da Fase 1

1. **Forward-fill Automatizado:** Implementado no módulo `cogna_etl.dictionaries` para preencher sistematicamente o nome do campo pai em todas as linhas filhas de domínio.
2. **Descarte de Registros Nulos:** Linhas totalmente em branco ou compostas exclusivamente por delimitadores foram suprimidas.
3. **Serialização Canônica JSON:** Dicionários convertidos para a estrutura `{campo: {descricao, dominio: [{codigo, rotulo}]}}` e salvos localmente em `data/dictionaries/` (protegidos contra commit via `.gitignore`).

