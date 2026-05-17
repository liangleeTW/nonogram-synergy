"""Shared value-model agents for controlled nonogram simulations.

Short description:
- Builds candidate actions over unknown cells and scores them with
  V = Q + beta_info * I - lambda_cost * C_ambiguity.
- Supports full-information, row-only, column-only, and row/column dyad agents.

Expected output files:
- None directly. scripts/run_controlled_dataset.py writes JSON logs and candidate tables.

Command to run code:
- poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver value_series --value-model all --policy argmax --beta-info 1.0 --lambda-cost 1.0 --lambda-partner 1.0 --all-puzzles --output-dir results/logs/controlled_value_argmax --quiet
- poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver value_series --value-model all --policy softmax --beta-info 1.0 --lambda-cost 1.0 --lambda-partner 1.0 --tau-decision 0.2 --seed 0 --all-puzzles --output-dir results/logs/controlled_value_softmax --quiet

Flag descriptions:
- --value-model: scoring variant; random, correctness_only, correctness_info,
  correctness_cost_ambiguity, or full_value_cost_ambiguity.
- --policy: action selection rule; random, argmax, or softmax.
- --beta-info: weight on cell entropy information value I.
- --lambda-cost: weight on ambiguity cost C_ambiguity.
- --lambda-partner: dyad-only weight on partner information B_partner.
- --tau-decision: softmax temperature; lower values are more deterministic.
- --seed: random seed used for stochastic choice and argmax tie-breaking.
"""

from __future__ import annotations

import copy
import math
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from solver_common import (
    EMPTY,
    FILLED,
    UNKNOWN,
    Move,
    apply_move,
    cell_to_char,
    generate_line_patterns,
    get_column,
    is_solved,
    log_event,
    print_grid,
)


Candidate = Dict[str, Any]


def value_name(value: int) -> str:
    return "FILLED" if value == FILLED else "EMPTY"


def binary_entropy(probability: float) -> float:
    if probability <= 0.0 or probability >= 1.0:
        return 0.0
    return -(
        probability * math.log(probability)
        + (1.0 - probability) * math.log(1.0 - probability)
    )


def safe_patterns_and_probabilities(
    length: int,
    clues: Sequence[int],
    current_line: List[int],
) -> Tuple[List[List[int]], List[float]]:
    patterns = generate_line_patterns(length, clues, current_line)
    if not patterns:
        return [], []

    denominator = float(len(patterns))
    fill_probabilities = [
        sum(1 for pattern in patterns if pattern[index] == FILLED) / denominator
        for index in range(length)
    ]
    return patterns, fill_probabilities


def line_after_action(line: List[int], index: int, value: int) -> List[int]:
    updated = line[:]
    updated[index] = value
    return updated


def compatible_count_after(
    line: List[int],
    clue: Sequence[int],
    index: int,
    value: int,
) -> int:
    return len(generate_line_patterns(len(line), clue, line_after_action(line, index, value)))


def row_signal(
    grid: List[List[int]],
    row_clues: List[List[int]],
    row: int,
    col: int,
) -> Optional[Tuple[float, int]]:
    patterns, fill_probabilities = safe_patterns_and_probabilities(
        len(grid[row]),
        row_clues[row],
        grid[row],
    )
    if not patterns:
        return None
    return fill_probabilities[col], len(patterns)


def col_signal(
    grid: List[List[int]],
    col_clues: List[List[int]],
    row: int,
    col: int,
) -> Optional[Tuple[float, int]]:
    column = get_column(grid, col)
    patterns, fill_probabilities = safe_patterns_and_probabilities(
        len(column),
        col_clues[col],
        column,
    )
    if not patterns:
        return None
    return fill_probabilities[row], len(patterns)


def accessible_axes(agent_view: str, actor: str = "ind") -> Tuple[str, ...]:
    if agent_view == "full":
        return ("row", "col")
    if agent_view == "row":
        return ("row",)
    if agent_view == "col":
        return ("col",)
    if agent_view == "dyad":
        if actor not in {"row", "col"}:
            raise ValueError(f"Unknown dyad actor={actor}")
        return (actor,)
    raise ValueError(f"Unknown agent_view={agent_view}")


def belief_for_cell(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    row: int,
    col: int,
    axes: Sequence[str],
) -> Optional[Tuple[float, Dict[str, int]]]:
    probabilities: List[float] = []
    counts: Dict[str, int] = {}

    if "row" in axes:
        signal = row_signal(grid, row_clues, row, col)
        if signal is None:
            return None
        probability, count = signal
        probabilities.append(probability)
        counts["row_pattern_count"] = count

    if "col" in axes:
        signal = col_signal(grid, col_clues, row, col)
        if signal is None:
            return None
        probability, count = signal
        probabilities.append(probability)
        counts["col_pattern_count"] = count

    if not probabilities:
        return None
    return sum(probabilities) / len(probabilities), counts


def ambiguity_cost(counts: Dict[str, int], axes: Sequence[str]) -> float:
    cost = 0.0
    if "row" in axes:
        cost += math.log(max(1, counts.get("row_pattern_count", 0)))
    if "col" in axes:
        cost += math.log(max(1, counts.get("col_pattern_count", 0)))
    return cost


def action_is_compatible(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    row: int,
    col: int,
    value: int,
    axes: Sequence[str],
) -> bool:
    if "row" in axes:
        if compatible_count_after(grid[row], row_clues[row], col, value) == 0:
            return False
    if "col" in axes:
        column = get_column(grid, col)
        if compatible_count_after(column, col_clues[col], row, value) == 0:
            return False
    return True


def partner_information(
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
    elif actor == "col":
        partner_line = grid[row]
        partner_clue = row_clues[row]
        partner_index = col
    else:
        return None, 0, 0, True

    before_count = len(generate_line_patterns(len(partner_line), partner_clue, partner_line))
    if before_count == 0:
        return 0.0, 0, 0, True

    after_count = compatible_count_after(partner_line, partner_clue, partner_index, value)
    if after_count == 0:
        return None, before_count, after_count, False

    return math.log(before_count) - math.log(after_count), before_count, after_count, True


def candidate_value(
    model: str,
    q_correct: float,
    information_value: float,
    c_ambiguity: float,
    beta_info: float,
    lambda_cost: float,
) -> float:
    if model == "random":
        return 0.0
    if model == "correctness_only":
        return q_correct
    if model == "correctness_info":
        return q_correct + beta_info * information_value
    if model == "correctness_cost_ambiguity":
        return q_correct - lambda_cost * c_ambiguity
    if model == "full_value_cost_ambiguity":
        return q_correct + beta_info * information_value - lambda_cost * c_ambiguity
    raise ValueError(f"Unknown value_model={model}")


def build_value_candidates(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    agent_view: str,
    actor: str = "ind",
    value_model: str = "full_value_cost_ambiguity",
    beta_info: float = 1.0,
    lambda_cost: float = 1.0,
    lambda_partner: float = 0.0,
    include_partner_info: bool = False,
) -> List[Candidate]:
    axes = accessible_axes(agent_view, actor)
    candidates: List[Candidate] = []

    for row_idx, row_values in enumerate(grid):
        for col_idx, cell in enumerate(row_values):
            if cell != UNKNOWN:
                continue
            belief = belief_for_cell(
                grid=grid,
                row_clues=row_clues,
                col_clues=col_clues,
                row=row_idx,
                col=col_idx,
                axes=axes,
            )
            if belief is None:
                continue
            p_filled, counts = belief
            c_ambiguity = ambiguity_cost(counts, axes)
            information_value = binary_entropy(p_filled)

            for value in (FILLED, EMPTY):
                if not action_is_compatible(
                    grid=grid,
                    row_clues=row_clues,
                    col_clues=col_clues,
                    row=row_idx,
                    col=col_idx,
                    value=value,
                    axes=axes,
                ):
                    continue

                q_correct = p_filled if value == FILLED else 1.0 - p_filled
                base_value = candidate_value(
                    model=value_model,
                    q_correct=q_correct,
                    information_value=information_value,
                    c_ambiguity=c_ambiguity,
                    beta_info=beta_info,
                    lambda_cost=lambda_cost,
                )
                b_partner, before_count, after_count, partner_compatible = partner_information(
                    grid=grid,
                    row_clues=row_clues,
                    col_clues=col_clues,
                    actor=actor,
                    row=row_idx,
                    col=col_idx,
                    value=value,
                )
                total_value = base_value
                if include_partner_info:
                    if b_partner is None:
                        total_value = -math.inf
                    else:
                        total_value += lambda_partner * b_partner

                candidates.append(
                    {
                        "agent": actor,
                        "actor": actor,
                        "row": row_idx,
                        "col": col_idx,
                        "value": value,
                        "value_name": value_name(value),
                        "agent_view": agent_view,
                        "accessible_axes": "+".join(axes),
                        "value_model": value_model,
                        "q": q_correct,
                        "q_own": q_correct,
                        "i_entropy": information_value,
                        "c_ambiguity": c_ambiguity,
                        "base_value": base_value,
                        "b_partner": b_partner,
                        "b_partner_local": b_partner,
                        "partner_pattern_count_before": before_count,
                        "partner_pattern_count_after": after_count,
                        "partner_compatible": partner_compatible,
                        "utility": total_value,
                        "value_score": total_value,
                        "row_pattern_count": counts.get("row_pattern_count"),
                        "col_pattern_count": counts.get("col_pattern_count"),
                    }
                )

    return candidates


def softmax_probabilities(values: Sequence[float], tau_decision: float) -> List[float]:
    if tau_decision <= 0:
        raise ValueError("tau_decision must be positive")
    finite_indices = [idx for idx, value in enumerate(values) if math.isfinite(value)]
    if not finite_indices:
        return [0.0 for _ in values]

    scaled = [values[idx] / tau_decision for idx in finite_indices]
    max_scaled = max(scaled)
    exp_values = [math.exp(value - max_scaled) for value in scaled]
    total = sum(exp_values)
    probabilities = [0.0 for _ in values]
    for idx, exp_value in zip(finite_indices, exp_values):
        probabilities[idx] = exp_value / total
    return probabilities


def choose_candidate(
    candidates: List[Candidate],
    policy: str,
    rng: np.random.Generator,
    tau_decision: float,
) -> Optional[Candidate]:
    if not candidates:
        return None

    finite_candidates = [
        candidate for candidate in candidates if math.isfinite(candidate["utility"])
    ]
    if not finite_candidates:
        return None

    if policy == "random":
        for candidate in candidates:
            candidate["probability"] = 1.0 / len(finite_candidates) if candidate in finite_candidates else 0.0
        return finite_candidates[int(rng.integers(0, len(finite_candidates)))]

    if policy == "argmax":
        max_value = max(candidate["utility"] for candidate in finite_candidates)
        best = [
            candidate
            for candidate in finite_candidates
            if abs(candidate["utility"] - max_value) <= 1e-12
        ]
        for candidate in candidates:
            candidate["probability"] = 1.0 / len(best) if candidate in best else 0.0
        return best[int(rng.integers(0, len(best)))]

    if policy == "softmax":
        probabilities = softmax_probabilities(
            [candidate["utility"] for candidate in candidates],
            tau_decision=tau_decision,
        )
        for candidate, probability in zip(candidates, probabilities):
            candidate["probability"] = probability
        total = float(sum(probabilities))
        if total <= 0.0:
            return None
        normalized = np.asarray(probabilities, dtype=float) / total
        return candidates[int(rng.choice(len(candidates), p=normalized))]

    raise ValueError(f"Unknown policy={policy}")


def move_from_candidate(candidate: Candidate) -> Move:
    b_partner = candidate.get("b_partner")
    b_text = "None" if b_partner is None else f"{b_partner:.4f}"
    explanation = (
        f"value_model={candidate['value_model']}, "
        f"axes={candidate['accessible_axes']}, "
        f"Q={candidate['q']:.4f}, I={candidate['i_entropy']:.4f}, "
        f"C_ambiguity={candidate['c_ambiguity']:.4f}, "
        f"B_partner={b_text}, V={candidate['utility']:.4f}, "
        f"prob={candidate.get('probability', 0.0):.4f}"
    )
    return candidate["row"], candidate["col"], candidate["value"], explanation


def candidate_table_entry(turn: int, candidate: Candidate, chosen: bool) -> Dict[str, Any]:
    return {
        "turn": turn,
        "agent": candidate["agent"],
        "row": candidate["row"],
        "col": candidate["col"],
        "value": candidate["value"],
        "value_name": candidate["value_name"],
        "agent_view": candidate["agent_view"],
        "accessible_axes": candidate["accessible_axes"],
        "value_model": candidate["value_model"],
        "q": candidate["q"],
        "q_own": candidate["q_own"],
        "i_entropy": candidate["i_entropy"],
        "c_ambiguity": candidate["c_ambiguity"],
        "base_value": candidate["base_value"],
        "b_partner": candidate["b_partner"],
        "b_partner_local": candidate["b_partner_local"],
        "partner_pattern_count_before": candidate["partner_pattern_count_before"],
        "partner_pattern_count_after": candidate["partner_pattern_count_after"],
        "partner_compatible": candidate["partner_compatible"],
        "row_pattern_count": candidate["row_pattern_count"],
        "col_pattern_count": candidate["col_pattern_count"],
        "utility": candidate["utility"],
        "value_score": candidate["value_score"],
        "probability": candidate.get("probability", 0.0),
        "chosen": chosen,
    }


def decision_summary(
    candidates: List[Candidate],
    chosen_candidate: Optional[Candidate],
    value_model: str,
    policy: str,
    beta_info: float,
    lambda_cost: float,
    lambda_partner: float,
    tau_decision: float,
    include_partner_info: bool,
) -> Dict[str, Any]:
    return {
        "utility_model": value_model,
        "effective_utility_model": value_model,
        "policy": policy,
        "beta_info": beta_info,
        "lambda_cost": lambda_cost,
        "lambda_partner": lambda_partner if include_partner_info else 0.0,
        "tau_decision": tau_decision,
        "candidate_count": len(candidates),
        "chosen_probability": None if chosen_candidate is None else chosen_candidate.get("probability"),
        "chosen_q_own": None if chosen_candidate is None else chosen_candidate["q_own"],
        "chosen_q": None if chosen_candidate is None else chosen_candidate["q"],
        "chosen_i_entropy": None if chosen_candidate is None else chosen_candidate["i_entropy"],
        "chosen_c_ambiguity": None if chosen_candidate is None else chosen_candidate["c_ambiguity"],
        "chosen_b_partner_local": None if chosen_candidate is None else chosen_candidate["b_partner_local"],
        "chosen_utility": None if chosen_candidate is None else chosen_candidate["utility"],
        "chosen_value_score": None if chosen_candidate is None else chosen_candidate["value_score"],
        "partner_pattern_count_before": None if chosen_candidate is None else chosen_candidate["partner_pattern_count_before"],
        "partner_pattern_count_after": None if chosen_candidate is None else chosen_candidate["partner_pattern_count_after"],
        "partner_compatible": None if chosen_candidate is None else chosen_candidate["partner_compatible"],
    }


def solve_value_ind_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    agent_view: str = "full",
    value_model: str = "full_value_cost_ambiguity",
    policy: str = "argmax",
    beta_info: float = 1.0,
    lambda_cost: float = 1.0,
    tau_decision: float = 0.2,
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

    log_event(log, turn=0, agent="system", action="start", grid_before=None, grid_after=grid)
    if verbose:
        print("Initial grid:")
        print_grid(grid)

    turn = 0
    agent = f"value_{agent_view}_ind"
    while turn < max_turns and not is_solved(grid):
        turn += 1
        grid_before = copy.deepcopy(grid)
        candidates = build_value_candidates(
            grid=grid,
            row_clues=row_clues,
            col_clues=col_clues,
            agent_view=agent_view,
            actor="ind",
            value_model=value_model,
            beta_info=beta_info,
            lambda_cost=lambda_cost,
        )
        chosen_candidate = choose_candidate(candidates, policy, rng, tau_decision)
        candidate_steps.append(
            {
                "turn": turn,
                "agent": agent,
                "value_model": value_model,
                "policy": policy,
                "candidates": [
                    candidate_table_entry(turn, candidate, candidate is chosen_candidate)
                    for candidate in candidates
                ],
            }
        )
        if chosen_candidate is None:
            log_event(log, turn, agent, "pass", grid_before, grid, None)
            log[-1]["decision"] = decision_summary(
                candidates,
                None,
                value_model,
                policy,
                beta_info,
                lambda_cost,
                0.0,
                tau_decision,
                False,
            )
            break

        move = move_from_candidate(chosen_candidate)
        apply_move(grid, move)
        log_event(log, turn, agent, "write", grid_before, grid, move)
        log[-1]["decision"] = decision_summary(
            candidates,
            chosen_candidate,
            value_model,
            policy,
            beta_info,
            lambda_cost,
            0.0,
            tau_decision,
            False,
        )
        if verbose:
            row, col, value, explanation = move
            print(f"Turn {turn} | {agent} writes ({row}, {col}) = {cell_to_char(value)} | {explanation}")
            print_grid(grid)

    log_event(log, turn + 1, "system", "end", grid, grid, None)
    return grid, log, candidate_steps


def solve_value_dyad_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    value_model: str = "full_value_cost_ambiguity",
    policy: str = "argmax",
    beta_info: float = 1.0,
    lambda_cost: float = 1.0,
    lambda_partner: float = 1.0,
    include_partner_info: bool = False,
    tau_decision: float = 0.2,
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

    log_event(log, turn=0, agent="system", action="start", grid_before=None, grid_after=grid)
    if verbose:
        print("Initial grid:")
        print_grid(grid)

    turn = 0
    stopped = False
    while turn < max_turns and not is_solved(grid):
        for actor in ("row", "col"):
            if turn >= max_turns or is_solved(grid):
                break

            turn += 1
            grid_before = copy.deepcopy(grid)
            candidates = build_value_candidates(
                grid=grid,
                row_clues=row_clues,
                col_clues=col_clues,
                agent_view="dyad",
                actor=actor,
                value_model=value_model,
                beta_info=beta_info,
                lambda_cost=lambda_cost,
                lambda_partner=lambda_partner,
                include_partner_info=include_partner_info,
            )
            chosen_candidate = choose_candidate(candidates, policy, rng, tau_decision)
            candidate_steps.append(
                {
                    "turn": turn,
                    "agent": actor,
                    "value_model": value_model,
                    "policy": policy,
                    "include_partner_info": include_partner_info,
                    "candidates": [
                        candidate_table_entry(turn, candidate, candidate is chosen_candidate)
                        for candidate in candidates
                    ],
                }
            )
            if chosen_candidate is None:
                log_event(log, turn, actor, "pass", grid_before, grid, None)
                log[-1]["decision"] = decision_summary(
                    candidates,
                    None,
                    value_model,
                    policy,
                    beta_info,
                    lambda_cost,
                    lambda_partner,
                    tau_decision,
                    include_partner_info,
                )
                stopped = True
                break

            move = move_from_candidate(chosen_candidate)
            apply_move(grid, move)
            log_event(log, turn, actor, "write", grid_before, grid, move)
            log[-1]["decision"] = decision_summary(
                candidates,
                chosen_candidate,
                value_model,
                policy,
                beta_info,
                lambda_cost,
                lambda_partner,
                tau_decision,
                include_partner_info,
            )
            if verbose:
                row, col, value, explanation = move
                print(f"Turn {turn} | {actor.upper()} writes ({row}, {col}) = {cell_to_char(value)} | {explanation}")
                print_grid(grid)
        if stopped:
            break

    log_event(log, turn + 1, "system", "end", grid, grid, None)
    return grid, log, candidate_steps


def augment_payload_with_value_candidate_tables(
    payload: Dict[str, Any],
    candidate_steps: List[Dict[str, Any]],
) -> Dict[str, Any]:
    payload["candidate_steps"] = candidate_steps
    decision_events = [
        event for event in payload["events"]
        if event["action"] in {"write", "pass"} and "decision" in event
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
    chosen_i_values = [
        event["decision"]["chosen_i_entropy"]
        for event in decision_events
        if event["decision"]["chosen_i_entropy"] is not None
    ]
    chosen_c_values = [
        event["decision"]["chosen_c_ambiguity"]
        for event in decision_events
        if event["decision"]["chosen_c_ambiguity"] is not None
    ]
    chosen_partner_values = [
        event["decision"]["chosen_b_partner_local"]
        for event in decision_events
        if event["decision"]["chosen_b_partner_local"] is not None
    ]

    payload["summary"]["mean_candidate_count"] = float(sum(candidate_counts)) / max(1, len(candidate_counts))
    payload["summary"]["mean_chosen_probability"] = float(sum(chosen_probabilities)) / max(1, len(chosen_probabilities))
    payload["summary"]["mean_chosen_q_own"] = float(sum(chosen_q_values)) / max(1, len(chosen_q_values))
    payload["summary"]["mean_chosen_i_entropy"] = float(sum(chosen_i_values)) / max(1, len(chosen_i_values))
    payload["summary"]["mean_chosen_c_ambiguity"] = float(sum(chosen_c_values)) / max(1, len(chosen_c_values))
    payload["summary"]["mean_chosen_b_partner_local"] = float(sum(chosen_partner_values)) / max(1, len(chosen_partner_values))
    payload["summary"]["candidate_table_steps"] = len(candidate_steps)
    payload["summary"]["candidate_table_rows"] = sum(len(step["candidates"]) for step in candidate_steps)
    return payload
