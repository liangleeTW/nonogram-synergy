"""Generate a controlled CSV dataset of random unique nonogram puzzles.
--size 5: generate 5x5 puzzles.
--density 0.35: target about 35% filled cells.
--density 0.50: also generate puzzles with about 50% filled cells.
--density 0.65: also generate puzzles with about 65% filled cells.
--puzzles-per-cell 10: keep 10 unique puzzles for each size-density condition. Here that means 3 densities * 10 = 30 puzzles total.

Expected output files:
- results/analysis/controlled_puzzles.csv by default, or the path passed to --output-csv.

Command to run code:
- poetry run python scripts/build_controlled_dataset.py --size 5 --density 0.35 --density 0.50 --density 0.65 --puzzles-per-cell 300 --output-csv results/analysis/controlled_puzzles_5x5.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from puzzle import Puzzle  # noqa: E402
from puzzle_metrics import puzzle_metrics  # noqa: E402


def parse_ints(values: Sequence[str]) -> List[int]:
    return [int(value) for value in values]


def parse_floats(values: Sequence[str]) -> List[float]:
    return [float(value) for value in values]


def random_solution(size: int, density: float, rng: np.random.Generator) -> list[list[int]]:
    return (rng.random((size, size)) < density).astype(int).tolist()


def puzzle_id(size: int, density: float, index: int) -> str:
    density_token = f"{density:.2f}".replace(".", "p")
    return f"n{size}_d{density_token}_{index:05d}"


def puzzle_row(
    puzzle: Puzzle,
    metrics: Dict[str, Any],
    dataset_id: str,
    target_density: float,
    seed: int,
    attempts_used: int,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "puzzle_id": dataset_id,
        "target_density": target_density,
        "seed": seed,
        "attempts_used": attempts_used,
        "solution": json.dumps(puzzle.solution_as_lists(), separators=(",", ":")),
        "row_clues": json.dumps(puzzle.row_clues_as_lists(), separators=(",", ":")),
        "col_clues": json.dumps(puzzle.col_clues_as_lists(), separators=(",", ":")),
    }
    row.update(metrics)
    return row


def generate_unique_puzzles(
    sizes: Sequence[int],
    densities: Sequence[float],
    puzzles_per_cell: int,
    max_attempts_per_cell: int,
    seed: int,
) -> List[Dict[str, Any]]:
    rng = np.random.default_rng(seed)
    rows: List[Dict[str, Any]] = []
    seen_clues: set[tuple[Any, ...]] = set()

    for size in sizes:
        for density in densities:
            accepted = 0
            attempts = 0
            while accepted < puzzles_per_cell and attempts < max_attempts_per_cell:
                attempts += 1
                solution = random_solution(size, density, rng)
                puzzle = Puzzle.from_solution(solution)
                clue_key = (puzzle.row_clues, puzzle.col_clues)
                if clue_key in seen_clues:
                    continue

                metrics = puzzle_metrics(puzzle, max_solutions=2)
                if not metrics["unique"]:
                    continue

                seen_clues.add(clue_key)
                rows.append(
                    puzzle_row(
                        puzzle=puzzle,
                        metrics=metrics,
                        dataset_id=puzzle_id(size, density, len(rows)),
                        target_density=density,
                        seed=seed,
                        attempts_used=attempts,
                    )
                )
                accepted += 1

            if accepted < puzzles_per_cell:
                print(
                    f"Warning: accepted {accepted}/{puzzles_per_cell} "
                    f"for size={size}, density={density} after {attempts} attempts",
                    file=sys.stderr,
                )

    return rows


def write_csv(rows: Sequence[Dict[str, Any]], output_csv: str) -> None:
    if not rows:
        raise ValueError("No puzzles generated")
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
        description="Generate a controlled table of random unique nonogram puzzles."
    )
    parser.add_argument("--size", action="append", help="Puzzle size. Repeatable. Defaults to 5.")
    parser.add_argument(
        "--density",
        action="append",
        help="Target filled density. Repeatable. Defaults to 0.35, 0.50, 0.65.",
    )
    parser.add_argument(
        "--puzzles-per-cell",
        type=int,
        default=10,
        help="Unique puzzles to keep per size-density condition.",
    )
    parser.add_argument(
        "--max-attempts-per-cell",
        type=int,
        default=1000,
        help="Maximum random solutions to try per size-density condition.",
    )
    parser.add_argument("--seed", type=int, default=0, help="Random seed.")
    parser.add_argument(
        "--output-csv",
        default="results/analysis/controlled_puzzles.csv",
        help="Destination CSV path.",
    )
    args = parser.parse_args()

    sizes = parse_ints(args.size) if args.size else [5]
    densities = parse_floats(args.density) if args.density else [0.35, 0.50, 0.65]

    rows = generate_unique_puzzles(
        sizes=sizes,
        densities=densities,
        puzzles_per_cell=args.puzzles_per_cell,
        max_attempts_per_cell=args.max_attempts_per_cell,
        seed=args.seed,
    )
    write_csv(rows, args.output_csv)
    print(f"Generated {len(rows)} unique puzzle(s)")
    print(f"Saved CSV to {args.output_csv}")


if __name__ == "__main__":
    main()
