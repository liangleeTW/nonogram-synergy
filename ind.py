from __future__ import annotations

import argparse
import copy
from typing import Dict, List, Optional, Tuple

from solver_common import (
    UNKNOWN,
    Move,
    apply_move,
    build_log_payload,
    cell_to_char,
    count_unknown_cells,
    default_max_turns,
    get_column,
    get_forced_cells_from_line,
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
    select_scored_move,
)


def individual_agent_move(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    strategy: str = "first",
) -> Optional[Move]:
    n_rows = len(grid)
    n_cols = len(grid[0])
    candidates: Dict[Tuple[int, int, int], Tuple[Move, int]] = {}

    for r in range(n_rows):
        unknowns = sum(cell == UNKNOWN for cell in grid[r])
        forced = get_forced_cells_from_line(n_cols, row_clues[r], grid[r])
        for c, value in forced:
            move = (r, c, value, f"row={r}, row_clue={row_clues[r]}")
            key = (r, c, value)
            existing = candidates.get(key)
            if existing is None or unknowns < existing[1]:
                candidates[key] = (move, unknowns)

    for c in range(n_cols):
        col = get_column(grid, c)
        unknowns = sum(grid[r][c] == UNKNOWN for r in range(n_rows))
        forced = get_forced_cells_from_line(n_rows, col_clues[c], col)
        for r, value in forced:
            move = (r, c, value, f"col={c}, col_clue={col_clues[c]}")
            key = (r, c, value)
            existing = candidates.get(key)
            if existing is None or unknowns < existing[1]:
                candidates[key] = (move, unknowns)

    return select_scored_move(list(candidates.values()), strategy)


def solve_individual_turn_based_logged(
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    strategy: str = "first",
    max_turns: int = 1000,
    verbose: bool = True,
) -> Tuple[List[List[int]], List[dict]]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)

    grid = [[UNKNOWN for _ in range(n_cols)] for _ in range(n_rows)]
    log: List[dict] = []

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
        turn += 1
        grid_before = copy.deepcopy(grid)
        move = individual_agent_move(grid, row_clues, col_clues, strategy=strategy)

        if move is not None:
            apply_move(grid, move)
            log_event(log, turn, "ind", "write", grid_before, grid, move)
            if verbose:
                r, c, value, explanation = move
                print(f"Turn {turn} | IND writes ({r}, {c}) = {cell_to_char(value)} | {explanation}")
                print_grid(grid)
        else:
            log_event(log, turn, "ind", "pass", grid_before, grid, None)
            if verbose:
                print(f"Turn {turn} | IND passes")
                print("Individual agent has no forced move. Stopping.")
            break

    log_event(log, turn + 1, "system", "end", grid, grid, None)

    if verbose:
        print("Final grid:")
        print_grid(grid)

    return grid, log


def resolve_strategy(args: argparse.Namespace) -> str:
    chosen = args.strategy
    aliases = [value for value in (args.row_strategy, args.col_strategy) if value is not None]

    if aliases and args.strategy != "first":
        for alias in aliases:
            if alias != args.strategy:
                raise ValueError(
                    "Use a single strategy for ind.py. --strategy, --row-strategy, "
                    "and --col-strategy must agree when provided."
                )

    if aliases:
        first_alias = aliases[0]
        for alias in aliases[1:]:
            if alias != first_alias:
                raise ValueError(
                    "Use a single strategy for ind.py. --row-strategy and --col-strategy "
                    "must match when both are provided."
                )
        chosen = first_alias

    return chosen


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Solve a nonogram with the single-agent full-information line solver."
    )
    parser.add_argument("--x-path", help="Path to packed clue x_*.npz file")
    parser.add_argument("--y-path", help="Optional path to target y_*.npz file")
    parser.add_argument("--sample-idx", type=int, default=0, help="Dataset sample index")
    parser.add_argument("--all-samples", action="store_true", help="Run all samples in the dataset")
    parser.add_argument(
        "--sample-start",
        type=int,
        help="Optional batch start index (inclusive). Enables batch mode.",
    )
    parser.add_argument(
        "--sample-end",
        type=int,
        help="Optional batch end index (exclusive). Enables batch mode.",
    )
    parser.add_argument(
        "--strategy",
        choices=["first", "random", "most_constrained"],
        default="first",
    )
    parser.add_argument(
        "--row-strategy",
        choices=["first", "random", "most_constrained"],
        help="Optional alias for --strategy to keep the interface close to collab.py.",
    )
    parser.add_argument(
        "--col-strategy",
        choices=["first", "random", "most_constrained"],
        help="Optional alias for --strategy to keep the interface close to collab.py.",
    )
    parser.add_argument(
        "--max-turns",
        type=int,
        help="Maximum number of turns. Default is 2 * number_of_cells.",
    )
    parser.add_argument("--quiet", action="store_true", help="Disable step-by-step printing")
    parser.add_argument("--json-path", help="Output JSON path for single-sample runs")
    parser.add_argument(
        "--output-dir",
        help="Output directory for automatically named JSON logs in batch mode",
    )
    args = parser.parse_args()

    strategy = resolve_strategy(args)
    batch_mode = args.all_samples or args.sample_start is not None or args.sample_end is not None

    if batch_mode and not args.x_path:
        raise ValueError("Batch mode requires --x-path")
    if batch_mode and args.json_path:
        raise ValueError("Use --output-dir instead of --json-path in batch mode")

    if args.x_path is None:
        target_grid = None
        row_clues = [
            [3],
            [4, 1],
            [1, 1, 2, 1],
            [3, 1, 3],
            [1],
            [3, 3],
            [5, 3],
            [3, 1, 1, 1],
            [5, 3],
            [3, 3],
        ]

        col_clues = [
            [1],
            [2, 3],
            [1, 1, 5],
            [2, 5],
            [2, 2, 2],
            [5, 3],
            [1, 1, 1, 1],
            [1, 1, 5],
            [2, 2, 2],
            [1, 3],
        ]
        max_turns = args.max_turns or default_max_turns(row_clues, col_clues)
        final_grid, log = solve_individual_turn_based_logged(
            row_clues=row_clues,
            col_clues=col_clues,
            strategy=strategy,
            max_turns=max_turns,
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
            sample_idx=None,
            metadata_extra={
                "solver": "ind",
                "strategy": strategy,
                "row_strategy": strategy,
                "col_strategy": strategy,
            },
        )
        output_path = args.json_path or "nonogram_turn_log.json"
        save_log_json(payload, output_path)

        unresolved = count_unknown_cells(final_grid)
        print(f"Unknown cells remaining: {unresolved}")
        if target_grid is not None:
            print(f"Matches target grid: {grids_equal(final_grid, target_grid)}")
        print(f"Saved log to {output_path}")
    else:
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
            final_grid, log = solve_individual_turn_based_logged(
                row_clues=row_clues,
                col_clues=col_clues,
                strategy=strategy,
                max_turns=max_turns,
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
                    "solver": "ind",
                    "strategy": strategy,
                    "row_strategy": strategy,
                    "col_strategy": strategy,
                },
            )
            if single_dataset_run and args.json_path:
                output_path = args.json_path
            else:
                output_path = make_default_log_path(
                    x_path=args.x_path,
                    solver_tag=f"ind-{strategy}",
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
