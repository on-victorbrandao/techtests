# Registro de Decisões e Premissas do Projeto (ADR)

Este documento registra todas as decisões arquiteturais, premissas de negócio e escolhas de engenharia adotadas durante o desenvolvimento do Teste Técnico da Cogna Educação.

---

## DEC-001: Arquitetura Medallion Local com DuckDB, Parquet e Python
- **Data:** 01/11/2026
- **Status:** Aprovada
- **Contexto:** Necessidade de construir um pipeline de ETL/ELT robusto em Python + SQL sem depender de servidores pagos ou infraestrutura em nuvem restrita.
- **Decisão:** Arquitetura Medallion local em 4 camadas:
  1. `data/raw`: Arquivos originais em modo somente leitura (imutáveis).
  2. `data/bronze`: Arquivos CSV normalizados (cabeçalhos em snake_case) e dicionários estruturados em JSON (`data/dictionaries`).
  3. `data/silver`: Tabelas tratadas e tipadas em formato Parquet (colunas padronizadas, deduplicação exata, flags de qualidade, pseudonimização LGPD).
  4. `data/gold`: Modelo estrela relacional gerado via DuckDB SQL e exportado em Parquet (Snappy) + CSV delimitado por `;` (UTF-8 com BOM).
- **Consequências:** Processamento veloz e vetorizado, reprodutibilidade em qualquer máquina local e consumo limpo no Power BI sem necessidade de transformações em M no Power Query.

---

## DEC-002: Reconciliação Inicial dos Dados Brutos (CSV vs XLSX)
- **Data:** 01/11/2026
- **Status:** Aprovada
- **Contexto:** Comparação de integridade entre os 8 arquivos CSV brutos e suas respectivas abas na planilha `analytical_database_callcenter.xlsx`.
- **Decisão:**
  - O arquivo `analytical_database_callcenter.dicionario_whatsapp.csv` possui 143 linhas físicas de texto devido a quebras de linha (`\n`) embutidas em campos descritivos entre aspas. O parser lógico (`csv.reader`) decodifica com exatidão 81 registros, idêntico aos 81 registros da aba correspondente no Excel.
  - O arquivo `analytical_database_callcenter.dicionario_video_chamado.csv` possui 10 linhas no CSV e 10 linhas no Excel, sendo as 4 últimas linhas vazias/nulas originárias da planilha de origem.
  - Todas as 8 tabelas/abas foram reconciliadas com zero perda de registros e colunas.

---

## DEC-003: Premissas Padrão de Negócio (Seção 5 do PLANO_MESTRE)
- **Data:** 01/11/2026
- **Status:** Premissa adotada, pendente de resposta da Cogna
- **Premissas aplicadas:**
  1. **Identificador do Aluno, LGPD e Agentes:** O campo `identificador_aluno` será tratado como texto pseudonimizado via hash SHA-256 com salt configurável via `.env` (`aluno_hash`). Exibição nas telas e visuais analíticos restrita a `aluno_hash`. A pergunta 9 exige comparar agentes; exibir seus nomes completos não é uma exigência explícita (podendo ser utilizado identificador anonimizado ou pseudonimizado).
  2. **Conceito de Recontato Posterior:** Por padrão, qualquer atendimento do mesmo aluno cronologicamente posterior dentro do período histórico é considerado recontato posterior. Sensibilidades adicionais para janelas de 24h e 7 dias serão disponibilizadas.
  3. **Identificação de Retenção:** Retenção será identificada tanto pela fila de atendimento (`fila_atend` contendo `retenc`) quanto pela tabulação (`eh_retencao_tabulacao` com texto "Atendimento de Retenção"), reportando as duas métricas lado a lado nas análises de negócio (Q4 e Q5).
  4. **Nota de Pesquisa:** Resposta `0` ou nula é classificada como `respondeu_pesquisa = false` e excluída do cálculo de nota média, mantendo a métrica de Taxa de Resposta visível em paralelo. Notas 1 e 2 são classificadas como "nota ruim".
  5. **Atribuição de Recontato ao Agente (Q9):** Recontato no mesmo dia é computado quando o mesmo aluno retorna no mesmo dia calendário, atribuindo o recontato ao agente que realizou o atendimento imediatamente anterior.
  6. **WhatsApp - Duração e TME:** Tratados e padronizados na unidade de segundos (`int`).
  7. **Modalidade Divergente da Tabulação:** Caso a modalidade cadastral divirja do texto da tabulação (ex.: Presencial vs EAD), prevalece o dado cadastral do aluno; a divergência será sinalizada através de uma flag booleana (`flag_divergencia_modalidade`).

---

## DEC-004: Definição das Fontes de Dados para as Camadas Bronze e Silver
- **Data:** 01/11/2026
- **Status:** Aprovada
- **Contexto:** Na exportação manual das abas do Excel para CSV, houve perda de precisão em timestamps (omissão dos segundos em WhatsApp, Totem e Call Center) e em 16 números de protocolo no Call Center (convertidos para notação científica `1,44496E+18` pelo Excel no locale pt-BR). A planilha `analytical_database_callcenter.xlsx` preserva os segundos e o float numérico completo desses protocolos.
- **Decisão:**
  1. **Referência da Bronze:** Os CSVs exportados são a referência exclusiva da camada Bronze (`data/bronze/`), garantindo fidelidade estrita aos arquivos CSV brutos recebidos.
  2. **Fonte Oficial da Silver:** A planilha original `analytical_database_callcenter.xlsx` é a fonte oficial dos timestamps e dos valores numéricos com precisão preservada.
  3. **Ingestão na Silver:** Na camada Silver, a leitura será realizada diretamente das abas analíticas do XLSX, aplicando o mapeamento padronizado de colunas em `snake_case` já definido no projeto. O XLSX preserva o valor nele armazenado, mas não garante recuperação de todos os dígitos originais dos protocolos numéricos.
  4. **Proibição de Join por Aluno para Restaurar Horários:** Fica vedada a tentativa de enriquecer os CSVs via join baseado apenas no `identificador_aluno`, uma vez que um mesmo aluno possui múltiplos registros no histórico.
  5. **Imutabilidade Raw:** Nenhum arquivo bruto em `data/raw/` será alterado.
  6. **Reconciliação e Diferenças Esperadas (Silver vs Bronze/XLSX):**
     - A entrada da Silver será reconciliada com o XLSX. Qualquer redução posterior terá regra e contagem documentadas.
     - Quantidade de linhas e identificadores de aluno de entrada serão exatamente iguais entre XLSX e Silver.
     - As colunas de data/hora na Silver conterão os segundos preservados da planilha original (enquanto na Bronze os segundos estavam ausentes nos CSVs de Call Center, WhatsApp e Totem).
     - Os 16 protocolos com notação científica na Bronze serão carregados com os valores numéricos do XLSX na Silver, ciente de que o XLSX preserva o valor nele armazenado, mas não garante recuperação de todos os dígitos originais dos protocolos numéricos que já sofreram perda de precisão no armazenamento de ponto flutuante.
