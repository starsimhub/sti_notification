# Exp 20 — History matching with time_to_undetectable opened (9 parameters)

**Question.** With `time_to_undetectable` opened as a 9th calibration
parameter (prior anchored from exp 19's sweep at 10–30y), can HM
converge to an NROY where the 9 parameters jointly bracket all 10
ZIMPHIA targets on the corrected 15-64 denominator — fixing the
structural ratio problem that broke exp 18's posterior at ESS=1.2%?

See [`../19_time_to_undetectable_sweep/SUMMARY.md`](../19_time_to_undetectable_sweep/SUMMARY.md)
for the prior anchor, [`../18_trajectory_selection_detectable/SUMMARY.md`](../18_trajectory_selection_detectable/SUMMARY.md)
for why the existing 8-parameter NROY isn't enough, and
[`../17_history_matching_detectable/SUMMARY.md`](../17_history_matching_detectable/SUMMARY.md)
for the HM protocol this experiment mirrors.

**Motivation.** Exp 18 trajectory selection failed structurally —
ESS=4.8 / 418 = 1.2%, not because the calibration method was
inadequate, but because the model couldn't simultaneously bracket
detectable_f, seroprev_f, and ANC under the default
`time_to_undetectable = lognorm(5y, 5y)`. Exp 19's sensitivity sweep
showed that opening this parameter to ~20y collapses the sero/detect
ratio from ~30× to ~3× (matching the data) and brings absolute
detect_f from 0.04% to 1.04% (matching the data target). This
experiment runs the calibration-grade HM under the new parameter
space.

**Plan.** Direct mirror of exp 17 with three deliberate diffs.

1. **Add `syph.time_to_undetectable` as the 9th parameter**, prior
   `uniform(10, 30)` years. Linear (not log) since the range is
   narrow and the parameter is naturally interpretable in years.
   Width matches exp 19's "plausible range 10–30y" finding. May
   widen if the Monday expert email response suggests it.

2. **Targets use the corrected 15-64 all-adult denominator** for
   syph detect / sero / ANC. HIV / NG / CT / TV unchanged (their
   targets are population-wide and weren't affected by the
   denominator fix). Coinfection targets still dropped pending the
   `coinfection_stats` stisim patch.

3. **Restart from wave 1.** Two reasons exp 17's NROY isn't
   transferable:
   - The 9th parameter shifts the random-number sequence (same as
     why exp 17 restarted after the detectable patch).
   - The stisim 15-64 results patch (`7c2feb8`) is on the disease
     module, so even at fixed parameters the sim produces slightly
     different output traces (cond_prob denominator change).

**Configuration.**

- 9 parameters (`priors.py`, extended):
  - 5 disease betas: HIV, syph, NG, CT, TV.
  - 2 network: `prop_f0`, `m1_conc`.
  - 1 FSW: `dur_sw`.
  - 1 new: `syph.time_to_undetectable`.
- 10 targets (15-64 denominator on syph; coinfection dropped).
- 1000 samples per wave, 10k agents, 1985–2025.
- Up to 8 waves, same emulator/implausibility settings as exp 17.
- 24 workers, maxtasksperchild=10, `pool.imap` (ordered — per
  `[[feedback-mp-pool-ordering]]` memory; the engine joins by
  positional index).
- Resumable per wave via the `history_matching` package's checkpoint
  mechanism.
- Estimated wall-clock: ~30 min/wave × 8 ≈ 4 hr total (same per-sim
  cost as exp 17; the new parameter adds one random draw per agent
  at late-latent entry).

**Stisim version.** `feat/syph-detectable-state` at commit `7c2feb8`
or later (15-64 results required) in `/home/robyn/stisim`.

**Success criteria.**

- **Primary:** NROY at wave 8 (or earlier convergence) contains
  draws bracketing all 10 targets within ~2 widened standard
  deviations. The 0.99% / 0.0099 fraction-of-prior that exp 17
  achieved on 8 parameters is a reasonable target here on 9
  parameters — a slightly larger NROY fraction is expected because
  the additional dimension adds volume.
- **Secondary:** Posterior emulator R² for `syph_seroprev_15_64_f`
  comparable to or better than exp 17 (which struggled at R²=0.18–
  0.25 because the constraint was structurally infeasible). Now
  that the model can produce sero/detect at the right ratio, the
  emulator should fit cleanly — ideally R² > 0.5 for syph after a
  few waves.
- **Tertiary:** `time_to_undetectable` posterior marginal lands
  inside the [15, 25] band that exp 19 flagged as the cohort-
  consistent sweet spot. If the marginal pins at 10y (lower bound)
  or 30y (upper bound), prior needs widening and exp 20 needs a
  re-run.
- **Diagnostic:** invisible-reservoir ratio (prevalence_f /
  detectable_15_64_f) on NROY draws — sanity check that the
  posterior reproduces the WHO Fig 7 mechanism, with most NROY
  draws falling in a 3–5× band.

**What this experiment does NOT address.**

- Coinfection targets — deferred to exp 22+ after `coinfection_stats`
  patch.
- Treatment-side `detectable` clearing (WHO Fig 7 mechanism for
  treated early-stage cases dropping non-trep titre) — deferred,
  unchanged from exp 17/18/19.
- MSM dynamics — deferred per
  [[project_syph_extinction_structural]]: not a candidate structural
  fix for the calibration; the 4 stisim MSM module bugs documented
  in `../../stisim_msm_bug_reports.md` are blocking but out of
  scope here.
- The age-OR over-prediction diagnostic from exp 19 — informative
  signal about late-latent accumulation but not a calibration
  target.
- Decision analysis — exp 21+ once a usable posterior exists.

**Resumability.** History matching package writes per-wave
checkpoints. Kill at any wave boundary and restart picks up cleanly.

**Pre-flight check.** Before launching, confirm:
- `priors.py` includes `syph.time_to_undetectable` with bounds
  (10, 30), `log_scale=False`.
- stisim `feat/syph-detectable-state` ≥ `7c2feb8` is the active
  editable install (`detectable_prevalence_15_64_f` must exist in
  sim results).
- `set_pars_local` handles `time_to_undetectable` by *replacing*
  the Dist (so std tracks mean) rather than calling `.set(mean=…)`
  (which would leave std at the original 5y).
