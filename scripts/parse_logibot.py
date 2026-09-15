"""
Extrai os dados do dump logibot-db.sql (testes de RAG com alunos da Gaspar Viana
e do IFPA) e gera dois JSONs em data/:

  - data/logibot-data.json          -> métricas agregadas, sem texto de mensagens (para gráficos)
  - data/logibot-chat-messages.json -> mensagens completas de chat (para análise qualitativa)

Uso: python3 scripts/parse_logibot.py
"""

import json
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "logibot-db.sql"
OUT_DATA = ROOT / "data" / "logibot-data.json"
OUT_MESSAGES = ROOT / "data" / "logibot-chat-messages.json"

LOAD_TEST_UNIVERSITY = "Escola de Testes de Carga"

COPY_RE = re.compile(r"^COPY (\S+) \((.*?)\) FROM stdin;$")


def unescape(s):
    """Reverses Postgres COPY text-format escaping (\\N handled separately)."""
    if "\\" not in s:
        return s
    out = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\" and i + 1 < n:
            nc = s[i + 1]
            if nc == "n":
                out.append("\n"); i += 2; continue
            if nc == "t":
                out.append("\t"); i += 2; continue
            if nc == "r":
                out.append("\r"); i += 2; continue
            if nc == "\\":
                out.append("\\"); i += 2; continue
        out.append(c)
        i += 1
    return "".join(out)


def parse_all_copies(path):
    """Single pass over the dump, returns {table_name: (cols, rows)}."""
    tables = {}
    current_table = current_cols = current_rows = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if current_table is None:
                m = COPY_RE.match(line)
                if m:
                    current_table = m.group(1)
                    current_cols = [c.strip().strip('"') for c in m.group(2).split(",")]
                    current_rows = []
                continue
            if line == "\\.":
                tables[current_table] = (current_cols, current_rows)
                current_table = current_cols = current_rows = None
                continue
            raw = line.split("\t")
            fields = [None if v == "\\N" else unescape(v) for v in raw]
            current_rows.append(fields)
    return tables


def rows_as_dicts(tables, table_name):
    cols, rows = tables[table_name]
    return [dict(zip(cols, r)) for r in rows]


def to_int(v, default=0):
    return default if v is None else int(v)


def to_bool(v):
    return v == "t"


def parse_json(v):
    if v is None:
        return None
    try:
        return json.loads(v)
    except (json.JSONDecodeError, TypeError):
        return None


def day_label(university, class_name):
    if university == LOAD_TEST_UNIVERSITY:
        return None
    prefix = "Turma A" if class_name.startswith("Turma A") else (
        "Turma B" if class_name.startswith("Turma B") else None
    )
    if prefix is None:
        return None
    if university == "Gaspar Viana":
        return 1 if prefix == "Turma A" else 2
    if university == "IFPA":
        return 3 if prefix == "Turma A" else 4
    return None


def group_label(class_name):
    m = re.search(r"Grupo (\d+)", class_name)
    return f"Grupo {m.group(1)}" if m else class_name


def main():
    print(f"Lendo {SRC} ...")
    tables = parse_all_copies(SRC)
    print(f"{len(tables)} tabelas encontradas: {sorted(tables)}")

    universities = {r["id"]: r["name"] for r in rows_as_dicts(tables, "public.universities")}
    courses = {r["id"]: r for r in rows_as_dicts(tables, "public.courses")}
    classes = {r["id"]: r for r in rows_as_dicts(tables, "public.classes")}
    class_rag = {r["class_id"]: r["rag_mode"] for r in rows_as_dicts(tables, "public.class_rag_settings")}
    accounts = {r["id"]: r for r in rows_as_dicts(tables, "public.accounts")}
    student_profiles = {r["account_id"]: r for r in rows_as_dicts(tables, "public.student_profiles")}

    chat_sessions = {r["id"]: r for r in rows_as_dicts(tables, "public.chat_sessions")}
    chat_messages_raw = rows_as_dicts(tables, "public.chat_messages")

    chat_topic_counts = defaultdict(dict)
    for r in rows_as_dicts(tables, "public.chat_topic_counts"):
        chat_topic_counts[r["user_id"]][r["topic"]] = to_int(r["count"])

    user_analyses = {r["id"]: r for r in rows_as_dicts(tables, "public.user_analyses")}
    analysis_sessions = {r["id"]: r for r in rows_as_dicts(tables, "public.analysis_sessions")}
    answer_attempts = {r["id"]: r for r in rows_as_dicts(tables, "public.answer_attempts")}
    answer_questions_raw = rows_as_dicts(tables, "public.answer_questions")

    # ---- classe -> universidade / curso / dia / grupo / rag_mode -------------
    def class_info(class_id):
        cls = classes.get(class_id)
        if not cls:
            return None
        course = courses.get(cls["course_id"], {})
        university = universities.get(course.get("university_id"), "?")
        return {
            "class_id": class_id,
            "class_name": cls["name"],
            "course_name": course.get("name", "?"),
            "university": university,
            "day": day_label(university, cls["name"]),
            "group": group_label(cls["name"]),
            "rag_mode": class_rag.get(class_id, "?"),
        }

    # ---- quem tem atividade real ---------------------------------------------
    users_with_chat = {r["user_id"] for r in chat_sessions.values()}
    users_with_analysis = {r["user_id"] for r in user_analyses.values()}
    users_with_topics = set(chat_topic_counts.keys())
    active_users = users_with_chat | users_with_analysis | users_with_topics

    students = {}
    n_load_test = 0
    n_empty = 0
    for account_id, sp in student_profiles.items():
        info = class_info(sp["class_id"])
        if info is None or info["day"] is None:
            n_load_test += 1
            continue  # escola de teste de carga ou turma não mapeada
        if account_id not in active_users:
            n_empty += 1
            continue  # conta vazia (criada mas nunca usada)
        acc = accounts.get(account_id, {})
        students[account_id] = {
            "student_id": account_id,
            "name": acc.get("name"),
            "email": acc.get("email"),
            "university": info["university"],
            "course_name": info["course_name"],
            "day": info["day"],
            "class_name": info["class_name"],
            "group": info["group"],
            "rag_mode": info["rag_mode"],
            "level": sp.get("level"),
            "total_usage_time_sec": 0,
            "active_chat_time_sec": 0,
            "total_correct_answers": 0,
            "total_wrong_answers": 0,
            "chat_session_count": 0,
            "user_message_count": 0,
            "assistant_message_count": 0,
            "topics": chat_topic_counts.get(account_id, {}),
        }

    print(f"Alunos ativos (excluindo teste de carga e contas vazias): {len(students)}")

    # ---- user_analyses -> totais de tempo/acerto/erro -------------------------
    # OBS: total_usage_time (timer do próprio app) está zerado para 58% dos alunos
    # ativos, mesmo em contas com chat/quiz reais - é um dado incompleto na origem.
    # Mantido aqui por transparência; para engajamento use active_chat_time_sec,
    # calculado abaixo a partir dos timestamps reais das mensagens.
    for ua in user_analyses.values():
        s = students.get(ua["user_id"])
        if s is None:
            continue
        s["total_usage_time_sec"] = to_int(ua["total_usage_time"])
        s["total_correct_answers"] = to_int(ua["total_correct_answers"])
        s["total_wrong_answers"] = to_int(ua["total_wrong_answers"])

    # ---- chat_sessions por aluno -----------------------------------------------
    for cs in chat_sessions.values():
        s = students.get(cs["user_id"])
        if s is not None:
            s["chat_session_count"] += 1

    # ---- quiz_answers: answer_questions -> answer_attempts -> analysis_sessions
    #      -> user_analyses -> student -------------------------------------------
    quiz_answers = []
    for aq in answer_questions_raw:
        attempt = answer_attempts.get(aq["attempt_id"])
        if attempt is None:
            continue
        asess = analysis_sessions.get(attempt["session_id"])
        if asess is None:
            continue
        ua = user_analyses.get(asess["analysis_id"])
        if ua is None:
            continue
        s = students.get(ua["user_id"])
        if s is None:
            continue
        quiz_answers.append({
            "student_id": s["student_id"],
            "rag_mode": s["rag_mode"],
            "day": s["day"],
            "university": s["university"],
            "subject": aq["subject"],
            "selected_option": aq["selected_option"],
            "is_correct": to_bool(aq["is_correct"]),
            "timestamp": aq["timestamp"],
        })

    print(f"Respostas de quiz vinculadas a alunos ativos: {len(quiz_answers)} / {len(answer_questions_raw)} no dump")

    # ---- mensagens de chat -------------------------------------------------------
    chat_message_metrics = []
    messages_full = []
    for cm in chat_messages_raw:
        cs = chat_sessions.get(cm["chat_session_id"])
        if cs is None:
            continue
        s = students.get(cs["user_id"])
        if s is None:
            continue

        role = cm["role"]
        if role == "user":
            s["user_message_count"] += 1
        elif role == "assistant":
            s["assistant_message_count"] += 1

        meta = parse_json(cm.get("metadata")) or {}
        provider = meta.get("provider")
        timings_ms = meta.get("timingsMs") or {}
        usage = meta.get("usage") or {}
        retrieved_chunks = meta.get("retrievedChunks") or []
        scores = [c.get("score") for c in retrieved_chunks if isinstance(c, dict) and c.get("score") is not None]

        base = {
            "message_id": cm["id"],
            "chat_session_id": cm["chat_session_id"],
            "student_id": s["student_id"],
            "rag_mode": s["rag_mode"],
            "day": s["day"],
            "university": s["university"],
            "role": role,
            "detected_topic": cm.get("detected_topic"),
            "timestamp": cm.get("timestamp"),
        }

        if role == "assistant":
            chat_message_metrics.append({
                **base,
                "provider": provider,
                "retrieved_chunk_count": len(retrieved_chunks),
                "avg_retrieval_score": round(statistics.mean(scores), 2) if scores else None,
                "max_retrieval_score": max(scores) if scores else None,
                "timings_ms": timings_ms,
                "tokens": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
            })
            messages_full.append({
                **base,
                "content": cm["content"],
                "provider": provider,
                "timings_ms": timings_ms,
                "tokens": {
                    "prompt_tokens": usage.get("prompt_tokens"),
                    "completion_tokens": usage.get("completion_tokens"),
                    "total_tokens": usage.get("total_tokens"),
                },
                "retrieved_chunks": [
                    {"score": c.get("score"), "content": c.get("content")}
                    for c in retrieved_chunks if isinstance(c, dict)
                ],
            })
        else:
            messages_full.append({**base, "content": cm["content"]})

    print(f"Mensagens de chat vinculadas a alunos ativos: {len(messages_full)} / {len(chat_messages_raw)} no dump")

    # ---- active_chat_time_sec: tempo de engajamento calculado a partir dos
    #      timestamps reais das mensagens (substitui o total_usage_time do app,
    #      que está zerado para boa parte dos alunos). Soma os intervalos entre
    #      mensagens consecutivas de cada chat_session, com teto de 5 min por
    #      intervalo para não contar tempo de aba parada/inativa como uso.
    GAP_CAP_SEC = 5 * 60
    messages_by_session = defaultdict(list)
    for m in messages_full:
        messages_by_session[m["chat_session_id"]].append(m)

    for session_id, msgs in messages_by_session.items():
        msgs.sort(key=lambda m: m["timestamp"])
        student_id = msgs[0]["student_id"]
        s = students.get(student_id)
        if s is None:
            continue
        active = 0.0
        for a, b in zip(msgs, msgs[1:]):
            gap = (datetime.fromisoformat(b["timestamp"].replace(" ", "T"))
                   - datetime.fromisoformat(a["timestamp"].replace(" ", "T"))).total_seconds()
            active += min(gap, GAP_CAP_SEC)
        s["active_chat_time_sec"] += round(active)

    # ---- resumos agregados por condição -------------------------------------------
    def summarize(students_subset, quiz_subset, msg_subset, assistant_subset):
        n_students = len(students_subset)
        total_correct = sum(q["is_correct"] for q in quiz_subset)
        total_quiz = len(quiz_subset)
        n_assistant = len(assistant_subset)
        with_retrieval = [m for m in assistant_subset if m["retrieved_chunk_count"] > 0]
        retrieval_scores = [m["avg_retrieval_score"] for m in assistant_subset if m["avg_retrieval_score"] is not None]
        response_times = [m["timings_ms"].get("total") for m in assistant_subset if m["timings_ms"].get("total") is not None]
        total_tokens = [m["tokens"]["total_tokens"] for m in assistant_subset if m["tokens"]["total_tokens"] is not None]
        total_messages = len(msg_subset)

        # tempo de engajamento: só entre quem de fato trocou mensagens no chat
        # (total_usage_time do app está zerado para 58% dos alunos - não usar)
        chatting = [s for s in students_subset if s["chat_session_count"] > 0]

        return {
            "student_count": n_students,
            "quiz_total_answers": total_quiz,
            "quiz_correct_answers": total_correct,
            "quiz_accuracy_pct": round(100 * total_correct / total_quiz, 2) if total_quiz else None,
            "students_with_chat_count": len(chatting),
            "avg_active_chat_time_sec": round(statistics.mean(s["active_chat_time_sec"] for s in chatting), 1) if chatting else None,
            "avg_messages_per_student": round(total_messages / n_students, 2) if n_students else None,
            "assistant_message_count": n_assistant,
            "retrieval_rate_pct": round(100 * len(with_retrieval) / n_assistant, 2) if n_assistant else None,
            "avg_retrieval_score": round(statistics.mean(retrieval_scores), 2) if retrieval_scores else None,
            "avg_response_time_ms": round(statistics.mean(response_times), 1) if response_times else None,
            "avg_tokens_per_response": round(statistics.mean(total_tokens), 1) if total_tokens else None,
        }

    students_list = list(students.values())
    rag_modes = sorted({s["rag_mode"] for s in students_list})
    days = sorted({s["day"] for s in students_list})

    summary_by_condition = []
    for mode in rag_modes:
        s_sub = [s for s in students_list if s["rag_mode"] == mode]
        q_sub = [q for q in quiz_answers if q["rag_mode"] == mode]
        m_sub = [m for m in messages_full if m["rag_mode"] == mode]
        a_sub = [m for m in chat_message_metrics if m["rag_mode"] == mode]
        summary_by_condition.append({"rag_mode": mode, **summarize(s_sub, q_sub, m_sub, a_sub)})

    summary_by_condition_and_day = []
    for day in days:
        for mode in rag_modes:
            s_sub = [s for s in students_list if s["rag_mode"] == mode and s["day"] == day]
            if not s_sub:
                continue
            q_sub = [q for q in quiz_answers if q["rag_mode"] == mode and q["day"] == day]
            m_sub = [m for m in messages_full if m["rag_mode"] == mode and m["day"] == day]
            a_sub = [m for m in chat_message_metrics if m["rag_mode"] == mode and m["day"] == day]
            summary_by_condition_and_day.append({"day": day, "rag_mode": mode, **summarize(s_sub, q_sub, m_sub, a_sub)})

    day_meta = []
    seen = set()
    for s in sorted(students_list, key=lambda s: s["day"]):
        key = (s["day"], s["university"], s["class_name"].split(" - ")[0])
        if key in seen:
            continue
        seen.add(key)
        day_meta.append({"day": s["day"], "university": s["university"], "class_name": s["class_name"].split(" - ")[0]})

    meta = {
        "source_file": SRC.name,
        "rag_modes": rag_modes,
        "days": day_meta,
        "excluded": {
            "load_test_university": LOAD_TEST_UNIVERSITY,
            "load_test_accounts": n_load_test,
            "empty_student_accounts": n_empty,
        },
        "counts": {
            "students": len(students),
            "quiz_answers": len(quiz_answers),
            "chat_messages_total": len(messages_full),
            "chat_messages_assistant": len(chat_message_metrics),
        },
    }

    data_json = {
        "meta": meta,
        "students": students_list,
        "quiz_answers": quiz_answers,
        "chat_message_metrics": chat_message_metrics,
        "summary_by_condition": summary_by_condition,
        "summary_by_condition_and_day": summary_by_condition_and_day,
    }

    messages_json = {
        "meta": meta,
        "messages": messages_full,
    }

    OUT_DATA.write_text(json.dumps(data_json, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_MESSAGES.write_text(json.dumps(messages_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nEscrito: {OUT_DATA} ({OUT_DATA.stat().st_size / 1024:.0f} KB)")
    print(f"Escrito: {OUT_MESSAGES} ({OUT_MESSAGES.stat().st_size / 1024:.0f} KB)")

    print("\n=== Resumo por condição (RAG mode) ===")
    for row in summary_by_condition:
        print(row)


if __name__ == "__main__":
    main()
