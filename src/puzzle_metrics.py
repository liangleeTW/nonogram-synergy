"""Puzzle uniqueness and structural metric functions.

Expected output files:
- None directly; scripts/build_controlled_dataset.py writes metric tables.

Command to run code:
- poetry run python -m unittest tests/test_puzzle_metrics.py
"""

from __future__ import annotations

import math
from statistics import mean, pvariance
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from puzzle import (
    EMPTY,
    FILLED,
    Clue,
    ClueSet,
    Grid,
    Puzzle,
    enumerate_valid_lines,
    normalize_clues,
    normalize_solution,
)


def safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def safe_variance(values: Sequence[float]) -> float:
    return pvariance(values) if len(values) >= 2 else 0.0


def count_solutions(
    row_clues: Iterable[Sequence[int]],
    col_clues: Iterable[Sequence[int]],
    max_solutions: int = 2,
) -> int:
    rows = normalize_clues(row_clues)
    cols = normalize_clues(col_clues)
    n_rows = len(rows)
    n_cols = len(cols)
    if n_rows == 0 or n_cols == 0:
        raise ValueError("Puzzle must have at least one row and one column")
    if max_solutions < 1:
        raise ValueError("max_solutions must be at least 1")

    row_configs = [enumerate_valid_lines(n_cols, clue) for clue in rows]
    col_configs = [enumerate_valid_lines(n_rows, clue) for clue in cols]
    col_prefixes_by_depth = [
        [set(config[:depth] for config in configs) for configs in col_configs]
        for depth in range(n_rows + 1)
    ]

    count = 0
    partial_rows: list[Tuple[int, ...]] = []

    def backtrack(row_idx: int) -> None:
        nonlocal count
        if count >= max_solutions:
            return
        if row_idx == n_rows:
            count += 1
            return

        for row in row_configs[row_idx]:
            partial_rows.append(row)
            depth = row_idx + 1
            compatible = True
            prefixes_for_depth = col_prefixes_by_depth[depth]
            for col_idx in range(n_cols):
                prefix = tuple(partial[col_idx] for partial in partial_rows)
                if prefix not in prefixes_for_depth[col_idx]:
                    compatible = False
                    break
            if compatible:
                backtrack(row_idx + 1)
            partial_rows.pop()
            if count >= max_solutions:
                return

    backtrack(0)
    return count


def line_ambiguities(line_length: int, clues: ClueSet) -> Tuple[float, ...]:
    return tuple(math.log(len(enumerate_valid_lines(line_length, clue))) for clue in clues)


def safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 1.0 if numerator == 0 else math.inf
    return numerator / denominator


def asymmetry_category(row_mean: float, col_mean: float, eps: float = 1e-9) -> str:
    if abs(row_mean - col_mean) <= eps:
        return "balanced"
    return "row_higher" if row_mean > col_mean else "col_higher"


def density(solution: Optional[Grid], row_clues: ClueSet, n_rows: int, n_cols: int) -> float:
    if solution is not None:
        return sum(sum(row) for row in solution) / max(1, n_rows * n_cols)
    return sum(sum(clue) for clue in row_clues) / max(1, n_rows * n_cols)


def repeated_pattern_count(lines: Sequence[Sequence[int]]) -> int:
    return len(lines) - len({tuple(line) for line in lines})


def symmetry_score(solution: Optional[Grid], axis: str) -> Optional[float]:
    if solution is None:
        return None
    n_rows = len(solution)
    n_cols = len(solution[0])
    matches = 0
    total = n_rows * n_cols
    for r in range(n_rows):
        for c in range(n_cols):
            if axis == "horizontal":
                other = solution[n_rows - 1 - r][c]
            elif axis == "vertical":
                other = solution[r][n_cols - 1 - c]
            else:
                raise ValueError(f"Unknown symmetry axis: {axis}")
            if solution[r][c] == other:
                matches += 1
    return matches / max(1, total)


def run_length_description_length(lines: Sequence[Sequence[int]]) -> int:
    total = 0
    for line in lines:
        previous: Optional[int] = None
        for value in line:
            if previous is None or value != previous:
                total += 1
            previous = value
    return total


def puzzle_metrics(puzzle: Puzzle, max_solutions: int = 2) -> Dict[str, Any]:
    n_rows, n_cols = puzzle.grid_size
    solution = puzzle.solution
    row_ambiguities = line_ambiguities(n_cols, puzzle.row_clues)
    col_ambiguities = line_ambiguities(n_rows, puzzle.col_clues)
    all_ambiguities = row_ambiguities + col_ambiguities

    row_mean = safe_mean(row_ambiguities)
    col_mean = safe_mean(col_ambiguities)
    solution_count = count_solutions(puzzle.row_clues, puzzle.col_clues, max_solutions=max_solutions)
    row_space_log_size = sum(row_ambiguities)
    col_space_log_size = sum(col_ambiguities)
    joint_space_log_size = math.log(solution_count) if solution_count > 0 else -math.inf

    rows = solution
    cols = None
    if solution is not None:
        cols = tuple(tuple(row[c] for row in solution) for c in range(n_cols))

    metrics: Dict[str, Any] = {
        "board_rows": n_rows,
        "board_cols": n_cols,
        "num_cells": n_rows * n_cols,
        "solution_count_capped": solution_count,
        "unique": solution_count == 1,
        "mean_line_ambiguity": safe_mean(all_ambiguities),
        "line_ambiguity_variance": safe_variance(all_ambiguities),
        "max_line_ambiguity": max(all_ambiguities) if all_ambiguities else 0.0,
        "min_line_ambiguity": min(all_ambiguities) if all_ambiguities else 0.0,
        "row_ambiguity_mean": row_mean,
        "col_ambiguity_mean": col_mean,
        "row_ambiguity_variance": safe_variance(row_ambiguities),
        "col_ambiguity_variance": safe_variance(col_ambiguities),
        "pooled_ambiguity_variance": safe_variance(all_ambiguities),
        "row_col_ambiguity_abs_diff": abs(row_mean - col_mean),
        "row_col_ambiguity_safe_ratio": safe_ratio(row_mean, col_mean),
        "row_col_asymmetry_category": asymmetry_category(row_mean, col_mean),
        "row_space_log_size": row_space_log_size,
        "col_space_log_size": col_space_log_size,
        "joint_space_log_size": joint_space_log_size,
        "joint_constraint_space_log": row_space_log_size + col_space_log_size - joint_space_log_size,
        "filled_density": density(solution, puzzle.row_clues, n_rows, n_cols),
    }

    if rows is not None and cols is not None:
        metrics.update(
            {
                "distinct_rows": len(set(rows)),
                "distinct_cols": len(set(cols)),
                "repeated_rows": repeated_pattern_count(rows),
                "repeated_cols": repeated_pattern_count(cols),
                "horizontal_symmetry": symmetry_score(solution, "horizontal"),
                "vertical_symmetry": symmetry_score(solution, "vertical"),
                "run_length_description_length": run_length_description_length(rows + cols),
            }
        )
    else:
        metrics.update(
            {
                "distinct_rows": None,
                "distinct_cols": None,
                "repeated_rows": None,
                "repeated_cols": None,
                "horizontal_symmetry": None,
                "vertical_symmetry": None,
                "run_length_description_length": None,
            }
        )

    return metrics


def make_puzzle_from_solution(solution: Iterable[Sequence[int]]) -> Puzzle:
    return Puzzle.from_solution(normalize_solution(solution))
