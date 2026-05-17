"""Run stochastic dyad simulations over parameter grids and write a summary CSV.

Flag descriptions:
- --x-path: required packed clue .npz file.
- --y-path: optional target solution .npz file for success and accuracy metrics.
- --sample-start / --sample-end: half-open sample range [start, end).
- --utility-model: repeatable; choose ind or dyad utility.
- --choice-set: repeatable; choose certainty1, threshold, or all_legal candidates.
- --q-threshold: repeatable Q cutoff used only by threshold choice-set.
- --beta-softmax: repeatable inverse softmax temperature.
- --tau-decision: repeatable softmax temperature; converted to beta_softmax = 1 / tau_decision.
- --lambda-partner: repeatable partner-information weight for dyad utility.
- --fallback: repeatable fallback mode: none, all_legal, or uninformed.
- --output-csv: destination summary CSV path.
- --save-logs-dir: optional directory for full JSON logs.

Expected output files:
- results/analysis/stoch_sweep_summary.csv by default, or the path passed to --output-csv.
- Optional JSON logs under --save-logs-dir.

Command to run code:
- poetry run python scripts/sweep_stoch.py --x-path data/NonoDataset/10x10/x_test_dataset.npz --y-path data/NonoDataset/10x10/y_test_dataset.npz --sample-start 0 --sample-end 10 --utility-model ind --utility-model dyad --choice-set certainty1 --choice-set threshold --q-threshold 0.75 --beta-softmax 5 --lambda-partner 1 --fallback uninformed --output-csv results/analysis/stoch_sweep_summary.csv --quiet
"""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from stoch_dyad import (
    augment_payload_with_candidate_tables,
    default_solver_tag,
    solve_stoch_turn_based_logged,
    tau_decision_from_beta_softmax,
)
from solver_common import (
    build_log_payload,
    count_unknown_cells,
    default_max_turns,
    get_sample_indices,
    grids_equal,
    load_dataset_sample,
    load_dataset_targets,
    load_npz_array,
    make_default_log_path,
    save_log_json,
)


def write_csv(rows: List[Dict[str, Any]], output_csv: str) -> None:
    if not rows:
        raise ValueError("No rows to write")

    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run stoch-choice sweeps and export a summary CSV."
    )
    parser.add_argument("--x-path", required=True, help="Path to packed clue x_*.npz file")
    parser.add_argument("--y-path", help="Optional path to target y_*.npz file")
    parser.add_argument("--sample-idx", type=int, default=0, help="Dataset sample index")
    parser.add_argument("--all-samples", action="store_true", help="Run all samples in the dataset")
    parser.add_argument("--sample-start", type=int, help="Optional batch start index (inclusive)")
    parser.add_argument("--sample-end", type=int, help="Optional batch end index (exclusive)")
    parser.add_argument(
        "--utility-model",
        action="append",
        choices=["ind", "dyad"],
        help="Repeat to sweep multiple utility models. Defaults to ind and dyad.",
    )
    parser.add_argument(
        "--choice-set",
        action="append",
        choices=["certainty1", "threshold", "all_legal"],
        help="Repeat to sweep multiple choice-set definitions. Defaults to certainty1 and threshold.",
    )
    parser.add_argument(
        "--q-threshold",
        action="append",
        type=float,
        help="Repeat to sweep threshold choice-set Q thresholds. Defaults to 0.75.",
    )
    parser.add_argument(
        "--tau",
        dest="deprecated_taus",
        action="append",
        type=float,
        help="Deprecated alias for --q-threshold.",
    )
    parser.add_argument(
        "--beta-softmax",
        action="append",
        type=float,
        help="Repeat to sweep softmax inverse temperatures. Defaults to 5.0 unless --tau-decision is set.",
    )
    parser.add_argument(
        "--tau-decision",
        action="append",
        type=float,
        help="Repeat to sweep softmax temperatures. Converted to beta_softmax = 1 / tau_decision.",
    )
    parser.add_argument(
        "--beta",
        dest="deprecated_betas",
        action="append",
        type=float,
        help="Deprecated alias for --beta-softmax.",
    )
    parser.add_argument(
        "--lambda-partner",
        dest="lambda_partners",
        action="append",
        type=float,
        help="Repeat to sweep multiple partner-information weights. Defaults to 1.0.",
    )
    parser.add_argument(
        "--lambda-weight",
        dest="deprecated_lambda_weights",
        action="append",
        type=float,
        help="Deprecated alias for --lambda-partner.",
    )
    parser.add_argument(
        "--fallback",
        action="append",
        choices=["none", "all_legal", "uninformed"],
        help="Repeat to sweep fallback modes. Defaults to uninformed.",
    )
    parser.add_argument(
        "--seed",
        action="append",
        type=int,
        help="Repeat to sweep multiple random seeds. Defaults to 0.",
    )
    parser.add_argument("--alpha", type=float, default=1.0, help="Weight on Q_own.")
    parser.add_argument(
        "--max-turns",
        type=int,
        help="Maximum number of turns. Default is 2 * number_of_cells.",
    )
    parser.add_argument(
        "--output-csv",
        default="results/analysis/stoch_sweep_summary.csv",
        help="Destination CSV path for the sweep summary.",
    )
    parser.add_argument(
        "--save-logs-dir",
        help="Optional directory to save full JSON logs for each run.",
    )
    parser.add_argument("--quiet", action="store_true", help="Disable step-by-step printing")
    args = parser.parse_args()

    utility_models = args.utility_model or ["ind", "dyad"]
    choice_sets = args.choice_set or ["certainty1", "threshold"]
    q_thresholds = args.q_threshold or args.deprecated_taus or [0.75]
    if args.tau_decision:
        beta_softmaxes = [1.0 / value for value in args.tau_decision]
    else:
        beta_softmaxes = args.beta_softmax or args.deprecated_betas or [5.0]
    lambda_partners = args.lambda_partners or args.deprecated_lambda_weights or [1.0]
    fallbacks = args.fallback or ["uninformed"]
    seeds = args.seed or [0]

    x_array = load_npz_array(args.x_path)
    y_array = load_dataset_targets(args.y_path)
    if y_array is not None and len(y_array) != len(x_array):
        raise ValueError(
            f"x/y sample count mismatch: {len(x_array)} in {args.x_path}, "
            f"{len(y_array)} in {args.y_path}"
        )

    sample_indices = get_sample_indices(
        total_samples=len(x_array),
        sample_idx=args.sample_idx,
        all_samples=args.all_samples,
        sample_start=args.sample_start,
        sample_end=args.sample_end,
    )

    rows: List[Dict[str, Any]] = []
    total_runs = 0
    for utility_model, choice_set, q_threshold, beta_softmax, lambda_partner, fallback, seed, sample_idx in product(
        utility_models,
        choice_sets,
        q_thresholds,
        beta_softmaxes,
        lambda_partners,
        fallbacks,
        seeds,
        sample_indices,
    ):
        if choice_set != "threshold" and q_threshold != q_thresholds[0]:
            continue
        if utility_model == "ind" and lambda_partner != lambda_partners[0]:
            continue

        row_clues, col_clues, target_grid = load_dataset_sample(
            x_path=args.x_path,
            sample_idx=sample_idx,
            y_path=args.y_path,
        )
        max_turns = args.max_turns or default_max_turns(row_clues, col_clues)
        final_grid, log, candidate_steps = solve_stoch_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            utility_model=utility_model,
            choice_set=choice_set,
            alpha=args.alpha,
            beta_softmax=beta_softmax,
            q_threshold=q_threshold,
            lambda_partner=lambda_partner,
            fallback=fallback,
            max_turns=max_turns,
            seed=seed,
            verbose=not args.quiet,
        )

        payload = build_log_payload(
            events=log,
            row_clues=row_clues,
            col_clues=col_clues,
            max_turns=max_turns,
            final_grid=final_grid,
            target_grid=target_grid,
            x_path=args.x_path,
            y_path=args.y_path,
            sample_idx=sample_idx,
            metadata_extra={
                "solver": "stoch_dyad",
                "utility_model": utility_model,
                "choice_set": choice_set,
                "alpha": args.alpha,
                "beta_softmax": beta_softmax,
                "tau_decision": tau_decision_from_beta_softmax(beta_softmax),
                "q_threshold": q_threshold,
                "lambda_partner": lambda_partner,
                "fallback": fallback,
                "seed": seed,
                "row_strategy": "softmax",
                "col_strategy": "softmax",
                "strategy": "softmax",
            },
        )
        payload = augment_payload_with_candidate_tables(payload, candidate_steps)

        if args.save_logs_dir:
            output_path = make_default_log_path(
                x_path=args.x_path,
                solver_tag=default_solver_tag(
                    utility_model=utility_model,
                    choice_set=choice_set,
                    q_threshold=q_threshold,
                    beta_softmax=beta_softmax,
                    seed=seed,
                ),
                sample_idx=sample_idx,
                output_dir=args.save_logs_dir,
            )
            save_log_json(payload, output_path)
        else:
            output_path = ""

        summary = payload["summary"]
        rows.append(
            {
                "sample_idx": sample_idx,
                "utility_model": utility_model,
                "choice_set": choice_set,
                "alpha": args.alpha,
                "beta_softmax": beta_softmax,
                "tau_decision": tau_decision_from_beta_softmax(beta_softmax),
                "q_threshold": q_threshold,
                "lambda_partner": lambda_partner,
                "fallback": fallback,
                "seed": seed,
                "board_rows": len(row_clues),
                "board_cols": len(col_clues),
                "max_turns": max_turns,
                "unknown_cells": summary["unknown_cells"],
                "complete": summary["complete"],
                "solved": summary["solved"],
                "success": summary["success"],
                "matches_target": summary["matches_target"],
                "n_errors": summary["n_errors"],
                "cell_accuracy": summary["cell_accuracy"],
                "known_cell_accuracy": summary["known_cell_accuracy"],
                "failure_reason": summary["failure_reason"],
                "write_events": summary["write_events"],
                "pass_events": summary["pass_events"],
                "row_writes": summary["row_writes"],
                "col_writes": summary["col_writes"],
                "mean_candidate_count": summary["mean_candidate_count"],
                "mean_chosen_probability": summary["mean_chosen_probability"],
                "mean_chosen_q_own": summary["mean_chosen_q_own"],
                "mean_chosen_b_partner_local": summary["mean_chosen_b_partner_local"],
                "candidate_table_rows": summary["candidate_table_rows"],
                "saved_log_path": output_path,
            }
        )
        total_runs += 1
        print(
            f"Completed sample={sample_idx} utility_model={utility_model} "
            f"choice_set={choice_set} beta_softmax={beta_softmax} "
            f"q_threshold={q_threshold} lambda_partner={lambda_partner} "
            f"fallback={fallback} seed={seed}"
        )

    write_csv(rows, args.output_csv)
    print(f"Completed {total_runs} run(s)")
    print(f"Saved sweep summary to {args.output_csv}")


if __name__ == "__main__":
    main()
