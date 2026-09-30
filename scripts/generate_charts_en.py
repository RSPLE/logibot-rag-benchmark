"""
Gera as versões em inglês dos 3 gráficos de acurácia do quiz
(charts/quiz/en/), a partir de data/logibot-data.json.

Uso:
    .venv/bin/python scripts/generate_charts_en.py
"""

import json

from generate_charts import (
    CHARTS_DIR,
    DATA_FILE,
    RAG_ORDER,
    grouped_bar,
    simple_bar,
)

RAG_LABELS_EN = {
    "none": "No RAG",
    "context": "Context RAG",
    "self": "Self RAG",
    "hybrid": "Hybrid RAG",
}

SUBJECT_LABELS_EN = {
    "Estruturas de Repetição": "Loop Structures",
    "Vetores, Matrizes e Arrays": "Vectors, Matrices and Arrays",
    "linguagem Python": "Python language",
}


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    summary = data["summary_by_condition"]
    summary_by_day = data["summary_by_condition_and_day"]
    quiz_answers = data["quiz_answers"]

    out_dir = CHARTS_DIR / "quiz" / "en"
    print("Gerando gráficos em inglês em charts/quiz/en/ ...")

    simple_bar(
        summary, "quiz_accuracy_pct",
        "Quiz accuracy by RAG mode", "% of correct answers",
        out_dir / "accuracy_by_rag.png",
        fmt="{:.1f}%",
    )

    subjects = sorted({q["subject"] for q in quiz_answers})
    acc_by_subject = {s: {} for s in subjects}
    for s in subjects:
        for mode in RAG_ORDER:
            qs = [q for q in quiz_answers if q["subject"] == s and q["rag_mode"] == mode]
            acc_by_subject[s][mode] = (100 * sum(q["is_correct"] for q in qs) / len(qs)) if qs else None
    groups = {s: acc_by_subject[s] for s in subjects}
    grouped_bar(
        groups, RAG_ORDER, RAG_LABELS_EN,
        "Quiz accuracy by RAG mode and subject", "% of correct answers",
        out_dir / "accuracy_by_rag_and_subject.png",
        group_labels=[SUBJECT_LABELS_EN[s] for s in subjects], fmt="{:.0f}%", pct=True,
    )

    days = sorted({r["day"] for r in summary_by_day})
    acc_by_day = {f"Day {d}": {} for d in days}
    n_by_day = {f"Day {d}": {} for d in days}
    for d in days:
        for mode in RAG_ORDER:
            row = next((r for r in summary_by_day if r["day"] == d and r["rag_mode"] == mode), None)
            acc_by_day[f"Day {d}"][mode] = row["quiz_accuracy_pct"] if row else None
            n_by_day[f"Day {d}"][mode] = row["quiz_total_answers"] if row else None
    grouped_bar(
        acc_by_day, RAG_ORDER, RAG_LABELS_EN,
        "Quiz accuracy by RAG mode and test day", "% of correct answers",
        out_dir / "accuracy_by_rag_and_day.png",
        group_labels=list(acc_by_day.keys()), fmt="{:.0f}%", pct=True, n_counts=n_by_day,
        footnote="\"n\" = number of quiz answers per bar - varies a lot between bars, read low-\"n\" peaks with caution.",
    )

    print(f"\nConcluído. {sum(1 for _ in out_dir.rglob('*.png'))} gráficos em {out_dir}/")


if __name__ == "__main__":
    main()
