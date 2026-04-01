from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt


def read_rows(path: str) -> List[Dict[str, str]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def as_float(row: Dict[str, str], key: str) -> float:
    value = row.get(key, "")
    if value in {"", None}:
        return 0.0
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered == "true":
            return 1.0
        if lowered == "false":
            return 0.0
    return float(value)


def as_str(row: Dict[str, str], key: str) -> str:
    value = row.get(key, "")
    return "" if value is None else str(value)


def safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def format_float(value: float) -> str:
    return f"{value:.4f}"


def format_table(rows: List[Dict[str, Any]], columns: List[Tuple[str, str]]) -> str:
    headers = [label for _, label in columns]
    body = [[str(row.get(key, "")) for key, _ in columns] for row in rows]
    widths = []
    for idx, header in enumerate(headers):
        col_values = [header] + [line[idx] for line in body]
        widths.append(max(len(value) for value in col_values))

    lines = []
    header_line = " | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers))
    divider = "-+-".join("-" * widths[idx] for idx in range(len(widths)))
    lines.append(header_line)
    lines.append(divider)
    for line in body:
        lines.append(" | ".join(line[idx].ljust(widths[idx]) for idx in range(len(widths))))
    return "\n".join(lines)


def summarize_by_solver(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[as_str(row, "solver") or "unknown"].append(row)

    summaries: List[Dict[str, Any]] = []
    for solver, solver_rows in sorted(grouped.items()):
        summaries.append(
            {
                "solver": solver,
                "runs": len(solver_rows),
                "solved_rate": format_float(safe_mean([as_float(row, "solved") for row in solver_rows])),
                "mean_unknown_ratio": format_float(
                    safe_mean([as_float(row, "unknown_ratio") for row in solver_rows])
                ),
                "mean_difficulty": format_float(
                    safe_mean([as_float(row, "difficulty_score") for row in solver_rows])
                ),
                "mean_action_turns": format_float(
                    safe_mean([as_float(row, "action_turns") for row in solver_rows])
                ),
                "mean_write_events": format_float(
                    safe_mean([as_float(row, "write_events") for row in solver_rows])
                ),
                "mean_pass_events": format_float(
                    safe_mean([as_float(row, "pass_events") for row in solver_rows])
                ),
            }
        )
    return summaries


def summarize_by_solver_and_size(rows: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str, str], List[Dict[str, str]]] = defaultdict(list)
    for row in rows:
        key = (
            as_str(row, "solver") or "unknown",
            as_str(row, "board_rows"),
            as_str(row, "board_cols"),
        )
        grouped[key].append(row)

    summaries: List[Dict[str, Any]] = []
    for (solver, board_rows, board_cols), solver_rows in sorted(
        grouped.items(),
        key=lambda item: (int(item[0][1]), int(item[0][2]), item[0][0]),
    ):
        summaries.append(
            {
                "solver": solver,
                "board_size": f"{board_rows}x{board_cols}",
                "runs": len(solver_rows),
                "solved_rate": format_float(safe_mean([as_float(row, "solved") for row in solver_rows])),
                "mean_unknown_ratio": format_float(
                    safe_mean([as_float(row, "unknown_ratio") for row in solver_rows])
                ),
                "mean_difficulty": format_float(
                    safe_mean([as_float(row, "difficulty_score") for row in solver_rows])
                ),
                "mean_action_turns": format_float(
                    safe_mean([as_float(row, "action_turns") for row in solver_rows])
                ),
            }
        )
    return summaries


def pair_key(row: Dict[str, str]) -> Tuple[str, str, str, str]:
    source_x = as_str(row, "source_x_path")
    if not source_x:
        source_x = as_str(row, "log_file")
    sample_idx = as_str(row, "sample_idx")
    sample_id = as_str(row, "sample_id")
    sample_token = sample_idx if sample_idx else sample_id
    return (
        source_x,
        as_str(row, "board_rows"),
        as_str(row, "board_cols"),
        sample_token,
    )


def paired_summary(rows: List[Dict[str, str]]) -> Optional[Dict[str, Any]]:
    by_key: Dict[Tuple[str, str, str, str], Dict[str, Dict[str, str]]] = defaultdict(dict)
    for row in rows:
        solver = as_str(row, "solver")
        if solver not in {"collab", "ind"}:
            continue
        by_key[pair_key(row)][solver] = row

    pairs = [entry for entry in by_key.values() if "collab" in entry and "ind" in entry]
    if not pairs:
        return None

    collab_better_solved = 0
    ind_better_solved = 0
    same_solved = 0
    collab_lower_unknown = 0
    ind_lower_unknown = 0
    tied_unknown = 0

    unknown_deltas: List[float] = []
    difficulty_deltas: List[float] = []
    action_turn_deltas: List[float] = []
    pass_event_deltas: List[float] = []

    for pair in pairs:
        collab = pair["collab"]
        ind = pair["ind"]

        collab_solved = as_float(collab, "solved")
        ind_solved = as_float(ind, "solved")
        if collab_solved > ind_solved:
            collab_better_solved += 1
        elif ind_solved > collab_solved:
            ind_better_solved += 1
        else:
            same_solved += 1

        collab_unknown = as_float(collab, "unknown_ratio")
        ind_unknown = as_float(ind, "unknown_ratio")
        if collab_unknown < ind_unknown:
            collab_lower_unknown += 1
        elif ind_unknown < collab_unknown:
            ind_lower_unknown += 1
        else:
            tied_unknown += 1

        unknown_deltas.append(collab_unknown - ind_unknown)
        difficulty_deltas.append(as_float(collab, "difficulty_score") - as_float(ind, "difficulty_score"))
        action_turn_deltas.append(as_float(collab, "action_turns") - as_float(ind, "action_turns"))
        pass_event_deltas.append(as_float(collab, "pass_events") - as_float(ind, "pass_events"))

    return {
        "paired_samples": len(pairs),
        "collab_better_solved": collab_better_solved,
        "ind_better_solved": ind_better_solved,
        "same_solved": same_solved,
        "collab_lower_unknown": collab_lower_unknown,
        "ind_lower_unknown": ind_lower_unknown,
        "tied_unknown": tied_unknown,
        "mean_unknown_ratio_delta_collab_minus_ind": format_float(safe_mean(unknown_deltas)),
        "mean_difficulty_delta_collab_minus_ind": format_float(safe_mean(difficulty_deltas)),
        "mean_action_turn_delta_collab_minus_ind": format_float(safe_mean(action_turn_deltas)),
        "mean_pass_event_delta_collab_minus_ind": format_float(safe_mean(pass_event_deltas)),
    }


def write_summary_csv(
    rows: List[Dict[str, Any]],
    output_path: str,
    columns: List[str],
) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def make_plot(rows: List[Dict[str, str]], output_path: str) -> None:
    grouped = defaultdict(list)
    for row in rows:
        grouped[as_str(row, "solver") or "unknown"].append(row)

    solvers = sorted(grouped.keys())
    solved_rates = [safe_mean([as_float(row, "solved") for row in grouped[solver]]) for solver in solvers]
    unknown_ratios = [safe_mean([as_float(row, "unknown_ratio") for row in grouped[solver]]) for solver in solvers]
    difficulty_scores = [
        safe_mean([as_float(row, "difficulty_score") for row in grouped[solver]]) for solver in solvers
    ]

    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    metrics = [
        ("Solved Rate", solved_rates, (0.0, 1.0)),
        ("Unknown Ratio", unknown_ratios, (0.0, 1.0)),
        ("Difficulty Score", difficulty_scores, (0.0, 100.0)),
    ]

    for ax, (title, values, ylim) in zip(axes, metrics):
        bars = ax.bar(solvers, values)
        ax.set_title(title)
        ax.set_ylim(*ylim)
        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                format_float(value),
                ha="center",
                va="bottom",
                fontsize=9,
            )

    fig.tight_layout()
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare collab and ind runs from the analysis CSV."
    )
    parser.add_argument("--analysis-csv", required=True, help="CSV produced by analyze_logs.py")
    parser.add_argument("--summary-csv", help="Optional output CSV for the solver summary table")
    parser.add_argument("--size-summary-csv", help="Optional output CSV for the solver-by-size table")
    parser.add_argument("--plot-path", help="Optional bar chart output path")
    args = parser.parse_args()

    rows = read_rows(args.analysis_csv)
    if not rows:
        raise ValueError(f"No rows found in {args.analysis_csv}")

    solver_rows = summarize_by_solver(rows)
    size_rows = summarize_by_solver_and_size(rows)
    paired = paired_summary(rows)

    print("Overall Solver Summary")
    print(
        format_table(
            solver_rows,
            [
                ("solver", "solver"),
                ("runs", "runs"),
                ("solved_rate", "solved_rate"),
                ("mean_unknown_ratio", "mean_unknown_ratio"),
                ("mean_difficulty", "mean_difficulty"),
                ("mean_action_turns", "mean_action_turns"),
                ("mean_write_events", "mean_write_events"),
                ("mean_pass_events", "mean_pass_events"),
            ],
        )
    )
    print()

    print("Solver Summary By Board Size")
    print(
        format_table(
            size_rows,
            [
                ("solver", "solver"),
                ("board_size", "board_size"),
                ("runs", "runs"),
                ("solved_rate", "solved_rate"),
                ("mean_unknown_ratio", "mean_unknown_ratio"),
                ("mean_difficulty", "mean_difficulty"),
                ("mean_action_turns", "mean_action_turns"),
            ],
        )
    )

    if paired is not None:
        print()
        print("Paired Comparison")
        for key, value in paired.items():
            print(f"{key}: {value}")
    else:
        print()
        print("Paired Comparison")
        print("No collab/ind sample pairs were found in the CSV.")

    if args.summary_csv:
        write_summary_csv(
            solver_rows,
            args.summary_csv,
            [
                "solver",
                "runs",
                "solved_rate",
                "mean_unknown_ratio",
                "mean_difficulty",
                "mean_action_turns",
                "mean_write_events",
                "mean_pass_events",
            ],
        )

    if args.size_summary_csv:
        write_summary_csv(
            size_rows,
            args.size_summary_csv,
            [
                "solver",
                "board_size",
                "runs",
                "solved_rate",
                "mean_unknown_ratio",
                "mean_difficulty",
                "mean_action_turns",
            ],
        )

    if args.plot_path:
        make_plot(rows, args.plot_path)
        print()
        print(f"Saved plot to {args.plot_path}")


if __name__ == "__main__":
    main()
