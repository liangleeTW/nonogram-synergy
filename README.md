# Nonogram Collaboration Project

This repository studies collaborative nonogram solving under partial information.

The main inference engine is still a line solver:
- it enumerates all line patterns consistent with a clue and the current board state
- it writes only what is justified from that line model
- the deterministic scripts do not guess or backtrack

There are two layers in the codebase:
- deterministic line-solver scripts used as engineering baselines
- stochastic latent-choice scripts used as cognitive process models

## What Each File Does

Core solver and data utilities:
- `solver_common.py`: shared constants, dataset loading, clue decoding, line-pattern generation, forced-cell extraction, JSON log building

Deterministic solver entry points:
- `collab.py`: two-agent collaborative condition; row agent sees only row clues, column agent sees only column clues
- `ind.py`: one-agent full-information baseline; the single agent sees both clue sets but still makes one line-justified move at a time

Stochastic latent-choice entry points:
- `latent_collab.py`: partial-information row/column agents with stochastic choice over line-based candidate actions
- `sweep_latent.py`: batch runner for repeated latent-model simulations over seeds and parameter settings

Visualization and analysis:
- `vis.py`: converts solver JSON logs into GIF or MP4 replay animations
- `analyze_logs.py`: converts a directory of JSON logs into a per-run CSV with summary, complexity, and difficulty measures
- `compare_runs.py`: compares `collab` and `ind` runs from the analysis CSV and can also save a simple plot

Research notes:
- `note.md`: conceptual modeling note for the latent behavioral models
- `line_solver.md`: notes about the line-solver logic
- `information.md`: supporting project notes

## Input And Output

Input files:
- `x_*.npz`: packed row and column clues
- `y_*.npz`: target solution grids

Current dataset examples:
- `NonoDataset-main/10x10/x_test_dataset.npz`
- `NonoDataset-main/10x10/y_test_dataset.npz`
- `NonoDataset-main/15x15/x_test_15x15_ok.npz`
- `NonoDataset-main/15x15/y_test_15x15_ok.npz`

Output files:
- solver scripts write JSON logs
- `vis.py` writes GIF or MP4 files
- `analyze_logs.py` writes a summary CSV
- `compare_runs.py` can write comparison CSVs and a plot
- `sweep_latent.py` writes a simulation-summary CSV and can optionally save per-run JSON logs

## How To Run The Project

This is the recommended order for a new user.

### Step 1. Create The Environment

The scripts require Python `>= 3.12`, `numpy`, and `matplotlib`.

If you want to use the local virtual environment pattern used in this repository:

```bash
python3 -m venv .venv
.venv/bin/pip install numpy matplotlib
```

If you use Poetry:

```bash
poetry install
```

### Step 2. Run One Deterministic Collaborative Example

```bash
.venv/bin/python collab.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-idx 0 \
  --quiet
```

Default output path:

```text
logs/x_test_dataset__row-first__col-first/x_test_dataset__sample-00000.json
```

### Step 3. Run One Deterministic Individual Baseline Example

```bash
.venv/bin/python ind.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-idx 0 \
  --quiet
```

Default output path:

```text
logs/x_test_dataset__ind-first/x_test_dataset__sample-00000.json
```

### Step 4. Visualize A Solver Log

```bash
.venv/bin/python vis.py \
  --log-path logs/x_test_dataset__row-first__col-first/x_test_dataset__sample-00000.json \
  --gif-path nonogram_replay.gif
```

### Step 5. Run A Batch Of Deterministic Logs

Collaborative solver over a sample range:

```bash
.venv/bin/python collab.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-start 0 \
  --sample-end 10 \
  --quiet
```

Individual baseline over a sample range:

```bash
.venv/bin/python ind.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-start 0 \
  --sample-end 10 \
  --quiet
```

Run the whole dataset:

```bash
.venv/bin/python collab.py --x-path NonoDataset-main/10x10/x_test_dataset.npz --y-path NonoDataset-main/10x10/y_test_dataset.npz --all-samples --quiet
.venv/bin/python ind.py --x-path NonoDataset-main/10x10/x_test_dataset.npz --y-path NonoDataset-main/10x10/y_test_dataset.npz --all-samples --quiet
```

### Step 6. Analyze Deterministic Logs

```bash
.venv/bin/python analyze_logs.py \
  --log-dir logs/x_test_dataset__row-first__col-first \
  --output-csv /tmp/collab_analysis.csv
```

If you want to use `compare_runs.py`, first create an analysis CSV from a directory that contains both `collab.py` and `ind.py` logs for the same samples.

```bash
.venv/bin/python compare_runs.py \
  --analysis-csv /tmp/mixed_analysis.csv \
  --summary-csv /tmp/summary.csv \
  --size-summary-csv /tmp/size_summary.csv \
  --plot-path /tmp/compare.png
```

### Step 7. Run Stochastic Latent Simulations

One stochastic latent run:

```bash
.venv/bin/python latent_collab.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-idx 0 \
  --utility-model collaborative \
  --choice-set threshold \
  --tau 0.75 \
  --beta 5 \
  --lambda-weight 1.0 \
  --seed 0 \
  --quiet
```

Sweep over many runs:

```bash
.venv/bin/python sweep_latent.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-start 0 \
  --sample-end 100 \
  --utility-model individual \
  --utility-model collaborative \
  --choice-set certainty1 \
  --choice-set threshold \
  --tau 0.75 \
  --beta 5 \
  --lambda-weight 1.0 \
  --seed 0 \
  --seed 1 \
  --output-csv /tmp/latent_sweep.csv \
  --quiet
```

## Important Command-Line Options

Shared dataset selection flags:
- `--x-path`: clue file
- `--y-path`: optional target-grid file
- `--sample-idx`: run one sample
- `--all-samples`: run the whole dataset
- `--sample-start`, `--sample-end`: run a half-open range `[start, end)`

Shared output flags:
- `--json-path`: explicit output JSON file for a single run
- `--output-dir`: directory for automatically named outputs in batch mode
- `--quiet`: disable turn-by-turn printing

Deterministic solver options:
- `collab.py --row-strategy {first,random,most_constrained}`
- `collab.py --col-strategy {first,random,most_constrained}`
- `ind.py --strategy {first,random,most_constrained}`
- `ind.py --row-strategy` and `--col-strategy`: aliases kept for interface compatibility with `collab.py`
- `--max-turns`: default is `2 * number_of_cells`

Latent-model options:
- `--utility-model {individual,collaborative}`
- `--choice-set {certainty1,threshold,all_legal}`
- `--alpha`: weight on own evidence `Q_own`
- `--beta`: softmax inverse temperature
- `--tau`: threshold used by the `threshold` choice set
- `--lambda-weight`: weight on local partner-information gain
- `--seed`: random seed

Visualization options:
- `vis.py --log-path`: one or more JSON logs
- `vis.py --log-dir`: directory of logs
- `vis.py --gif-path`: single GIF output path
- `vis.py --output-dir`: batch GIF output directory
- `vis.py --interval`: animation frame interval

## Output Structure

`collab.py`, `ind.py`, and `latent_collab.py` all write JSON logs with the same top-level structure:
- `metadata`
- `summary`
- `target_grid`
- `final_grid`
- `events`

`latent_collab.py` additionally writes:
- `candidate_steps`

Important summary fields:
- `unknown_cells`: number of cells still unresolved at the end
- `solved`: whether there are no unknown cells left
- `matches_target`: whether the final board equals the target grid when `--y-path` is provided
- `write_events`
- `pass_events`

Important distinction:
- `solved` means the board is complete
- `matches_target` means the completed board is correct

For deterministic line-solver runs, these usually coincide.
For stochastic latent runs with sub-certain actions, they can diverge.

## Solver Logic

Both solver scripts use the same underlying line-solver core.

### Collaborative Solver: `collab.py`

### What Each Agent Sees

- the row agent only uses row clues and the current contents of each row
- the column agent only uses column clues and the current contents of each column

Neither agent reasons globally over the whole puzzle. Each move is justified by one line only.

### Cell States

The grid uses three states:
- `UNKNOWN = -1`
- `EMPTY = 0`
- `FILLED = 1`

At the start, every cell is `UNKNOWN`.

### How One Line Is Solved

For a given row or column:

1. the solver generates every valid line pattern that matches:
   - the clue numbers for that line
   - the current known cells in that line
2. it compares all valid patterns position by position
3. if a cell has the same value in every valid pattern, that cell is forced

This means:
- if every valid pattern has a cell filled, the agent can write `FILLED`
- if every valid pattern has a cell empty, the agent can write `EMPTY`
- if valid patterns disagree, the agent cannot act on that cell yet

### Turn-Based Interaction

The solving loop alternates:
1. row agent takes one move
2. column agent takes one move
3. repeat

Each agent can do only one of the following on its turn:
- write one forced `FILLED` cell
- write one forced `EMPTY` cell
- pass if it has no forced move

If both agents pass consecutively, the solver stops.
It also stops if:
- the puzzle is fully solved
- `max_turns` is reached

If `--max-turns` is not given, `collab.py` sets it to `2 * number_of_cells`.

### Move Selection

When an agent has multiple valid forced moves, `collab.py` can choose among them with:
- `first`
- `random`
- `most_constrained`

The default is `first`.

### Why This Is Useful For Your Research

This solver is deliberately limited:
- it does not use guessing or backtracking
- it does not use a full centralized solver
- each move is attributable to either the row side or the column side

That makes the log useful for studying collaboration, coordination, passing behavior, and how partial information shapes action.

### Individual Baseline: `ind.py`

### What The Agent Sees

- the individual agent sees both row clues and column clues
- it also sees the current full board state

This is the full-information baseline for comparison with the collaborative condition.
The agent is still limited to line-by-line certainty: each move must be justified by one row or one column alone.

### Turn-Based Interaction

The solving loop is simpler:
1. the individual agent takes one move
2. repeat

On each turn, the agent can:
- write one forced `FILLED` cell
- write one forced `EMPTY` cell
- pass if there is no forced move available from any row or column

If the individual agent passes, the solver stops.
It also stops if:
- the puzzle is fully solved
- `max_turns` is reached

### Move Selection

When the individual agent has multiple valid forced moves, `ind.py` can choose among them with:
- `first`
- `random`
- `most_constrained`

The default is `first`.

### Why This Is Useful For Your Research

This baseline keeps the same line-solver logic and log format as `collab.py`, but removes the distributed-information split.

That makes it useful for isolating the effect of collaboration itself:
- if `ind.py` succeeds and `collab.py` stalls, the split information is the bottleneck
- if both stall, the limitation is more likely the bounded line-solver itself

## Why JSON Only

JSON is the better format for this project because the log contains nested data:
- row clues and column clues
- full grid states
- move metadata
- experiment metadata and solver summary

CSV is possible, but it becomes harder to read and less useful once the log includes structured state needed for replay and analysis.

## Batch Notes

- If you omit `--sample-idx`, the default is still sample `0`
- `--all-samples` runs the whole dataset
- `--sample-start` and `--sample-end` enable batch mode over a range
- `--sample-end` is exclusive, so `--sample-start 0 --sample-end 10` runs samples `0` through `9`
- In batch mode, output filenames are generated automatically so logs do not overwrite each other
- In `vis.py`, GIF names are derived from the JSON log filename, so multiple GIFs do not overwrite each other unless you explicitly point them to the same path

## Complexity And Difficulty

This project separates `complexity` from `difficulty`.

### Complexity

`complexity` means structural complexity of the nonogram itself, independent of whether the current solver succeeds.

It is based on factors such as:
- board size
- number of clue blocks
- average clue blocks per line
- variation in clue lengths
- number of trivial lines such as `0` or full-line clues
- filled-cell density
- number of transitions between filled and empty in the target grid

So complexity answers:
- how structurally rich is this puzzle?
- how much internal patterning does it contain?

Current score formula in `analyze_logs.py`:

```text
complexity_score = 100 * (
    0.15 * size_factor
  + 0.30 * nontrivial_line_ratio
  + 0.20 * block_density
  + 0.20 * density_balance
  + 0.15 * transition_norm
)
```

Where:
- `size_factor = num_cells / 225`, clipped to `[0, 1]`
- `nontrivial_line_ratio = 1 - trivial_line_ratio`
- `trivial_line_ratio = (zero_clue_rows + zero_clue_cols + full_rows + full_cols) / total_lines`
- `block_density = avg_blocks_per_line / avg_max_blocks`, clipped to `[0, 1]`
- `density_balance = 1 - abs(filled_ratio - 0.5) / 0.5`
- `transition_norm = avg_transitions_per_line / max(board_rows - 1, board_cols - 1)`, clipped to `[0, 1]`

And the lower-level factors are calculated as:

- `num_cells = board_rows * board_cols`
- `total_lines = board_rows + board_cols`
- `zero_clue_rows = number of row clues equal to []`
- `zero_clue_cols = number of column clues equal to []`
- `full_rows = number of row clues equal to [board_cols]`
- `full_cols = number of column clues equal to [board_rows]`
- `avg_blocks_per_line = mean(number of clue blocks on each row and column line)`
- `avg_max_blocks = weighted average of the theoretical maximum clue blocks per line`

```text
max_row_blocks = ceil(board_cols / 2)
max_col_blocks = ceil(board_rows / 2)
avg_max_blocks =
    (max_row_blocks * board_rows + max_col_blocks * board_cols)
    / total_lines
```

- `filled_cells = total number of filled cells in target_grid`
- `filled_ratio = filled_cells / num_cells`
- `avg_transitions_per_line = mean(number of value changes between adjacent cells)`

For transitions:
- compute this for every row in `target_grid`
- compute this for every column in `target_grid`
- for a line like `[1,1,0,0,1]`, the transition count is `2`
- then average across all rows and columns

Interpretation:
- larger puzzles increase complexity
- fewer trivial lines increase complexity
- more segmented clue structure increases complexity
- balanced black/white density increases complexity
- more changes between filled and empty regions increase complexity

### Difficulty

`difficulty` means how hard the puzzle is for the current turn-based two-agent solver under your research condition.

It is based on factors such as:
- whether the puzzle is solved at all
- how many unknown cells remain
- how many pass events occur
- how early the first pass happens
- how many forced moves are available before the first pass
- how much of the turn budget is consumed

So difficulty answers:
- how hard is this puzzle for this specific solver setup?
- does the collaboration stall early, stall late, or solve smoothly?

Current score formula in `analyze_logs.py`:

```text
difficulty_score = 100 * (
    0.45 * unknown_ratio
  + 0.25 * pass_density
  + 0.20 * first_pass_penalty
  + 0.10 * turn_pressure
)
```

If the solver does not solve the puzzle, an extra penalty is added:

```text
difficulty_score += 25 + 25 * unknown_ratio
```

The final score is clipped to `[0, 100]`.

Where:
- `unknown_ratio = unknown_cells / num_cells`
- `pass_density = pass_events / num_cells`
- `first_pass_penalty = 1 - (writes_before_first_pass / num_cells)`
- `turn_pressure = action_turns / max_turns`

And the lower-level factors are calculated as:

- `unknown_cells = number of cells still equal to UNKNOWN in final_grid`
- `action_turns = number of events whose action is write or pass`
- `write_events = number of events whose action is write`
- `pass_events = number of events whose action is pass`
- `writes_before_first_pass = number of write events before the first pass event`
- if no pass occurs:
  - `first_pass_turn = -1`
  - `first_pass_penalty = 0`
- if a pass does occur:
  - find the first event whose `action == "pass"`
  - count how many write events happened before it
  - use:

```text
first_pass_penalty = 1 - (writes_before_first_pass / num_cells)
```

This means:
- if the solver can make many forced moves before the first pass, difficulty is lower
- if the solver passes very early, difficulty is higher

- `turn_pressure = action_turns / max_turns`
  This measures how much of the available turn budget was used.

- `row_writes = number of write events by the row agent`
- `col_writes = number of write events by the column agent`
- `row_passes = number of pass events by the row agent`
- `col_passes = number of pass events by the column agent`

These are included in the CSV as descriptive factors, even though they are not all directly used in the final difficulty score.

Interpretation:
- more unsolved cells means harder
- more passing means harder
- earlier passing means harder
- using more of the turn budget means harder
- failing to solve adds a large penalty

### Why They Are Different

A puzzle can be:
- structurally complex but still easy for this solver
- structurally simple but difficult under partial-information collaboration

This distinction is useful for your research because your question is not only whether a puzzle is mathematically hard, but whether it is hard under a restricted collaborative condition.

### Labels

`complexity_score` is mapped to:
- `very_low` if `< 20`
- `low` if `< 40`
- `medium` if `< 60`
- `high` if `< 80`
- `very_high` otherwise

`difficulty_score` is mapped to:
- if unsolved and `unknown_ratio >= 0.40`: `stalled_hard`
- if unsolved and `unknown_ratio >= 0.15`: `stalled_moderate`
- if unsolved: `stalled_near_complete`
- if solved and score `< 10`: `trivial`
- if solved and score `< 25`: `easy`
- if solved and score `< 45`: `moderate`
- if solved and score `< 65`: `challenging`
- otherwise: `hard`

These are heuristic scores, not absolute ground-truth measures.

### Worked Example: `x_test_dataset__sample-00000`

This example uses:
- log file: `logs/x_test_dataset__row-first__col-first/x_test_dataset__sample-00000.json`
- row clues:

```text
[[10], [10], [10], [3, 2, 3], [3, 2, 3], [4, 2], [2, 4, 2], [3, 3], [10], [10]]
```

- column clues:

```text
[[10], [10], [6, 3], [3, 2, 2], [5, 1, 2], [5, 1, 2], [3, 1, 2], [5, 3], [10], [10]]
```

- solver outcome:
  - solved = `True`
  - unknown cells = `0`
  - write events = `100`
  - pass events = `0`

#### Structural Indices

- `board_rows = 10`
- `board_cols = 10`
- `num_cells = 10 * 10 = 100`
- `total_lines = 10 + 10 = 20`

- `total_blocks = 38`
  Count the clue blocks in every row and column:
  - row block counts = `[1,1,1,3,3,2,3,2,1,1]`, sum = `18`
  - col block counts = `[1,1,2,3,3,3,3,2,1,1]`, sum = `20`
  - total = `18 + 20 = 38`

- `avg_blocks_per_line = total_blocks / total_lines = 38 / 20 = 1.9`

- `max_blocks_on_line = 3`
  The largest number of clue blocks on any single row or column is `3`.

- `block_count_std = 0.8888`
  This is the population standard deviation of the 20 line block counts above.

- `avg_block_length = 4.5263`
  Collect all clue numbers from rows and columns and average them.
  Since row clues and column clues both describe the same image from different directions, this averages over both directions.

- `block_length_std = 3.2342`
  This is the population standard deviation of all clue numbers.

- `zero_clue_rows = 0`
  No row clue is `[]`.

- `zero_clue_cols = 0`
  No column clue is `[]`.

- `full_rows = 5`
  Five row clues are `[10]`.

- `full_cols = 4`
  Four column clues are `[10]`.

- `trivial_line_ratio = (0 + 0 + 5 + 4) / 20 = 0.45`

- `avg_max_blocks = 5`
  For a `10x10` puzzle:
  - `max_row_blocks = ceil(10 / 2) = 5`
  - `max_col_blocks = ceil(10 / 2) = 5`
  - so the weighted average is also `5`

- `filled_cells = 86`
  Count the filled cells in the target grid.

- `filled_ratio = 86 / 100 = 0.86`

- `density_balance = 1 - abs(0.86 - 0.5) / 0.5 = 0.28`

- `avg_transitions_per_line = 1.8`
  For each row and each column in the target grid:
  - count adjacent changes between `1` and `0`
  - average those 20 transition counts

#### Complexity Score

First compute the normalized factors:

- `size_factor = 100 / 225 = 0.4444`
- `nontrivial_line_ratio = 1 - 0.45 = 0.55`
- `block_density = 1.9 / 5 = 0.38`
- `density_balance = 0.28`
- `transition_norm = 1.8 / 9 = 0.2`

Then:

```text
complexity_score = 100 * (
    0.15 * 0.4444
  + 0.30 * 0.55
  + 0.20 * 0.38
  + 0.20 * 0.28
  + 0.15 * 0.2
)
```

This gives:

```text
complexity_score = 39.37
complexity_label = low
```

The score is relatively low because this puzzle contains many full-line clues like `[10]`, which makes it structurally more trivial.

#### Run-Dependent Indices

- `action_turns = 100`
  Count only `write` and `pass` events.
  For this sample:
  - `write_events = 100`
  - `pass_events = 0`
  - so `action_turns = 100`

- `row_writes = 50`
- `col_writes = 50`
- `row_passes = 0`
- `col_passes = 0`

- `fill_writes = 86`
  Number of write events where `move.value_name == FILLED`

- `empty_writes = 14`
  Number of write events where `move.value_name == EMPTY`

- `write_fill_ratio = 86 / 100 = 0.86`
- `write_empty_ratio = 14 / 100 = 0.14`

- `row_col_write_imbalance = abs(50 - 50) / 100 = 0`

- `unknown_cells = 0`
  Count cells still equal to `UNKNOWN` in `final_grid`.

- `unknown_ratio = 0 / 100 = 0`

- `first_pass_turn = -1`
  There is no pass event in this run.

- `writes_before_first_pass = 100`
  Because no pass ever occurs, the script sets this to all write events.

- `initial_forced_ratio = 100 / 100 = 1`

- `first_pass_penalty = 0`
  Since there is no pass, the script treats this as no early-stall penalty.

- `pass_density = 0 / 100 = 0`

- `pass_ratio = 0 / 100 = 0`

- `max_turns = 200`
  For a `10x10` puzzle, the default is `2 * 100 = 200`.

- `turn_pressure = 100 / 200 = 0.5`

#### Difficulty Score

Now plug the run-dependent values into the formula:

```text
difficulty_score = 100 * (
    0.45 * 0
  + 0.25 * 0
  + 0.20 * 0
  + 0.10 * 0.5
)
```

This gives:

```text
difficulty_score = 5.0
difficulty_label = trivial
overall_label = trivial
```

This sample is labeled `trivial` because:
- it is fully solved
- it never passes
- all cells are determined
- many lines are structurally trivial from the beginning

## Log Analysis

`analyze_logs.py` reads a folder of JSON log files and exports one CSV row per nonogram.

The CSV includes:
- puzzle id
- puzzle size
- clue-based structural features
- solver-run features
- `complexity_score`
- `complexity_label`
- `difficulty_score`
- `difficulty_label`
- `overall_label`

The final `overall_label` is intended as a convenient summary column for filtering.

### Run Log Analysis

```bash
.venv/bin/python analyze_logs.py \
  --log-dir logs/x_test_dataset__row-first__col-first \
  --output-csv nonogram_log_analysis.csv
```

The CSV now records solver-specific run metadata for both conditions, including:
- `solver` such as `collab` or `ind`
- `agent_mode` such as `collaborative` or `individual`
- per-agent event counts including `row_writes`, `col_writes`, `ind_writes`, `row_passes`, `col_passes`, and `ind_passes`

### Compare `collab` And `ind`

```bash
.venv/bin/python compare_runs.py \
  --analysis-csv nonogram_log_analysis.csv \
  --summary-csv /tmp/nonogram_compare_summary.csv \
  --size-summary-csv /tmp/nonogram_compare_by_size.csv \
  --plot-path /tmp/nonogram_compare.png
```

This script prints:
- an overall solver summary
- a solver-by-board-size summary
- a paired comparison for samples that have both `collab` and `ind` runs

It can also save summary CSVs and a simple comparison plot.

### Latent-Choice Simulation

Simulate stochastic row/column agents with different candidate-set definitions:

```bash
.venv/bin/python latent_collab.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-idx 54 \
  --utility-model individual \
  --choice-set threshold \
  --tau 0.75 \
  --beta 5 \
  --seed 0 \
  --json-path /tmp/latent_threshold_ind.json \
  --quiet
```

Important options:
- `--choice-set certainty1`
- `--choice-set threshold --tau 0.75`
- `--choice-set all_legal`
- `--utility-model individual`
- `--utility-model collaborative --lambda-weight 1.0`

The JSON output keeps the normal event log and also adds:
- `candidate_steps`
- per-turn decision metadata such as `Q_own`, `B_partner_local`, utility, and chosen probability

### Latent Sweep

Run a compact simulation sweep and save a CSV summary:

```bash
.venv/bin/python sweep_latent.py \
  --x-path NonoDataset-main/10x10/x_test_dataset.npz \
  --y-path NonoDataset-main/10x10/y_test_dataset.npz \
  --sample-idx 54 \
  --utility-model individual \
  --utility-model collaborative \
  --choice-set certainty1 \
  --choice-set threshold \
  --beta 5 \
  --tau 0.75 \
  --seed 0 \
  --output-csv /tmp/latent_sweep54.csv \
  --quiet
```

This summary CSV records per-run quantities such as:
- `unknown_cells`
- `matches_target`
- `write_events`
- `pass_events`
- `mean_candidate_count`
- `mean_chosen_q_own`
- `mean_chosen_b_partner_local`

### Example Use

Typical workflow:
1. run `collab.py` or `ind.py` on many samples to generate JSON logs
2. run `analyze_logs.py` on the log folder
3. run `compare_runs.py` on the analysis CSV if you want direct baseline-vs-collaboration summaries
4. inspect the CSVs or plots and filter puzzles based on `complexity`, `difficulty`, or solver differences
