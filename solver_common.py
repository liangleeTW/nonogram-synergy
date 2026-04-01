from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

UNKNOWN = -1
EMPTY = 0
FILLED = 1

Move = Tuple[int, int, int, str]  # (r, c, value, explanation)
ScoredMove = Tuple[Move, int]


def cell_to_char(v: int) -> str:
    if v == FILLED:
        return "■"
    if v == EMPTY:
        return "·"
    return "?"


def print_grid(grid: List[List[int]]) -> None:
    for row in grid:
        print(" ".join(cell_to_char(c) for c in row))
    print()


def is_solved(grid: List[List[int]]) -> bool:
    return all(cell != UNKNOWN for row in grid for cell in row)


def get_column(grid: List[List[int]], c: int) -> List[int]:
    return [grid[r][c] for r in range(len(grid))]


def load_npz_array(path: str, key: Optional[str] = None) -> np.ndarray:
    data = np.load(path)
    if key is None:
        if len(data.files) != 1:
            raise ValueError(f"Expected exactly one array in {path}, found {data.files}")
        key = data.files[0]
    return data[key]


def infer_board_size_from_solution_length(length: int) -> int:
    size = int(length ** 0.5)
    if size * size != length:
        raise ValueError(f"Cannot infer square board size from solution length {length}")
    return size


def infer_board_size_from_clue_length(length: int) -> int:
    matches = [
        size
        for size in range(1, 256)
        if size * 2 * ((size + 1) // 2) == length
    ]
    if len(matches) != 1:
        raise ValueError(f"Cannot infer board size from packed clue length {length}")
    return matches[0]


def decode_padded_clues(values: np.ndarray) -> List[int]:
    return [int(v) for v in values if int(v) != 0]


def decode_dataset_clues(
    packed_sample: np.ndarray,
    board_size: Optional[int] = None,
) -> Tuple[List[List[int]], List[List[int]]]:
    flat = np.asarray(packed_sample).reshape(-1)
    if board_size is None:
        board_size = infer_board_size_from_clue_length(flat.size)

    max_clues = (board_size + 1) // 2
    expected_len = board_size * 2 * max_clues
    if flat.size != expected_len:
        raise ValueError(
            f"Packed sample has length {flat.size}, expected {expected_len} "
            f"for board size {board_size}"
        )

    packed_rows = flat.reshape(board_size, 2 * max_clues)
    all_clues: List[List[int]] = []
    for packed_row in packed_rows:
        all_clues.append(decode_padded_clues(packed_row[:max_clues]))
        all_clues.append(decode_padded_clues(packed_row[max_clues:]))

    row_clues = all_clues[:board_size]
    col_clues = all_clues[board_size: 2 * board_size]
    return row_clues, col_clues


def load_dataset_sample(
    x_path: str,
    sample_idx: int = 0,
    y_path: Optional[str] = None,
) -> Tuple[List[List[int]], List[List[int]], Optional[List[List[int]]]]:
    x_array = load_npz_array(x_path)
    if sample_idx < 0 or sample_idx >= len(x_array):
        raise IndexError(f"sample_idx={sample_idx} is out of range for {x_path}")

    board_size: Optional[int] = None
    target_grid: Optional[List[List[int]]] = None

    if y_path is not None:
        y_array = load_npz_array(y_path)
        if len(y_array) != len(x_array):
            raise ValueError(
                f"x/y sample count mismatch: {len(x_array)} in {x_path}, "
                f"{len(y_array)} in {y_path}"
            )
        board_size = infer_board_size_from_solution_length(int(y_array[sample_idx].size))
        target_grid = y_array[sample_idx].reshape(board_size, board_size).astype(int).tolist()

    row_clues, col_clues = decode_dataset_clues(x_array[sample_idx], board_size=board_size)
    return row_clues, col_clues, target_grid


def load_dataset_targets(y_path: Optional[str]) -> Optional[np.ndarray]:
    if y_path is None:
        return None
    return load_npz_array(y_path)


def count_unknown_cells(grid: List[List[int]]) -> int:
    return sum(cell == UNKNOWN for row in grid for cell in row)


def grids_equal(a: List[List[int]], b: List[List[int]]) -> bool:
    return a == b


def default_max_turns(row_clues: List[List[int]], col_clues: List[List[int]]) -> int:
    return 2 * len(row_clues) * len(col_clues)


def prefix_consistent(prefix: List[int], current_line: List[int]) -> bool:
    for i, v in enumerate(prefix):
        if current_line[i] != UNKNOWN and current_line[i] != v:
            return False
    return True


def line_consistent(candidate: List[int], current_line: List[int]) -> bool:
    return all(
        current_line[i] == UNKNOWN or current_line[i] == candidate[i]
        for i in range(len(candidate))
    )


def generate_line_patterns(
    length: int,
    clues: List[int],
    current_line: List[int],
) -> List[List[int]]:
    patterns: List[List[int]] = []

    if not clues:
        candidate = [EMPTY] * length
        if line_consistent(candidate, current_line):
            return [candidate]
        return []

    def backtrack(clue_idx: int, pos: int, partial: List[int]) -> None:
        if clue_idx == len(clues):
            candidate = partial + [EMPTY] * (length - len(partial))
            if line_consistent(candidate, current_line):
                patterns.append(candidate)
            return

        block_len = clues[clue_idx]
        remaining = clues[clue_idx + 1:]
        min_remaining_len = sum(remaining) + max(0, len(remaining))
        max_start = length - block_len - min_remaining_len

        for start in range(pos, max_start + 1):
            candidate = partial[:]
            candidate.extend([EMPTY] * (start - len(candidate)))
            candidate.extend([FILLED] * block_len)

            if clue_idx < len(clues) - 1:
                candidate.append(EMPTY)

            if prefix_consistent(candidate, current_line):
                backtrack(clue_idx + 1, len(candidate), candidate)

    backtrack(0, 0, [])
    return patterns


def get_forced_cells_from_line(
    length: int,
    clues: List[int],
    current_line: List[int],
) -> List[Tuple[int, int]]:
    patterns = generate_line_patterns(length, clues, current_line)
    if not patterns:
        raise ValueError(f"No valid patterns. clues={clues}, line={current_line}")

    forced = []
    for i in range(length):
        values = {pattern[i] for pattern in patterns}
        if len(values) == 1:
            value = next(iter(values))
            if current_line[i] == UNKNOWN:
                forced.append((i, value))
    return forced


def get_line_fill_probabilities(
    length: int,
    clues: List[int],
    current_line: List[int],
) -> List[float]:
    patterns = generate_line_patterns(length, clues, current_line)
    if not patterns:
        raise ValueError(f"No valid patterns. clues={clues}, line={current_line}")

    pattern_count = float(len(patterns))
    return [
        sum(1 for pattern in patterns if pattern[i] == FILLED) / pattern_count
        for i in range(length)
    ]


def count_line_patterns(
    length: int,
    clues: List[int],
    current_line: List[int],
) -> int:
    return len(generate_line_patterns(length, clues, current_line))


def select_scored_move(
    scored_candidates: List[ScoredMove],
    strategy: str = "first",
) -> Optional[Move]:
    if not scored_candidates:
        return None

    if strategy == "random":
        import random

        return random.choice(scored_candidates)[0]

    if strategy == "most_constrained":
        return min(scored_candidates, key=lambda item: item[1])[0]

    return scored_candidates[0][0]


def apply_move(grid: List[List[int]], move: Move) -> None:
    r, c, value, _ = move
    if grid[r][c] != UNKNOWN and grid[r][c] != value:
        raise ValueError(f"Contradiction at ({r}, {c}).")
    grid[r][c] = value


def log_event(
    log: List[Dict[str, Any]],
    turn: int,
    agent: str,
    action: str,
    grid_before: Optional[List[List[int]]],
    grid_after: List[List[int]],
    move: Optional[Move] = None,
) -> None:
    event: Dict[str, Any] = {
        "turn": turn,
        "agent": agent,
        "action": action,
        "grid_before": copy.deepcopy(grid_before) if grid_before is not None else None,
        "grid_after": copy.deepcopy(grid_after),
        "move": None,
    }

    if move is not None:
        r, c, value, explanation = move
        event["move"] = {
            "row": r,
            "col": c,
            "value": value,
            "value_name": "FILLED" if value == FILLED else "EMPTY",
            "explanation": explanation,
        }

    log.append(event)


def build_log_payload(
    events: List[Dict[str, Any]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    max_turns: int,
    final_grid: List[List[int]],
    target_grid: Optional[List[List[int]]] = None,
    x_path: Optional[str] = None,
    y_path: Optional[str] = None,
    sample_idx: Optional[int] = None,
    metadata_extra: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    unresolved = count_unknown_cells(final_grid)
    matches_target = None if target_grid is None else grids_equal(final_grid, target_grid)

    writes = [event for event in events if event["action"] == "write"]
    passes = [event for event in events if event["action"] == "pass"]
    agent_write_counts = Counter(event["agent"] for event in writes)
    agent_pass_counts = Counter(event["agent"] for event in passes)

    metadata: Dict[str, Any] = {
        "board_rows": len(row_clues),
        "board_cols": len(col_clues),
        "row_clues": row_clues,
        "col_clues": col_clues,
        "max_turns": max_turns,
        "source": {
            "x_path": x_path,
            "y_path": y_path,
            "sample_idx": sample_idx,
        },
    }
    if metadata_extra:
        metadata.update(metadata_extra)

    return {
        "metadata": metadata,
        "summary": {
            "unknown_cells": unresolved,
            "solved": unresolved == 0,
            "matches_target": matches_target,
            "total_events": len(events),
            "write_events": len(writes),
            "pass_events": len(passes),
            "row_writes": agent_write_counts.get("row", 0),
            "col_writes": agent_write_counts.get("col", 0),
            "ind_writes": agent_write_counts.get("ind", 0),
            "row_passes": agent_pass_counts.get("row", 0),
            "col_passes": agent_pass_counts.get("col", 0),
            "ind_passes": agent_pass_counts.get("ind", 0),
            "agent_write_counts": dict(agent_write_counts),
            "agent_pass_counts": dict(agent_pass_counts),
        },
        "target_grid": target_grid,
        "final_grid": final_grid,
        "events": events,
    }


def save_log_json(payload: Dict[str, Any], filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def make_default_log_path(
    x_path: Optional[str],
    solver_tag: str,
    sample_idx: Optional[int] = None,
    output_dir: Optional[str] = None,
) -> str:
    if x_path is None:
        return "nonogram_turn_log.json"

    x_stem = Path(x_path).stem
    dirname = output_dir or f"logs/{x_stem}__{solver_tag}"
    path = Path(dirname)
    path.mkdir(parents=True, exist_ok=True)

    if sample_idx is None:
        filename = f"{x_stem}.json"
    else:
        filename = f"{x_stem}__sample-{sample_idx:05d}.json"
    return str(path / filename)


def get_sample_indices(
    total_samples: int,
    sample_idx: int,
    all_samples: bool,
    sample_start: Optional[int],
    sample_end: Optional[int],
) -> List[int]:
    if not all_samples and sample_start is None and sample_end is None:
        return [sample_idx]

    start = 0 if sample_start is None else sample_start
    end = total_samples if sample_end is None else sample_end

    if start < 0 or end < 0 or start > end or end > total_samples:
        raise ValueError(
            f"Invalid sample range [{start}, {end}) for dataset of size {total_samples}"
        )

    return list(range(start, end))
