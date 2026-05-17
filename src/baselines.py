"""Baseline solvers for controlled-dataset comparisons.

Flag descriptions:
- This module has no command-line flags; scripts/run_controlled_dataset.py exposes these solvers with --solver.

Expected output files:
- None directly; scripts/run_controlled_dataset.py writes JSON logs for these baseline solvers.

Command to run code:
- poetry run python scripts/run_controlled_dataset.py --puzzle-csv results/analysis/controlled_puzzles_5x5.csv --solver baseline_series --all-puzzles --output-dir results/logs/controlled_baseline --quiet
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Tuple

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
    get_forced_cells_from_line,
    is_solved,
    log_event,
    print_grid,
    select_scored_move,
)


def row_only_move(
    grid: List[List[int]],
    row_clues: List[List[int]],
    strategy: str = "first",
) -> Optional[Move]:
    n_cols = len(grid[0])
    scored_candidates = []
    for row_idx, clue in enumerate(row_clues):
        unknowns = sum(cell == UNKNOWN for cell in grid[row_idx])
        forced = get_forced_cells_from_line(n_cols, clue, grid[row_idx])
        for col_idx, value in forced:
            scored_candidates.append(
                (
                    (
                        row_idx,
                        col_idx,
                        value,
                        f"row_only row={row_idx}, row_clue={clue}",
                    ),
                    unknowns,
                )
            )
    return select_scored_move(scored_candidates, strategy)


def col_only_move(
    grid: List[List[int]],
    col_clues: List[List[int]],
    strategy: str = "first",
) -> Optional[Move]:
    n_rows = len(grid)
    scored_candidates = []
    for col_idx, clue in enumerate(col_clues):
        col = get_column(grid, col_idx)
        unknowns = sum(grid[row_idx][col_idx] == UNKNOWN for row_idx in range(n_rows))
        forced = get_forced_cells_from_line(n_rows, clue, col)
        for row_idx, value in forced:
            scored_candidates.append(
                (
                    (
                        row_idx,
                        col_idx,
                        value,
                        f"col_only col={col_idx}, col_clue={clue}",
                    ),
                    unknowns,
                )
            )
    return select_scored_move(scored_candidates, strategy)


def action_keeps_line_compatible(
    line: List[int],
    clue: List[int],
    index: int,
    value: int,
) -> bool:
    candidate_line = line[:]
    candidate_line[index] = value
    return bool(generate_line_patterns(len(candidate_line), clue, candidate_line))


def random_legal_move(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    rng: np.random.Generator,
) -> Optional[Move]:
    candidates: List[Move] = []
    n_rows = len(grid)
    n_cols = len(grid[0])
    for row_idx in range(n_rows):
        for col_idx in range(n_cols):
            if grid[row_idx][col_idx] != UNKNOWN:
                continue
            for value in (FILLED, EMPTY):
                row_ok = action_keeps_line_compatible(
                    line=grid[row_idx],
                    clue=row_clues[row_idx],
                    index=col_idx,
                    value=value,
                )
                col_ok = action_keeps_line_compatible(
                    line=get_column(grid, col_idx),
                    clue=col_clues[col_idx],
                    index=row_idx,
                    value=value,
                )
                if row_ok and col_ok:
                    candidates.append(
                        (
                            row_idx,
                            col_idx,
                            value,
                            "random_legal compatible with row and column clues",
                        )
                    )

    if not candidates:
        return None
    return candidates[int(rng.integers(0, len(candidates)))]


def solve_partial_ind_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    axis: str,
    strategy: str = "first",
    max_turns: int = 1000,
    verbose: bool = True,
) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)
    grid = [[UNKNOWN for _ in range(n_cols)] for _ in range(n_rows)]
    log: List[Dict[str, Any]] = []

    log_event(log, turn=0, agent="system", action="start", grid_before=None, grid_after=grid)
    if verbose:
        print("Initial grid:")
        print_grid(grid)

    turn = 0
    agent = f"{axis}_only_ind"
    while turn < max_turns and not is_solved(grid):
        turn += 1
        grid_before = copy.deepcopy(grid)
        if axis == "row":
            move = row_only_move(grid, row_clues, strategy=strategy)
        elif axis == "col":
            move = col_only_move(grid, col_clues, strategy=strategy)
        else:
            raise ValueError(f"Unknown partial-information axis: {axis}")

        if move is None:
            log_event(log, turn, agent, "pass", grid_before, grid, None)
            if verbose:
                print(f"Turn {turn} | {agent} passes")
            break

        apply_move(grid, move)
        log_event(log, turn, agent, "write", grid_before, grid, move)
        if verbose:
            row, col, value, explanation = move
            print(f"Turn {turn} | {agent} writes ({row}, {col}) = {cell_to_char(value)} | {explanation}")
            print_grid(grid)

    log_event(log, turn + 1, "system", "end", grid, grid, None)
    return grid, log


def solve_random_legal_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    max_turns: int = 1000,
    seed: int = 0,
    verbose: bool = True,
) -> Tuple[List[List[int]], List[Dict[str, Any]]]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)
    rng = np.random.default_rng(seed)
    grid = [[UNKNOWN for _ in range(n_cols)] for _ in range(n_rows)]
    log: List[Dict[str, Any]] = []

    log_event(log, turn=0, agent="system", action="start", grid_before=None, grid_after=grid)
    if verbose:
        print("Initial grid:")
        print_grid(grid)

    turn = 0
    while turn < max_turns and not is_solved(grid):
        turn += 1
        grid_before = copy.deepcopy(grid)
        move = random_legal_move(grid, row_clues, col_clues, rng)
        if move is None:
            log_event(log, turn, "random_legal", "pass", grid_before, grid, None)
            if verbose:
                print(f"Turn {turn} | random_legal passes")
            break

        apply_move(grid, move)
        log_event(log, turn, "random_legal", "write", grid_before, grid, move)
        if verbose:
            row, col, value, explanation = move
            print(f"Turn {turn} | random_legal writes ({row}, {col}) = {cell_to_char(value)} | {explanation}")
            print_grid(grid)

    log_event(log, turn + 1, "system", "end", grid, grid, None)
    return grid, log
