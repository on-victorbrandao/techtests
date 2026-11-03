# Guia de UI/UX e design system — Cogna Educação

Este documento reúne a especificação visual, os tokens de design, o mapa das 9 perguntas de negócio e a arquitetura para o visual HTML Content do dashboard executivo no Power BI.

---

## 1. Identidade visual oficial da Cogna Educação

Extraído diretamente do portal oficial ([cogna.com.br](https://www.cogna.com.br/)):

### Paleta institucional de cores

| Token de cor | Código HEX | RGB | Aplicação no dashboard |
| :--- | :--- | :--- | :--- |
| **Cogna Purple (Primária)** | `#5219A1` | `rgb(82, 25, 161)` | Cor principal da marca, cabeçalhos, barra lateral ativa, botões primários |
| **Electric Purple (Destaque)** | `#7433DA` | `rgb(116, 51, 218)` | Acentos interativos, gradientes de destaque, linhas principais |
| **Vibrant Violet (Ação)** | `#8038F0` | `rgb(128, 56, 240)` | Hover, foco, indicadores ativos de transição |
| **Cogna Gold (Secundária)** | `#FFAD01` | `rgb(255, 173, 1)` | Alertas moderados, barras de destaque financeiro, contraste visual |
| **Midnight Navy (Neutro escuro)** | `#28114B` | `rgb(40, 17, 75)` | Fundo da sidebar escura (quando em dark mode), títulos de alto peso |
| **Surface Dark (Texto título)** | `#151D48` | `rgb(21, 29, 72)` | Textos principais, valores numéricos de KPIs (alto contraste) |
| **Text Secondary (Subtítulo)** | `#737791` | `rgb(115, 119, 145)` | Rótulos de cartões, legendas, categorias e cabeçalhos de tabela |
| **Canvas Background** | `#FAFBFC` | `rgb(250, 251, 252)` | Fundo geral da tela do relatório (off-white suave, descanso visual) |
| **Card Surface** | `#FFFFFF` | `rgb(255, 255, 255)` | Superfície dos cards analíticos com cantos arredondados de 16px |
| **Border & Divider** | `#F0F2F7` | `rgb(240, 242, 247)` | Linhas de grade e separadores sutis |
| **Success Mint** | `#0BB783` | `rgb(11, 183, 131)` | Indicadores positivos, taxas de retenção, metas batidas |
| **Critical Rose** | `#EF4444` | `rgb(239, 68, 68)` | Notas ruins, pedidos de cancelamento, alertas críticos |
| **Omni Blue** | `#0095FF` | `rgb(0, 149, 255)` | Canal WhatsApp e fluxos digitais |

### Tipografia oficial

1. **Títulos, cabeçalhos e números grandes:**
   - Família: `Poppins, 'Segoe UI', Arial, sans-serif`
   - Pesos: `600 (SemiBold)` e `700 (Bold)`
2. **Corpo de texto, rótulos e tabelas:**
   - Família: `Roboto, 'Segoe UI', Arial, sans-serif`
   - Pesos: `400 (Regular)` e `500 (Medium)`
3. **Códigos e identificadores (Hash de aluno, IDs de contato):**
   - Família: `'JetBrains Mono', 'Consolas', monospace`

---

## 2. Estrutura do layout (baseada no protótipo opção 1)

O layout segue o estilo moderno de SaaS executivo com proporção widescreen:

1. **Barra lateral esquerda (Sidebar de navegação):**
   - Largura fixa: `260px` a `300px` em desktop.
   - Fundo branco (`#FFFFFF`) com linha divisória suave à direita (`#F0F2F7`).
   - Logotipo da Cogna no topo (`160px` de largura).
   - Menu em formato de pílulas (`rx: 14px`):
     - Item ativo com preenchimento em roxo institucional (`#5219A1`), texto branco e ícone SVG embutido.
     - Itens inativos com texto neutro secundário (`#737791`) e efeito hover suave (`#F7F1FF`).

2. **Área superior de controle (Top bar):**
   - Título da visão atual (ex.: `Visão Executiva Omnichannel | Atendimento & Retenção`).
   - Campo visual de busca rápida.
   - Tag de identificação do usuário e perfil (`Victor | Analista de Dados Sênior`).

3. **Área central de métricas (Cards de KPI):**
   - 4 blocos de indicadores com micro-fundos temáticos:
     - **Card 1 (Volumetria Total):** Fundo suave `#F7F1FF`, badge com ícone `#5219A1`, total de contatos e variação.
     - **Card 2 (Alunos Distintos):** Fundo suave `#FFF4DE`, badge com ícone `#FFAD01`, contagem de alunos únicos.
     - **Card 3 (Nota Média CSAT):** Fundo suave `#DCFCE7`, badge com ícone `#0BB783`, nota média ponderada (1 a 5).
     - **Card 4 (Taxa de Retenção):** Fundo suave `#FFE2E5`, badge com ícone `#EF4444`, percentual de retenção e cancelamento.

4. **Grade de visualização dos objetivos de negócio (Q1 a Q9):**
   - **Q1 e Q2 (Fluxo de transição omnichannel):** Gráfico de transição e barras empilhadas mostrando passagem de Call Center para WhatsApp e terceiros canais.
   - **Q3 (Matriz de motivos):** Gráfico de barras horizontais com os principais motivos por canal.
   - **Q4 e Q5 (Jornada de retenção):** Indicador de contatos prévios antes da retenção e tempo mediano de recontato (1,55 h).
   - **Q6 e Q7 (Diagnóstico de satisfação):** Comparativo de notas médias por canal (destaque para o Totem como pior nota) e perfil de alunos insatisfeitos.
   - **Q8 (Navegação URA / Ponto SOA):** Ranking dos nós com maiores volumes de nota ruim (suporte financeiro e cobrança).
   - **Q9 (Atribuição de recontatos no mesmo dia):** Tabela executiva com ranking dos agentes com maior volume e taxa de recontatos.

---

## 3. Matriz de respostas de negócio no dashboard

| Pergunta | Indicador principal | Medida DAX correspondente | Componente visual no dashboard |
| :--- | :--- | :--- | :--- |
| **Q1** | Alunos CC com WA posterior | `[#01_Q1_Alunos_Call_Center_WhatsApp_Posterior]` | Card de funil + percentual de migração (100% dos alunos, 93,6% dos contatos) |
| **Q2** | Trinca consecutiva CC → WA → Outro | `[#11_Q2_Alunos_Trinca_CC_WA_Outro_Canal]` | Card comparativo de sequências (138 alunos consecutivos, 173 na jornada ampla) |
| **Q3** | Principais motivos por canal | `[#01_Total_Contatos]` por `dim_motivo[motivo_principal]` | Gráfico de barras horizontais ordenado por volume de atendimentos |
| **Q4** | Perfil do aluno na retenção | `[#20_%_Fila_Retencao_Com_Outro_Canal_Anterior]` | Card de alerta (94,44% passaram antes por outro canal; 96,49% nos cancelamentos) |
| **Q5** | Comportamento pré-retenção | `[#23_Tempo_Mediano_Desde_Ultimo_Contato_Ate_Retencao_h]` | Medidor de tempo mediano (1,55 h) + mediana de contatos prévios (11 contatos) |
| **Q6** | Canal com pior nota | `[#04_Nota_Media_Satisfacao]` por canal | Gráfico de colunas com badge de destaque no Totem (nota 2,96 vs 4,37 no Call Center) |
| **Q7** | Perfil com nota ruim | `[#06_%_Notas_Ruins]` por perfil e polo | Gráfico de rosca/barras destacando calouros e polos de maior insatisfação |
| **Q8** | Influência da URA na nota | `[#06_Q8_%_Notas_Ruins_Ponto_Navegacao]` | Tabela analítica com os nós críticos da URA e % de notas ruins |
| **Q9** | Recontato no mesmo dia por agente | `[#20_Q9_Recontatos_Mesmo_Dia_Omnichannel]` | Tabela de classificação dos agentes por volume e taxa de recontato |

---

## 4. Arquitetura do visual HTML Content

O visual customizado **HTML Content** renderiza o dashboard dinamicamente através de medidas DAX que geram marcação HTML5/CSS3 pura:

### Princípios da implementação

1. **Reatividade a filtros:** O DAX calcula os valores dentro do contexto de avaliação das dimensões selecionadas (datas, canais, polos, perfis) e interpola as strings no código HTML.
2. **Gráficos em SVG embutido:** Gráficos de barras, roscas e sparklines são gerados como elementos `<svg>` nativos com vetores responsivos, dispensando bibliotecas externas pesadas e garantindo renderização instantânea no Power BI Desktop e Web.
3. **Cards e containers padronizados:** Uso de CSS Flexbox e Grid com classes utilitárias para alinhamento e espaçamento limpo:
   - `border-radius: 16px;`
   - `box-shadow: 0px 4px 20px rgba(0, 0, 0, 0.04);`
   - `background: #FFFFFF;`
   - `padding: 20px;`

---

## 5. Como aplicar o tema oficial no Power BI Desktop

1. No Power BI Desktop, clique na guia **Exibição** (View) no menu superior.
2. No grupo **Temas**, clique na seta para baixo para expandir a galeria de temas.
3. Clique em **Procurar temas** (Browse for themes).
4. Navegue até a pasta do projeto:
   `c:\Users\victo\OneDrive\Documentos\learning-work\test\cogna\powerbi\theme\`
5. Selecione o arquivo `cogna_theme.json` e clique em **Abrir**.
6. Uma mensagem confirmará que o tema foi importado com sucesso. Todos os novos visuais seguirão a paleta e a tipografia oficiais da Cogna Educação.
