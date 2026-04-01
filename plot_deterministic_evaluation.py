"""
Create deterministic-evaluation plots from saved analysis CSV files.

Input:
- outputs/analysis/deterministic_collab_1000_analysis.csv
- outputs/analysis/deterministic_ind_1000_analysis.csv

Output:
- outputs/plots/deterministic_evaluation_1000.png

Run:
- .venv/bin/python plot_deterministic_evaluation.py
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, List

import matplotlib.pyplot as plt


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def exact_match_rate(rows: List[Dict[str, str]]) -> float:
    return sum(row["matches_target"] == "True" for row in rows) / max(1, len(rows))


def mean_unknown_cells(rows: List[Dict[str, str]]) -> float:
    return mean(float(row["unknown_cells"]) for row in rows) if rows else 0.0


def mean_pass_events(rows: List[Dict[str, str]]) -> float:
    return mean(float(row["pass_events"]) for row in rows) if rows else 0.0


def plot_deterministic_evaluation(
    collab_csv: str,
    ind_csv: str,
    output_path: str,
) -> None:
    collab_rows = read_csv_rows(collab_csv)
    ind_rows = read_csv_rows(ind_csv)

    labels = ["Det Collab", "Det Ind"]
    rows_by_label = {
        "Det Collab": collab_rows,
        "Det Ind": ind_rows,
    }

    complexity_order = ["very_low", "low", "medium", "high", "very_high"]
    difficulty_order = [
        "trivial",
        "easy",
        "moderate",
        "challenging",
        "hard",
        "stalled_near_complete",
        "stalled_moderate",
        "stalled_hard",
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    colors = ["#355C7D", "#6C8EAD"]

    exact_match = [exact_match_rate(rows_by_label[label]) for label in labels]
    mean_unknown = [mean_unknown_cells(rows_by_label[label]) for label in labels]
    mean_pass = [mean_pass_events(rows_by_label[label]) for label in labels]

    for ax, values, title in [
        (axes[0, 0], exact_match, "Exact Match Rate"),
        (axes[0, 1], mean_unknown, "Mean Unknown Cells"),
        (axes[1, 0], mean_pass, "Mean Pass Events"),
    ]:
        bars = ax.bar(labels, values, color=colors)
        ax.set_title(title)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f"{value:.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )

    grouped = {
        label: defaultdict(list)
        for label in labels
    }
    for label in labels:
        for row in rows_by_label[label]:
            grouped[label][row["complexity_label"]].append(row)

    x_positions = range(len(complexity_order))
    width = 0.35
    for idx, label in enumerate(labels):
        values = []
        for complexity_label in complexity_order:
            values.append(exact_match_rate(grouped[label][complexity_label]))
        positions = [x + (idx - 0.5) * width for x in x_positions]
        axes[1, 1].bar(positions, values, width=width, label=label, color=colors[idx])
        for xpos, value in zip(positions, values):
            axes[1, 1].text(xpos, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)

    axes[1, 1].set_title("Exact Match By Structural Complexity")
    axes[1, 1].set_xticks(list(x_positions))
    axes[1, 1].set_xticklabels(complexity_order)
    axes[1, 1].set_ylim(0, 1.0)
    axes[1, 1].legend()

    fig.suptitle("Deterministic Evaluation on 1000 10x10 Puzzles", fontsize=14)
    fig.tight_layout()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    difficulty_counts = {
        label: Counter(row["difficulty_label"] for row in rows_by_label[label])
        for label in labels
    }
    print("Difficulty label counts:")
    for label in labels:
        print(label)
        for difficulty_label in difficulty_order:
            count = difficulty_counts[label].get(difficulty_label, 0)
            if count:
                print(f"  {difficulty_label}: {count}")

    print(f"Saved plot to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot deterministic nonogram evaluation summaries.")
    parser.add_argument(
        "--collab-csv",
        default="outputs/analysis/deterministic_collab_1000_analysis.csv",
        help="Analysis CSV for the deterministic collaborative solver.",
    )
    parser.add_argument(
        "--ind-csv",
        default="outputs/analysis/deterministic_ind_1000_analysis.csv",
        help="Analysis CSV for the deterministic individual solver.",
    )
    parser.add_argument(
        "--output-path",
        default="outputs/plots/deterministic_evaluation_1000.png",
        help="Destination path for the deterministic evaluation plot.",
    )
    args = parser.parse_args()

    plot_deterministic_evaluation(
        collab_csv=args.collab_csv,
        ind_csv=args.ind_csv,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()
