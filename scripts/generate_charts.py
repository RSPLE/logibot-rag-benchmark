"""
Gera os gráficos comparativos entre os 4 modos de RAG (none/context/self/hybrid)
a partir de data/logibot-data.json.

Uso:
    .venv/bin/python scripts/generate_charts.py

Requer matplotlib (veja requirements.txt).
"""

import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "logibot-data.json"
CHARTS_DIR = ROOT / "charts"

# ---- paleta (dataviz skill: paleta categórica, ordem fixa, modo claro) --------
SURFACE = "#fcfcfb"
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
BASELINE = "#c3c2b7"

RAG_ORDER = ["none", "context", "self", "hybrid"]
RAG_LABELS = {
    "none": "Sem RAG",
    "context": "Context RAG",
    "self": "Self RAG",
    "hybrid": "Hybrid RAG",
}
RAG_COLORS = {
    "none": "#2a78d6",     # slot 1 blue
    "context": "#eb6834",  # slot 2 orange
    "self": "#1baf7a",     # slot 3 aqua
    "hybrid": "#eda100",   # slot 4 yellow
}

FONT = {"family": "sans-serif", "sans-serif": ["Helvetica", "Arial", "DejaVu Sans"]}
plt.rcParams.update({
    "font.family": FONT["family"],
    "font.sans-serif": FONT["sans-serif"],
    "text.color": INK_PRIMARY,
    "axes.edgecolor": BASELINE,
    "axes.labelcolor": INK_SECONDARY,
    "xtick.color": INK_SECONDARY,
    "ytick.color": INK_SECONDARY,
    "axes.facecolor": SURFACE,
    "figure.facecolor": SURFACE,
    "savefig.facecolor": SURFACE,
})


def new_fig(width=7.5, height=5.0):
    fig, ax = plt.subplots(figsize=(width, height), dpi=180)
    ax.set_facecolor(SURFACE)
    for spine in ("top", "right"):
        ax.spines[spine].set_visible(False)
    for spine in ("left", "bottom"):
        ax.spines[spine].set_color(BASELINE)
    ax.yaxis.grid(True, color=GRIDLINE, linewidth=0.8, zorder=0)
    ax.set_axisbelow(True)
    ax.tick_params(length=0)
    return fig, ax


def bar_labels(ax, bars, fmt="{:.0f}", fontsize=9):
    for b in bars:
        h = b.get_height()
        if h is None:
            continue
        ax.annotate(
            fmt.format(h),
            xy=(b.get_x() + b.get_width() / 2, h),
            xytext=(0, 4),
            textcoords="offset points",
            ha="center",
            va="bottom",
            fontsize=fontsize,
            color=INK_SECONDARY,
        )


def save(fig, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"  -> {path.relative_to(ROOT)}")


def simple_bar(summary, key, title, ylabel, out_path, fmt="{:.0f}", pct=False):
    fig, ax = new_fig(6.5, 4.8)
    by_mode = {r["rag_mode"]: r for r in summary}
    xs = list(range(len(RAG_ORDER)))
    heights = [by_mode[m][key] or 0 for m in RAG_ORDER]
    colors = [RAG_COLORS[m] for m in RAG_ORDER]
    bars = ax.bar(xs, heights, width=0.6, color=colors, zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=13, fontweight="bold", color=INK_PRIMARY, pad=14)
    if pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    bar_labels(ax, bars, fmt)
    save(fig, out_path)


def grouped_bar(groups, series_keys, series_labels, title, ylabel, out_path,
                 group_labels=None, fmt="{:.0f}", pct=False, series_colors=None,
                 n_counts=None, footnote=None):
    """groups: list of group keys (e.g. subjects or days).
    series_keys/series_labels: the rag modes plotted within each group.
    n_counts: optional {group: {series: n}} - sample size shown under each bar,
    so a bar built from very few data points doesn't carry the same visual
    weight as one built from many."""
    fig, ax = new_fig(8.5, 5.6 if n_counts else 5.2)
    n_groups = len(groups)
    n_series = len(series_keys)
    width = 0.8 / n_series
    x = list(range(n_groups))
    colors = series_colors or {k: RAG_COLORS[k] for k in series_keys}

    for i, sk in enumerate(series_keys):
        offset = (i - (n_series - 1) / 2) * width
        heights = [groups[g].get(sk) or 0 for g in groups]
        xs = [xi + offset for xi in x]
        bars = ax.bar(xs, heights, width=width * 0.92, color=colors[sk],
                       label=series_labels[sk], zorder=3)
        bar_labels(ax, bars, fmt, fontsize=7.5)
        if n_counts:
            for xi, g in zip(xs, groups):
                n = n_counts.get(g, {}).get(sk)
                if n is not None:
                    ax.annotate(f"n={n}", xy=(xi, 0), xytext=(0, -14),
                                textcoords="offset points", ha="center", va="top",
                                fontsize=6.5, color=INK_MUTED, rotation=90)

    ax.set_xticks(x)
    ax.set_xticklabels(group_labels or list(groups.keys()))
    ax.set_ylabel(ylabel)
    ax.set_title(title, fontsize=13, fontweight="bold", color=INK_PRIMARY, pad=14)
    if pct:
        ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=100))
    legend_anchor = -0.16 if n_counts else -0.12
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, legend_anchor),
               ncol=n_series, fontsize=9)
    if footnote:
        fig.text(0.5, 0.01, footnote, ha="center", fontsize=7.5, color=INK_MUTED)
        fig.tight_layout()
        fig.subplots_adjust(bottom=0.30 if n_counts else 0.24)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(out_path)
        plt.close(fig)
        print(f"  -> {out_path.relative_to(ROOT)}")
    else:
        if n_counts:
            fig.tight_layout()
            fig.subplots_adjust(bottom=0.26)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            fig.savefig(out_path)
            plt.close(fig)
            print(f"  -> {out_path.relative_to(ROOT)}")
        else:
            save(fig, out_path)


def main():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    summary = data["summary_by_condition"]
    summary_by_day = data["summary_by_condition_and_day"]
    quiz_answers = data["quiz_answers"]
    students = data["students"]
    by_mode = {r["rag_mode"]: r for r in summary}

    print("Gerando gráficos em charts/ ...")

    # ============================== charts/quiz ================================
    simple_bar(
        summary, "quiz_accuracy_pct",
        "Acurácia no quiz por modo de RAG", "% de respostas corretas",
        CHARTS_DIR / "quiz" / "acuracia_por_rag.png",
        fmt="{:.1f}%",
    )

    # acurácia por rag x assunto
    subjects = sorted({q["subject"] for q in quiz_answers})
    acc_by_subject = {s: {} for s in subjects}
    n_by_subject = {s: {} for s in subjects}
    for s in subjects:
        for mode in RAG_ORDER:
            qs = [q for q in quiz_answers if q["subject"] == s and q["rag_mode"] == mode]
            acc_by_subject[s][mode] = (100 * sum(q["is_correct"] for q in qs) / len(qs)) if qs else None
            n_by_subject[s][mode] = len(qs)
    groups = {s: acc_by_subject[s] for s in subjects}
    grouped_bar(
        groups, RAG_ORDER, RAG_LABELS,
        "Acurácia no quiz por modo de RAG e assunto", "% de respostas corretas",
        CHARTS_DIR / "quiz" / "acuracia_por_rag_e_assunto.png",
        group_labels=subjects, fmt="{:.0f}%", pct=True, n_counts=n_by_subject,
        footnote="\"n\" = número de respostas de quiz por barra.",
    )

    # acurácia por rag x dia - amostras por barra variam bastante (15 a 130
    # respostas), então o "n" embaixo de cada barra é essencial aqui: sem ele,
    # um pico como o do Hybrid RAG no Dia 4 (só 15 respostas de 2 alunos)
    # parece tão confiável quanto uma barra com 130 respostas.
    days = sorted({r["day"] for r in summary_by_day})
    acc_by_day = {f"Dia {d}": {} for d in days}
    n_by_day = {f"Dia {d}": {} for d in days}
    for d in days:
        for mode in RAG_ORDER:
            row = next((r for r in summary_by_day if r["day"] == d and r["rag_mode"] == mode), None)
            acc_by_day[f"Dia {d}"][mode] = row["quiz_accuracy_pct"] if row else None
            n_by_day[f"Dia {d}"][mode] = row["quiz_total_answers"] if row else None
    grouped_bar(
        acc_by_day, RAG_ORDER, RAG_LABELS,
        "Acurácia no quiz por modo de RAG e dia de teste", "% de respostas corretas",
        CHARTS_DIR / "quiz" / "acuracia_por_rag_e_dia.png",
        group_labels=list(acc_by_day.keys()), fmt="{:.0f}%", pct=True, n_counts=n_by_day,
        footnote="\"n\" = número de respostas de quiz por barra - varia bastante entre barras, leia picos de \"n\" baixo com cautela.",
    )

    # acertos vs erros: duas barras lado a lado por modo (corretas coloridas pelo
    # modo, incorretas em cinza), cada uma com o valor rotulado em cima - dá pra
    # ler a contagem exata de erradas direto, sem precisar subtrair.
    fig, ax = new_fig(8.0, 5.0)
    correct = [by_mode[m]["quiz_correct_answers"] for m in RAG_ORDER]
    wrong = [by_mode[m]["quiz_total_answers"] - by_mode[m]["quiz_correct_answers"] for m in RAG_ORDER]
    n = len(RAG_ORDER)
    x = list(range(n))
    width = 0.34
    b1 = ax.bar([xi - width / 2 for xi in x], correct, width=width * 0.92,
                color=[RAG_COLORS[m] for m in RAG_ORDER], zorder=3)
    b2 = ax.bar([xi + width / 2 for xi in x], wrong, width=width * 0.92,
                color=GRIDLINE, edgecolor=BASELINE, linewidth=0.6, zorder=3)
    ax.set_xticks(x)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel("Nº de respostas de quiz")
    ax.set_title("Respostas corretas vs incorretas por modo de RAG", fontsize=13,
                  fontweight="bold", color=INK_PRIMARY, pad=14)
    bar_labels(ax, b1)
    bar_labels(ax, b2)
    handles = [
        plt.Rectangle((0, 0), 1, 1, facecolor=INK_MUTED, edgecolor="none"),
        plt.Rectangle((0, 0), 1, 1, facecolor=GRIDLINE, edgecolor=BASELINE, linewidth=0.6),
    ]
    ax.legend(handles, ["Corretas (cor = modo de RAG)", "Incorretas"], frameon=False,
              loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2, fontsize=9)
    save(fig, CHARTS_DIR / "quiz" / "acertos_vs_erros_por_rag.png")

    # ============================ charts/engajamento ============================
    # Tempo ativo de chat (minutos) - calculado a partir dos timestamps reais das
    # mensagens (primeira -> última mensagem de cada chat_session), só entre os
    # alunos que de fato conversaram. Sessões reaproveitadas pelo app em dias de
    # calendário diferentes (span > 2h) são excluídas por parse_logibot.py antes
    # de chegar aqui. O campo total_usage_time do app está zerado para 58% dos
    # alunos ativos e não é usado.
    fig, ax = new_fig(6.5, 5.3)
    xs = list(range(len(RAG_ORDER)))
    heights = [(by_mode[m]["avg_active_chat_time_sec"] or 0) / 60 for m in RAG_ORDER]
    bars = ax.bar(xs, heights, width=0.6, color=[RAG_COLORS[m] for m in RAG_ORDER], zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel("Minutos")
    ax.set_title("Tempo médio de chat por modo de RAG", fontsize=13,
                  fontweight="bold", color=INK_PRIMARY, pad=14)
    bar_labels(ax, bars, "{:.0f} min")
    for i, m in enumerate(RAG_ORDER):
        n = by_mode[m]["students_with_chat_count"]
        ax.annotate(f"n={n}", xy=(i, 0), xytext=(0, -22), textcoords="offset points",
                    ha="center", va="top", fontsize=8, color=INK_MUTED)
    fig.text(0.5, 0.01,
              "Só alunos com chat registrado; sessões reaproveitadas em dias\ndiferentes (>2h de intervalo) foram excluídas do cálculo.",
              ha="center", fontsize=7.5, color=INK_MUTED, linespacing=1.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    out_path = CHARTS_DIR / "engajamento" / "tempo_medio_sessao_por_rag.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"  -> {out_path.relative_to(ROOT)}")

    # mensagens por aluno - o denominador é TODOS os alunos do grupo (inclusive
    # quem nunca conversou, que entra como 0 mensagens), diferente do gráfico de
    # tempo de chat acima (que só considera quem de fato conversou). Isso é
    # deixado explícito aqui com "n=" e uma nota, pra não parecer a mesma base.
    fig, ax = new_fig(6.5, 5.3)
    xs = list(range(len(RAG_ORDER)))
    heights = [by_mode[m]["avg_messages_per_student"] or 0 for m in RAG_ORDER]
    bars = ax.bar(xs, heights, width=0.6, color=[RAG_COLORS[m] for m in RAG_ORDER], zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel("Mensagens por aluno")
    ax.set_title("Mensagens médias por aluno, por modo de RAG", fontsize=13,
                  fontweight="bold", color=INK_PRIMARY, pad=14)
    bar_labels(ax, bars, "{:.1f}")
    for i, m in enumerate(RAG_ORDER):
        n = by_mode[m]["student_count"]
        ax.annotate(f"n={n}", xy=(i, 0), xytext=(0, -22), textcoords="offset points",
                    ha="center", va="top", fontsize=8, color=INK_MUTED)
    fig.text(0.5, 0.01,
              "\"n\" = todos os alunos do grupo, inclusive quem nunca abriu o chat\n(conta como 0 mensagens) - dilui grupos com mais alunos só de quiz.",
              ha="center", fontsize=7.5, color=INK_MUTED, linespacing=1.4)
    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    out_path = CHARTS_DIR / "engajamento" / "mensagens_por_aluno_por_rag.png"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path)
    plt.close(fig)
    print(f"  -> {out_path.relative_to(ROOT)}")

    # alunos por condição x dia
    students_by_day = {f"Dia {d}": {} for d in days}
    for d in days:
        for mode in RAG_ORDER:
            row = next((r for r in summary_by_day if r["day"] == d and r["rag_mode"] == mode), None)
            students_by_day[f"Dia {d}"][mode] = row["student_count"] if row else 0
    grouped_bar(
        students_by_day, RAG_ORDER, RAG_LABELS,
        "Nº de alunos ativos por modo de RAG e dia de teste", "Nº de alunos",
        CHARTS_DIR / "engajamento" / "alunos_por_condicao_e_dia.png",
        group_labels=list(students_by_day.keys()), fmt="{:.0f}",
    )

    # ========================= charts/comportamento_rag ==========================
    simple_bar(
        summary, "retrieval_rate_pct",
        "Taxa de recuperação de contexto por modo de RAG",
        "% de respostas com chunks recuperados",
        CHARTS_DIR / "comportamento_rag" / "taxa_recuperacao_por_rag.png",
        fmt="{:.1f}%",
    )

    # score médio de recuperação - "Sem RAG" nunca busca contexto, então a
    # métrica não se aplica (None nos dados). Antes isso virava uma barra de
    # altura 0 rotulada "0.0", como se a IA tivesse buscado algo irrelevante;
    # agora fica sem barra, com "N/A" escrito no lugar, pra não confundir "não
    # se aplica" com "buscou e a relevância foi zero".
    fig, ax = new_fig(6.5, 4.8)
    xs = list(range(len(RAG_ORDER)))
    for i, m in enumerate(RAG_ORDER):
        score = by_mode[m]["avg_retrieval_score"]
        if score is None:
            ax.annotate("N/A", xy=(i, 0), xytext=(0, 6), textcoords="offset points",
                        ha="center", va="bottom", fontsize=10, color=INK_MUTED,
                        style="italic")
            continue
        bar = ax.bar([i], [score], width=0.6, color=RAG_COLORS[m], zorder=3)
        bar_labels(ax, bar)
    ax.set_xticks(xs)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel("Score médio (0-100)")
    ax.set_title("Score médio de recuperação por modo de RAG", fontsize=13,
                  fontweight="bold", color=INK_PRIMARY, pad=14)
    save(fig, CHARTS_DIR / "comportamento_rag" / "score_recuperacao_por_rag.png")

    # tempo de resposta em segundos
    fig, ax = new_fig(6.5, 4.8)
    xs = list(range(len(RAG_ORDER)))
    heights = [(by_mode[m]["avg_response_time_ms"] or 0) / 1000 for m in RAG_ORDER]
    bars = ax.bar(xs, heights, width=0.6, color=[RAG_COLORS[m] for m in RAG_ORDER], zorder=3)
    ax.set_xticks(xs)
    ax.set_xticklabels([RAG_LABELS[m] for m in RAG_ORDER])
    ax.set_ylabel("Segundos")
    ax.set_title("Tempo médio de resposta por modo de RAG", fontsize=13,
                  fontweight="bold", color=INK_PRIMARY, pad=14)
    bar_labels(ax, bars, "{:.1f}s")
    save(fig, CHARTS_DIR / "comportamento_rag" / "tempo_resposta_por_rag.png")

    simple_bar(
        summary, "avg_tokens_per_response",
        "Tokens médios por resposta, por modo de RAG", "Tokens (prompt + completion)",
        CHARTS_DIR / "comportamento_rag" / "tokens_por_rag.png",
        fmt="{:.0f}",
    )

    print(f"\nConcluído. {sum(1 for _ in CHARTS_DIR.rglob('*.png'))} gráficos em {CHARTS_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
