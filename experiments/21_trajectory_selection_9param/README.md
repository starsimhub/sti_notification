# Exp 21 — Trajectory selection within exp 20's 9-parameter NROY

**Question.** With exp 20's 9-parameter HM-converged NROY (0.91% of
prior, 10 targets on the 15-64 denominator, `time_to_undetectable`
opened and centred at 19.6y), does Gaussian pseudo-likelihood
reweighting produce a usable posterior ensemble with ESS > 5% that
brackets all 10 targets — including `syph_seroprev_15_64_f/m` and
`syph_anc`, which had wide z-tails in NROY?

See [`../20_history_matching_9param/SUMMARY.md`](../20_history_matching_9param/SUMMARY.md)
for the NROY, [`../19_time_to_undetectable_sweep/SUMMARY.md`](../19_time_to_undetectable_sweep/SUMMARY.md)
for the parameter anchor, and [`../18_trajectory_selection_detectable/SUMMARY.md`](../18_trajectory_selection_detectable/SUMMARY.md)
for what we're trying to fix (ESS=1.2% structural failure).

**Motivation.** Exp 18 closed with ESS=4.8 / 418 = 1.2% — calibration
failed — because the model could not simultaneously bracket
detect_f, sero_f, and ANC under default `time_to_undetectable = 5y`.
Exp 19 sweep + exp 20 HM both confirm that opening
`time_to_undetectable` and setting it near 20y removes the structural
ceiling. This experiment is the calibration-closing step: does the
weighted posterior now produce a usable ensemble?

This is the analogue of exp 18 but on the corrected NROY +
9-parameter space.

**Plan.** Direct mirror of exp 18 with three deliberate diffs.

1. **NROY source.** `experiments/20_history_matching_9param/nroy/hm_zim/wave8/nroy_samples.csv`
   (1000 draws, 9 parameters). Replaces exp 18's reference to exp 17.

2. **Targets.** Same 10 targets as exp 20 (HIV×2, NG, CT, TV,
   `syph_detectable_15_64_f/m`, `syph_seroprev_15_64_f/m`,
   `syph_anc_2000_2015`). Likelihood widening: 2× std for non-syph,
   3× for syph (exp 18 convention).

3. **9-parameter handling.** `set_pars_local` must special-case
   `time_to_undetectable` by *replacing* the Dist (so std tracks
   mean) rather than calling `.set(mean=…)`. Same handler as exp 20.

**Configuration.**

- 1000 NROY draws × 1 seed = 1000 sims.
- 10k agents, 1985–2025.
- 24 workers, maxtasksperchild=10, incremental JSONL writes — same
  memory-safe pattern as exp 13/17/18/20.
- Pseudo-likelihood: **Gaussian**, with widened stds matching exp 18
  (2× non-syph, 3× syph).
- Extinction filter: `syph_detectable_15_64_f_2016 > 0.001` (matches
  exp 18; reported separately per project memory
  [[project-syph-extinction-structural]]).

**Success criteria.**

- **Primary:** ESS/N > 0.05 (≥ 5% efficiency, exp 13/18 floor). Exp
  18 hit 1.2%; this experiment needs to clear 5% by a meaningful
  margin to qualify as a usable posterior.
- **Secondary:** Posterior predictive brackets all 10 targets within
  ±2 widened sds. Detectable_f/m should now centre on data
  (~1%/~0.6%) rather than undershoot to ~0.001 as in exp 18.
- **Tertiary:** Posterior marginal on `time_to_undetectable` lands
  inside [15, 25] (matching the sweep + HM concordance).
- **Diagnostic:** Sero/detect ratio in the posterior. Data is 3×.
  Posterior should now be in the 2.5–5× band, not the 30× corner
  exp 18 was driven into.

**What this experiment does NOT address.**

- Coinfection targets — still deferred pending stisim
  `coinfection_stats` patch.
- Multi-seed within-draw averaging — single seed per draw matches
  exp 18 for clean comparison. If ESS is uncomfortably low and the
  residual is single-seed noise, can re-run with 3 seeds.
- Treatment-side `detectable` clearing — deferred unchanged.
- MSM dynamics — deferred per [[project-syph-extinction-structural]].
- The detectable_m emulator noise residual from exp 20 — would have
  affected NROY shape but trajectory selection bypasses the emulator
  entirely by evaluating per-sim likelihood directly.
- Decision analysis — exp 22+ once posterior is usable.

**Resumability.** JSONL append per sim. `--reweight` flag skips
simulation and re-derives posterior from existing JSONL.

**Pre-flight check.** Before launching, confirm:
- stisim `feat/syph-detectable-state` ≥ `7c2feb8` (active editable
  install).
- exp 20's NROY csv exists at the expected path.
- `priors.py` has the 9th parameter `syph.time_to_undetectable` with
  bounds (10, 30).
