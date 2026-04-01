# Information-Theoretic Notes On Nonogram Complexity And Difficulty

This note summarizes possible ways to define `complexity` and `difficulty` for nonograms from an information-theoretic perspective, with explicit links to the theories that motivate each idea.

## 1. Core Distinction

The first distinction is:

- `complexity` = how much structured information the puzzle contains
- `difficulty` = how hard it is for a bounded solver or collaborating pair of solvers to extract and use that information

This distinction is inspired by the difference between:
- `information content` in Shannon information theory
- `computational cost` and `bounded rationality` in algorithmic and cognitive settings

Relevant inspirations:
- Claude Shannon, 1948: entropy as uncertainty / information content
- Andrey Kolmogorov, Gregory Chaitin, Ray Solomonoff: algorithmic complexity / description length
- Herbert Simon: bounded rationality, where agents may have access to information but still face difficulty in using it efficiently

## 2. Complexity As Information Content

### 2.1 Description Length Of The Clues

One way to define puzzle complexity is by the number of bits needed to describe the clue set.

For a nonogram with row clues `R` and column clues `C`, complexity can be approximated by:
- number of clue blocks
- variability of clue lengths
- number of trivial clues like `0` or full-line clues
- redundancy across rows and columns

Theoretical inspiration:
- Shannon source coding theorem: more probable / more redundant descriptions require fewer bits on average
- Minimum Description Length (MDL), mainly associated with Jorma Rissanen: more regular structures have shorter encodings

Interpretation:
- a puzzle with many `0` or full-line clues has low description length and low structural complexity
- a puzzle with many irregular, heterogeneous clue patterns has higher description length and higher complexity

### 2.2 Description Length Of The Solution

Another way to define complexity is through the hidden solution grid `S`.

If `S` is highly regular, it can be compressed easily.
If `S` is irregular, it will be harder to compress.

Possible practical approximation:
- compress the solution bitmap with a standard compressor
- use compressed size as a proxy for complexity

Theoretical inspiration:
- Kolmogorov complexity: the complexity of an object is the length of the shortest program that generates it
- In practice, Kolmogorov complexity is uncomputable, so compression is often used as an approximation

Interpretation:
- highly symmetric or repetitive solutions have lower structural complexity
- irregular solutions have higher structural complexity

### 2.3 Entropy Of Local Patterns

Complexity can also be approximated by entropy over local structure:
- row clue types
- column clue types
- run-length distributions
- boundary-transition distributions

Theoretical inspiration:
- Shannon entropy over discrete distributions
- Entropy rate ideas from information theory and stochastic processes

Interpretation:
- if many rows and columns look similar, the clue distribution is low-entropy
- if clue structures are highly varied, the distribution is higher-entropy

## 3. Difficulty As Uncertainty Reduction

Difficulty is better understood as the process of reducing uncertainty from an incomplete state of knowledge.

The solver starts uncertain and gradually narrows the set of possible solutions.

### 3.1 Feasible-Set Entropy

Let `F_t` be the set of all complete grids still consistent with the clues and the board state at time `t`.

Define:

```text
H_t = log2 |F_t|
```

This measures how many bits are still required to specify the true solution among the remaining feasible solutions.

Theoretical inspiration:
- Shannon entropy
- Hartley entropy (`log |F|`) for a finite set of equally possible states

Interpretation:
- large `H_0` means many possible solutions are initially feasible
- a rapid drop in `H_t` means the puzzle becomes easy quickly
- a slow drop suggests higher difficulty

Limitation:
- exactly counting `|F_t|` is computationally expensive

### 3.2 Cell-Wise Entropy

A more practical approximation is to compute uncertainty cell by cell.

For each cell `X_i`, define:

```text
p_t(i) = P(X_i = filled | current constraints)
h_t(i) = -p_t(i) log2 p_t(i) - (1-p_t(i)) log2 (1-p_t(i))
```

Then define total uncertainty as:

```text
H_cells(t) = sum_i h_t(i)
```

Theoretical inspiration:
- Shannon entropy for binary random variables
- Belief-state uncertainty in probabilistic inference

Interpretation:
- `h_t(i) = 0` means the cell is fully determined
- `h_t(i) = 1` bit means maximum uncertainty for a binary cell
- a difficult puzzle is one where cell entropy remains high for a long time

## 4. Distributed Information In The Two-Agent Setting

Your research is not about a central omniscient solver.
It is about two agents with partial information:

- one sees row clues
- one sees column clues
- both interact through a shared board

This makes the distributed location of information important.

### 4.1 Unilateral Information Vs Joint Information

For a cell `X`, one can ask:

- how much information does the row-side clue set provide?
- how much information does the column-side clue set provide?
- how much information only appears when both are combined?

Theoretical inspiration:
- Mutual information in Shannon information theory

Possible quantities:

```text
I(X; R)
I(X; C)
I(X; R, C)
```

Where:
- `R` = row-side information
- `C` = column-side information

Interpretation:
- if `I(X; R)` is high, row-side reasoning is already informative
- if `I(X; C)` is high, column-side reasoning is informative
- if useful information emerges mainly in `I(X; R, C)` but not from either side alone, then solving depends on combining information across agents

This is very relevant for collaborative difficulty.

### 4.2 Synergistic Information

Some information may only appear when row and column constraints are combined, not from either source separately.

Theoretical inspiration:
- synergy / redundancy decomposition ideas from multivariate information theory
- especially Partial Information Decomposition (PID), associated with Williams and Beer (2010)

Interpretation:
- a puzzle with high synergistic information is not just hard in general
- it is specifically hard under a partial-information collaborative condition

This may be one of the most important quantities for your research.

## 5. Communication Complexity

Another perspective is:

- how much communication is needed between two agents to solve the puzzle?

This does not have to mean explicit text messages only.
It can include:
- actions on the shared board
- annotations
- signals about confidence or uncertainty

Theoretical inspiration:
- communication complexity, especially the framework introduced by Andrew Yao (1979)
- distributed problem solving and distributed cognition traditions

Interpretation:
- two puzzles may have similar structural complexity
- but one may require much more information exchange between agents
- that puzzle would have higher collaborative difficulty

This is especially promising for human-human and human-AI comparisons.

## 6. Why Final-Solution Entropy Alone Is Not Enough

For a uniquely solvable puzzle:

```text
H(S | R, C) = 0
```

That means once the full puzzle specification is known, the solution is fully determined.

Theoretical inspiration:
- conditional entropy in Shannon information theory

But this does not mean the puzzle is easy.
It only means the solution exists uniquely.

Difficulty is not about whether the answer is determined in principle.
It is about:
- how much uncertainty remains during solving
- how much computation is needed to reduce it
- how much coordination is needed to access and combine distributed information

So final conditional entropy is not enough as a difficulty measure.

## 7. Practical Information-Theoretic Decomposition

For this research, a useful practical decomposition would be:

### 7.1 Structural Complexity

This should be solver-independent.

Possible approximations:
- clue description length
- solution compression complexity
- entropy of clue patterns
- entropy or variability of run lengths
- transition entropy in the target grid

Main inspirations:
- Shannon entropy
- MDL
- Kolmogorov-complexity approximations via compression

### 7.2 Collaborative Difficulty

This should be solver- and setting-dependent.

Possible approximations:
- entropy reduction per turn
- number of cells determined unilaterally by row-only reasoning
- number of cells determined unilaterally by column-only reasoning
- number of cells determined only after cross-agent interaction
- number of passes before progress resumes
- communication or annotation cost if communication is added experimentally

Main inspirations:
- Shannon entropy and mutual information
- partial information decomposition / synergy
- communication complexity
- bounded rationality

## 8. Three Especially Promising Measures For This Project

### 8.1 Initial Trivial Information

Definition:
- fraction of cells determined immediately by one-sided overlap reasoning at time `t = 0`

Theoretical motivation:
- low initial cell entropy
- high unilateral information from one side’s clue structure

Interpretation:
- if this value is high, the puzzle starts easy and may be too trivial for the research

### 8.2 Synergistic Information

Definition:
- fraction of useful deductions that cannot be made by row-only or column-only reasoning alone, but emerge after interaction through the shared board

Theoretical motivation:
- mutual information and multivariate synergy / PID

Interpretation:
- if this value is high, the puzzle is especially suitable for studying collaboration

### 8.3 Entropy Reduction Trajectory

Definition:
- how fast uncertainty falls across turns

Possible approximation:
- track total cell-wise entropy or number of feasible line patterns across the run

Theoretical motivation:
- Shannon entropy over time
- information gain per step

Interpretation:
- easy puzzles show steep early entropy reduction
- difficult puzzles show slow reduction, plateaus, or repeated passes

## 9. Suggested Research Position

From an information-theoretic perspective, the strongest framing may be:

- `complexity` = information content and structural irregularity of the puzzle
- `difficulty` = cost of uncertainty reduction and information integration under bounded, distributed solving

That framing is better than a single undifferentiated “difficulty” measure because it separates:
- what is in the puzzle
- from what the agents can extract under your collaborative condition

## 10. Practical Implication For The Current Codebase

Your current `analyze_logs.py` already approximates:
- structural complexity from clue statistics and target-grid structure
- empirical difficulty from solver outcomes such as passes, unknown cells, and turn usage

A stronger future information-theoretic extension would be to add:
- cell-wise entropy estimates from feasible line patterns
- per-turn information gain
- unilateral vs joint information estimates
- communication-complexity proxies once messaging or annotation is introduced

## 11. Worked Example: `x_test_dataset__sample-00000`

This section shows how the ideas above can be instantiated on one concrete puzzle.

The example puzzle has:

- board size: `10 x 10`
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
  - unknown cells remaining = `0`
  - pass events = `0`
  - write events = `100`

This sample is useful because it is a clear example of:
- low collaborative difficulty
- high unilateral information
- strong clue redundancy

### 11.1 Description-Length Style View Of The Clues

Theory inspiration:
- Shannon source coding
- Minimum Description Length (Rissanen)

A simple fixed-width encoding proxy for a `10x10` puzzle is:

- each clue number lies in `{0,1,...,10}`
- so one clue value can be stored in `ceil(log2(11)) = 4` bits

This puzzle has:
- `38` clue numbers in total

So a very naive clue-value description length proxy is:

```text
L_clue_values = 38 * 4 = 152 bits
```

This is not a canonical coding scheme.
It is only a simple proxy.

The more important observation is structural redundancy:
- row clue `[10]` appears `5` times
- row clue `[3, 2, 3]` appears `2` times
- column clue `[10]` appears `4` times
- column clue `[5, 1, 2]` appears `2` times

So the clue set is quite compressible, which suggests lower structural complexity.

### 11.2 Entropy Of Clue Patterns

Theory inspiration:
- Shannon entropy over discrete distributions

For row clue patterns, frequencies are:

- `[10]`: `5/10 = 0.5`
- `[3, 2, 3]`: `2/10 = 0.2`
- `[4, 2]`: `1/10 = 0.1`
- `[2, 4, 2]`: `1/10 = 0.1`
- `[3, 3]`: `1/10 = 0.1`

So the row-pattern entropy is:

```text
H_rows =
  -(0.5 log2 0.5
   +0.2 log2 0.2
   +0.1 log2 0.1
   +0.1 log2 0.1
   +0.1 log2 0.1)
  ≈ 1.96 bits
```

For column clue patterns, frequencies are:

- `[10]`: `4/10 = 0.4`
- `[5, 1, 2]`: `2/10 = 0.2`
- `[6, 3]`: `1/10 = 0.1`
- `[3, 2, 2]`: `1/10 = 0.1`
- `[3, 1, 2]`: `1/10 = 0.1`
- `[5, 3]`: `1/10 = 0.1`

So the column-pattern entropy is:

```text
H_cols ≈ 2.32 bits
```

Interpretation:
- these entropies are not extremely low, but they are clearly reduced by repeated clue patterns
- this supports the view that the puzzle is structurally somewhat regular rather than highly irregular

### 11.3 Solution Compression / Structural Regularity

Theory inspiration:
- Kolmogorov complexity approximated by compression

This puzzle has:
- `filled_cells = 86`
- `filled_ratio = 0.86`
- `avg_transitions_per_line = 1.8`

Interpretation:
- the image is very dense
- there are relatively few black/white changes per line
- many rows and columns are nearly solid blocks

Even without actually running a compressor, this suggests the solution bitmap is fairly compressible.
So under a compression-style proxy, this puzzle is not highly complex.

### 11.4 Feasible-Set Entropy Intuition

Theory inspiration:
- Hartley entropy `H = log2 |F|`
- Shannon entropy over feasible hypothesis sets

We do not exactly compute `|F_0|` here, but we can see it is small relative to many other puzzles because many lines are uniquely determined by clue length alone.

For a line of length `10`, if:

```text
sum(clues) + (number_of_blocks - 1) = 10
```

then the line has exactly one legal arrangement.

In this sample, exact-fit row clues are:
- `[10]` five times
- `[3, 2, 3]` two times because `3 + 2 + 3 + 2 separators = 10`
- `[2, 4, 2]` one time because `2 + 4 + 2 + 2 separators = 10`

So:
- `8` of the `10` rows are uniquely determined from row clues alone

Exact-fit column clues are:
- `[10]` four times
- `[6, 3]` one time because `6 + 3 + 1 separator = 10`
- `[5, 1, 2]` two times because `5 + 1 + 2 + 2 separators = 10`

So:
- `7` of the `10` columns are uniquely determined from column clues alone

Interpretation:
- the feasible set `F_0` should already be much smaller than for a puzzle where no lines are exact-fit
- this is one reason the puzzle is easy

### 11.5 Cell-Wise Entropy Intuition

Theory inspiration:
- Shannon entropy for binary variables

For a cell in row `0`, the row clue is `[10]`.
So row-side reasoning alone implies:

```text
P(X_i = filled | row clue [10]) = 1
```

Therefore:

```text
h(i) = -1 log2 1 - 0 log2 0 = 0
```

So every cell in row `0` has zero row-side entropy.

The same is true for:
- rows `1`, `2`, `8`, `9`
- rows `3`, `4`, `6` because they are exact-fit clue patterns

This means a very large fraction of the board starts with zero uncertainty from one side alone.

Interpretation:
- initial cell-wise entropy is already low
- the puzzle should be easy for a line-based solver

### 11.6 Unilateral Information Vs Joint Information

Theory inspiration:
- mutual information

This sample has very high unilateral information.

Row-side unilateral information is high because:
- `8` out of `10` rows are exact-fit

Column-side unilateral information is also high because:
- `7` out of `10` columns are exact-fit

A simple unilateral-information proxy is:

```text
row_exact_fit_ratio = 8 / 10 = 0.8
col_exact_fit_ratio = 7 / 10 = 0.7
```

Interpretation:
- much of the board can be inferred from one side alone
- therefore the joint gain from combining row and column information is relatively small
- in mutual-information language, `I(X; R)` and `I(X; C)` are already large for many cells

### 11.7 Synergistic Information

Theory inspiration:
- partial information decomposition / synergy

A rough collaboration-oriented proxy is:
- how many deductions require row and column interaction rather than one-sided certainty?

For this sample, synergy should be low because:
- many rows are fully determined on their own
- many columns are fully determined on their own
- the solver never stalls

So this puzzle is probably not ideal for studying rich collaborative coordination.

### 11.8 Communication Complexity Proxy

Theory inspiration:
- communication complexity (Yao)

In the current setup, a practical proxy is:
- number of passes
- number of stalled regions
- whether progress requires many alternating updates

For this sample:
- `pass_events = 0`
- `row_writes = 50`
- `col_writes = 50`
- `unknown_cells = 0`

Interpretation:
- no explicit rescue communication would be needed
- the board alone is sufficient for smooth progress
- communication complexity is therefore low under a board-mediated proxy

### 11.9 Entropy Reduction Trajectory

Theory inspiration:
- Shannon entropy over time
- information gain per step

The exact entropy trajectory is not computed in the current codebase.
But a simple uncertainty proxy is the number of unresolved cells.

For this sample:
- initial unresolved cells = `100`
- final unresolved cells = `0`
- pass events = `0`

Interpretation:
- uncertainty decreases monotonically
- there is no plateau where the agents get stuck
- this is the trajectory of an easy puzzle, not a hard collaborative one

### 11.10 What This Example Suggests

For `x_test_dataset__sample-00000`:

- description-length proxy suggests relatively low complexity because of repeated clue patterns
- entropy-of-patterns proxy suggests moderate regularity
- compression-style reasoning suggests a fairly compressible solution
- feasible-set and cell-entropy reasoning suggest high initial determinacy
- unilateral information is high
- synergistic information is likely low
- communication complexity proxy is low

So from an information-theoretic perspective, this sample is a good example of:
- low collaborative difficulty
- relatively low useful synergy
- a puzzle that may be too easy for studying rich interaction
