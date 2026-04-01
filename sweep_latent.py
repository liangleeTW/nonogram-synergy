from __future__ import annotations

import argparse
import csv
from itertools import product
from pathlib import Path
from typing import Any, Dict, List

from latent_collab import (
    augment_payload_with_candidate_tables,
    default_solver_tag,
    solve_latent_turn_based_logged,
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
        description="Run stochastic latent-choice sweeps and export a summary CSV."
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
        choices=["individual", "collaborative"],
        help="Repeat to sweep multiple utility models. Defaults to individual and collaborative.",
    )
    parser.add_argument(
        "--choice-set",
        action="append",
        choices=["certainty1", "threshold", "all_legal"],
        help="Repeat to sweep multiple choice-set definitions. Defaults to certainty1 and threshold.",
    )
    parser.add_argument(
        "--tau",
        action="append",
        type=float,
        help="Repeat to sweep multiple tau values. Defaults to 0.75.",
    )
    parser.add_argument(
        "--beta",
        action="append",
        type=float,
        help="Repeat to sweep multiple beta values. Defaults to 5.0.",
    )
    parser.add_argument(
        "--lambda-weight",
        dest="lambda_weights",
        action="append",
        type=float,
        help="Repeat to sweep multiple collaborative lambda values. Defaults to 1.0.",
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
        default="latent_sweep_summary.csv",
        help="Destination CSV path for the sweep summary.",
    )
    parser.add_argument(
        "--save-logs-dir",
        help="Optional directory to save full JSON logs for each run.",
    )
    parser.add_argument("--quiet", action="store_true", help="Disable step-by-step printing")
    args = parser.parse_args()

    utility_models = args.utility_model or ["individual", "collaborative"]
    choice_sets = args.choice_set or ["certainty1", "threshold"]
    taus = args.tau or [0.75]
    betas = args.beta or [5.0]
    lambda_weights = args.lambda_weights or [1.0]
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
    for utility_model, choice_set, tau, beta, lambda_weight, seed, sample_idx in product(
        utility_models,
        choice_sets,
        taus,
        betas,
        lambda_weights,
        seeds,
        sample_indices,
    ):
        if choice_set != "threshold" and tau != taus[0]:
            continue
        if utility_model == "individual" and lambda_weight != lambda_weights[0]:
            continue

        row_clues, col_clues, target_grid = load_dataset_sample(
            x_path=args.x_path,
            sample_idx=sample_idx,
            y_path=args.y_path,
        )
        max_turns = args.max_turns or default_max_turns(row_clues, col_clues)
        final_grid, log, candidate_steps = solve_latent_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            utility_model=utility_model,
            choice_set=choice_set,
            alpha=args.alpha,
            beta=beta,
            tau=tau,
            lambda_weight=lambda_weight,
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
                "solver": "latent_collab",
                "utility_model": utility_model,
                "choice_set": choice_set,
                "alpha": args.alpha,
                "beta": beta,
                "tau": tau,
                "lambda_weight": lambda_weight,
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
                    tau=tau,
                    beta=beta,
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
                "beta": beta,
                "tau": tau,
                "lambda_weight": lambda_weight,
                "seed": seed,
                "board_rows": len(row_clues),
                "board_cols": len(col_clues),
                "max_turns": max_turns,
                "unknown_cells": summary["unknown_cells"],
                "solved": summary["solved"],
                "matches_target": summary["matches_target"],
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
            f"choice_set={choice_set} beta={beta} tau={tau} "
            f"lambda={lambda_weight} seed={seed}"
        )

    write_csv(rows, args.output_csv)
    print(f"Completed {total_runs} run(s)")
    print(f"Saved sweep summary to {args.output_csv}")


if __name__ == "__main__":
    main()
