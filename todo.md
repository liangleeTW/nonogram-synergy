# Nonogram Research Roadmap

This document organizes the project plan for studying nonogram difficulty, bounded ind behavior, and dyad dyadoration/complementarity.

The goal is not only to solve nonograms. The goal is to build a controlled simulation framework where we can:

- generate or select puzzles with measurable structure,
- test which puzzle features predict difficulty,
- compare ind and dyad agents under controlled budgets,
- evaluate whether a proposed cognitive value model explains behavior better than simpler alternatives.

## 1. Research Questions

### Puzzle Difficulty

Which structural properties of a nonogram predict difficulty?

Candidate predictors:

- line ambiguity / `AS`
- row-column symmetry or asymmetry
- across-row and across-column ambiguity variance
- constraint interaction between row and column clues
- visual/compressibility properties

Difficulty should be measured across multiple solvers. It is not a fixed puzzle property independent of the agent.

### Individual Decision Model

The advisor model is:

```text
V(x) = Q(x) + beta_info * I(x) - lambda_cost * C(x)
```

Where:

- `x` is a candidate action.
- `Q(x)` is subjective correctness.
- `I(x)` is information value, initially approximated by entropy or information gain.
- `C(x)` is cognitive/action cost.
- `beta_info` controls information seeking.
- `lambda_cost` controls cost sensitivity.

Policies:

- determin: choose `argmax_x V(x)`
- stochastic: choose by softmax, `P(x) proportional to exp(V(x) / tau_decision)`
- `tau_decision` controls stochasticity/noise

Cost decision:

- Do not make `C(x)` a large hand-built bundle of many possible factors.
- First implementation should use one preregistered cost proxy.
- Recommended first proxy:

```text
C_ambiguity(x) = log |S_row(i)| + log |S_col(j)|
```

where `S_row(i)` and `S_col(j)` are remaining line configurations compatible with the current board.

Alternative cost ideas, such as belief-distance cost or rate-distortion-inspired policy cost, should be separate model variants.

### Collaboration Theory

Group wisdom is the starting frame.

The dyad should be compared against partial-information solo baselines, not only against a full-information agent.

Core comparison:

```text
dyad_benefit = dyad_performance - max(row_only_performance, col_only_performance)
dyad_gap_to_full = full_information_performance - dyad_performance
```

Important distinction:

- `board_update_only`: partner actions only update the shared board.
- `partner_information`: partner actions are valued because they may reduce partner uncertainty.
- `communication_model`: partner actions are interpreted as communicative evidence. Future only.

Do not claim communication before a communication model exists.

## 2. Current Code Baseline

Already implemented:

- `src/solver_common.py`
  - dataset loading from downloaded `.npz` files
  - padded clue decoding
  - `generate_line_patterns(length, clues, current_line)`
  - forced-cell extraction
  - basic JSON log payloads
- `src/ind.py`
  - determin full-information ind line solver
  - supports complete/budgeted behavior via `max_turns`
- `src/determin_dyad.py`
  - determin row/column dyad line solver
  - strict alternating turns
  - row agent sees row clues; column agent sees column clues
- `src/stoch_ind.py`
  - stochastic full-information ind stoch-choice solver
  - candidate tables and softmax choice
- `src/stoch_dyad.py`
  - stochastic row/column stoch-choice solver
  - local partner-information term
  - `lambda_partner` for partner-information gain
  - candidate tables with `q_own`, partner counts, utility, probability, fallback flags
- `scripts/analyze_logs.py`
  - determin-style complexity/difficulty CSV summaries
- `scripts/sweep_stoch.py`
  - sweeps over `utility_model`, `choice_set`, threshold `tau`, `beta`, `lambda_partner`, and seeds

## 3. Conflicts And Naming Decisions

### Completion vs Correctness

- `complete`: no unknown cells remain.
- `success`: final board equals the true solution.
- `consistent_with_clues`: current board is still compatible with all row and column clues.
- `contradiction_detected`: at least one row or column has no valid completion under the current board.
- `failure_reason`: one of `none`, `step_limit`, `no_valid_action`, `contradiction`, or `complete_wrong`.

### Tau and beta

- `tau` means threshold for the stoch `threshold` choice set. Change to: `tau` means softmax stochasticity/temperature.
- rename current threshold `tau` to `q_threshold`,
- use `tau_decision` for softmax temperature,
- current code use `beta` as inverse temperature, change to `beta_softmax`
- beta in V(x) = Q(x) + beta * I(x) - lambda_cost * C(x) should be `beta_info`

### Lambda

- `lambda_partner` means partner-information weight in `src/stoch_dyad.py`.
- use `lambda_partner` or existing `lambda_partner` for dyadoration,(choose one and report to me what you chose)
- use `lambda_cost` for cost sensitivity.

### Clue Representation

Current code:

- clues are `List[int]`,
- empty clues are `[]`.

Planned puzzle layer:

- clues should be `tuple[int, ...]`,
- empty clues should be `()`,
- convert at boundaries so existing solvers are not broken.
- Reason: lists are mutable and cannot be used as cache keys; tuples are immutable and can be used for cached line enumeration.

Example fix:

```python
# current solver/data style
row_clues = [[3], [1, 1], []]

# normalized puzzle/metric/cache style
row_clues = ((3,), (1, 1), ())
cache_key = (line_length, row_clues[row_idx])
```

Implementation note:

- `src/puzzle.py` should normalize clue inputs to tuples.
- Existing solvers can still receive list clues by converting `tuple` back to `list` at the boundary when needed.

### Existing Line Enumeration

Current code already has:

```text
generate_line_patterns(length, clues, current_line)
```

Missing:

```text
enumerate_valid_lines(length, clue)
```

Decision:

- implement `enumerate_valid_lines` as a cached wrapper around `generate_line_patterns` with an all-unknown line.

### Latent Fallback

Current stoch solvers never pass if fallback candidates exist.

Fallback chain:

```text
certainty/threshold -> all_legal_fallback -> uninformed_fallback
```

Decision:

- make fallback configurable:

```text
fallback = none | all_legal | uninformed
```

- if fallback is disabled and no action exists, record `failure_reason = "no_valid_action"`.

## 4. Model Branch Map

These branches should stay explicit even when some are not priority.

### Information Access

| Branch | Meaning | Status |
| --- | --- | --- |
| `full_information_ind` | one agent sees row and column clues | exists: `src/ind.py`, `src/stoch_ind.py` |
| `row_only_ind` | one agent sees only row clues | missing |
| `col_only_ind` | one agent sees only column clues | missing |
| `dyad_row_col` | row agent sees row clues, column agent sees column clues, shared board | exists: `src/determin_dyad.py`, `src/stoch_dyad.py` |

### Task Horizon

| Branch | Meaning | Use |
| --- | --- | --- |
| `complete` | run until success, complete wrong board, no valid action, contradiction, or max iterations | objective solvability and steps-to-solve |
| `finite` | fixed step budget | human-like bounded behavior; final accuracy and information gain matter |

### Action Requirement

| Branch | Meaning | Use |
| --- | --- | --- |
| `action_mode = "forced"` | active agent must choose a cell action each trial if any unknown cells remain | finite-step behavioral simulations; makes determin and stochastic policies comparable |
| `action_mode = "pass_if_no_valid"` | agent passes only when no valid/acceptable cell action exists | logical-completion/difficulty analysis |
| `action_mode = "pass_as_action"` | pass is included as an explicit candidate action | experiments where inaction competes with cell actions |

Open preference:

- We currently lean toward forcing agents to choose in each finite-step trial.
- Use one `action_mode` enum rather than multiple booleans, so illegal combinations cannot occur.

### Policy Type

| Branch | Meaning | Use |
| --- | --- | --- |
| `determin` | choose `argmax V(x)` or logical first/most-constrained move | idealized baseline |
| `stochastic` | choose by softmax | bounded/noisy human-like behavior and likelihood comparison |

### Decision Value Model

| Branch | Formula | Status |
| --- | --- | --- |
| `random` | random legal action | missing as shared baseline |
| `correctness_only` | `V = Q` | partially present through stoch `q_own` |
| `correctness_info` | `V = Q + beta_info * I` | missing |
| `correctness_cost_ambiguity` | `V = Q - lambda_cost * C_ambiguity` | missing |
| `full_value_cost_ambiguity` | `V = Q + beta_info * I - lambda_cost * C_ambiguity` | missing |
| `dyad_board_update_only` | dyadoration only through shared board updates | determin version exists; value-model version missing |
| `dyad_partner_info` | adds partner-information value | partially exists in `src/stoch_dyad.py` |

### Collaboration Interpretation

| Branch | Meaning | Priority |
| --- | --- | --- |
| `board_update_only` | partner actions only change the shared board | high |
| `partner_information` | active agent chooses actions that may be useful for the partner by reducing partner uncertainty | medium/high |
| `communication_model` | actions are interpreted as evidence about hidden information | future |

## 5. Big Topics And Expected Outputs

### Topic A: Build A Controlled Nonogram Dataset

Purpose:

- Generate or select puzzles whose structural properties are measurable and controllable.
- Avoid relying only on downloaded datasets whose difficulty distribution is unknown.
- Create puzzle sets where ambiguity, row/column symmetry, and constraint interaction can be varied deliberately.

Related phases:

- Phase 1: Puzzle representation.
- Phase 2: Puzzle metrics and generation.

Expected output:

- a puzzle dataset/table with solution, clues, uniqueness, ambiguity, asymmetry, interaction, and visual metrics.

### Topic B: Test Nonogram Difficulty

Purpose:

- Test which puzzle features predict difficulty.
- Compare difficulty across different solvers.
- Use simple complexity metrics as baseline predictors.

Related phases:

- Phase 2: Puzzle metrics.
- Phase 3: Outcome metrics.
- Phase 6: Experiments.
- Phase 7: Analysis.

Expected output:

- plots/tables such as:
  - line ambiguity vs steps to solve,
  - ambiguity variance vs final accuracy,
  - row-column asymmetry vs dyad benefit,
  - constraint interaction vs dyad benefit.

### Topic C: Run Simulations

Purpose:

- Compare ind and dyad agents on the same puzzles under the same budgets.
- Separate complete-solving tasks from finite-step tasks.
- Separate determin idealized behavior from stochastic bounded behavior.

Related phases:

- Phase 3: Belief and entropy.
- Phase 4: Agent interface and model variants.
- Phase 5: Simulation modes and baselines.
- Phase 6: Experiments.

Expected output:

- simulation logs and summary tables with model type, mode, parameters, steps, final accuracy, errors, entropy, and dyad benefit.

### Topic D: Model Comparison

Purpose:

- Test whether the hypothesized value model explains behavior better than simpler alternatives.
- This does not prove the model is absolutely correct.
- The target claim is comparative:
  - `Q + beta_info * I` improves over `Q`,
  - adding `lambda_cost * C` improves prediction or performance,
  - partner-information improves dyad behavior on high-interaction puzzles.

Related phases:

- Phase 4: Model variants.
- Phase 6: Parameter sweeps.
- Phase 7: Replay likelihood and analysis.

Expected output:

- model comparison tables,
- likelihood comparisons for action sequences,
- parameter trends across puzzle classes,
- evidence that model improvements align with the theory.

## 6. Implementation Roadmap

### Phase 1: Puzzle Representation

Goal:

- create a clean puzzle layer without breaking existing solvers.

Tasks:

- [ ] Add `src/puzzle.py`.
- [ ] Define `Puzzle` with:
  - `solution`
  - `row_clues`
  - `col_clues`
  - `grid_size`
  - cached `valid_row_configs`
  - cached `valid_col_configs`
- [ ] Implement clue extraction:
  - `extract_line_clue(line) -> tuple[int, ...]`
  - `extract_row_clues(solution)`
  - `extract_col_clues(solution)`
  - `extract_all_clues(solution)`
- [ ] Implement cached line enumeration:
  - `enumerate_valid_lines(length, clue)`
  - cache by `(length, clue)`
  - internally may call `generate_line_patterns(length, list(clue), [UNKNOWN] * length)`
- [ ] Validate that extracted clues match stored clues.
- [ ] Add tests for empty lines, full lines, alternating lines, and multi-block lines.

### Phase 2: Puzzle Metrics And Generation

Goal:

- measure puzzle structure before running agents.

Tasks:

- [ ] Implement `count_solutions(row_clues, col_clues, max_solutions=2)`.
- [ ] Use exhaustive row-combination search first for 5x5 and 7x7.
- [ ] Add pruning/backtracking before using this for large 10x10 batches.
- [ ] Generate random unique puzzles:
  - sizes: 5x5, 7x7, 10x10
  - densities: 0.35, 0.50, 0.65
- [ ] Implement line ambiguity metrics:
  - `line_ambiguity` / `AS = log(number_of_valid_lines)`
  - row/column means and variances
  - max/min line ambiguity
- [ ] Implement row-column asymmetry metrics:
  - mean-row ambiguity
  - mean-column ambiguity
  - absolute difference
  - safe ratio
  - row/column/balanced category
- [ ] Implement across-line ambiguity variance controls:
  - row ambiguity variance
  - column ambiguity variance
  - pooled ambiguity variance
  - matched puzzle sets with similar mean ambiguity but different variance
- [ ] Implement joint constraint-space metrics:
  - `row_space_log_size`
  - `col_space_log_size`
  - `joint_space_log_size`
  - `joint_constraint_space_log`
  - label this cautiously because, for unique puzzles, it may mostly reflect total hypothesis-space size rather than a clean interaction/synergy measure
- [ ] Implement visual/compressibility metrics:
  - filled density
  - repeated row/column patterns
  - horizontal/vertical symmetry
  - run-length description length
  - distinct rows/cols

### Phase 3: Belief, Entropy, And Outcomes

Goal:

- make finite-step and stoch analyses meaningful.

Tasks:

- [ ] Implement board utility functions:
  - initialize unknown board
  - apply action
  - action legality
  - action correctness against solution
  - complete board check
  - board equals solution check
- [ ] Implement filtered line config helpers:
  - `filter_line_configs(configs, observed_line)`
  - row-based cell probability
  - column-based cell probability
  - combined full-information cell probability
  - label combined row/column probabilities as approximate local belief, not exact Bayesian posterior
  - later validate this approximation against exact posterior inference for 5x5
- [ ] Implement partial-information probabilities:
  - row-only agent uses row configs only
  - column-only agent uses column configs only
- [ ] Implement entropy helpers:
  - `cell_entropy(p)`
  - `board_entropy(cell_probs)`
  - `mean_unknown_cell_entropy`
  - `max_unknown_cell_entropy`
- [ ] Add outcome metrics:
  - `complete`
  - `success` / `matches_target`
  - `consistent_with_clues`
  - `contradiction_detected`
  - `n_steps`
  - `n_errors`
  - `final_accuracy`
  - `failure_reason`
  - `action_entropy_mean`
  - `belief_entropy_mean`
- [ ] Add `cell_accuracy` to analysis output.

### Phase 4: Agent Interface And Model Variants

Goal:

- avoid mixing determin line solvers, stoch models, and new value models in one ad hoc API.

Tasks:

- [ ] Define a shared agent interface:
  - observe board
  - generate candidate actions
  - score candidate actions
  - choose action
  - return action-value table
- [ ] Implement candidate generation over unknown cells:
  - `(row, col, EMPTY)`
  - `(row, col, FILLED)`
  - optional contradiction filtering
- [ ] Implement value terms:
  - `Q(action)` subjective correctness from cell belief
  - `I(action)` information proxy from cell entropy
  - `C_ambiguity(action)` from remaining compatible line-config counts accessible to the active agent
  - full-information agent cost: row cost + column cost
  - row-only / row-agent cost: row cost only
  - column-only / column-agent cost: column cost only
- [ ] Implement value function:

```text
V = Q + beta_info * I - lambda_cost * C_ambiguity
```

- [ ] Keep dyadoration separate:

```text
V_dyad = V + lambda_partner * B_partner
```

- [ ] Implement policies:
  - random legal action
  - determin argmax with seeded tie-break
  - expose `tau_decision` for new stochastic value models
  - if legacy code needs inverse temperature, convert internally with `beta_softmax = 1 / tau_decision`
- [ ] Implement model variants:
  - `random`
  - `correctness_only`
  - `correctness_info`
  - `correctness_cost_ambiguity`
  - `full_value_cost_ambiguity`
  - `dyad_board_update_only`
  - `dyad_partner_info`
  - later: alternative cost-proxy versions

### Phase 5: Simulation Modes And Baselines

Goal:

- compare ind and dyad behavior under the same budgets.

Tasks:

- [ ] Define explicit modes:
  - `ind_complete`
  - `ind_finite`
  - `dyad_complete`
  - `dyad_finite`
- [ ] Add action-requirement controls:
  - `action_mode = "forced"` for forced-choice finite-step simulations
  - `action_mode = "pass_if_no_valid"` for logical solvers
  - `action_mode = "pass_as_action"` for pass-as-candidate experiments
  - if `action_mode = "forced"`, determin and stochastic agents should use the same candidate set and differ only by policy
- [ ] Implement random legal action baseline early, before more complex value models.
- [ ] Wrap existing solvers as baseline modes before rewriting them.
- [ ] Add partial-information ind baselines:
  - row-only ind
  - column-only ind
  - full-information ind
- [ ] Add dyad board-update-only value-model solver:
  - strict alternating turns
  - `first_agent = row | col | random`
  - partner action only updates shared board
- [ ] Keep `dyad_partner_info` separate from board-update-only; define it as choosing actions useful for the partner, not interpreting partner actions communicatively.
- [ ] Compute:
  - `dyad_benefit`
  - `dyad_gap_to_full`

### Phase 6: Experiments

Goal:

- run theory-driven experiments after metrics and baselines are stable.

Experiments:

- [ ] Ambiguity and ind difficulty.
- [ ] Row-column asymmetry and dyad benefit.
- [ ] Constraint interaction and dyad benefit.
- [ ] Parameter sweeps:
  - current stoch sweep covers legacy `beta_softmax`, threshold `q_threshold`, `lambda_partner`, and seeds
  - add `beta_info`, `lambda_cost`, `tau_decision`, and action-mode/fallback settings after the new value model exists

### Phase 7: Analysis And Model Comparison

Goal:

- compare model predictions and produce final analysis outputs.

Tasks:

- [ ] Build a separate stoch/simulation scoring file rather than reusing determin difficulty.
- [ ] Produce one row per puzzle/model/run with:
  - puzzle metrics
  - model name and parameters
  - success/completeness metrics
  - final accuracy and errors
  - entropy metrics
  - dyad benefit metrics where applicable
- [ ] Implement replay likelihood:
  - replay observed action sequence
  - compute `P(action_t | state_t, theta)`
  - accumulate log likelihood
- [ ] Use simulated logs first; add human replay data later.
- [ ] Add diagnostic plots:
  - ambiguity vs steps/final accuracy
  - ambiguity variance vs performance
  - row-column asymmetry vs dyad benefit
  - constraint interaction vs dyad benefit
  - compressibility vs difficulty
  - parameter heatmaps
  - action entropy over time
  - belief entropy over time

## 7. Priority Plan

### Priority Now

1. Add `src/puzzle.py` with clue extraction, cached line enumeration, and tests.
2. Add `cell_accuracy`, `n_errors`, and `complete`/`success` distinction to analysis.
3. Add clue-consistency and contradiction detection to analysis.
4. Make stoch fallback/action mode configurable:
   - `action_mode = forced | pass_if_no_valid | pass_as_action`
   - `fallback = none | all_legal | uninformed` if fallback is still needed inside a mode
   - record `failure_reason` instead of always forcing a move.
5. Add random legal action, row-only, and column-only baselines.
6. Build the clean value-model interface.
7. Add finite-budget simulation modes.

### Later

- Generate larger controlled puzzle sets after metrics are stable.
- Add replay likelihood for human or simulated action sequences.
- Compare alternative cost proxies as separate model variants.

### Future / Not Priority

- Bayesian exact posterior model for small puzzles:
  - for 5x5, enumerate complete grids consistent with clues and current board,
  - define a prior over valid solution grids, starting with uniform prior,
  - compute posterior cell probabilities exactly,
  - use this as a validation benchmark for approximate local beliefs, not as the first main solver.
- Consider POMDP framing or small-puzzle POMDP benchmark:
  - useful as a formal frame for partial observability and sequential decision-making,
  - not a priority for the main implementation.
- Partner-action communication model.
- Dynamic partner reliability.
- Pattern-sensitive human-like priors.
- Full PID-style synergy decomposition.
