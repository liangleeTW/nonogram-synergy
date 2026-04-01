- Algorithm to create nonograms i want, criteria
  1. no trivial moves(or not so many trivial moves)
  2. 
- Filter nonograms that doesn't fit criteria


current difficulty criteria doesn't suit for latent

- Add the collaboration term by estimating partner uncertainty before and after each candidate move, then compute partner information gain and include a collaboration weight `lambda` in the utility.
- Expand the event log so each move stores model-side quantities needed for analysis, such as candidate set size, chosen action utility, own-certainty score, partner-information score, and remaining uncertainty.
- Add multiple baselines in code, not just the current line solver: at minimum random, individual-certainty, bounded line-solver, and collaborative-information agents with a shared interface.
- Build evaluation functions that compare agents under the same move budget using metrics aligned with the note, such as uncertainty reduction, correct cells added, coordination efficiency, and not only full completion.
- Add a fitting/analysis path for human data or replay logs so the code can test whether observed moves are better explained by the individual model or the collaborative model.
- Add small reproducible test cases to verify core math and behavior: hypothesis updates, entropy calculations, utility calculations, softmax probabilities, and partner-information gain on toy puzzles.
- Keep the exact normative version and the bounded approximation separate in the codebase so they can be compared cleanly instead of being mixed into one solver.


# Questions needed to be answered: 

- Add `cell_accuracy` directly into `analyze_logs.py`.
- Create a separate latent-evaluation scoring file instead of reusing deterministic difficulty.
- Make uninformed fallback optional and explicitly named.
- Sweep `lambda` next, because the current collaborative latent model still uses utility fallback a lot.
- Update the README and model note to document:
  - `latent_ind.py`
  - repo-local `outputs/`
  - no-pass latent behavior
  - fallback logic
