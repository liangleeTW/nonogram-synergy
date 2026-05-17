"""
Create boxplot-based stoch-evaluation figures from saved analysis CSV files and stoch JSON logs.

Input:
- results/analysis/stoch_ind_threshold_seed0_1000_analysis.csv
- results/analysis/stoch_dyad_threshold_seed0_1000_analysis.csv
- results/runs/stoch_ind_threshold_seed0_1000/*.json
- results/runs/stoch_dyad_threshold_seed0_1000/*.json

Output:
- results/plots/stoch_evaluation_boxplot_1000.png

Run:
- .venv/bin/python scripts/plot_stoch_boxplots.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Dict, List

import matplotlib.pyplot as plt


def read_csv_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def bool_series(rows: List[Dict[str, str]], key: str) -> List[float]:
    return [1.0 if row[key] == "True" else 0.0 for row in rows]


def load_stoch_log_metrics(folder: str) -> Dict[str, List[float]]:
    metrics = {
        "cell_accuracy": [],
        "choice_fallback_steps": [],
        "utility_fallback_steps": [],
        "mean_chosen_q_own": [],
    }
    for filename in sorted(os.listdir(folder)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(folder, filename)
        with open(path, "r", encoding="utf-8") as f:
            payload = json.load(f)
        target_grid = payload["target_grid"]
        final_grid = payload["final_grid"]
        total_cells = len(target_grid) * len(target_grid[0])
        correct_cells = 0
        for row_idx in range(len(target_grid)):
            for col_idx in range(len(target_grid[0])):
                if final_grid[row_idx][col_idx] == target_grid[row_idx][col_idx]:
                    correct_cells += 1

        summary = payload["summary"]
        metrics["cell_accuracy"].append(correct_cells / max(1, total_cells))
        metrics["choice_fallback_steps"].append(float(summary.get("choice_fallback_steps", 0)))
        metrics["utility_fallback_steps"].append(float(summary.get("utility_fallback_steps", 0)))
        metrics["mean_chosen_q_own"].append(float(summary.get("mean_chosen_q_own", 0.0)))
    return metrics


def add_boxplot(ax: plt.Axes, data: List[List[float]], labels: List[str], colors: List[str], title: str) -> None:
    box = ax.boxplot(tick_labels=labels, x=data, patch_artist=True, showfliers=False)
    for patch, color in zip(box["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
    for median in box["medians"]:
        median.set_color("#222222")
        median.set_linewidth(1.5)
    ax.set_title(title)


def plot_stoch_boxplots(
    ind_csv: str,
    dyad_csv: str,
    ind_log_dir: str,
    dyad_log_dir: str,
    output_path: str,
) -> None:
    ind_rows = read_csv_rows(ind_csv)
    dyad_rows = read_csv_rows(dyad_csv)
    ind_metrics = load_stoch_log_metrics(ind_log_dir)
    dyad_metrics = load_stoch_log_metrics(dyad_log_dir)

    labels = ["Latent Ind", "Stoch Dyad"]
    colors = ["#C06C84", "#F67280"]

    metrics = [
        ("Exact Match Indicator", [bool_series(ind_rows, "matches_target"), bool_series(dyad_rows, "matches_target")]),
        ("Cell Accuracy", [ind_metrics["cell_accuracy"], dyad_metrics["cell_accuracy"]]),
        ("Choice-Fallback Steps", [ind_metrics["choice_fallback_steps"], dyad_metrics["choice_fallback_steps"]]),
        ("Utility-Fallback Steps", [ind_metrics["utility_fallback_steps"], dyad_metrics["utility_fallback_steps"]]),
    ]

    fig, axes = plt.subplots(2, 2, figsize=(13, 9))
    for ax, (title, data) in zip(axes.flat, metrics):
        add_boxplot(ax=ax, data=data, labels=labels, colors=colors, title=title)

    fig.suptitle("Latent Evaluation Distributions on 1000 10x10 Puzzles", fontsize=14)
    fig.tight_layout()

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=180)
    plt.close(fig)
    print(f"Saved plot to {output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Create stoch evaluation boxplots.")
    parser.add_argument(
        "--ind-csv",
        default="results/analysis/stoch_ind_threshold_seed0_1000_analysis.csv",
        help="Analysis CSV for the stoch ind solver.",
    )
    parser.add_argument(
        "--dyad-csv",
        default="results/analysis/stoch_dyad_threshold_seed0_1000_analysis.csv",
        help="Analysis CSV for the stoch dyad solver.",
    )
    parser.add_argument(
        "--ind-log-dir",
        default="results/runs/stoch_ind_threshold_seed0_1000",
        help="Folder containing stoch ind JSON logs.",
    )
    parser.add_argument(
        "--dyad-log-dir",
        default="results/runs/stoch_dyad_threshold_seed0_1000",
        help="Folder containing stoch dyad JSON logs.",
    )
    parser.add_argument(
        "--output-path",
        default="results/plots/stoch_evaluation_boxplot_1000.png",
        help="Destination path for the stoch evaluation boxplot.",
    )
    args = parser.parse_args()

    plot_stoch_boxplots(
        ind_csv=args.ind_csv,
        dyad_csv=args.dyad_csv,
        ind_log_dir=args.ind_log_dir,
        dyad_log_dir=args.dyad_log_dir,
        output_path=args.output_path,
    )


if __name__ == "__main__":
    main()
