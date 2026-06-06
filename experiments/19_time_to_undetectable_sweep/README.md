# Exp 19 — Sensitivity sweep on `time_to_undetectable`

**Question.** At what value of the `time_to_undetectable` mean does
the model's sero/detect ratio for an endemic Zimbabwe-like
equilibrium reach the data ratio of ~3×?

A defensible answer here anchors the prior for opening
`time_to_undetectable` as a 9th calibration parameter in exp 20's
re-run of history matching. Without this anchor, the prior would
have to span the full plausible biological range (~1y to ~50y) and
HM would burn waves searching ground exp 19 can map directly.

**Motivation.** Exp 18 closed with calibration-failed ESS=4.8 and
a sharp diagnosis: under the stisim default
`time_to_undetectable = lognorm(5y, 5y)`, the model produces an
*alive-pool minimum* sero/detect ratio of ~4× and a posterior-mode
ratio of ~30×. Data sits at 3×. The model cannot bracket detectable_f
AND seroprev_f simultaneously without changing this parameter.

See [`../18_trajectory_selection_detectable/SUMMARY.md`](../18_trajectory_selection_detectable/SUMMARY.md)
section "The model's sero/detect ratio has a structural ceiling" and
the `sero_detect_ratio.png` diagnostic figure for the framing.

**Plan.** A small grid sweep, not a full calibration pass.

1. **Pick a representative subset of NROY draws (n=15).** Draws are
   sampled from `experiments/17_history_matching_detectable/nroy/hm_zim/wave8/nroy_samples.csv`:
   - Top 5 by exp 18 posterior weight (the "best fit under default
     time_to_undetectable" corner — currently 30× too high on
     sero/detect ratio).
   - 5 draws from the alive pool with the *lowest* sero/detect ratio
     (the closest the default model can get to data — currently ~4×).
   - 5 draws chosen uniformly across the NROY (control — checks
     that the sweep response is consistent across NROY, not
     idiosyncratic to a particular parameter corner).
2. **Sweep grid: 5 values of `time_to_undetectable` mean.** 2y, 5y,
   10y, 20y, 30y. Standard deviation tracks mean (`lognorm_ex(m, m)`)
   for sensitivity-on-mean.
3. **For each (draw, mean) pair, run one sim** at 10k agents,
   1985–2025, single seed. Extract the 10 exp 18 targets plus the
   full prevalence_f / detectable_f / seroprev_f at 2016.
4. **Plot: sero/detect ratio vs `time_to_undetectable` mean.** One
   line per draw. Look for the value where the lines cross the
   y=3× data line. Also plot absolute detect/sero/ANC against the
   grid for verification that the trade-off isn't shifting the
   absolute levels into a bad place.

**Configuration.**

- 15 draws × 5 grid points × 1 seed = **75 sims total.**
- 10k agents, 1985–2025.
- 24 workers, JSONL append. Same memory profile as exp 13/17/18.
- Each sim ~30s wall-clock; 75 sims / 24 workers ≈ 4 passes ×
  30s ≈ **~2 min wall-clock** (negligible compared to the
  ~30 min exp 18 took).

**Success criteria.**

- **Primary:** At least one grid value brings the sero/detect ratio
  on a majority of draws to within [2.5×, 4×]. If yes, the
  bracketing prior for exp 20 is anchored. If no, the structural
  problem is deeper than `time_to_undetectable` and we need to
  reconsider whether the model's late-latent dynamics are right at
  all.
- **Secondary:** Absolute detectable_f at the "right ratio" grid point
  is in [0.005, 0.020] (around data ± reasonable widening). If
  ratio is right but detectable is still 10× too low, then matching
  the data needs both `time_to_undetectable` *and* `log_syph.beta_m2f`
  to move — a joint move HM should handle.
- **Tertiary:** Consistency across the 3 draw cohorts (top-weight,
  low-ratio, uniform). If the sweep response is monotone and
  consistent, anchor confidently; if the cohorts diverge, surface
  the interaction in exp 20's parameter design.

**What this experiment does NOT do.**

- Does not re-run HM or trajectory selection.
- Does not vary `time_to_undetectable` std relative to mean
  (sensitivity-on-mean only).
- Does not address treatment-side detectable clearing (deferred
  unchanged from exp 16/17/18).
- Does not produce a posterior — only a deterministic sweep table
  for prior elicitation.

**Resumability.** JSONL append per sim — same pattern as exp 13/17/18.
Kill and restart picks up unfinished (draw, mean) pairs.

**Open implementation question.** The patched stisim wires
`time_to_undetectable` into `SyphPars.__init__` as an
`ss.lognorm_ex(...)` Dist. Setting via `set_pars_local` should work
if Dist has a `.set(mean=...)` method that updates the parameterised
mean. To be verified during run.py drafting.
