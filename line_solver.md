# Line Solver Tutorial

This note explains how the line solver in [test.py](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py) works.

The goal is to describe the exact logic used by the current nonogram solver, not a generic nonogram strategy.

## 1. What The Line Solver Does

The solver treats each row or column as a separate `line`.

For one line, it takes:
- the line length
- the clue list for that line
- the current known cell states on that line

Then it:
1. generates every valid pattern for that line
2. removes patterns that conflict with known cells
3. compares the remaining patterns
4. marks a cell as forced if every remaining pattern agrees on that cell

This is implemented mainly in:
- [prefix_consistent](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L159)
- [line_consistent](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L166)
- [generate_line_patterns](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L173)
- [get_forced_cells_from_line](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L224)

## 2. Cell Encoding

The line solver uses three cell states:

- `UNKNOWN = -1`
- `EMPTY = 0`
- `FILLED = 1`

So a line like:

```text
[UNKNOWN, UNKNOWN, FILLED, UNKNOWN, EMPTY]
```

means:
- first cell not known yet
- second cell not known yet
- third cell definitely black / filled
- fourth cell not known yet
- fifth cell definitely empty

## 3. What A Clue Means

A clue like:

```text
[3, 1]
```

means:
- one block of `3` consecutive filled cells
- then at least one empty separator
- then one block of `1` filled cell

Examples of valid length-7 patterns for `[3, 1]` are:

```text
1110100
1110010
1110001
0111010
0111001
0011101
```

The exact set depends on the line length.

## 4. Step 1: Consistency Checks

Before looking for forced cells, the code needs to decide whether a partial or complete candidate conflicts with what is already known.

### 4.1 `prefix_consistent`

Function:
- [prefix_consistent](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L159)

Purpose:
- check whether a partial candidate is still possible

Logic:
- compare the current partial prefix with the known cells in the line
- if any known cell disagrees, reject that branch early

Example:

```text
current_line = [UNKNOWN, EMPTY, UNKNOWN, UNKNOWN]
prefix       = [FILLED, FILLED]
```

At index `1`, the line says `EMPTY` but the prefix says `FILLED`, so this prefix is inconsistent and is rejected immediately.

This is important because it prunes bad branches before building a full candidate.

### 4.2 `line_consistent`

Function:
- [line_consistent](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L166)

Purpose:
- check whether a full candidate matches all known cells

Logic:
- for every position:
  - if the line says `UNKNOWN`, anything is allowed
  - if the line says `FILLED` or `EMPTY`, the candidate must match it

Example:

```text
current_line = [UNKNOWN, EMPTY, FILLED, UNKNOWN]
candidate    = [FILLED, EMPTY, FILLED, EMPTY]
```

This is consistent.

But:

```text
candidate    = [FILLED, FILLED, FILLED, EMPTY]
```

is inconsistent because index `1` should be `EMPTY`.

## 5. Step 2: Generate All Valid Line Patterns

Function:
- [generate_line_patterns](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L173)

This function generates every line pattern that satisfies:
- the clue
- the line length
- the currently known cells

### 5.1 Easy Case: No Clues

If the clue list is empty:

```text
clues = []
```

then the whole line must be empty.

So the only candidate is:

```text
[EMPTY, EMPTY, ..., EMPTY]
```

If that candidate conflicts with known cells, then there are no valid patterns.

### 5.2 General Case: Backtracking

For non-empty clues, the code uses recursive backtracking.

The recursive helper tracks:
- `clue_idx`: which clue block is being placed
- `pos`: earliest legal start position for the next block
- `partial`: the line built so far

At each step:
1. choose a legal start index for the current block
2. insert empties before the block
3. place the filled block
4. if this is not the last block, add one mandatory empty separator
5. check the partial candidate with `prefix_consistent`
6. recurse to place the next block

### 5.3 Why `max_start` Matters

In the code:

```text
remaining = clues[clue_idx + 1:]
min_remaining_len = sum(remaining) + max(0, len(remaining))
max_start = length - block_len - min_remaining_len
```

This calculates the latest position where the current block can start while still leaving enough room for all remaining blocks and their required separators.

Without this, the search would try impossible placements.

## 6. Worked Example: `[3]` In A Length-5 Line

Suppose:

```text
length = 5
clues = [3]
current_line = [UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN, UNKNOWN]
```

Valid candidates are:

```text
11100
01110
00111
```

There are only three because the block of length `3` can start at positions `0`, `1`, or `2`.

## 7. Step 3: Find Forced Cells

Function:
- [get_forced_cells_from_line](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L224)

Once all valid patterns are generated, the code compares them position by position.

For each index `i`:
- collect all values that appear at index `i` across all patterns
- if the set has size `1`, that position is forced
- if the current line still has `UNKNOWN` there, return it as a move

### Example: `[3]` In Length 5

Patterns:

```text
11100
01110
00111
```

Compare by column:

- position 0: `1,0,0` -> not forced
- position 1: `1,1,0` -> not forced
- position 2: `1,1,1` -> forced `FILLED`
- position 3: `0,1,1` -> not forced
- position 4: `0,0,1` -> not forced

So the solver returns:

```text
[(2, FILLED)]
```

## 8. Worked Example With Known Cells

Suppose:

```text
length = 5
clues = [3]
current_line = [UNKNOWN, EMPTY, UNKNOWN, UNKNOWN, UNKNOWN]
```

All raw placements for `[3]` would be:

```text
11100
01110
00111
```

Now compare with the known line:
- position 1 is already `EMPTY`

So:
- `11100` is impossible because it puts `FILLED` at position 1
- `01110` is valid
- `00111` is valid

Remaining patterns:

```text
01110
00111
```

Compare by position:
- position 0: `0,0` -> forced `EMPTY`
- position 1: `1,0` -> not forced, but note this cell is already known empty in the line
- position 2: `1,1` -> forced `FILLED`
- position 3: `1,1` -> forced `FILLED`
- position 4: `0,1` -> not forced

Since the solver only returns newly forced unknown cells, it would return:

```text
[(0, EMPTY), (2, FILLED), (3, FILLED)]
```

## 9. Worked Example: Exact-Fit Line

Suppose:

```text
length = 10
clues = [3, 2, 3]
current_line = all UNKNOWN
```

The total space required is:

```text
3 + 2 + 3 + 2 separators = 10
```

So there is only one valid pattern:

```text
1110110111
```

Because there is only one valid pattern, every cell is forced.

This is why exact-fit clues are so strong.

## 10. Why The Line Solver Is Powerful

The line solver is more general than simple overlap logic.

Simple overlap logic only reasons from obvious block overlap.
This solver instead:
- enumerates all legal patterns
- removes any that conflict with current knowledge
- then finds agreement across all survivors

That means it can discover:
- forced fills
- forced empties
- new deductions that only become visible after earlier moves

## 11. How The Row And Column Agents Use It

The line solver itself works on one line only.

The row agent:
- [row_agent_move](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L254)
- runs `get_forced_cells_from_line` on each row
- collects all forced row moves
- chooses one move using a tie-break strategy

The column agent:
- [col_agent_move](/Users/lianglee/Desktop/0HMC/ERC/nonogram/test.py#L284)
- does the same on columns

So the full puzzle solver is built by repeatedly applying the line solver to rows and columns.

## 12. Tie-Break Strategies

When multiple forced moves exist, the code chooses one using:

- `first`
  first candidate found in scan order
- `random`
  choose a random candidate
- `most_constrained`
  prefer the line with fewer unknown cells remaining

These strategies do not change what is logically valid.
They only change which valid move is taken next.

## 13. When The Solver Passes

An agent passes when the line solver finds no forced move on any line it can inspect.

That means:
- the row agent checked all rows and found no new forced cells
or
- the column agent checked all columns and found no new forced cells

In that case the agent returns `None`, and the event is recorded as a `pass` in the log.

## 14. Limitations Of The Line Solver

This solver does not:
- guess
- backtrack
- search globally over full-board states
- reason with probabilistic confidence

It only uses:
- exact pattern generation per line
- consistency with known cells
- agreement across valid line completions

So if no line has a forced cell, the solver stalls even if the puzzle is still solvable by deeper reasoning.

## 15. Summary

The line solver in `test.py` works like this:

1. generate all valid patterns for a line
2. discard patterns inconsistent with current knowledge
3. compare the remaining patterns
4. any cell that is identical in all remaining patterns is forced
5. row and column agents repeatedly use this to update the board

That is the core logic behind the current two-agent nonogram solver.
