"""
Create latent-evaluation plots from saved analysis CSV files and latent JSON logs.

Input:
- outputs/analysis/latent_ind_threshold_seed0_1000_analysis.csv
- outputs/analysis/latent_collab_threshold_seed0_1000_analysis.csv
- outputs/runs/latent_ind_threshold_seed0_1000/*.json
- outputs/runs/latent_collab_threshold_seed0_1000/*.json

Output:
- outputs/plots/latent_evaluation_1000.png

Run:
- .venv/bin/python plot_latent_evaluation.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Dict, List

import matplotlib.pyplot as plt


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def exact_match_rate(rows: List[Dict[str, str]]) -> float:
    return sum(row["matches_target"] == "True" for row in rows) / max(1, len(rows))


def folder_cell_accuracy(folder: str) -> float:
    total = 0
    correct = 0
    for filename in os.listdir(folder):
        if not filename.endswith(".json"):
            continue
        payload = json.load(open(os.path.join(folder, filename), "r", encoding="utf-8"))
        target_grid = payload["target_grid"]
        final_grid = payload["final_grid"]
        for row_idx in range(len(target_grid)):
            for col_idx in range(len(target_grid[0])):
                total += 1
                if final_grid[row_idx][col_idx] == target_grid[row_idx][col_idx]:
                    correct += 1
    return correct / max(1, total)


def folder_fallback_means(folder: str) -> Dict[str, float]:
    choice_fallback_steps = []
    utility_fallback_steps = []
    candidate_rows = []
    for filename in os.listdir(folder):
        if not filename.endswith(".json"):
            continue
        payload = json.load(open(os.path.join(folder, filename), "r", encoding="utf-8"))
        summary = payload["summary"]
        choice_fallback_steps.append(float(summary.get("choice_fallback_steps", 0)))
        utility_fallback_steps.append(float(summary.get("utility_fallback_steps", 0)))
        candidate_rows.append(float(summary.get("candidate_table_rows", 0)))
    return {
        "mean_choice_fallback_steps": mean(choice_fallback_steps) if choice_fallback_steps else 0.0,
        "mean_utility_fallback_steps": mean(utility_fallback_steps) if utility_fallback_steps else 0.0,
        "mean_candidate_rows": mean(candidate_rows) if candidate_rows else 0.0,
    }


def plot_latent_evaluation(
    ind_csv: str,
    collab_csv: str,
    ind_log_dir: str,
    collab_log_dir: str,
    output_path: str,
) -> None:
    ind_rows = read_csv_rows(ind_csv)
    collab_rows = read_csv_rows(collab_csv)
    labels = ["Latent Ind", "Latent Collab"]
    rows_by_label = {
        "Latent Ind": ind_rows,
        "Latent Collab": collab_rows,
    }
    folders = {
        "Latent Ind": ind_log_dir,
        "Latent Collab": collab_log_dir,
    }
    colors = ["#C06C84", "#F67280"]

    complexity_order = ["very_low", "low", "medium", "high", "very_high"]

    exact_match = [exact_match_rate(rows_by_label[label]) for label in labels]
    cell_accuracy = [folder_cell_accuracy(folders[label]) for label in labels]
    fallback_choice = [folder_fallback_means(folders[label])["mean_choice_fallback_steps"] for label in labels]
    fallback_utility = [folder_fallback_means(folders[label])["mean_utility_fallback_steps"] for label in labels]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))

    for ax, values, title in [
        (axes[0, 0], exact_match, "Exact Match Rate"),
        (axes[0, 1], cell_accuracy, "Cell Accuracy"),
        (axes[1, 0], fallback_choice, "Mean Choice-Fallback Steps"),
        (axes[1, 1], fallback_utility, "Mean Utility-Fallback Steps"),
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

    fig.suptitle("Latent Evaluation on 1000 10x10 Puzzles", fontsize=14)
    fig.tight_layout()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)

    by_complexity = {label: defaultdict(list) for label in labels}
    for label in labels:
        for row in rows_by_label[label]:
            by_complexity[label][row["complexity_label"]].append(row)

    complexity_plot = output.with_name("latent_evaluation_by_complexity_1000.png")
    fig, ax = plt.subplots(figsize=(9, 5))
    width = 0.35
    x_positions = range(len(complexity_order))
    for idx, label in enumerate(labels):
        values = []
        for complexity_label in complexity_order:
            values.append(exact_match_rate(by_complexity[label][complexity_label]))
        positions = [x + (idx - 0.5) * width for x in x_positions]
        ax.bar(positions, values, width=width, label=label, color=colors[idx])
        for xpos, value in zip(positions, values):
            ax.text(xpos, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8)

    ax.set_title("Latent Exact Match By Structural Complexity")
    ax.set_xticks(list(x_positions))
    ax.set_xticklabels(complexity_order)
    ax.set_ylim(0, 0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(complexity_plot, dpi=180)
    plt.close(fig)

    print(f"Saved plot to {output}")
    print(f"Saved plot to {complexity_plot}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Plot latent nonogram evaluation summaries.")
    parser.add_argument(
        "--ind-csv",
        default="outputs/analysis/latent_ind_threshold_seed0_1000_analysis.csv",
        help="Analysis CSV for the latent individual solver.",
    )
    parser.add_argument(
        "--collab-csv",
        default="outputs/analysis/latent_collab_threshold_seed0_1000_analysis.csv",
        help="Analysis CSV for the latent collaborative solver.",
    )
    parser.add_argument(
        "--ind-log-dir",
        default="outputs/runs/latent_ind_threshold_seed0_1000",
        help="Folder containing latent individual JSON logs.",
    )
    parser.add_argument(
        "--collab-log-dir",
        default="outputs/runs/latent_collab_threshold_seed0_1000",
        help="Folder containing latent collaborative JSON logs.",
    )
    parser.add_argument(
        "--output-path",
        default="outputs/plots/latent_evaluation_1000.png",
        help="Destination path for the latent evaluation summary plot.",
    )
    args = parser.parse_args()

    plot_latent_evaluation(
        ind_csv=args.ind_csv,
        collab_csv=args.collab_csv,
        ind_log_dir=args.ind_log_dir,
        collab_log_dir=args.collab_log_dir,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()
