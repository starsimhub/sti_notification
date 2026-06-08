# Exp 35 — Build the decision-analysis ensemble

**Question.** Exps 32-34 demonstrated that parameter-only calibration to
ZIMPHIA absolute prev is provably exhausted in 20 dims. The cluster of
sustained draws passing 5+/9 structural targets is the best the model
can do — sustained, FSW-concentrated, primary-driven, HIV-stratified,
but ~30-40% hot on absolute general-pop prev. With this ceiling
acknowledged, can we assemble ~100+ such draws into a robust ensemble
for the PN decision analysis?

**Plan.** Two-phase.

**Phase 1 — candidate discovery.** New 1500-draw LHS over the 20-prior
space, seed=43 (orthogonal to exp 34's seed=42). Single seed per draw.
Expected ~165 sustained AND 5+/9 draws based on exp 34's 11% rate.
Re-uses the analyzers already wired into model.py (HIV-stratified
coinfection + SyphTransmissionEvents). ~63 min wall at 24 workers.

**Phase 2 — ensemble re-run.** Filter Phase 1 results to:
- `sustained` is True (the non-negotiable: no decay-through-band draws)
- `n_pass >= 5` (structurally-correct cluster)

Re-run each filtered draw with **3 seeds** (offset starting at 100,000
to avoid collisions with Phase 1's `draw_idx * 1000` scheme). Each draw
now has 3 independent realizations; this stabilizes the small-N HIV
stratification numerators and gives stochastic variance for the
decision-analysis sensitivity step.

If Phase 1 yields fewer than 100 candidates at 5+/9, automatically
backfill from 4+/9 sustained draws until the candidate pool reaches
100 (logged in `outputs/ensemble_selection.json`).

**Outputs.**

- `outputs/phase1_results.jsonl` — 1500-draw single-seed results
- `outputs/phase1_priors.csv` — 20-dim LHS sample (seed=43)
- `outputs/ensemble_draws.csv` — selected candidate draws (~100-200)
- `outputs/ensemble_results.jsonl` — Phase 2 per-(draw, seed) results
- `outputs/ensemble_summary.csv` — per-draw means across 3 seeds
- `outputs/events/events_NNNN_seedM.json` — transmission events per
  (draw, seed)

**Success criteria.** ≥100 unique draws in the final ensemble, each
sustained and structurally correct on most/all of: FSW prev, primary
share, secondary share, HIV+/HIV- ratio. The ensemble spans a usable
range of absolute prev (likely nontrep_f median ~0.10-0.12, trep_f
median ~0.18-0.22) with parameter uncertainty captured across 20 dims.

## Why a fresh LHS instead of just re-running exp 34's candidates

Exp 34 yielded 32 sustained 5+/9 draws — substantially fewer than the
target ~100. To reach 100, we either (a) drop the threshold to 4+/9
(91 draws) at the cost of structural quality, or (b) sample more
parameter space. Going with (b) preserves structural quality and
gives a more diverse ensemble across the prior space.

The fresh seed (43) ensures the new draws are not a strict superset
of exp 34's seed=42 draws — we get genuinely new parameter
configurations. We could combine with exp 34's 32 draws as a small
sweetener at the end, but the cleanest framing is to use Phase 1
alone for ensemble selection.

## Acceptance

Once Phase 2 completes, the resulting ensemble + per-draw means is the
working dataset for the PN intervention analysis (exp 36+). The
absolute-scale gap is documented as a model limitation; intervention
effects are reported in relative terms.

## Forward reference

Exp 36 — PN intervention scoring on the ensemble. For each draw,
run the PN intervention configuration vs counterfactual, measure
the relative reduction in syph incidence / APO / cumulative cases
over 2030-2040. Aggregate distribution across the ensemble for the
decision-analysis posterior.
