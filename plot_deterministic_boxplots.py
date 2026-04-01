"""
Create boxplot-based deterministic-evaluation figures from saved analysis CSV files.

Input:
- outputs/analysis/deterministic_collab_1000_analysis.csv
- outputs/analysis/deterministic_ind_1000_analysis.csv

Output:
- outputs/plots/deterministic_evaluation_boxplot_1000.png

Run:
- .venv/bin/python plot_deterministic_boxplots.py
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def float_series(rows: List[Dict[str, str]], key: str) -> List[float]:
    return [float(row[key]) for row in rows]


def bool_series(rows: List[Dict[str, str]], key: str) -> List[float]:
    return [1.0 if row[key] == "True" else 0.0 for row in rows]


def add_boxplot(ax: plt.Axes, data: List[List[float]], labels: List[str], colors: List[str], title: str) -> None:
    box = ax.boxplot(tick_labels=labels, x=data, patch_artist=True, showfliers=False)
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
    for median in box["medians"]:
        median.set_color("#222222")
        median.set_linewidth(1.5)
    ax.set_title(title)


def plot_deterministic_boxplots(collab_csv: str, ind_csv: str, output_path: str) -> None:
    collab_rows = read_csv_rows(collab_csv)
    ind_rows = read_csv_rows(ind_csv)

    labels = ["Det Collab", "Det Ind"]
    colors = ["#355C7D", "#6C8EAD"]
    rows_by_label = [collab_rows, ind_rows]

    metrics = [
        ("Exact Match Indicator", [bool_series(rows, "matches_target") for rows in rows_by_label]),
        ("Unknown Cells", [float_series(rows, "unknown_cells") for rows in rows_by_label]),
        ("Pass Events", [float_series(rows, "pass_events") for rows in rows_by_label]),
        ("Writes Before First Pass", [float_series(rows, "writes_before_first_pass") for rows in rows_by_label]),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (title, data) in zip(axes.flat, metrics):
        add_boxplot(ax=ax, data=data, labels=labels, colors=colors, title=title)

    fig.suptitle("Deterministic Evaluation Distributions on 1000 10x10 Puzzles", fontsize=14)
    fig.tight_layout()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    print(f"Saved plot to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create deterministic evaluation boxplots.")
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
        default="outputs/plots/deterministic_evaluation_boxplot_1000.png",
        help="Destination path for the deterministic evaluation boxplot.",
    )
    args = parser.parse_args()

    plot_deterministic_boxplots(
        collab_csv=args.collab_csv,
        ind_csv=args.ind_csv,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()
