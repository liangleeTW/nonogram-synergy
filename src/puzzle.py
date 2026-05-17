"""Core nonogram puzzle representation and clue utilities.

Expected output files:
- None; this module is imported by solvers, metrics, and dataset builders.

Command to run code:
- poetry run python -m unittest tests/test_puzzle.py
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import cached_property, lru_cache
from typing import Iterable, Optional, Sequence, Tuple

EMPTY = 0
FILLED = 1

Cell = int
Line = Tuple[Cell, ...]
Grid = Tuple[Line, ...]
Clue = Tuple[int, ...]
ClueSet = Tuple[Clue, ...]


@dataclass(frozen=True)
class Puzzle:
    row_clues: ClueSet
    col_clues: ClueSet
    solution: Optional[Grid] = None

    def __post_init__(self) -> None:
        row_clues = normalize_clues(self.row_clues)
        col_clues = normalize_clues(self.col_clues)
        object.__setattr__(self, "row_clues", row_clues)
        object.__setattr__(self, "col_clues", col_clues)

        if self.solution is not None:
            solution = normalize_solution(self.solution)
            validate_solution_shape(solution)
            if len(solution) != len(row_clues) or len(solution[0]) != len(col_clues):
                raise ValueError("Solution shape does not match clue dimensions")
            extracted_rows, extracted_cols = extract_all_clues(solution)
            if extracted_rows != row_clues or extracted_cols != col_clues:
                raise ValueError("Stored clues do not match solution-derived clues")
            object.__setattr__(self, "solution", solution)

    @classmethod
    def from_solution(cls, solution: Iterable[Sequence[int]]) -> "Puzzle":
        normalized_solution = normalize_solution(solution)
        row_clues, col_clues = extract_all_clues(normalized_solution)
        return cls(
            solution=normalized_solution,
            row_clues=row_clues,
            col_clues=col_clues,
        )

    @classmethod
    def from_clues(
        cls,
        row_clues: Iterable[Sequence[int]],
        col_clues: Iterable[Sequence[int]],
        solution: Optional[Iterable[Sequence[int]]] = None,
    ) -> "Puzzle":
        normalized_solution = None if solution is None else normalize_solution(solution)
        return cls(
            solution=normalized_solution,
            row_clues=normalize_clues(row_clues),
            col_clues=normalize_clues(col_clues),
        )

    @property
    def grid_size(self) -> Tuple[int, int]:
        return len(self.row_clues), len(self.col_clues)

    @cached_property
    def valid_row_configs(self) -> Tuple[Tuple[Line, ...], ...]:
        _, n_cols = self.grid_size
        return tuple(enumerate_valid_lines(n_cols, clue) for clue in self.row_clues)

    @cached_property
    def valid_col_configs(self) -> Tuple[Tuple[Line, ...], ...]:
        n_rows, _ = self.grid_size
        return tuple(enumerate_valid_lines(n_rows, clue) for clue in self.col_clues)

    def row_clues_as_lists(self) -> list[list[int]]:
        return clues_as_lists(self.row_clues)

    def col_clues_as_lists(self) -> list[list[int]]:
        return clues_as_lists(self.col_clues)

    def solution_as_lists(self) -> Optional[list[list[int]]]:
        if self.solution is None:
            return None
        return [list(row) for row in self.solution]


def normalize_solution(solution: Iterable[Sequence[int]]) -> Grid:
    return tuple(tuple(int(cell) for cell in row) for row in solution)


def validate_solution_shape(solution: Grid) -> None:
    if not solution:
        raise ValueError("Solution must contain at least one row")
    width = len(solution[0])
    if width == 0:
        raise ValueError("Solution rows must contain at least one cell")
    for row in solution:
        if len(row) != width:
            raise ValueError("Solution rows must all have the same width")
        invalid = [cell for cell in row if cell not in {EMPTY, FILLED}]
        if invalid:
            raise ValueError(f"Solution contains non-binary cell value(s): {invalid}")


def normalize_clue(clue: Sequence[int]) -> Clue:
    return tuple(int(value) for value in clue if int(value) != 0)


def normalize_clues(clues: Iterable[Sequence[int]]) -> ClueSet:
    return tuple(normalize_clue(clue) for clue in clues)


def clues_as_lists(clues: Iterable[Sequence[int]]) -> list[list[int]]:
    return [list(clue) for clue in clues]


def extract_line_clue(line: Sequence[int]) -> Clue:
    blocks: list[int] = []
    current = 0
    for cell in line:
        value = int(cell)
        if value == FILLED:
            current += 1
        elif value == EMPTY:
            if current:
                blocks.append(current)
                current = 0
        else:
            raise ValueError(f"Cannot extract clue from non-binary cell value: {cell}")

    if current:
        blocks.append(current)
    return tuple(blocks)


def extract_row_clues(solution: Iterable[Sequence[int]]) -> ClueSet:
    grid = normalize_solution(solution)
    validate_solution_shape(grid)
    return tuple(extract_line_clue(row) for row in grid)


def extract_col_clues(solution: Iterable[Sequence[int]]) -> ClueSet:
    grid = normalize_solution(solution)
    validate_solution_shape(grid)
    n_cols = len(grid[0])
    return tuple(
        extract_line_clue(tuple(row[col] for row in grid))
        for col in range(n_cols)
    )


def extract_all_clues(solution: Iterable[Sequence[int]]) -> Tuple[ClueSet, ClueSet]:
    grid = normalize_solution(solution)
    validate_solution_shape(grid)
    return extract_row_clues(grid), extract_col_clues(grid)


@lru_cache(maxsize=None)
def enumerate_valid_lines(length: int, clue: Clue) -> Tuple[Line, ...]:
    clue = normalize_clue(clue)
    if length < 0:
        raise ValueError("Line length must be non-negative")
    if not clue:
        return (tuple([EMPTY] * length),)

    lines: list[Line] = []

    def backtrack(clue_idx: int, pos: int, partial: list[int]) -> None:
        if clue_idx == len(clue):
            lines.append(tuple(partial + [EMPTY] * (length - len(partial))))
            return

        block_len = clue[clue_idx]
        remaining = clue[clue_idx + 1:]
        min_remaining_len = sum(remaining) + max(0, len(remaining))
        max_start = length - block_len - min_remaining_len

        for start in range(pos, max_start + 1):
            candidate = partial[:]
            candidate.extend([EMPTY] * (start - len(candidate)))
            candidate.extend([FILLED] * block_len)
            if clue_idx < len(clue) - 1:
                candidate.append(EMPTY)
            backtrack(clue_idx + 1, len(candidate), candidate)

    backtrack(0, 0, [])
    return tuple(lines)
