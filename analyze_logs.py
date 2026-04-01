from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Sequence


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def safe_mean(values: Sequence[float]) -> float:
    return mean(values) if values else 0.0


def safe_pstdev(values: Sequence[float]) -> float:
    return pstdev(values) if len(values) >= 2 else 0.0


def iter_log_paths(log_dir: str) -> List[Path]:
    root = Path(log_dir)
    if not root.exists():
        raise FileNotFoundError(f"Log directory does not exist: {log_dir}")
    return sorted(path for path in root.rglob("*.json") if path.is_file())


def load_payload(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected structured JSON payload in {path}")
    return payload


def count_transitions(line: Sequence[int]) -> int:
    return sum(1 for i in range(1, len(line)) if line[i] != line[i - 1])


def get_columns(grid: Sequence[Sequence[int]]) -> List[List[int]]:
    return [[row[c] for row in grid] for c in range(len(grid[0]))]


def line_clue_stats(row_clues: List[List[int]], col_clues: List[List[int]]) -> Dict[str, float]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)

    row_block_counts = [len(clue) for clue in row_clues]
    col_block_counts = [len(clue) for clue in col_clues]
    all_block_counts = row_block_counts + col_block_counts
    all_block_lengths = [block for clue in row_clues + col_clues for block in clue]

    zero_rows = sum(1 for clue in row_clues if not clue)
    zero_cols = sum(1 for clue in col_clues if not clue)
    full_rows = sum(1 for clue in row_clues if len(clue) == 1 and clue[0] == n_cols)
    full_cols = sum(1 for clue in col_clues if len(clue) == 1 and clue[0] == n_rows)

    total_lines = n_rows + n_cols
    max_row_blocks = math.ceil(n_cols / 2)
    max_col_blocks = math.ceil(n_rows / 2)
    avg_max_blocks = (max_row_blocks * n_rows + max_col_blocks * n_cols) / max(1, total_lines)

    return {
        "total_blocks": float(sum(all_block_counts)),
        "avg_blocks_per_line": safe_mean(all_block_counts),
        "max_blocks_on_line": float(max(all_block_counts) if all_block_counts else 0),
        "block_count_std": safe_pstdev(all_block_counts),
        "avg_block_length": safe_mean(all_block_lengths),
        "block_length_std": safe_pstdev(all_block_lengths),
        "zero_clue_rows": float(zero_rows),
        "zero_clue_cols": float(zero_cols),
        "full_rows": float(full_rows),
        "full_cols": float(full_cols),
        "trivial_line_ratio": (zero_rows + zero_cols + full_rows + full_cols) / max(1, total_lines),
        "avg_max_blocks": avg_max_blocks,
    }


def target_grid_stats(
    target_grid: Optional[List[List[int]]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
) -> Dict[str, float]:
    n_rows = len(row_clues)
    n_cols = len(col_clues)
    num_cells = n_rows * n_cols

    if target_grid is None:
        filled_cells = sum(sum(clue) for clue in row_clues)
        filled_ratio = filled_cells / max(1, num_cells)
        return {
            "filled_cells": float(filled_cells),
            "filled_ratio": filled_ratio,
            "density_balance": 1.0 - abs(filled_ratio - 0.5) / 0.5,
            "avg_transitions_per_line": 0.0,
        }

    rows = target_grid
    cols = get_columns(rows)
    filled_cells = sum(sum(row) for row in rows)
    filled_ratio = filled_cells / max(1, num_cells)
    transitions = [count_transitions(line) for line in rows + cols]

    return {
        "filled_cells": float(filled_cells),
        "filled_ratio": filled_ratio,
        "density_balance": 1.0 - abs(filled_ratio - 0.5) / 0.5,
        "avg_transitions_per_line": safe_mean(transitions),
    }


def event_stats(events: List[Dict[str, Any]], num_cells: int, max_turns: int) -> Dict[str, float]:
    action_events = [event for event in events if event["action"] in {"write", "pass"}]
    write_events = [event for event in action_events if event["action"] == "write"]
    pass_events = [event for event in action_events if event["action"] == "pass"]

    row_writes = sum(1 for event in write_events if event["agent"] == "row")
    col_writes = sum(1 for event in write_events if event["agent"] == "col")
    ind_writes = sum(1 for event in write_events if event["agent"] == "ind")
    row_passes = sum(1 for event in pass_events if event["agent"] == "row")
    col_passes = sum(1 for event in pass_events if event["agent"] == "col")
    ind_passes = sum(1 for event in pass_events if event["agent"] == "ind")

    first_pass_index: Optional[int] = None
    writes_before_first_pass = len(write_events)
    for idx, event in enumerate(action_events):
        if event["action"] == "pass":
            first_pass_index = idx
            writes_before_first_pass = sum(
                1 for previous in action_events[:idx] if previous["action"] == "write"
            )
            break

    fill_writes = sum(
        1 for event in write_events if event.get("move", {}).get("value_name") == "FILLED"
    )
    empty_writes = sum(
        1 for event in write_events if event.get("move", {}).get("value_name") == "EMPTY"
    )

    active_write_agents = sum(1 for value in (row_writes, col_writes, ind_writes) if value > 0)
    active_pass_agents = sum(1 for value in (row_passes, col_passes, ind_passes) if value > 0)
    dominant_write_share = max([row_writes, col_writes, ind_writes], default=0) / max(1, len(write_events))

    if first_pass_index is None:
        first_pass_turn = -1.0
        first_pass_penalty = 0.0
    else:
        first_pass_turn = float(action_events[first_pass_index]["turn"])
        first_pass_penalty = 1.0 - (writes_before_first_pass / max(1, num_cells))

    return {
        "action_turns": float(len(action_events)),
        "write_events": float(len(write_events)),
        "pass_events": float(len(pass_events)),
        "row_writes": float(row_writes),
        "col_writes": float(col_writes),
        "ind_writes": float(ind_writes),
        "row_passes": float(row_passes),
        "col_passes": float(col_passes),
        "ind_passes": float(ind_passes),
        "active_write_agents": float(active_write_agents),
        "active_pass_agents": float(active_pass_agents),
        "fill_writes": float(fill_writes),
        "empty_writes": float(empty_writes),
        "write_fill_ratio": fill_writes / max(1, len(write_events)),
        "write_empty_ratio": empty_writes / max(1, len(write_events)),
        "row_col_write_imbalance": abs(row_writes - col_writes) / max(1, len(write_events)),
        "dominant_write_share": dominant_write_share,
        "first_pass_turn": first_pass_turn,
        "writes_before_first_pass": float(writes_before_first_pass),
        "initial_forced_ratio": writes_before_first_pass / max(1, num_cells),
        "first_pass_penalty": first_pass_penalty,
        "pass_density": len(pass_events) / max(1, num_cells),
        "pass_ratio": len(pass_events) / max(1, len(action_events)),
        "turn_pressure": len(action_events) / max(1, max_turns),
    }


def complexity_score(features: Dict[str, float], num_cells: int, n_rows: int, n_cols: int) -> float:
    size_factor = clamp(num_cells / 225.0, 0.0, 1.0)
    nontrivial_line_ratio = 1.0 - features["trivial_line_ratio"]
    block_density = clamp(
        features["avg_blocks_per_line"] / max(1.0, features["avg_max_blocks"]),
        0.0,
        1.0,
    )
    density_balance = clamp(features["density_balance"], 0.0, 1.0)
    transition_norm = clamp(
        features["avg_transitions_per_line"] / max(1.0, max(n_rows - 1, n_cols - 1)),
        0.0,
        1.0,
    )

    score = 100.0 * (
        0.15 * size_factor
        + 0.30 * nontrivial_line_ratio
        + 0.20 * block_density
        + 0.20 * density_balance
        + 0.15 * transition_norm
    )
    return round(score, 2)


def complexity_label(score: float) -> str:
    if score < 20:
        return "very_low"
    if score < 40:
        return "low"
    if score < 60:
        return "medium"
    if score < 80:
        return "high"
    return "very_high"


def difficulty_score(
    solved: bool,
    unknown_ratio: float,
    pass_density: float,
    first_pass_penalty: float,
    turn_pressure: float,
) -> float:
    score = 100.0 * (
        0.45 * clamp(unknown_ratio, 0.0, 1.0)
        + 0.25 * clamp(pass_density, 0.0, 1.0)
        + 0.20 * clamp(first_pass_penalty, 0.0, 1.0)
        + 0.10 * clamp(turn_pressure, 0.0, 1.0)
    )

    if not solved:
        score += 25.0 + 25.0 * clamp(unknown_ratio, 0.0, 1.0)

    return round(clamp(score, 0.0, 100.0), 2)


def difficulty_label(solved: bool, unknown_ratio: float, score: float) -> str:
    if not solved:
        if unknown_ratio >= 0.40:
            return "stalled_hard"
        if unknown_ratio >= 0.15:
            return "stalled_moderate"
        return "stalled_near_complete"

    if score < 10:
        return "trivial"
    if score < 25:
        return "easy"
    if score < 45:
        return "moderate"
    if score < 65:
        return "challenging"
    return "hard"


def overall_label(complexity_label_value: str, difficulty_label_value: str) -> str:
    if difficulty_label_value.startswith("stalled"):
        return difficulty_label_value
    if difficulty_label_value == "trivial" and complexity_label_value in {"very_low", "low"}:
        return "trivial"
    if difficulty_label_value in {"easy", "moderate"} and complexity_label_value in {"high", "very_high"}:
        return "moderate"
    return difficulty_label_value


def sample_id_for_row(path: Path, metadata: Dict[str, Any]) -> str:
    source = metadata.get("source", {})
    sample_idx = source.get("sample_idx")
    if sample_idx is None:
        return path.stem
    return str(sample_idx)


def analyze_payload(path: Path, payload: Dict[str, Any]) -> Dict[str, Any]:
    metadata = payload["metadata"]
    summary = payload["summary"]
    row_clues = metadata["row_clues"]
    col_clues = metadata["col_clues"]
    target_grid = payload.get("target_grid")
    events = payload["events"]

    n_rows = metadata["board_rows"]
    n_cols = metadata["board_cols"]
    num_cells = n_rows * n_cols
    max_turns = metadata["max_turns"]
    source = metadata.get("source", {})
    solver = metadata.get("solver")
    if solver is None:
        event_agents = {event.get("agent") for event in events}
        if "ind" in event_agents:
            solver = "ind"
        elif "row" in event_agents or "col" in event_agents:
            solver = "collab"
        else:
            solver = "unknown"

    strategy = metadata.get("strategy")
    row_strategy = metadata.get("row_strategy", strategy)
    col_strategy = metadata.get("col_strategy", strategy)

    clue_stats = line_clue_stats(row_clues, col_clues)
    grid_stats = target_grid_stats(target_grid, row_clues, col_clues)
    run_stats = event_stats(events, num_cells=num_cells, max_turns=max_turns)

    unknown_cells = summary["unknown_cells"]
    unknown_ratio = unknown_cells / max(1, num_cells)
    solved = bool(summary["solved"])
    matches_target = summary.get("matches_target")

    merged: Dict[str, Any] = {
        "log_file": str(path),
        "sample_id": sample_id_for_row(path, metadata),
        "sample_idx": source.get("sample_idx"),
        "source_x_path": source.get("x_path"),
        "source_y_path": source.get("y_path"),
        "board_rows": n_rows,
        "board_cols": n_cols,
        "num_cells": num_cells,
        "solver": solver,
        "agent_mode": "individual" if solver == "ind" else "collaborative" if solver == "collab" else "unknown",
        "strategy": strategy if strategy is not None else row_strategy,
        "row_strategy": row_strategy,
        "col_strategy": col_strategy,
        "max_turns": max_turns,
        "solved": solved,
        "matches_target": matches_target,
        "unknown_cells": unknown_cells,
        "unknown_ratio": round(unknown_ratio, 4),
    }
    merged.update({k: round(v, 4) if isinstance(v, float) else v for k, v in clue_stats.items()})
    merged.update({k: round(v, 4) if isinstance(v, float) else v for k, v in grid_stats.items()})
    merged.update({k: round(v, 4) if isinstance(v, float) else v for k, v in run_stats.items()})

    c_score = complexity_score(merged, num_cells=num_cells, n_rows=n_rows, n_cols=n_cols)
    c_label = complexity_label(c_score)
    d_score = difficulty_score(
        solved=solved,
        unknown_ratio=unknown_ratio,
        pass_density=run_stats["pass_density"],
        first_pass_penalty=run_stats["first_pass_penalty"],
        turn_pressure=run_stats["turn_pressure"],
    )
    d_label = difficulty_label(solved=solved, unknown_ratio=unknown_ratio, score=d_score)
    overall = overall_label(c_label, d_label)

    merged["complexity_score"] = c_score
    merged["complexity_label"] = c_label
    merged["difficulty_score"] = d_score
    merged["difficulty_label"] = d_label
    merged["overall_label"] = overall

    return merged


def csv_columns(rows: Iterable[Dict[str, Any]]) -> List[str]:
    rows = list(rows)
    if not rows:
        return []

    preferred = [
        "sample_id",
        "sample_idx",
        "log_file",
        "source_x_path",
        "source_y_path",
        "board_rows",
        "board_cols",
        "num_cells",
        "solver",
        "agent_mode",
        "strategy",
        "solved",
        "matches_target",
        "unknown_cells",
        "unknown_ratio",
        "total_blocks",
        "avg_blocks_per_line",
        "max_blocks_on_line",
        "block_count_std",
        "avg_block_length",
        "block_length_std",
        "zero_clue_rows",
        "zero_clue_cols",
        "full_rows",
        "full_cols",
        "trivial_line_ratio",
        "filled_cells",
        "filled_ratio",
        "density_balance",
        "avg_transitions_per_line",
        "action_turns",
        "write_events",
        "pass_events",
        "row_writes",
        "col_writes",
        "ind_writes",
        "row_passes",
        "col_passes",
        "ind_passes",
        "active_write_agents",
        "active_pass_agents",
        "fill_writes",
        "empty_writes",
        "write_fill_ratio",
        "write_empty_ratio",
        "row_col_write_imbalance",
        "dominant_write_share",
        "first_pass_turn",
        "writes_before_first_pass",
        "initial_forced_ratio",
        "pass_density",
        "pass_ratio",
        "turn_pressure",
        "max_turns",
        "row_strategy",
        "col_strategy",
        "complexity_score",
        "complexity_label",
        "difficulty_score",
        "difficulty_label",
        "overall_label",
    ]

    row_keys = set().union(*(row.keys() for row in rows))
    remaining = sorted(key for key in row_keys if key not in preferred)
    return preferred + remaining


def write_csv(rows: List[Dict[str, Any]], output_csv: str) -> None:
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fields = csv_columns(rows)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Analyze nonogram solver logs and export per-puzzle complexity/difficulty metrics."
    )
    parser.add_argument("--log-dir", required=True, help="Folder containing JSON log files")
    parser.add_argument(
        "--output-csv",
        default="nonogram_log_analysis.csv",
        help="Destination CSV path",
    )
    args = parser.parse_args()

    log_paths = iter_log_paths(args.log_dir)
    if not log_paths:
        raise ValueError(f"No JSON logs found under {args.log_dir}")

    rows = [analyze_payload(path, load_payload(path)) for path in log_paths]
    rows.sort(
        key=lambda row: (
            row["board_rows"],
            row["board_cols"],
            float("inf") if row["sample_idx"] in (None, "") else int(row["sample_idx"]),
            str(row["sample_id"]),
        )
    )
    write_csv(rows, args.output_csv)

    print(f"Analyzed {len(rows)} log(s)")
    print(f"Saved CSV to {args.output_csv}")


if __name__ == "__main__":
    main()
