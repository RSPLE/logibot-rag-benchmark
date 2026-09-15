# logibot-rag-benchmark

Análise comparativa de 4 estratégias de RAG (Retrieval-Augmented Generation) usadas pelo **LogiBot**, um chatbot educacional de lógica de programação, testadas em campo com alunos reais.

## O experimento

Foram realizados testes cegos em 4 dias, com alunos de duas instituições:

| Dia | Instituição   | Turma    |
|-----|---------------|----------|
| 1   | Gaspar Viana  | Turma A  |
| 2   | Gaspar Viana  | Turma B  |
| 3   | IFPA          | Turma A  |
| 4   | IFPA          | Turma B  |

Em cada dia, os alunos foram divididos igualmente em 4 grupos, cada um usando uma condição diferente de RAG, sem saber qual estavam usando:

- **none** — Sem RAG (baseline)
- **context** — Context RAG
- **self** — Self RAG
- **hybrid** — Hybrid RAG

Cada aluno conversou livremente com o chatbot e respondeu quizzes de lógica de programação (assuntos: *Estruturas de Repetição*, *Vetores, Matrizes e Arrays*, *linguagem Python*). O objetivo é comparar as 4 condições em métricas de aprendizado (acerto no quiz) e de comportamento do RAG (taxa de recuperação, score de recuperação, tempo de resposta, tokens usados).

## Dados

Os dados brutos vêm de um dump PostgreSQL (`logibot-db.sql`, não versionado) extraído para dois arquivos JSON em `data/`:

- **`data/logibot-data.json`** — dados prontos para gráficos, sem texto de mensagens:
  - `students[]`: um registro por aluno ativo (74 no total) — instituição, dia, turma, grupo, `rag_mode`, tempo ativo de chat, acertos/erros, contagem de mensagens, tópicos abordados. Veja a ressalva sobre `total_usage_time_sec` abaixo.
  - `quiz_answers[]`: uma linha por pergunta de quiz respondida (assunto, opção escolhida, acerto/erro).
  - `chat_message_metrics[]`: uma linha por resposta do assistente (provider, nº de chunks recuperados, score de recuperação, tempo de resposta, tokens) — sem o texto da mensagem.
  - `summary_by_condition[]` / `summary_by_condition_and_day[]`: métricas já agregadas por modo de RAG (e por dia), prontas para gráfico de barras comparativo.
- **`data/logibot-chat-messages.json`** — todas as mensagens de chat com texto completo (pergunta do aluno + resposta da IA) e os trechos recuperados pelo RAG, para análise qualitativa.

Ambos são gerados a partir do dump por [`scripts/parse_logibot.py`](scripts/parse_logibot.py):

```bash
python3 scripts/parse_logibot.py
```

### Exclusões aplicadas

- **Escola de Testes de Carga** (turmas `K6LOAD-*`, 3 contas): dados de teste de carga técnico (k6) do sistema, não são alunos reais.
- **20 contas de aluno sem nenhuma atividade**: contas criadas para um número esperado de participantes, mas que nunca chegaram a usar a plataforma (sem sessão de chat, sem quiz, sem tópico registrado).

Sobram **74 alunos reais** distribuídos nos 4 dias × 4 grupos.

### Ressalva: tempo de uso

O campo `total_usage_time` do próprio app (tabela `user_analyses`) está **zerado em 58% dos alunos ativos** (43 de 74) — inclusive contas com chat e quiz reais registrados. É uma falha de instrumentação na origem, não um problema na extração. Por isso, `students[].total_usage_time_sec` é mantido no JSON só por transparência, mas **não é usado nos gráficos**.

Em vez disso, `students[].active_chat_time_sec` é calculado por [`scripts/parse_logibot.py`](scripts/parse_logibot.py) a partir dos timestamps reais das mensagens: para cada sessão de chat, é o intervalo entre a primeira e a última mensagem, sem descontar tempo parado. Esse cálculo só é possível para os 60 alunos que têm sessão de chat registrada — os outros 14 alunos ativos só fizeram quiz, sem chat.

**Sem teto por intervalo, esse número é dominado por outliers**: um aluno que deixou a aba aberta por horas entre duas mensagens conta esse tempo todo como "chat", o que infla bastante a média em grupos pequenos (ex.: em "Sem RAG", uma única sessão de ~10h por um aluno já puxa a média do grupo para quase 400 min). Leia o gráfico de tempo de chat com essa ressalva em mente — ele reflete o intervalo bruto entre primeira e última mensagem, não necessariamente tempo de uso ativo.

## Gráficos

Gerados a partir de `data/logibot-data.json` por [`scripts/generate_charts.py`](scripts/generate_charts.py) e salvos como PNG em `charts/`, organizados por tema. As 4 condições usam sempre a mesma cor em todos os gráficos (azul = Sem RAG, laranja = Context RAG, verde = Self RAG, amarelo = Hybrid RAG), para facilitar a comparação visual entre eles.

📖 **[Guia dos gráficos](charts/README.md)** — explicação simples de cada gráfico e do que cada métrica significa, com as imagens embutidas.

### [`charts/quiz/`](charts/quiz/) — desempenho de aprendizado
- `acuracia_por_rag.png` — % de acerto no quiz, por modo de RAG
- `acuracia_por_rag_e_assunto.png` — % de acerto por modo de RAG × assunto
- `acuracia_por_rag_e_dia.png` — % de acerto por modo de RAG × dia de teste
- `acertos_vs_erros_por_rag.png` — volume de respostas corretas vs incorretas

### [`charts/engajamento/`](charts/engajamento/) — uso da plataforma
- `tempo_medio_sessao_por_rag.png` — tempo médio ativo de chat, em minutos (só entre quem conversou; veja a ressalva acima)
- `mensagens_por_aluno_por_rag.png` — mensagens médias trocadas por aluno
- `alunos_por_condicao_e_dia.png` — nº de alunos ativos por condição × dia (tamanho de amostra)

### [`charts/comportamento_rag/`](charts/comportamento_rag/) — telemetria do RAG
- `taxa_recuperacao_por_rag.png` — % de respostas que recuperaram algum chunk de contexto
- `score_recuperacao_por_rag.png` — score médio dos chunks recuperados
- `tempo_resposta_por_rag.png` — tempo médio de resposta da IA (segundos)
- `tokens_por_rag.png` — tokens médios (prompt + completion) por resposta

### Regerar os gráficos

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/parse_logibot.py      # regera data/*.json a partir do dump
.venv/bin/python scripts/generate_charts.py    # regera charts/**/*.png
```

## Estrutura

```
.
├── logibot-db.sql                    # dump PostgreSQL original (não versionado)
├── data/
│   ├── logibot-data.json             # dados agregados para gráficos
│   └── logibot-chat-messages.json    # mensagens completas para análise qualitativa
├── charts/
│   ├── quiz/                         # gráficos de desempenho de aprendizado
│   ├── engajamento/                  # gráficos de uso da plataforma
│   └── comportamento_rag/            # gráficos de telemetria do RAG
├── scripts/
│   ├── parse_logibot.py              # dump SQL -> data/*.json
│   └── generate_charts.py            # data/logibot-data.json -> charts/**/*.png
└── requirements.txt                  # matplotlib
```