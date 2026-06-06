# Exp 18 — Trajectory selection within exp 17's detectable-mapping NROY

**Question.** With exp 17's HM-converged NROY (0.99% of prior, 10
targets including `detectable_prevalence_f/m`), does Gaussian
pseudo-likelihood reweighting produce a usable posterior ensemble
that brackets all 10 targets — *including* the `syph_seroprev_f/m`
and `syph_anc` tails that exp 17 flagged as the residual diagnostic
problem (z-scores reaching +25–40σ in NROY)?

**Motivation.** Exp 17 left two known issues for downstream cleanup:

1. The NROY contains a meaningful population of draws that overshoot
   `syph_seroprev_f`, `syph_seroprev_m`, and `syph_anc` because the
   bayes_linear emulator for `syph_seroprev_f` never reached R² > 0.25
   across four feature-selection passes. Trajectory selection's
   per-sim likelihood weighting is the natural place to clean this up:
   draws that overshoot get small weights, draws inside the bracket
   get large weights, and the posterior pulls in regardless of what
   the emulator could or couldn't learn.
2. The active-syph targets (`detectable_f/m`) converged in HM via
   indirect constraint through `log_syph.beta_m2f`. Direct evaluation
   of the per-sim distance on these targets is the validation step —
   if the posterior brackets them under proper likelihood weighting,
   the exp 16 → exp 17 chain is complete.

This is the analogue of exp 13 (post-ANC-fix trajectory selection
within exp 09's NROY) but against the corrected target set and the
patched stisim that exposes `detectable`. Exp 13's verdict was
"bifurcates, ESS=7.3, unusable"; exp 17's pairplot shows the
bifurcation is gone under the detectable mapping. The expectation is
that this pass produces the first usable posterior ensemble in the
project.

**Plan.** Direct mirror of exp 13's setup with three deliberate diffs.

1. **NROY source.** `experiments/17_history_matching_detectable/nroy/hm_zim/wave8/nroy_samples.csv`
   (1000 draws, post-detectable-fix). Replaces exp 13's reference to
   exp 09's NROY.

2. **Target set.** Same 10 targets as exp 17 (HIV×2, NG, CT, TV,
   `detectable_f`, `detectable_m`, syph_seroprev_f, syph_seroprev_m,
   syph_anc). Coinfection targets stay dropped — `coinfection_stats`
   analyzer not yet patched. Likelihood widening: 2× std for non-syph,
   3× for syph (exp 13 convention).

3. **stisim branch.** `feat/syph-detectable-state` (commit 24bdf58)
   in `/home/robyn/stisim`. Must be checked out as the editable
   install before running.

**Configuration.**

- 1000 NROY draws × 1 seed = 1000 sims (matches exp 13).
- 10k agents, 1985–2025.
- 24 workers, `maxtasksperchild=10`, incremental JSONL writes —
  same memory-safe pattern as exp 13/17.
- `time_to_undetectable` **stays at the stisim default**
  (`lognorm_ex(5y, 5y)`). Per exp 17 README's rationale: expert
  input pending (Monday email), and exp 17's NROY didn't surface a
  late-latent reservoir problem big enough to force opening it.
- Pseudo-likelihood: **Gaussian** by default. Student-t robust
  variant (per Dan's calib-plugin feedback) reserved as a fallback
  if Gaussian's ESS is low *and* the residuals show heavy tails.

**Success criteria.**

- **Primary:** ESS/N > 0.05 (≥ 5% efficiency, exp 13's threshold)
  *and* the posterior predictive brackets all 10 targets within ±2σ
  widened bands. Exp 13 hit ESS=7.3 (0.7%) and bifurcated — this
  experiment needs to clear that floor by a meaningful margin.
- **Secondary:** Posterior predictive on `detectable_f/m`
  centred on data, not just bracketing — i.e. the calibration found
  the basin, not just kept some draws compatible with it.
- **Tertiary:** Posterior marginals tighter than exp 17's NROY
  marginals (which were already unimodal — a tightening should be
  visible on `log_syph.beta_m2f` particularly).
- **Diagnostic:** Posterior predictive on `prevalence_f` (not a
  target — the full-stage prevalence) gives the invisible-reservoir
  sanity check from exp 16. Expect posterior median around 6–8%
  with detectable_f median around 1%, consistent with the WHO Fig 7
  ratio.

**What this experiment does NOT address.**

- Coinfection targets — still deferred to a later experiment after
  the `coinfection_stats` stisim patch.
- Multi-seed within-draw averaging — single seed per draw matches
  exp 13 for clean comparison. If ESS is uncomfortably low and the
  residual is single-seed noise, can re-run with 3 seeds; if the
  residual is structural, that won't help.
- `time_to_undetectable` calibration — still flagged for expert input.
- Decision analysis — exp 19+ once a usable posterior exists.

**Resumability.** JSONL append per sim. Kill and restart picks up
where it left off (the `--reweight` flag skips simulation entirely
and re-derives weights from the JSONL).
