from __future__ import annotations

import argparse
import copy
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from solver_common import (
    EMPTY,
    FILLED,
    UNKNOWN,
    apply_move,
    build_log_payload,
    cell_to_char,
    count_unknown_cells,
    default_max_turns,
    generate_line_patterns,
    get_column,
    get_sample_indices,
    grids_equal,
    is_solved,
    load_dataset_sample,
    load_dataset_targets,
    load_npz_array,
    log_event,
    make_default_log_path,
    print_grid,
    save_log_json,
)


Candidate = Dict[str, Any]


def value_name(value: int) -> str:
    return "FILLED" if value == FILLED else "EMPTY"


def safe_line_probabilities(
    length: int,
    clues: List[int],
    current_line: List[int],
) -> Tuple[List[List[int]], List[float]]:
    patterns = generate_line_patterns(length, clues, current_line)
    if not patterns:
        return [], []

    pattern_count = float(len(patterns))
    probabilities = [
        sum(1 for pattern in patterns if pattern[i] == FILLED) / pattern_count
        for i in range(length)
    ]
    return patterns, probabilities


def include_action(choice_set: str, q_own: float, tau: float, eps: float = 1e-9) -> bool:
    if choice_set == "all_legal":
        return True
    if choice_set == "certainty1":
        return q_own >= 1.0 - eps
    if choice_set == "threshold":
        return q_own + eps >= tau
    raise ValueError(f"Unknown choice_set={choice_set}")


def build_uninformed_candidates_for_actor(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    actor: str,
) -> List[Candidate]:
    candidates: List[Candidate] = []

    if actor == "row":
        for row_idx, clue in enumerate(row_clues):
            for col_idx, cell in enumerate(grid[row_idx]):
                if cell != UNKNOWN:
                    continue
                for value in (FILLED, EMPTY):
                    candidates.append(
                        {
                            "actor": actor,
                            "row": row_idx,
                            "col": col_idx,
                            "value": value,
                            "value_name": value_name(value),
                            "q_own": 0.5,
                            "source_axis": "row",
                            "source_index": row_idx,
                            "source_clue": clue,
                            "source_pattern_count": 0,
                            "candidate_origin": "uninformed_fallback",
                        }
                    )
    else:
        n_rows = len(grid)
        for col_idx, clue in enumerate(col_clues):
            for row_idx in range(n_rows):
                if grid[row_idx][col_idx] != UNKNOWN:
                    continue
                for value in (FILLED, EMPTY):
                    candidates.append(
                        {
                            "actor": actor,
                            "row": row_idx,
                            "col": col_idx,
                            "value": value,
                            "value_name": value_name(value),
                            "q_own": 0.5,
                            "source_axis": "col",
                            "source_index": col_idx,
                            "source_clue": clue,
                            "source_pattern_count": 0,
                            "candidate_origin": "uninformed_fallback",
                        }
                    )
    return candidates


def softmax_probabilities(utilities: Sequence[float], beta: float) -> List[float]:
    finite_indices = [idx for idx, utility in enumerate(utilities) if math.isfinite(utility)]
    if not finite_indices:
        return [0.0 for _ in utilities]

    scaled = [beta * utilities[idx] for idx in finite_indices]
    max_scaled = max(scaled)
    exp_values = [math.exp(value - max_scaled) for value in scaled]
    total = sum(exp_values)
    probabilities = [0.0 for _ in utilities]
    for idx, exp_value in zip(finite_indices, exp_values):
        probabilities[idx] = exp_value / total
    return probabilities


def local_partner_information(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    actor: str,
    row: int,
    col: int,
    value: int,
) -> Tuple[Optional[float], int, int, bool]:
    if actor == "row":
        partner_line = get_column(grid, col)
        partner_clue = col_clues[col]
        partner_index = row
    else:
        partner_line = grid[row]
        partner_clue = row_clues[row]
        partner_index = col

    before_patterns = generate_line_patterns(len(partner_line), partner_clue, partner_line)
    before_count = len(before_patterns)
    if before_count == 0:
        return 0.0, 0, 0, True

    after_line = partner_line[:]
    after_line[partner_index] = value
    after_patterns = generate_line_patterns(len(after_line), partner_clue, after_line)
    after_count = len(after_patterns)
    if after_count == 0:
        return None, before_count, after_count, False

    info_gain = math.log(before_count) - math.log(after_count)
    return info_gain, before_count, after_count, True


def build_candidates_for_actor(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    actor: str,
    choice_set: str,
    tau: float,
) -> List[Candidate]:
    candidates: List[Candidate] = []

    if actor == "row":
        for row_idx, clue in enumerate(row_clues):
            current_line = grid[row_idx]
            patterns, fill_probabilities = safe_line_probabilities(len(current_line), clue, current_line)
            if not patterns:
                continue

            for col_idx, cell in enumerate(current_line):
                if cell != UNKNOWN:
                    continue

                q_filled = fill_probabilities[col_idx]
                q_empty = 1.0 - q_filled
                for value, q_own in ((FILLED, q_filled), (EMPTY, q_empty)):
                    if not include_action(choice_set, q_own, tau):
                        continue
                    candidates.append(
                        {
                            "actor": actor,
                            "row": row_idx,
                            "col": col_idx,
                            "value": value,
                            "value_name": value_name(value),
                            "q_own": q_own,
                            "source_axis": "row",
                            "source_index": row_idx,
                            "source_clue": clue,
                            "source_pattern_count": len(patterns),
                            "candidate_origin": choice_set,
                        }
                    )
    else:
        n_rows = len(grid)
        n_cols = len(grid[0])
        for col_idx, clue in enumerate(col_clues):
            current_line = get_column(grid, col_idx)
            patterns, fill_probabilities = safe_line_probabilities(len(current_line), clue, current_line)
            if not patterns:
                continue

            for row_idx in range(n_rows):
                if grid[row_idx][col_idx] != UNKNOWN:
                    continue

                q_filled = fill_probabilities[row_idx]
                q_empty = 1.0 - q_filled
                for value, q_own in ((FILLED, q_filled), (EMPTY, q_empty)):
                    if not include_action(choice_set, q_own, tau):
                        continue
                    candidates.append(
                        {
                            "actor": actor,
                            "row": row_idx,
                            "col": col_idx,
                            "value": value,
                            "value_name": value_name(value),
                            "q_own": q_own,
                            "source_axis": "col",
                            "source_index": col_idx,
                            "source_clue": clue,
                            "source_pattern_count": len(patterns),
                            "candidate_origin": choice_set,
                        }
                    )

    return candidates


def prepare_candidates_for_actor(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    actor: str,
    choice_set: str,
    tau: float,
) -> Tuple[List[Candidate], str, bool]:
    candidates = build_candidates_for_actor(
        grid=grid,
        row_clues=row_clues,
        col_clues=col_clues,
        actor=actor,
        choice_set=choice_set,
        tau=tau,
    )
    if candidates:
        return candidates, choice_set, False

    if choice_set != "all_legal":
        fallback_candidates = build_candidates_for_actor(
            grid=grid,
            row_clues=row_clues,
            col_clues=col_clues,
            actor=actor,
            choice_set="all_legal",
            tau=tau,
        )
        if fallback_candidates:
            for candidate in fallback_candidates:
                candidate["candidate_origin"] = "all_legal_fallback"
            return fallback_candidates, "all_legal_fallback", True

    fallback_candidates = build_uninformed_candidates_for_actor(
        grid=grid,
        row_clues=row_clues,
        col_clues=col_clues,
        actor=actor,
    )
    return fallback_candidates, "uninformed_fallback", True


def score_candidates(
    candidates: List[Candidate],
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    utility_model: str,
    alpha: float,
    beta: float,
    lambda_weight: float,
) -> None:
    utilities: List[float] = []
    for candidate in candidates:
        info_gain, before_count, after_count, partner_compatible = local_partner_information(
            grid=grid,
            row_clues=row_clues,
            col_clues=col_clues,
            actor=candidate["actor"],
            row=candidate["row"],
            col=candidate["col"],
            value=candidate["value"],
        )

        candidate["b_partner_local"] = info_gain
        candidate["partner_pattern_count_before"] = before_count
        candidate["partner_pattern_count_after"] = after_count
        candidate["partner_compatible"] = partner_compatible

        utility = alpha * candidate["q_own"]
        if utility_model == "collaborative":
            if info_gain is None:
                utility = -math.inf
            else:
                utility += lambda_weight * info_gain
        candidate["utility"] = utility
        utilities.append(utility)

    probabilities = softmax_probabilities(utilities, beta)
    for candidate, probability in zip(candidates, probabilities):
        candidate["probability"] = probability


def choose_candidate(
    candidates: List[Candidate],
    rng: np.random.Generator,
) -> Optional[Candidate]:
    if not candidates:
        return None

    probabilities = np.asarray([candidate.get("probability", 0.0) for candidate in candidates], dtype=float)
    total = float(probabilities.sum())
    if total <= 0.0:
        return None

    probabilities = probabilities / total
    chosen_idx = int(rng.choice(len(candidates), p=probabilities))
    return candidates[chosen_idx]


def move_from_candidate(candidate: Candidate) -> Tuple[int, int, int, str]:
    b_partner = candidate.get("b_partner_local")
    if b_partner is None:
        b_text = "None"
    else:
        b_text = f"{b_partner:.4f}"

    explanation = (
        f"{candidate['source_axis']}={candidate['source_index']}, "
        f"{candidate['source_axis']}_clue={candidate['source_clue']}, "
        f"Q_own={candidate['q_own']:.4f}, "
        f"B_partner_local={b_text}, "
        f"utility={candidate['utility']:.4f}, "
        f"prob={candidate['probability']:.4f}"
    )
    return candidate["row"], candidate["col"], candidate["value"], explanation


def candidate_table_entry(turn: int, candidate: Candidate, chosen: bool) -> Dict[str, Any]:
    return {
        "turn": turn,
        "agent": candidate["actor"],
        "row": candidate["row"],
        "col": candidate["col"],
        "value": candidate["value"],
        "value_name": candidate["value_name"],
        "source_axis": candidate["source_axis"],
        "source_index": candidate["source_index"],
        "source_clue": candidate["source_clue"],
        "source_pattern_count": candidate["source_pattern_count"],
        "candidate_origin": candidate.get("candidate_origin"),
        "q_own": candidate["q_own"],
        "b_partner_local": candidate["b_partner_local"],
        "partner_pattern_count_before": candidate["partner_pattern_count_before"],
        "partner_pattern_count_after": candidate["partner_pattern_count_after"],
        "partner_compatible": candidate["partner_compatible"],
        "utility": candidate["utility"],
        "probability": candidate["probability"],
        "chosen": chosen,
    }


def solve_latent_turn_based_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    utility_model: str = "individual",
    choice_set: str = "certainty1",
    alpha: float = 1.0,
    beta: float = 5.0,
    tau: float = 0.75,
    lambda_weight: float = 1.0,
    max_turns: int = 1000,
    seed: int = 0,
    verbose: bool = True,
) -> Tuple[List[List[int]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)
    rng = np.random.default_rng(seed)

    grid = [[UNKNOWN for _ in range(n_cols)] for _ in range(n_rows)]
    log: List[Dict[str, Any]] = []
    candidate_steps: List[Dict[str, Any]] = []

    turn = 0
    log_event(
        log,
        turn=0,
        agent="system",
        action="start",
        grid_before=None,
        grid_after=grid,
        move=None,
    )

    if verbose:
        print("Initial grid:")
        print_grid(grid)

    while turn < max_turns and not is_solved(grid):
        for actor in ("row", "col"):
            if turn >= max_turns or is_solved(grid):
                break

            turn += 1
            grid_before = copy.deepcopy(grid)
            candidates, effective_choice_set, choice_fallback_used = prepare_candidates_for_actor(
                grid=grid,
                row_clues=row_clues,
                col_clues=col_clues,
                actor=actor,
                choice_set=choice_set,
                tau=tau,
            )
            score_candidates(
                candidates=candidates,
                grid=grid,
                row_clues=row_clues,
                col_clues=col_clues,
                utility_model=utility_model,
                alpha=alpha,
                beta=beta,
                lambda_weight=lambda_weight,
            )

            effective_utility_model = utility_model
            utility_fallback_used = False
            chosen_candidate = choose_candidate(candidates, rng)
            if chosen_candidate is None:
                score_candidates(
                    candidates=candidates,
                    grid=grid,
                    row_clues=row_clues,
                    col_clues=col_clues,
                    utility_model="individual",
                    alpha=alpha,
                    beta=beta,
                    lambda_weight=lambda_weight,
                )
                effective_utility_model = "individual_fallback"
                utility_fallback_used = True
                chosen_candidate = choose_candidate(candidates, rng)
            if chosen_candidate is None:
                raise ValueError(
                    f"No selectable candidate for actor={actor} at turn={turn} "
                    f"with {len(candidates)} candidate(s)"
                )
            candidate_table_rows = [
                candidate_table_entry(turn, candidate, candidate is chosen_candidate)
                for candidate in candidates
            ]
            candidate_steps.append(
                {
                    "turn": turn,
                    "agent": actor,
                    "requested_choice_set": choice_set,
                    "effective_choice_set": effective_choice_set,
                    "requested_utility_model": utility_model,
                    "effective_utility_model": effective_utility_model,
                    "candidates": candidate_table_rows,
                }
            )

            move = move_from_candidate(chosen_candidate)
            apply_move(grid, move)
            log_event(log, turn, actor, "write", grid_before, grid, move)
            log[-1]["decision"] = {
                "utility_model": utility_model,
                "effective_utility_model": effective_utility_model,
                "utility_fallback_used": utility_fallback_used,
                "choice_set": choice_set,
                "effective_choice_set": effective_choice_set,
                "choice_fallback_used": choice_fallback_used,
                "alpha": alpha,
                "beta": beta,
                "tau": tau,
                "lambda_weight": lambda_weight,
                "candidate_count": len(candidates),
                "chosen_probability": chosen_candidate["probability"],
                "chosen_q_own": chosen_candidate["q_own"],
                "chosen_b_partner_local": chosen_candidate["b_partner_local"],
                "chosen_utility": chosen_candidate["utility"],
                "chosen_candidate_origin": chosen_candidate.get("candidate_origin"),
                "partner_pattern_count_before": chosen_candidate["partner_pattern_count_before"],
                "partner_pattern_count_after": chosen_candidate["partner_pattern_count_after"],
                "partner_compatible": chosen_candidate["partner_compatible"],
            }
            if verbose:
                row, col, value, explanation = move
                print(
                    f"Turn {turn} | {actor.upper()} writes ({row}, {col}) = "
                    f"{cell_to_char(value)} | {explanation}"
                )
                print_grid(grid)

    log_event(log, turn + 1, "system", "end", grid, grid, None)

    if verbose:
        print("Final grid:")
        print_grid(grid)

    return grid, log, candidate_steps


def augment_payload_with_candidate_tables(
    payload: Dict[str, Any],
    candidate_steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload["candidate_steps"] = candidate_steps

    decision_events = [
        event for event in payload["events"]
        if event["action"] == "write" and "decision" in event
    ]
    candidate_counts = [event["decision"]["candidate_count"] for event in decision_events]
    chosen_probabilities = [
        event["decision"]["chosen_probability"]
        for event in decision_events
        if event["decision"]["chosen_probability"] is not None
    ]
    chosen_q_values = [
        event["decision"]["chosen_q_own"]
        for event in decision_events
        if event["decision"]["chosen_q_own"] is not None
    ]
    chosen_partner_values = [
        event["decision"]["chosen_b_partner_local"]
        for event in decision_events
        if event["decision"]["chosen_b_partner_local"] is not None
    ]

    payload["summary"]["mean_candidate_count"] = (
        float(sum(candidate_counts)) / max(1, len(candidate_counts))
    )
    payload["summary"]["mean_chosen_probability"] = (
        float(sum(chosen_probabilities)) / max(1, len(chosen_probabilities))
    )
    payload["summary"]["mean_chosen_q_own"] = (
        float(sum(chosen_q_values)) / max(1, len(chosen_q_values))
    )
    payload["summary"]["mean_chosen_b_partner_local"] = (
        float(sum(chosen_partner_values)) / max(1, len(chosen_partner_values))
    )
    payload["summary"]["candidate_table_steps"] = len(candidate_steps)
    payload["summary"]["candidate_table_rows"] = sum(len(step["candidates"]) for step in candidate_steps)
    payload["summary"]["choice_fallback_steps"] = sum(
        1 for event in decision_events if event["decision"].get("choice_fallback_used")
    )
    payload["summary"]["utility_fallback_steps"] = sum(
        1 for event in decision_events if event["decision"].get("utility_fallback_used")
    )
    return payload


def default_solver_tag(utility_model: str, choice_set: str, tau: float, beta: float, seed: int) -> str:
    tau_token = f"tau-{tau:.2f}".replace(".", "p")
    beta_token = f"beta-{beta:.2f}".replace(".", "p")
    return f"latent-{utility_model}__{choice_set}__{tau_token}__{beta_token}__seed-{seed}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Simulate stochastic latent-choice row/column agents on the collaborative nonogram task."
    )
    parser.add_argument("--x-path", help="Path to packed clue x_*.npz file")
    parser.add_argument("--y-path", help="Optional path to target y_*.npz file")
    parser.add_argument("--sample-idx", type=int, default=0, help="Dataset sample index")
    parser.add_argument("--all-samples", action="store_true", help="Run all samples in the dataset")
    parser.add_argument("--sample-start", type=int, help="Optional batch start index (inclusive)")
    parser.add_argument("--sample-end", type=int, help="Optional batch end index (exclusive)")
    parser.add_argument(
        "--utility-model",
        choices=["individual", "collaborative"],
        default="individual",
        help="Whether utility uses only Q_own or Q_own + lambda * B_partner_local.",
    )
    parser.add_argument(
        "--choice-set",
        choices=["certainty1", "threshold", "all_legal"],
        default="certainty1",
        help="Candidate action family for the stochastic policy.",
    )
    parser.add_argument("--alpha", type=float, default=1.0, help="Weight on Q_own.")
    parser.add_argument("--beta", type=float, default=5.0, help="Inverse temperature for softmax.")
    parser.add_argument(
        "--tau",
        type=float,
        default=0.75,
        help="Threshold for the threshold choice set. Ignored otherwise.",
    )
    parser.add_argument(
        "--lambda-weight",
        type=float,
        default=1.0,
        help="Weight on local partner-information gain in collaborative utility.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed for stochastic choice.")
    parser.add_argument(
        "--max-turns",
        type=int,
        help="Maximum number of turns. Default is 2 * number_of_cells.",
    )
    parser.add_argument("--quiet", action="store_true", help="Disable step-by-step printing")
    parser.add_argument("--json-path", help="Output JSON path for single-sample runs")
    parser.add_argument("--output-dir", help="Output directory for batch logs")
    args = parser.parse_args()

    if args.choice_set == "threshold" and not (0.0 <= args.tau <= 1.0):
        raise ValueError("--tau must be in [0, 1]")

    batch_mode = args.all_samples or args.sample_start is not None or args.sample_end is not None
    if batch_mode and not args.x_path:
        raise ValueError("Batch mode requires --x-path")
    if batch_mode and args.json_path:
        raise ValueError("Use --output-dir instead of --json-path in batch mode")

    if args.x_path is None:
        raise ValueError("latent_collab.py currently requires --x-path")

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

    print(f"Running {len(sample_indices)} sample(s) from {args.x_path}")
    single_dataset_run = len(sample_indices) == 1 and not batch_mode

    for idx in sample_indices:
        row_clues, col_clues, target_grid = load_dataset_sample(
            x_path=args.x_path,
            sample_idx=idx,
            y_path=args.y_path,
        )
        max_turns = args.max_turns or default_max_turns(row_clues, col_clues)
        final_grid, log, candidate_steps = solve_latent_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            utility_model=args.utility_model,
            choice_set=args.choice_set,
            alpha=args.alpha,
            beta=args.beta,
            tau=args.tau,
            lambda_weight=args.lambda_weight,
            max_turns=max_turns,
            seed=args.seed,
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
            sample_idx=idx,
            metadata_extra={
                "solver": "latent_collab",
                "utility_model": args.utility_model,
                "choice_set": args.choice_set,
                "alpha": args.alpha,
                "beta": args.beta,
                "tau": args.tau,
                "lambda_weight": args.lambda_weight,
                "seed": args.seed,
                "row_strategy": "softmax",
                "col_strategy": "softmax",
                "strategy": "softmax",
            },
        )
        payload = augment_payload_with_candidate_tables(payload, candidate_steps)

        if single_dataset_run and args.json_path:
            output_path = args.json_path
        else:
            output_path = make_default_log_path(
                x_path=args.x_path,
                solver_tag=default_solver_tag(
                    utility_model=args.utility_model,
                    choice_set=args.choice_set,
                    tau=args.tau,
                    beta=args.beta,
                    seed=args.seed,
                ),
                sample_idx=idx,
                output_dir=args.output_dir,
            )
        save_log_json(payload, output_path)

        unresolved = count_unknown_cells(final_grid)
        matches_target = None if target_grid is None else grids_equal(final_grid, target_grid)
        print(
            f"Sample {idx}: unknown_cells={unresolved} "
            f"matches_target={matches_target} saved={output_path}"
        )


if __name__ == "__main__":
    main()
