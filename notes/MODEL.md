# Model Overview

This note explains the difference between:
- the deterministic line solver used in `collab.py` and `ind.py`
- the stochastic latent-choice model used in `latent_collab.py`

The deterministic scripts are engineering baselines.
The stochastic script is the current process-model prototype for latent human behavior.

## 1. The Common Core: Line-Based Inference

All model variants in this repository start from the same line-based inference step.

For a given row or column:
- take the clue for that line
- take the current known cell states on that line
- enumerate all line patterns consistent with both

If a line has `K` consistent patterns, then each unknown cell in that line gets a local belief:
- `p(fill) = number of consistent patterns with FILLED at that cell / K`
- `p(empty) = 1 - p(fill)`

In the code, this local belief is stored as `Q_own`.

Interpretation:
- if `Q_own = 1.0`, the move is locally forced
- if `Q_own = 0.8`, the move is strongly supported but not certain
- if `Q_own = 0.5`, the line gives no preference

This is implemented in:
- `safe_line_probabilities()` in `latent_collab.py`
- `build_candidates_for_actor()` in `latent_collab.py`

## 2. Deterministic vs Stochastic Models

### Deterministic line solver

Used in:
- `collab.py`
- `ind.py`

Behavior:
- only forced moves are allowed
- if a move is not certainty-1 from a line, it is not taken
- there is no probabilistic sampling
- there is no deliberate partner-information term

Consequence:
- these scripts should stall rather than guess
- under consistent clues, they should not intentionally write incorrect cells

### Stochastic latent-choice model

Used in:
- `latent_collab.py`

Behavior:
- candidate actions can include sub-certain moves, depending on the choice-set definition
- each candidate gets a utility
- utilities are converted to probabilities with softmax
- one action is sampled from that probability distribution

Consequence:
- the model can make non-forced moves
- once non-forced moves are allowed, completed boards can be wrong
- this is why `solved` and `matches_target` can diverge in latent runs

## 3. The Three Candidate-Set Options

The three options do not change the softmax formula.
They change which actions are allowed into the candidate set before softmax is applied.

### Option 1. `certainty1`

Rule:
- only include actions with `Q_own = 1`

Meaning:
- the actor only considers locally certain moves
- stochasticity is only used to choose among multiple forced moves

Strength:
- very clean and conservative

Weakness:
- often too rigid for latent human modeling
- if many candidates all have `Q_own = 1`, softmax mostly becomes tie-breaking

### Option 2. `all_legal`

Rule:
- include every legal write action on every currently unknown cell

Meaning:
- the actor may consider low-confidence as well as high-confidence moves

Strength:
- expressive and flexible

Weakness:
- often too unconstrained psychologically
- can make the model consider actions a human would likely ignore

### Option 3. `threshold`

Rule:
- include actions with `Q_own >= tau`

Meaning:
- the actor filters out low-confidence actions
- among sufficiently plausible actions, choice is probabilistic

Strength:
- a useful compromise between the first two options

Weakness:
- introduces a threshold parameter `tau` that must be interpreted and fit

Interpretation of `tau`:
- high `tau` = cautious actor
- low `tau` = risk-tolerant actor

In the current project, this is the best main candidate for latent human modeling.

## 4. Utility Functions

After the candidate set is built, each candidate gets a utility.

### Individual utility

`U(a) = alpha * Q_own(a)`

Meaning:
- actions are valued only by the actor's own local support

### Collaborative utility

`U(a) = alpha * Q_own(a) + lambda * B_partner_local(a)`

Meaning:
- actions are valued both by own support and by how much they help the partner

`B_partner_local` is a local partner-information term.
It is computed as:

`B_partner_local = log(partner patterns before) - log(partner patterns after)`

Interpretation:
- larger positive values mean the move reduces the partner line's uncertainty more
- `0` means no local reduction
- if an action makes the partner line impossible, it is treated as incompatible

In the implementation:
- for collaborative utility, partner-incompatible actions get utility `-inf`
- that means they receive probability `0`

## 5. Softmax Choice

Once utilities are assigned, the model converts them to probabilities:

`P(a) = exp(beta * U(a)) / sum_a' exp(beta * U(a'))`

Interpretation of `beta`:
- low `beta`: flatter probabilities, noisier behavior
- high `beta`: sharper probabilities, stronger preference for the highest-utility move

Important clarification:
- `beta` controls how sharp the softmax is
- `certainty1`, `threshold`, and `all_legal` control which actions enter the softmax at all

So the three candidate-set options are not three different softmax scales.
They are three different definitions of the candidate set.

## 6. Worked Intuition

Suppose a row has 10 consistent patterns.
For some unknown cell:
- 8 patterns place `FILLED`
- 2 patterns place `EMPTY`

Then:
- choosing `FILLED` has `Q_own = 0.8`
- choosing `EMPTY` has `Q_own = 0.2`

Under the three options:
- `certainty1`: neither action is allowed
- `threshold` with `tau = 0.75`: `FILLED` is allowed, `EMPTY` is not
- `all_legal`: both are allowed

If the model then uses individual utility with `alpha = 1`:
- `U(FILLED) = 0.8`
- `U(EMPTY) = 0.2`

Softmax with higher `beta` will assign much more probability to `FILLED` than to `EMPTY`.

## 7. What Is Stored In The Logs

Yes, the latent model stores these quantities in the JSON output.

Per candidate, in `candidate_steps`:
- `q_own`
- `b_partner_local`
- `utility`
- `probability`
- `chosen`
- source line metadata

Per chosen action, in `events[].decision`:
- `utility_model`
- `choice_set`
- `alpha`
- `beta`
- `tau`
- `lambda_weight`
- `candidate_count`
- `chosen_probability`
- `chosen_q_own`
- `chosen_b_partner_local`
- `chosen_utility`
- partner compatibility metadata

This makes the log suitable for:
- simulation summaries
- action-level model inspection
- later fitting against human action sequences

## 8. Practical Reading Guide

If you want the shortest path through the documentation:

1. read this file for the implementation-level overview
2. read `notes/note.md` for the broader research framing
3. read `notes/line_solver.md` if you want more detail on the deterministic line-solver core

## 9. Current Recommendation

For this project:
- use `collab.py` and `ind.py` as deterministic bounded baselines
- use `latent_collab.py` as the stochastic latent human-choice model
- prioritize `threshold` as the main latent candidate
- keep `certainty1` as a conservative comparison
- keep `all_legal` as a richer but riskier comparison
