


# Nonogram collaboration task — detailed working notes

## Reading guide

This note currently mixes four functions:
1. conceptual framing
2. candidate model definitions
3. experimental design considerations
4. implementation and analysis planning

To make future use easier, the note can be read in this order:
- Sections 1–5: conceptual framing
- Sections 6–10: model family
- Sections 11–14: puzzle design, data, and fitting
- Sections 15–18: interpretation, example, and next steps
- Sections 19–22: open decisions and immediate implementation plan

This document is a working research note, not yet a finalized methods section.

## 1. Core research idea

The task is not primarily about whether two people can fully solve a nonogram.
The main question is whether, under partial information and a limited action budget, two players choose actions that efficiently transmit information to each other through a shared external workspace.

More specifically, the task is designed to test whether dyads behave like:

1. two individuals acting in parallel, each choosing moves that are locally good from their own perspective; or
2. a genuinely collaborative system, in which each player sometimes chooses moves because those moves are informative for the partner.

This distinction matters because the theoretical interest is not generic “group performance,” but complementary information use, synergy, and coordination under partial observability.

---

## 2. Important clarification: task, model, simulation, and human experiment are different layers

One source of confusion is that several things were mixed together in discussion. They should be separated clearly.

### 2.1 Task-design layer

This defines the behavioral task the participants actually play.

Examples:
- one player sees only row clues
- the other player sees only column clues
- both see the same shared grid
- each turn allows only one action
- there is a fixed action budget `T`
- actions may include fill, X, and optionally an uncertain mark

This layer defines **what game is being played**.

### 2.2 Model / algorithm layer

This layer defines computational agents or observer models.
These are not the human participants themselves.
They are candidate formalizations of how behavior could be generated.

Examples:
- random agent
- individual certainty-based agent
- bounded line-solver agent
- collaborative information-seeking agent

This layer defines **the baseline and comparison models**.

### 2.3 Human experiment layer

This is the actual data collection stage.
Human participants play the task, and sequential action data are recorded.

Examples of recorded data:
- step number
- actor identity
- actor role (row / column)
- chosen cell
- chosen mark
- board state before action
- board state after action
- reaction time
- remaining action budget

This layer gives **the observed sequential behavioral data**.

### 2.4 Analysis layer

This layer compares human behavior against the candidate models.
It asks questions such as:
- does a human move look like a move chosen only from own certainty?
- does it look like a move chosen because it reduces partner uncertainty?
- does collaboration outperform non-collaborative baselines under the same action budget?

This layer produces **the actual theoretical inference**.

---

## 3. What the task is and is not

### 3.1 What it is

A sequential, partially observed, budget-limited coordination task with a shared external workspace.

### 3.2 What it is not

It is not necessarily a standard full nonogram-solving task where success is defined by complete puzzle completion.

A more appropriate framing is:

> Given a fixed number of actions, how effectively do two players use their complementary information to reduce uncertainty in the shared problem space?

So the outcome of interest can be:
- correct information added to the board
- uncertainty reduction
- partner-informative action choice
- coordination efficiency

not only full completion.

---

## 4. Why an individual baseline is still meaningful even if the puzzle cannot be solved alone

A key concern was:
if the puzzle is designed so that row clues alone or column clues alone are insufficient to completely solve it, then why is an individual baseline meaningful at all?

The answer is that the individual baseline is **not** meant to be a completion baseline.
It is not meant to show that a single player should be able to solve the whole puzzle.

Instead, it is meant to answer a different question:

> If an agent does not model the partner and does not deliberately act to help the partner, what kind of moves would it choose under the same information and the same action budget?

So the individual baseline is a:
- local-inference baseline
- non-collaborative action-selection baseline
- information-limited baseline

Its purpose is to establish what behavior looks like **without partner-oriented reasoning**.

That is why it is still meaningful even if the puzzle eventually forces a lone player to stall.
In fact, if the puzzle does force an individual to stall, that is evidence that complementary information is genuinely needed.

A useful way to state this more carefully:

> Under a specified family of non-collaborative baseline models, if individual agents make only limited progress while a collaborative model or human dyad makes substantially more progress, then the puzzle can be operationally treated as requiring complementary information.

This is more precise than saying, in an absolute sense, that the puzzle “requires collaboration.”

---

## 5. Normative vs bounded models

### 5.1 Normative

A normative model is an idealized model of what an agent should infer if it uses all available information rationally and has sufficient computational resources.

In this context, a normative model might:
- represent all currently possible complete boards consistent with the observed constraints
- update that hypothesis space exactly after every move
- compute exact posterior beliefs over cells

This is often called an ideal observer or near-ideal inference model.

### 5.2 Why that may be too strong for humans

Humans probably do not:
- enumerate all possible full-board completions
- perform exact global consistency updates at every step
- maintain a full exact posterior distribution over the entire board

So a purely normative model may be useful for defining theoretical upper bounds or ideal information gain, but it may be cognitively unrealistic.

### 5.3 Bounded models

A bounded model approximates human reasoning under cognitive limits.
It may include constraints such as:
- local line-based deduction only
- limited search depth
- no full-board enumeration
- limited working memory
- attentional bottlenecks
- noisy or inconsistent application of rules

A bounded model is often more appropriate as a cognitive process model for actual human behavior.

### 5.4 Practical compromise

A good overall strategy is:
- use normative definitions for some clean theoretical quantities, such as ideal uncertainty reduction
- use bounded solvers to model actual human action selection

These two roles should not be conflated.

---

## 6. Formal task notation

Assume a nonogram with `N` cells.
For convenience, let each cell be indexed by `i = 1, ..., N`.

### 6.1 Hidden ground-truth board

Let the true solution be

`z = (z_1, ..., z_N)`, where `z_i in {0, 1}`

with:
- `1` = filled / black
- `0` = empty / white

### 6.2 Private information

There are two players:
- row player `R`
- column player `C`

Let:
- `I_R` = row clues
- `I_C` = column clues

The row player only sees `I_R`.
The column player only sees `I_C`.

### 6.3 Public board state

At time or step `t`, the shared board state is

`s_t = (s_{t,1}, ..., s_{t,N})`

Each cell state may be coded as:
- `U` = unknown
- `B` = marked black
- `X` = marked empty / crossed out

A convenient numeric encoding for storage is:
- `0` = unknown
- `1` = black
- `-1` = X / empty

### 6.4 Action

An action at step `t` is

`a_t = (i_t, m_t, j_t)`

where:
- `i_t` = which cell is selected
- `m_t` = chosen mark, e.g. `B` or `X`
- `j_t` = acting player (`R` or `C`)

The public state updates by

`s_{t+1} = T(s_t, a_t)`

where `T` is the state-transition rule.

### 6.5 Budgeted task

The task lasts only `T_max` steps.
The goal is not necessarily complete solution.
Instead, the task is to make the best use of limited actions.

---

## 7. Individual baseline model

Important: this is first and foremost a **computational model**, not a direct readout of human internal thought.

The idea is:

> If a player chooses actions without modeling the partner, and only uses their own clue information plus the shared board, what would that player prefer to do?

### 7.1 Hypothesis space for a player

For player `j in {R, C}`, define the set of full-board hypotheses still consistent with the player’s private information and the current public board:

`H_t^(j) = { h in {0,1}^N : h is consistent with I_j and s_t }`

This is a model-defined latent hypothesis space, not something directly observed from participants.

### 7.2 Cell belief under a normative uniform-hypothesis approximation

One simple approximation is to assign equal weight to all hypotheses in `H_t^(j)`.
Then the belief that cell `i` is black is:

`p_t^(j)(z_i = 1) = (1 / |H_t^(j)|) * sum_{h in H_t^(j)} 1[h_i = 1]`

and similarly:

`p_t^(j)(z_i = 0) = 1 - p_t^(j)(z_i = 1)`

Interpretation:
this is the fraction of remaining hypotheses in which that cell is black.

### 7.3 “Not sure” is not a third symbolic state in the belief itself

Instead:
- if `p` is near 1, the model is highly confident the cell is black
- if `p` is near 0, the model is highly confident the cell is empty
- if `p` is near 0.5, the model is uncertain

So uncertainty can be represented via entropy:

`H_t^(j)(i) = - p_t^(j)(z_i=1) log p_t^(j)(z_i=1) - p_t^(j)(z_i=0) log p_t^(j)(z_i=0)`

### 7.4 Own-certainty score for an action

For an action `a = (i, m)`, define a correctness-based score:

- if `m = B`, then `Q_t^(j)(a) = p_t^(j)(z_i = 1)`
- if `m = X`, then `Q_t^(j)(a) = p_t^(j)(z_i = 0)`

This says how justified the move is given the acting player’s own information.

### 7.5 Individual utility

A minimal individual utility is:

`U_t^ind(a | j) = alpha * Q_t^(j)(a) - C(a)`

where:
- `alpha` controls sensitivity to own-certainty
- `C(a)` is an optional action cost

The simplest version sets cost to a constant or zero.

### 7.6 Individual policy via softmax

The probability of choosing action `a` is:

`pi_t^ind(a | j) = exp(beta * U_t^ind(a | j)) / sum_{a' in A_t^(j)} exp(beta * U_t^ind(a' | j))`

where:
- `A_t^(j)` is the candidate action set available to player `j`
- `beta` is the inverse temperature parameter

### 7.7 Intuition of beta

`beta` is a standard softmax parameter.
It is not specific to this task.

Interpretation:
- small `beta` -> choices are noisy / close to random
- large `beta` -> choices strongly track the utility ranking

So `beta` measures how consistently the agent follows the utility function.
It is **not** itself a measure of collaboration.

In model fitting, `beta` would typically be a parameter estimated from behavioral data.

### 7.8 Two different roles for probabilistic choice

It is important to distinguish two different uses of a stochastic policy.

#### A. Probabilistic choice as a latent model of human behavior

In this use, the policy is not mainly intended to maximize task performance.
It is intended to assign probabilities to observed human actions.

This is the natural use case for:
- softmax choice rules
- inverse temperature `beta`
- likelihood-based model fitting

In that setting, the key question is:

> Given the candidate actions available at step `t`, how probable is the action the human actually chose under model `M`?

So the main output is:
- `pi_t(a | j)`
- sequence likelihood
- fitted parameters such as `beta`, `alpha`, and `lambda`

This is primarily an analysis-layer use of probabilistic choice.

#### B. Probabilistic choice as a simulation policy

In this use, the policy is used to generate full artificial trials.
The model is rolled forward step by step and its performance is evaluated.

In that setting, the main outputs are:
- solved rate
- cells resolved
- uncertainty reduction
- variability across repeated runs

This is primarily a model / simulation-layer use of probabilistic choice.

The important consequence is that a stochastic simulation agent no longer has a single performance value for a puzzle.
It has a distribution over outcomes.
So evaluation should be based on repeated simulations, not one run only.

#### Why this distinction matters

A stochastic policy can be highly appropriate as a human-choice model even if it is not the best first simulation baseline.

For example:
- a deterministic bounded solver may be preferable as a clean engineering baseline
- a stochastic softmax policy may be preferable for fitting human action sequences

So these two uses should not be conflated.
The same mathematical policy form can serve both purposes, but the inferential goal is different.

### 7.9 Important implication for the first bounded prototype

If the candidate action set contains only certainty-1 moves, then many candidate actions may receive the same `Q_own`.

In particular, if:
- candidate actions are restricted to moves with local probability exactly `1`
- `C(a)` is constant or zero
- no additional utility term is included

then the individual softmax policy may collapse into near-uniform random tie-breaking over forced moves.

That is still a valid stochastic policy, but it is not very informative if the goal is to model graded preferences among multiple plausible actions.

Therefore, if probabilistic choice is meant to do more than break ties, at least one of the following should be added:
- allow sub-certain actions into the candidate set
- add non-constant action costs or attentional/salience terms
- include partner-information value in the collaborative model

### 7.10 Three candidate stochastic choice-set definitions

If the goal is latent modeling of human behavior, at least three candidate stochastic policies are worth distinguishing.

#### Option 1. Softmax only over certainty-1 actions

Definition:
- the candidate set contains only actions with `Q_own = 1` under the actor’s bounded inference process
- choice among those candidates is probabilistic, for example via softmax

Interpretation:
- the human is assumed to consider only fully justified moves
- stochasticity mainly reflects noisy selection among moves seen as certain

Advantages:
- very clean interpretation
- closely aligned with conservative task instructions such as “only mark a cell if you are sure”
- easy to debug

Limitations:
- often too narrow for real human behavior
- if many candidates all have `Q_own = 1`, the policy may collapse into tie-breaking unless other utility terms are added
- does not naturally account for near-certain but not fully certain moves

#### Option 2. Softmax over all legal actions with graded local probabilities

Definition:
- the candidate set contains all legal actions available at the current board state
- `Q_own` is defined continuously from the actor’s local bounded belief state
- choice probability is distributed over the full legal action set

Interpretation:
- the human can in principle choose any legal move
- stronger local justification leads to higher probability, but weaker moves remain possible

Advantages:
- richest representation of graded confidence
- can model hesitant, exploratory, or error-prone human choices
- gives `beta` and other utility terms more room to matter

Limitations:
- may be psychologically too permissive
- humans likely do not inspect every legal action on every turn
- may overpredict low-probability weak moves unless cost or attention terms are added

#### Option 3. Hybrid threshold model

Definition:
- the candidate set contains actions with `Q_own >= tau`
- within that filtered set, choice is probabilistic

Interpretation:
- the human screens out moves that look too implausible
- among sufficiently plausible moves, selection is noisy

Advantages:
- more realistic than certainty-1 only
- more constrained than all-legal-actions
- `tau` has a natural interpretation as a caution threshold

Limitations:
- introduces another fitted or chosen parameter
- the threshold itself becomes a modeling assumption that must be justified

#### Provisional recommendation

For a formal model-comparison program, all three can be implemented and compared.
That is preferable to assuming one is correct in advance.

However, if only one probabilistic latent-choice model should be prioritized first, the hybrid threshold model is likely the best starting point because:
- certainty-1 only may be too rigid
- all-legal-actions may be too unconstrained
- thresholded choice matches the intuition that humans consider only sufficiently plausible moves, not all possible moves and not only perfectly certain ones

So a practical first sequence would be:
- first implement Option 1 as the cleanest sanity-check model
- then implement Option 3 as the main latent-behavior model
- treat Option 2 as an important comparison model if resources permit

#### Recommended interpretation of parameters

Under this three-way family, the parameters have distinct meanings:
- `tau`: what actions enter consideration at all
- `beta`: how consistently the actor prefers higher-utility actions among considered actions
- `lambda`: how much partner-oriented information value affects choice

This separation is conceptually useful because:
- `tau` is about candidate generation / caution
- `beta` is about stochastic selection consistency
- `lambda` is about collaboration

---

## 8. Why the individual baseline is only one candidate model

A concern was that if the researcher defines the algorithm, then its behavior is partly under the researcher’s control.
That is correct.
Therefore the solution is **not** to treat one hand-designed baseline as truth.

Instead, multiple candidate models should be defined and compared.

Examples:
- `M0`: random baseline
- `M1`: individual certainty model
- `M2`: bounded line-based individual solver
- `M3`: collaborative information model

The point is not to assume one model is right in advance.
The point is to compare which model best explains human behavior.

---

## 9. Collaboration model

The collaboration model differs from the individual model in one essential way:

> An action is valuable not only because it is locally justified for the actor, but also because it may reduce the partner’s uncertainty.

### 9.1 Partner hypothesis space

For the partner `-j`, define:

`H_t^(-j) = { h in {0,1}^N : h is consistent with I_-j and s_t }`

### 9.2 Partner uncertainty

Two reasonable definitions were discussed.

#### Option A: hypothesis-count uncertainty

`U_t^(-j) = log |H_t^(-j)|`

Interpretation:
how many globally possible boards remain for the partner.

#### Option B: summed cellwise entropy

`U_t^(-j) = sum_{i : s_{t,i} = U} H_t^(-j)(i)`

Interpretation:
how much uncertainty remains across unresolved cells.

Option A is more global and cleaner in theory.
Option B is more graded and often easier to approximate locally.

### 9.3 Partner information gain

If action `a` changes the public board from `s_t` to `s_{t+1}`, define:

`B_t^partner(a | j) = U_t^(-j) - U_{t+1}^(-j)`

Interpretation:
how much the partner’s uncertainty would be reduced by seeing that move.

This quantity is model-defined.
It is not a direct readout of the partner’s real subjective uncertainty.
It depends on the chosen partner model.

### 9.4 Collaborative utility

`U_t^collab(a | j) = alpha * Q_t^(j)(a) + lambda * B_t^partner(a | j) - C(a)`

where:
- `Q_t^(j)(a)` = own-certainty / local justification
- `B_t^partner(a | j)` = information value for partner
- `lambda` = weight on partner-oriented information value

### 9.5 Collaborative policy

`pi_t^collab(a | j) = exp(beta * U_t^collab(a | j)) / sum_{a' in A_t^(j)} exp(beta * U_t^collab(a' | j))`

### 9.6 Formal marker of collaboration

If `lambda = 0`, this collapses back toward the individual model.
So, conceptually, collaboration enters when action value depends on partner-oriented information gain.

Important note:
`lambda > 0` in the fitted model would be evidence that behavior is better explained by partner-oriented utility, not proof that the participant consciously verbalized such a strategy.

---

## 10. Bounded individual solver as a more human-like process model

Because exact hypothesis enumeration may be too strong, a bounded solver may be preferable.

Possible bounded assumptions:
- use only line-based overlap rules
- no exact full-board enumeration
- only local propagation
- no deep tree search
- limited working memory
- attentional constraints on which lines or regions are inspected
- noisy application of otherwise valid rules

A bounded individual solver can define:
- candidate moves available to a player
- confidence attached to each move
- which moves are even noticed

This may be a more realistic generator of human-like uncertainty than the fully normative hypothesis-space model.

This issue should remain open and empirical rather than assumed too early.

---

## 11. Puzzle complexity, complementarity, and step budget

Because the task uses a limited number of moves, puzzle difficulty cannot be treated simply as “can the puzzle eventually be solved.”

Instead, puzzle characterization should include at least three components.

### 11.1 Individual difficulty

How much progress can a row-only or column-only non-collaborative agent make under the same action budget?

### 11.2 Joint difficulty

How much progress can be made if all clues are integrated?

### 11.3 Collaboration opportunity / complementarity

How often does the puzzle contain moves that are:
- not necessarily the highest-certainty move for the actor
- but highly informative for the partner

This third dimension is especially important for the present research question.

### 11.4 Choosing the action budget `T_max`

`T_max` should not be chosen arbitrarily.
A better strategy is:

1. simulate different puzzle types with baseline agents
2. examine performance at different action budgets
3. choose a budget where collaboration is neither trivial nor impossible

For example:
- too few steps -> everyone performs near floor
- too many steps -> individual and collaborative agents both eventually do well, reducing diagnostic value
- intermediate steps -> collaboration advantage may become most visible

So `T_max` should be selected in the regime where differences in information-use strategy are most likely to appear.

---

## 12. Puzzle classes that should likely be included

It is likely not enough to use only one puzzle type.
A broader task set would improve interpretability.

### 12.1 Weak-complementarity / more redundant puzzles

Puzzles where row-only or column-only reasoning can already make substantial progress.

### 12.2 Moderate-complementarity puzzles

Puzzles where each side can infer part of the structure, but key regions require integration.

### 12.3 Strong-complementarity puzzles

Puzzles where single-sided reasoning quickly stalls, so progress depends heavily on the partner’s contributions.

Using multiple puzzle classes would allow tests of whether:
- collaboration-like behavior increases when the task structure truly favors it
- humans adapt their strategy to complementarity structure
- the fitted collaboration weight changes across puzzle classes

---

## 13. What data should be stored

The fundamental unit of analysis should be the **single action event**, not only static board snapshots.

### 13.1 Raw event log

Each row should represent one action.
Suggested fields:
- `session_id`
- `puzzle_id`
- `dyad_id`
- `step_index`
- `actor_id`
- `actor_role` (`row` / `column`)
- `cell_row`
- `cell_col`
- `cell_index`
- `action_type` (`fill`, `x`, maybe `uncertain` if allowed)
- `board_state_before`
- `board_state_after`
- `reaction_time_ms`
- `remaining_budget`
- `overwrite_flag`
- `timestamp`

### 13.2 Why snapshots alone are insufficient

If only the whole-board snapshot at each timepoint is stored, important sequential structure is lost.
It becomes difficult to know:
- who changed what
- in what order
- whether a move was informative or merely late-stage cleanup
- whether the other player exploited the prior move immediately

So action-level logs are essential.

### 13.3 Derived state-level quantities

From the action log, derive for each step:
- board entropy under different models
- own-certainty of each candidate move
- partner information gain of each candidate move
- rank of the chosen move among all candidates
- whether the move was locally best for the actor
- whether the move was globally informative for the dyad

### 13.4 Candidate-action analysis table

For each step, generate a long-format table over all candidate actions:
- `step`
- `actor`
- `candidate_action`
- `Q_own`
- `B_partner`
- `U_ind`
- `U_collab`
- `chosen` (0/1)
- `rank_Q`
- `rank_B`
- `rank_U_ind`
- `rank_U_collab`

This table is especially useful for model fitting and action-level analysis.

---

## 14. Model fitting

Let the observed action sequence be `D = (a_1, ..., a_T)`.
For a candidate model `M`, the probability of the observed sequence is:

`P(D | M) = product_t pi_t(a_t^obs | s_t, I_j, M)`

and the log-likelihood is:

`log P(D | M) = sum_t log pi_t(a_t^obs | s_t, I_j, M)`

This allows comparison among candidate models.

Potential fitted parameters include:
- `beta`: choice consistency / inverse temperature
- `alpha`: weight on own-certainty
- `lambda`: weight on partner information gain

Depending on the model family, additional boundedness parameters may also be estimated, such as:
- search depth
- number of lines inspected
- attentional sampling bias
- memory limit parameters

---

## 15. Important interpretation cautions

### 15.1 Do not say

“We know the participant’s true internal state probability.”

### 15.2 Prefer to say

“We compare candidate latent belief-state models and ask which one best explains the observed action sequence.”

### 15.3 Do not say

“An individual baseline should solve the puzzle too.”

### 15.4 Prefer to say

“The individual baseline defines non-collaborative action selection under private information constraints.”

### 15.5 Do not say

“Collaboration just means two people are both present.”

### 15.6 Prefer to say

“Collaboration enters the model when action value depends on reducing partner uncertainty, not only local actor certainty.”

---

## 16. Worked example from the 10x10 puzzle that was discussed

The example puzzle had the following clues.

### 16.1 Row clues

`R1 = [3]`
`R2 = [4,1]`
`R3 = [1,1,2,1]`
`R4 = [3,1,3]`
`R5 = [1]`
`R6 = [3,3]`
`R7 = [5,3]`
`R8 = [3,1,1,1]`
`R9 = [5,3]`
`R10 = [3,3]`

### 16.2 Column clues

`C1 = [1]`
`C2 = [2,3]`
`C3 = [1,1,5]`
`C4 = [2,5]`
`C5 = [2,2,2]`
`C6 = [5,3]`
`C7 = [1,1,1,1]`
`C8 = [1,1,5]`
`C9 = [2,2]`
`C10 = [1,3]`

### 16.3 Suppose the task is run as follows

Assume:
- row player sees only row clues
- column player sees only column clues
- both see the same empty 10x10 grid
- they take turns
- each turn allows marking exactly one cell as black or X
- the puzzle is run for a fixed budget, e.g. `T_max = 8`

Then the experimental unit is not “did they finish the whole puzzle?”
Rather, it is “what sequence of externally visible information-carrying actions did they choose under a limited budget?”

### 16.4 Example of row-only local certainty

Take row `R7 = [5,3]` in a row of length 10.
The minimum required length is:
- 5 black
- at least 1 empty separator
- 3 black

So total minimum length is `5 + 1 + 3 = 9`.
That leaves only two placements in a row of length 10.
Their overlap implies that some cells are guaranteed black.

This means that for some cells in row 7, the row player’s certainty is effectively 1 under a line-overlap style reasoning scheme.
Those would be high-certainty cells for the row player.

### 16.5 Why individual and collaborative choices may differ

Suppose candidate action `a1 = (7,4,B)` has very high own-certainty for the row player.
Then under an individual model, it may rank highly because it is strongly justified locally.

But another action `a2 = (2,6,B)` might be slightly less certain for the row player while being much more informative for the column player because it strongly constrains column 6.

Then:
- the individual model may prefer `a1`
- the collaborative model may prefer `a2` if `lambda * B_partner` is large enough

This is the key qualitative dissociation.

### 16.6 Example of candidate-action table for one step

An illustrative table at one step might look like this:

| step | actor | action    | Q_own | B_partner | chosen |
|------|-------|-----------|------:|----------:|-------:|
| 1    | R     | (7,4,B)   | 1.00  | 0.10      | 0      |
| 1    | R     | (7,5,B)   | 1.00  | 0.12      | 0      |
| 1    | R     | (2,6,B)   | 0.78  | 0.55      | 1      |
| 1    | R     | (9,3,B)   | 0.95  | 0.20      | 0      |

If the human chooses `(2,6,B)`, that choice would not be well described as simply maximizing own-certainty.
It would be more compatible with a partner-informative move policy.

### 16.7 Example sequential log

An example of observed event-level data might look like:

| step | actor | row | col | mark | board_before | board_after | rt_ms |
|------|-------|----:|----:|------|--------------|-------------|------:|
| 1    | R     | 2   | 6   | B    | s0           | s1          | 1420  |
| 2    | C     | 3   | 6   | B    | s1           | s2          | 980   |
| 3    | R     | 7   | 4   | B    | s2           | s3          | 1105  |
| 4    | C     | 7   | 8   | B    | s3           | s4          | 890   |

This preserves the sequential coordination structure that would be lost in static snapshots alone.

---

## 17. Suggested next steps

### 17.1 Define a bounded individual solver family before collecting human data

Before large-scale human data collection, define at least one plausible bounded individual solver.
Without this, it is hard to ground:
- own-certainty estimates
- candidate action sets
- partner information gain under bounded assumptions

### 17.2 Build a puzzle bank and characterize it computationally

For each puzzle, estimate:
- row-only progress potential
- column-only progress potential
- joint progress potential
- complementarity / collaboration potential

### 17.3 Run small toy examples before scaling up

Before a full experiment, manually or computationally work through a few small puzzles step by step and generate:
- candidate actions
- own-certainty values
- partner-information values
- expected differences between individual and collaborative models

This is likely the most useful way to check whether the framework is actually operational.

### 17.4 Decide the stochastic choice-set family before human fitting

Before fitting human data, decide which candidate-set definition will be treated as:
- sanity-check baseline
- main latent-choice model
- optional richer comparison model

A good default sequence is:
- Option 1: certainty-1 only, as a minimal baseline
- Option 3: thresholded `Q_own >= tau`, as the main latent-choice model
- Option 2: all legal actions, as a broader comparison model if needed

This order helps separate:
- basic engineering/debugging
- psychologically plausible latent modeling
- more permissive comparison models

### 17.5 Use simulation to choose model family and task regime before human data

Simulation should not only measure performance.
It should also test whether the model family generates interpretable action distributions.

In particular, simulation should be used to check:
- whether candidate sets are too small or too large
- whether `beta` actually changes action probabilities in meaningful ways
- whether `lambda` changes rankings only in strong-complementarity puzzles or everywhere
- whether different model families are distinguishable at the chosen action budget

This is important because a latent-choice model is only useful if the observable predictions of competing models are actually separable.

### 17.6 Formal computational-cognitive-science workflow

For this project, a more formal research pipeline would be:

1. Define the task precisely
   - fixed action space
   - information partitions
   - turn order
   - scoring / stopping rule
   - action budget

2. Define candidate cognitive models before seeing human data
   - random model
   - bounded individual model
   - bounded collaborative model
   - stochastic variants of candidate-set definition

3. Implement simulation and logging infrastructure
   - event-level logs
   - candidate-action tables
   - latent quantities such as `Q_own`, `B_partner`, and action ranks

4. Build or curate puzzle classes
   - weak complementarity
   - moderate complementarity
   - strong complementarity

5. Run simulation sweeps
   - vary puzzle class
   - vary action budget
   - vary model parameters such as `beta`, `tau`, and `lambda`

6. Check identifiability before human collection
   - verify that candidate models produce measurably different action distributions
   - verify that simulated data from one model can, in principle, be distinguished from another

7. Choose the final task regime for human study
   - pick puzzle classes and action budgets where the theoretical distinction is most visible

8. Pilot the human experiment
   - confirm instructions are understandable
   - confirm participants actually use the intended action space
   - confirm the event logging and timing are correct

9. Fit candidate models to human sequential action data
   - compute stepwise candidate sets
   - evaluate action likelihoods
   - fit parameters such as `beta`, `tau`, and `lambda`
   - compare models with likelihood-based criteria

10. Interpret model comparison cautiously
   - evidence for a collaborative model means better fit to observed action sequences
   - it does not automatically prove conscious partner-modeling in a verbal or introspective sense

11. Report both behavior-level and model-level results
   - solved rate / progress / uncertainty reduction
   - action-level model fit
   - parameter estimates across puzzle classes
   - whether collaboration weight changes with complementarity

### 17.7 Strong recommendation for the current project stage

Because simulation comes before human data in the present project, the immediate priority should be:

1. finalize one bounded inference engine
2. implement at least two candidate-set definitions for stochastic choice
3. run simulation sweeps to test identifiability
4. only then finalize the human-model fitting plan

At minimum, the two stochastic variants worth implementing first are:
- certainty-1 only
- thresholded `Q_own >= tau`

If those two already produce clearly different predictions, that will give a much stronger foundation for later human-model comparison.

---


## 18. Minimal summary of the overall logic

1. Design a nonogram-based task with asymmetric private information and a shared board.
2. Define several candidate computational models, including non-collaborative and collaborative ones.
3. Characterize puzzle types by how much progress is possible individually vs jointly.
4. Collect human sequential action data under a limited action budget.
5. Compare whether human actions are better explained by own-certainty alone or by partner-oriented information value.
6. Use that comparison to evaluate whether observed dyad behavior reflects parallel solo inference or genuinely collaborative information use.

---

## 19. Open decisions that still need to be fixed

The note above defines the overall framework, but several major decisions are still unresolved. These should be treated as design questions rather than hidden assumptions.

### 19.1 What should count as the primary cognitive baseline?

Possible options include:
- a simple certainty-based individual model
- a bounded line-overlap solver
- a bounded local-propagation solver
- a family of baselines with increasing complexity

At the current stage, the safest position is not to commit to a single baseline too early.
A better strategy is to compare a small family of plausible individual models.

### 19.2 Should partner information gain be computed normatively or under a bounded partner model?

There are at least two legitimate options:
- compute partner uncertainty reduction under a normative hypothesis-space model
- compute it under a bounded partner model that approximates human inference limits

The normative version is cleaner mathematically.
The bounded version may be more cognitively realistic.
This choice will affect the meaning of `B_partner`.

### 19.3 What action set should the player have?

This still needs to be fixed explicitly.
Possible action spaces:
- mark one cell black
- mark one cell X
- optionally mark uncertainty
- optionally remove or revise a previous mark

The broader the action space, the richer the data, but the harder the modeling problem.
For early implementation, a minimal action space may be best.

### 19.4 Turn structure

Still to be decided:
- strict turn-taking or free asynchronous interaction
- fixed number of turns per player or shared team budget
- whether both players always see the action immediately

Strict turn-taking is simpler for modeling and for event-level analysis.

### 19.5 Outcome variable

Still to be decided more precisely:
- number of correct marks after `T_max`
- reduction in joint uncertainty
- model-based informativeness of chosen actions
- mixture of action-level and task-level measures

Most likely, the final study should include both:
- an action-level model comparison measure
- a task-level information-efficiency measure

### 19.6 Puzzle construction strategy

Still to be decided:
- hand-designed puzzle sets
- generated puzzle bank with computational screening
- hybrid strategy: generate many, manually curate some

A hybrid strategy is likely most practical.

---

## 20. Recommended concrete workflow from now on

A useful practical workflow would be:

### Step 1. Fix the minimal task format

Decide the smallest viable task version:
- row player vs column player
- shared board
- strict alternation
- one action per turn
- actions limited to black / X
- fixed action budget

This should be the first prototype version.

### Step 2. Implement one bounded individual solver

Before implementing all models, define one clear bounded baseline.
For example:
- only line-overlap deductions
- no full-board search
- only moves with certainty 1 are considered candidate actions

This gives a usable first operationalization of:
- candidate action set
- own certainty
- individual progress

### Step 3. Implement one collaborative scoring rule

Start with a simple collaboration term:
- for each candidate move, estimate how much it reduces the partner’s remaining line-level ambiguity
- do not start with a fully global exact version unless it is computationally easy

The goal is to build a working prototype first.

### Step 4. Build a small puzzle bank for simulation

Start with a small number of puzzles, for example:
- a few weak-complementarity puzzles
- a few strong-complementarity puzzles

Run the baseline and collaborative agents on them.
This will help determine:
- whether the proposed metrics behave sensibly
- whether the action budget is too short or too long
- whether the puzzle classes are actually separable

### Step 5. Inspect trial-by-trial outputs manually

Before any large-scale human experiment, inspect several full simulated trials manually.
For each step, check:
- what candidate actions were available
- why the model preferred one move over another
- whether the collaborative term genuinely changes the ranking of actions

This is important because many modeling problems only become visible when looking at actual step-by-step examples.

### Step 6. Only then move to human piloting

Human data collection should come after the basic computational pipeline is already interpretable.
Otherwise it will be difficult to understand what the human sequences mean.

---

## 21. Minimal implementation plan for a first prototype

This section is intentionally concrete.
It is not the only implementation plan, but it is a realistic one.

### 21.1 Data representation

Represent the board as a matrix with values:
- `0` = unknown
- `1` = black
- `-1` = X

Represent row clues and column clues as lists of integer lists.

Example:
- `row_clues = [[3], [4,1], ...]`
- `col_clues = [[1], [2,3], ...]`

### 21.2 First bounded individual solver

Define a row-player bounded solver as follows:
- it only reasons over rows, not full-board global solutions
- for each row, enumerate all row patterns consistent with that row clue and the current public row state
- compute cellwise frequencies within that row-level hypothesis set
- candidate actions are only cells whose row-level probability is exactly 1 for black or exactly 1 for empty
- if multiple candidate actions exist, select among them using a policy rule

Define the column-player solver symmetrically over columns.

This is bounded because it does not enumerate the full board, only line-level possibilities.

Important note:
if the first prototype keeps the candidate set restricted to certainty-1 moves, then a stochastic policy over candidates will function mainly as a tie-breaking rule unless additional utility terms are introduced.

### 21.3 Own-certainty in the bounded prototype

In the bounded prototype, `Q_own` can be defined from the local line-level hypothesis set rather than a global full-board hypothesis set.

For example, if the row player is considering cell `(r,c)`:
- let `L_t^(R,r)` be the set of row patterns for row `r` consistent with the row clue and current public row state
- define `p_t^(R,r)(z_(r,c)=1)` as the fraction of patterns in `L_t^(R,r)` where that cell is black

Then:
- choosing black gets score `Q_own = p`
- choosing X gets score `Q_own = 1-p`

This is easier to compute and more plausibly human-like than full-board exact inference.

### 21.4 First collaboration term in the bounded prototype

For the first prototype, define `B_partner` locally rather than globally.

Example approximation:
- if the acting player marks cell `(r,c)`
- recompute the partner’s compatible line patterns for the corresponding partner line
- measure how much the number of compatible partner-line patterns decreases

So if the row player acts on `(r,c)`, the partner term may be approximated by the reduction in ambiguity for column `c`.
If the column player acts on `(r,c)`, the partner term may be approximated by the reduction in ambiguity for row `r`.

A concrete local measure could be:

`B_partner_local = log(number of compatible partner-line patterns before action) - log(number of compatible partner-line patterns after action)`

This is not yet a full global partner uncertainty measure, but it is a usable first approximation.

### 21.5 First candidate model family

A minimal first set of models could be:

- `M0`: random over all unknown cells and legal marks
- `M1`: bounded individual model using only `Q_own`
- `M2`: bounded collaborative model using `Q_own + lambda * B_partner_local`

This would already allow meaningful first simulations and early model comparison.

However, if `M1` is implemented with:
- only certainty-1 candidate actions
- constant cost
- softmax over candidate actions

then `M1` may effectively reduce to stochastic tie-breaking among forced moves.

That is acceptable for a first engineering prototype, but it should be described honestly.
If a richer probabilistic individual model is desired, a later variant should allow graded candidate scores rather than only certainty-1 actions.

### 21.6 First output files to save

For each simulated or human trial, save:
- event log
- board state after each step
- candidate-action table for each step
- values of `Q_own`, `B_partner_local`, and chosen action rank

These outputs will make debugging and interpretation much easier.

---

## 22. Immediate questions to answer before coding further

These are the questions that should probably be answered first, in order.

1. What exact action space should the prototype allow?
2. Will the first solver be normative or bounded?
3. If bounded, will it be line-level only or include limited propagation across lines?
4. Will the partner-information term be global or line-local in the first prototype?
5. How will puzzle classes be generated or selected?
6. What fixed action budgets should be tested in simulation?
7. What exact outputs should every trial save by default?

If these seven questions are fixed, the rest of the prototype becomes much easier to organize.
