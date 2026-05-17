"""Run controlled nonogram solver series on a controlled CSV dataset.

Flag descriptions:
- --puzzle-csv: controlled puzzle CSV produced by scripts/build_controlled_dataset.py.
- --solver: one solver or one solver series. Defaults to original_series.
    - Series choices:
      - original_series: determin_ind, determin_dyad, stoch_ind, stoch_dyad.
      - baseline_series: row_only_ind, col_only_ind, random_legal.
      - value_series: value_full_ind, value_row_only_ind, value_col_only_ind,
        value_dyad_board_update, value_dyad_partner_info.
    - Single-solver choices for debugging:
      - determin_ind, determin_dyad, stoch_ind, stoch_dyad,
      - row_only_ind, col_only_ind, random_legal,
      - value_full_ind, value_row_only_ind, value_col_only_ind,
        value_dyad_board_update, value_dyad_partner_info.
- --puzzle-id: run one puzzle by its puzzle_id column.
- --puzzle-idx: run one puzzle by CSV row index when --puzzle-id and range flags are not used.
- --all-puzzles: run every puzzle in the CSV.
- --puzzle-start / --puzzle-end: half-open row range [start, end) for batch runs.
- --max-turns: optional step budget; default is 2 * number_of_cells.
- --output-dir: directory where solver JSON logs are written.
- --quiet: suppress turn-by-turn solver printing.
- --strategy: only determin_ind, row_only_ind, and col_only_ind; deterministic move ordering.
- --row-strategy / --col-strategy: only determin_dyad; row/column deterministic move ordering.
- --utility-model: only stoch_dyad; ind means Q-only, dyad means Q + lambda_partner * B_partner.
- --choice-set: only stoch_ind and stoch_dyad; stochastic candidate family: certainty1, threshold, or all_legal.
- --q-threshold: only stoch_ind and stoch_dyad with --choice-set threshold; Q cutoff for candidates.
- --alpha: only stoch_ind and stoch_dyad; weight on Q in the legacy stochastic solvers.
- --beta-softmax: only stoch_ind and stoch_dyad; inverse softmax temperature.
- --fallback: only stoch_ind and stoch_dyad; fallback mode: none, all_legal, or uninformed.
- --value-model: only value_series or single value_* solvers; choose one formula or all.
    - all expands to random, correctness_only, correctness_info,
      correctness_cost_ambiguity, full_value_cost_ambiguity.
- --policy: only value_series or single value_* solvers; action-selection policy: random, argmax, or softmax.
- --beta-info: only value_* solvers except value_model=random/correctness_only; weight on entropy information value I.
- --lambda-cost: only value_* solvers with cost variants; weight on ambiguity cost C_ambiguity.
- --lambda-partner: stoch_dyad and value_dyad_partner_info; partner-information weight.
- --tau-decision: only value_* solvers with --policy softmax; softmax temperature.
- --seed: random_legal, stoch_* solvers, and value_* solvers; random seed.

Expected output files:
- JSON logs under the requested results/logs subfolder.
- Filenames include the solver condition, so different value_model/policy settings do not overwrite each other.

Command to run code:
1. Original determin/stoch series, 4 solver conditions, output folder results/logs/controlled_original:
poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver original_series --all-puzzles --output-dir results/logs/controlled_original --quiet

2. Baseline series, 3 solver conditions, output folder results/logs/controlled_baseline:
poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver baseline_series --all-puzzles --output-dir results/logs/controlled_baseline --quiet

3. Value deterministic/argmax series, 25 solver conditions, output folder results/logs/controlled_value_argmax:
poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver value_series --value-model all --policy argmax --beta-info 1.0 --lambda-cost 1.0 --lambda-partner 1.0 --all-puzzles --output-dir results/logs/controlled_value_argmax --quiet

4. Value stochastic/softmax series, 25 solver conditions, output folder results/logs/controlled_value_softmax:
poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver value_series --value-model all --policy softmax --beta-info 1.0 --lambda-cost 1.0 --lambda-partner 1.0 --tau-decision 0.2 --seed 0 --all-puzzles --output-dir results/logs/controlled_value_softmax --quiet

Value-series combination count:
- One value policy command runs 5 value solvers * 5 value formulas = 25 conditions.
- Running both argmax and softmax gives 25 * 2 = 50 value-series conditions.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from baselines import solve_partial_ind_logged, solve_random_legal_logged  # noqa: E402
from determin_dyad import solve_two_agent_turn_based_logged  # noqa: E402
from determin_ind import solve_ind_turn_based_logged  # noqa: E402
from solver_common import (  # noqa: E402
    build_log_payload,
    default_max_turns,
    load_controlled_puzzle_rows,
    load_controlled_puzzle_sample,
    save_log_json,
)
from stoch_dyad import augment_payload_with_candidate_tables as augment_dyad_payload  # noqa: E402
from stoch_dyad import solve_stoch_turn_based_logged  # noqa: E402
from stoch_ind import augment_payload_with_candidate_tables as augment_ind_payload  # noqa: E402
from stoch_ind import solve_stoch_ind_logged  # noqa: E402
from value_model import augment_payload_with_value_candidate_tables  # noqa: E402
from value_model import solve_value_dyad_logged, solve_value_ind_logged  # noqa: E402


ORIGINAL_SOLVERS = ["determin_ind", "determin_dyad", "stoch_ind", "stoch_dyad"]
BASELINE_SOLVERS = ["row_only_ind", "col_only_ind", "random_legal"]
VALUE_SOLVERS = [
    "value_full_ind",
    "value_row_only_ind",
    "value_col_only_ind",
    "value_dyad_board_update",
    "value_dyad_partner_info",
]
VALUE_MODELS = [
    "random",
    "correctness_only",
    "correctness_info",
    "correctness_cost_ambiguity",
    "full_value_cost_ambiguity",
]
SOLVER_SERIES = {
    "original_series": ORIGINAL_SOLVERS,
    "baseline_series": BASELINE_SOLVERS,
    "value_series": VALUE_SOLVERS,
}


def selected_indices(args: argparse.Namespace, total_rows: int) -> List[int]:
    if args.puzzle_id is not None:
        return [-1]
    if args.all_puzzles or args.puzzle_start is not None or args.puzzle_end is not None:
        start = 0 if args.puzzle_start is None else args.puzzle_start
        end = total_rows if args.puzzle_end is None else args.puzzle_end
        if start < 0 or end < 0 or start > end or end > total_rows:
            raise ValueError(f"Invalid puzzle range [{start}, {end}) for {total_rows} rows")
        return list(range(start, end))
    return [args.puzzle_idx]


def token(value: Any) -> str:
    text = str(value)
    return text.replace("/", "_").replace(" ", "-").replace(".", "p")


def condition_tag(payload: Dict[str, Any]) -> str:
    metadata = payload["metadata"]
    solver = metadata["solver"]
    if solver.startswith("value_"):
        parts = [
            solver,
            metadata.get("utility_model"),
            metadata.get("policy"),
            f"bi-{metadata.get('beta_info')}",
            f"lc-{metadata.get('lambda_cost')}",
            f"lp-{metadata.get('lambda_partner')}",
            f"tau-{metadata.get('tau_decision')}",
            f"seed-{metadata.get('seed')}",
        ]
        return "__".join(token(part) for part in parts if part is not None)
    if solver.startswith("stoch_"):
        parts = [
            solver,
            metadata.get("utility_model"),
            metadata.get("choice_set"),
            f"qthr-{metadata.get('q_threshold')}",
            f"bsoft-{metadata.get('beta_softmax')}",
            f"lp-{metadata.get('lambda_partner')}",
            f"seed-{metadata.get('seed')}",
        ]
        return "__".join(token(part) for part in parts if part is not None)
    return token(solver)


def output_path(output_dir: str, puzzle_id: str, payload: Dict[str, Any]) -> str:
    safe_puzzle_id = puzzle_id.replace("/", "_")
    return str(Path(output_dir) / f"{safe_puzzle_id}__{condition_tag(payload)}.json")


def resolve_solvers(solver: str) -> List[str]:
    if solver in SOLVER_SERIES:
        return SOLVER_SERIES[solver]
    return [solver]


def resolve_value_models(value_model: str, solvers: Sequence[str]) -> List[str]:
    uses_value_solver = any(solver.startswith("value_") for solver in solvers)
    if value_model == "all":
        if not uses_value_solver:
            raise ValueError("--value-model all can only be used with value_series or value_* solvers")
        return VALUE_MODELS
    return [value_model]


def expanded_conditions(args: argparse.Namespace) -> List[Tuple[str, str]]:
    solvers = resolve_solvers(args.solver)
    value_models = resolve_value_models(args.value_model, solvers)
    conditions: List[Tuple[str, str]] = []
    for solver in solvers:
        if solver.startswith("value_"):
            for value_model in value_models:
                conditions.append((solver, value_model))
        else:
            conditions.append((solver, args.value_model))
    return conditions


def run_solver(
    solver: str,
    value_model: str,
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    target_grid: List[List[int]],
    metadata: Dict[str, Any],
    args: argparse.Namespace,
) -> Dict[str, Any]:
    max_turns = args.max_turns or default_max_turns(row_clues, col_clues)
    candidate_steps = None

    if solver == "determin_ind":
        final_grid, log = solve_ind_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            strategy=args.strategy,
            max_turns=max_turns,
            verbose=not args.quiet,
        )
        solver_metadata: Dict[str, Any] = {
            "solver": solver,
            "strategy": args.strategy,
            "row_strategy": args.strategy,
            "col_strategy": args.strategy,
        }
    elif solver == "row_only_ind":
        final_grid, log = solve_partial_ind_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            axis="row",
            strategy=args.strategy,
            max_turns=max_turns,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "information_access": "row_only",
            "strategy": args.strategy,
            "row_strategy": args.strategy,
            "col_strategy": None,
        }
    elif solver == "col_only_ind":
        final_grid, log = solve_partial_ind_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            axis="col",
            strategy=args.strategy,
            max_turns=max_turns,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "information_access": "col_only",
            "strategy": args.strategy,
            "row_strategy": None,
            "col_strategy": args.strategy,
        }
    elif solver == "random_legal":
        final_grid, log = solve_random_legal_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            max_turns=max_turns,
            seed=args.seed,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "information_access": "full_information",
            "strategy": "random_legal",
            "row_strategy": "random_legal",
            "col_strategy": "random_legal",
            "seed": args.seed,
        }
    elif solver == "determin_dyad":
        final_grid, log = solve_two_agent_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            row_strategy=args.row_strategy,
            col_strategy=args.col_strategy,
            max_turns=max_turns,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "row_strategy": args.row_strategy,
            "col_strategy": args.col_strategy,
        }
    elif solver == "stoch_ind":
        final_grid, log, candidate_steps = solve_stoch_ind_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            choice_set=args.choice_set,
            alpha=args.alpha,
            beta_softmax=args.beta_softmax,
            q_threshold=args.q_threshold,
            fallback=args.fallback,
            max_turns=max_turns,
            seed=args.seed,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "utility_model": "ind",
            "choice_set": args.choice_set,
            "alpha": args.alpha,
            "beta_softmax": args.beta_softmax,
            "q_threshold": args.q_threshold,
            "lambda_partner": 0.0,
            "fallback": args.fallback,
            "seed": args.seed,
            "strategy": "softmax",
        }
    elif solver == "stoch_dyad":
        final_grid, log, candidate_steps = solve_stoch_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            utility_model=args.utility_model,
            choice_set=args.choice_set,
            alpha=args.alpha,
            beta_softmax=args.beta_softmax,
            q_threshold=args.q_threshold,
            lambda_partner=args.lambda_partner,
            fallback=args.fallback,
            max_turns=max_turns,
            seed=args.seed,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "utility_model": args.utility_model,
            "choice_set": args.choice_set,
            "alpha": args.alpha,
            "beta_softmax": args.beta_softmax,
            "q_threshold": args.q_threshold,
            "lambda_partner": args.lambda_partner,
            "fallback": args.fallback,
            "seed": args.seed,
            "strategy": "softmax",
            "row_strategy": "softmax",
            "col_strategy": "softmax",
        }
    elif solver in {"value_full_ind", "value_row_only_ind", "value_col_only_ind"}:
        agent_view = {
            "value_full_ind": "full",
            "value_row_only_ind": "row",
            "value_col_only_ind": "col",
        }[solver]
        final_grid, log, candidate_steps = solve_value_ind_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            agent_view=agent_view,
            value_model=value_model,
            policy=args.policy,
            beta_info=args.beta_info,
            lambda_cost=args.lambda_cost,
            tau_decision=args.tau_decision,
            max_turns=max_turns,
            seed=args.seed,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "utility_model": value_model,
            "information_access": f"{agent_view}_information",
            "policy": args.policy,
            "beta_info": args.beta_info,
            "lambda_cost": args.lambda_cost,
            "lambda_partner": 0.0,
            "tau_decision": args.tau_decision,
            "seed": args.seed,
            "strategy": args.policy,
            "row_strategy": args.policy if agent_view in {"full", "row"} else None,
            "col_strategy": args.policy if agent_view in {"full", "col"} else None,
        }
    elif solver in {"value_dyad_board_update", "value_dyad_partner_info"}:
        include_partner_info = solver == "value_dyad_partner_info"
        final_grid, log, candidate_steps = solve_value_dyad_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            value_model=value_model,
            policy=args.policy,
            beta_info=args.beta_info,
            lambda_cost=args.lambda_cost,
            lambda_partner=args.lambda_partner,
            include_partner_info=include_partner_info,
            tau_decision=args.tau_decision,
            max_turns=max_turns,
            seed=args.seed,
            verbose=not args.quiet,
        )
        solver_metadata = {
            "solver": solver,
            "utility_model": value_model,
            "information_access": "dyad_row_col",
            "collaboration_model": "partner_information" if include_partner_info else "board_update_only",
            "policy": args.policy,
            "beta_info": args.beta_info,
            "lambda_cost": args.lambda_cost,
            "lambda_partner": args.lambda_partner if include_partner_info else 0.0,
            "tau_decision": args.tau_decision,
            "seed": args.seed,
            "strategy": args.policy,
            "row_strategy": args.policy,
            "col_strategy": args.policy,
        }
    else:
        raise ValueError(f"Unknown solver={solver}")

    payload = build_log_payload(
        events=log,
        row_clues=row_clues,
        col_clues=col_clues,
        max_turns=max_turns,
        final_grid=final_grid,
        target_grid=target_grid,
        x_path=metadata["puzzle_csv"],
        y_path=None,
        sample_idx=metadata["puzzle_idx"],
        metadata_extra={
            **solver_metadata,
            "dataset_type": "controlled_csv",
            "puzzle_id": metadata["puzzle_id"],
            "controlled_metrics": metadata,
        },
    )
    if solver == "stoch_ind" and candidate_steps is not None:
        payload = augment_ind_payload(payload, candidate_steps)
    if solver == "stoch_dyad" and candidate_steps is not None:
        payload = augment_dyad_payload(payload, candidate_steps)
    if solver.startswith("value_") and candidate_steps is not None:
        payload = augment_payload_with_value_candidate_tables(payload, candidate_steps)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run solvers on controlled puzzle CSV rows."
    )
    parser.add_argument("--puzzle-csv", required=True, help="Controlled puzzle CSV path.")
    parser.add_argument(
        "--solver",
        choices=[
            "original_series",
            "baseline_series",
            "value_series",
            "determin_ind",
            "determin_dyad",
            "row_only_ind",
            "col_only_ind",
            "random_legal",
            "stoch_ind",
            "stoch_dyad",
            "value_full_ind",
            "value_row_only_ind",
            "value_col_only_ind",
            "value_dyad_board_update",
            "value_dyad_partner_info",
        ],
        default="original_series",
        help="Run one solver or one solver series. Defaults to original_series.",
    )
    parser.add_argument("--puzzle-id", help="Run one puzzle by puzzle_id.")
    parser.add_argument("--puzzle-idx", type=int, default=0, help="Run one puzzle by row index.")
    parser.add_argument("--all-puzzles", action="store_true", help="Run all CSV rows.")
    parser.add_argument("--puzzle-start", type=int, help="Batch start index, inclusive.")
    parser.add_argument("--puzzle-end", type=int, help="Batch end index, exclusive.")
    parser.add_argument("--max-turns", type=int, help="Maximum solver turns.")
    parser.add_argument("--output-dir", default="results/logs/controlled_original", help="JSON output directory.")
    parser.add_argument("--quiet", action="store_true", help="Disable step-by-step solver printing.")
    parser.add_argument(
        "--strategy",
        choices=["first", "random", "most_constrained"],
        default="first",
        help="Only determin_ind, row_only_ind, col_only_ind: deterministic move ordering.",
    )
    parser.add_argument(
        "--row-strategy",
        choices=["first", "random", "most_constrained"],
        default="first",
        help="Only determin_dyad: row-agent deterministic move ordering.",
    )
    parser.add_argument(
        "--col-strategy",
        choices=["first", "random", "most_constrained"],
        default="first",
        help="Only determin_dyad: column-agent deterministic move ordering.",
    )
    parser.add_argument(
        "--utility-model",
        choices=["ind", "dyad"],
        default="ind",
        help="Only stoch_dyad: legacy utility family, ind=Q only, dyad=Q + partner information.",
    )
    parser.add_argument(
        "--choice-set",
        choices=["certainty1", "threshold", "all_legal"],
        default="certainty1",
        help="Only stoch_ind/stoch_dyad: candidate family.",
    )
    parser.add_argument("--alpha", type=float, default=1.0, help="Only stoch_ind/stoch_dyad: weight on Q.")
    parser.add_argument(
        "--beta-softmax",
        type=float,
        default=5.0,
        help="Only stoch_ind/stoch_dyad: inverse softmax temperature.",
    )
    parser.add_argument(
        "--q-threshold",
        type=float,
        default=0.75,
        help="Only stoch_ind/stoch_dyad with --choice-set threshold: Q cutoff.",
    )
    parser.add_argument(
        "--lambda-partner",
        type=float,
        default=1.0,
        help="Only stoch_dyad and value_dyad_partner_info: partner-information weight.",
    )
    parser.add_argument(
        "--fallback",
        choices=["none", "all_legal", "uninformed"],
        default="uninformed",
        help="Only stoch_ind/stoch_dyad: fallback when requested choice set has no candidates.",
    )
    parser.add_argument(
        "--value-model",
        choices=[
            "all",
            "random",
            "correctness_only",
            "correctness_info",
            "correctness_cost_ambiguity",
            "full_value_cost_ambiguity",
        ],
        default="full_value_cost_ambiguity",
        help="Only value_series/value_*: scoring formula. Use all to run every value formula.",
    )
    parser.add_argument(
        "--policy",
        choices=["random", "argmax", "softmax"],
        default="argmax",
        help="Only value_series/value_*: choice policy.",
    )
    parser.add_argument(
        "--beta-info",
        type=float,
        default=1.0,
        help="Only value_series/value_* information variants: weight on entropy value I.",
    )
    parser.add_argument(
        "--lambda-cost",
        type=float,
        default=1.0,
        help="Only value_series/value_* cost variants: weight on ambiguity cost C_ambiguity.",
    )
    parser.add_argument(
        "--tau-decision",
        type=float,
        default=0.2,
        help="Only value_series/value_* with --policy softmax: softmax temperature.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="random_legal, stoch_* and value_*: random seed.",
    )
    args = parser.parse_args()

    rows = load_controlled_puzzle_rows(args.puzzle_csv)
    conditions = expanded_conditions(args)
    indices = selected_indices(args, total_rows=len(rows))

    written = 0
    for selected_idx in indices:
        row_clues, col_clues, target_grid, metadata = load_controlled_puzzle_sample(
            csv_path=args.puzzle_csv,
            puzzle_idx=0 if selected_idx < 0 else selected_idx,
            puzzle_id=args.puzzle_id,
        )
        for solver, value_model in conditions:
            payload = run_solver(
                solver=solver,
                value_model=value_model,
                row_clues=row_clues,
                col_clues=col_clues,
                target_grid=target_grid,
                metadata=metadata,
                args=args,
            )
            path = output_path(args.output_dir, metadata["puzzle_id"], payload)
            save_log_json(payload, path)
            written += 1
            print(
                f"Wrote puzzle_id={metadata['puzzle_id']} solver={solver} "
                f"utility_model={payload['metadata'].get('utility_model')} "
                f"policy={payload['metadata'].get('policy')} "
                f"success={payload['summary']['success']} path={path}"
            )

    print(f"Wrote {written} log(s)")


if __name__ == "__main__":
    main()
