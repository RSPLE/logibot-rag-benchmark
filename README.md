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

Os dados brutos vêm de um dump PostgreSQL (`logibot-db.sql`, não versionado) extraído para dois arquivos JSON:

- **`logibot-data.json`** — dados prontos para gráficos, sem texto de mensagens:
  - `students[]`: um registro por aluno ativo (74 no total) — instituição, dia, turma, grupo, `rag_mode`, tempo de uso, acertos/erros, contagem de mensagens, tópicos abordados.
  - `quiz_answers[]`: uma linha por pergunta de quiz respondida (assunto, opção escolhida, acerto/erro).
  - `chat_message_metrics[]`: uma linha por resposta do assistente (provider, nº de chunks recuperados, score de recuperação, tempo de resposta, tokens) — sem o texto da mensagem.
  - `summary_by_condition[]` / `summary_by_condition_and_day[]`: métricas já agregadas por modo de RAG (e por dia), prontas para gráfico de barras comparativo.
- **`logibot-chat-messages.json`** — todas as mensagens de chat com texto completo (pergunta do aluno + resposta da IA) e os trechos recuperados pelo RAG, para análise qualitativa.

Ambos são gerados a partir do dump por [`scripts/parse_logibot.py`](scripts/parse_logibot.py):

```bash
python3 scripts/parse_logibot.py
```

### Exclusões aplicadas

- **Escola de Testes de Carga** (turmas `K6LOAD-*`, 3 contas): dados de teste de carga técnico (k6) do sistema, não são alunos reais.
- **20 contas de aluno sem nenhuma atividade**: contas criadas para um número esperado de participantes, mas que nunca chegaram a usar a plataforma (sem sessão de chat, sem quiz, sem tópico registrado).

Sobram **74 alunos reais** distribuídos nos 4 dias × 4 grupos.

## Estrutura

```
.
├── logibot-db.sql              # dump PostgreSQL original (não versionado)
├── logibot-data.json           # dados agregados para gráficos
├── logibot-chat-messages.json  # mensagens completas para análise qualitativa
└── scripts/
    └── parse_logibot.py        # script que gera os dois JSONs a partir do dump
```