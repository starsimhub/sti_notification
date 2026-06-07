# Exp 22 — Sustainability coverage check under softened ANC ramp

**Question.** Under the softened ANC test-probability ramp
(`anc_probs[5:] = [0.70, 0.70]`, down from `[0.90, 0.95]`), do at
least 30 of 100 prior draws sustain syphilis with non-zero new
infections through 2030-2040 at agent-level resolution?

This is the **sustainability gate** before any further history
matching. See [`../21_trajectory_selection_9param/SUMMARY.md`](../21_trajectory_selection_9param/SUMMARY.md)
post-mortem for the diagnosis and [[feedback-calibration-guards]]
memory for why every model-structure change now goes through a
coverage check before HM.

**Motivation.** Exp 21's post-mortem revealed that under the
existing ANC ramp (0.50 → 0.90 → 0.95 across 2012-2040), zero
NROY draws produced new syph infections in 2030-2040 — the EMTCT
treatment cliff killed transmission in every draw. The ramp was
calibrated against assumed 90-95% EMTCT coverage by 2018, but
Zimbabwe's actual reported coverage is closer to 70%. Softening
the ramp is the upstream structural fix; this experiment tests
whether it works.

**Two upstream fixes both land in this experiment.**

**Fix A — ANC ramp softened** (`interventions.py` line 330):
`anc_probs = [0.20, 0.30, 0.40, 0.35, 0.50, 0.70, 0.70]` (down from
`[…, 0.90, 0.95]`). 70% 2018+ matches Zimbabwe's actual reported
EMTCT coverage and removes the treatment cliff we diagnosed in
exp 21.

**Fix B — `dt_scale=False` on `syph_symp_test`** (`interventions.py`
line 360-ish): the CSV `symp_test_prob_soc.csv` values are the
proportion of people with visible chancres who seek care during
their ~1-month symptomatic episode — i.e. they are already per-step
probabilities, not annual rates. The stisim default (`dt_scale=True`)
was dividing them by 12 at dt=month, making effective symptomatic
treatment of primary syph ~12× lower than intended. **Silent bug.**

Net effect of the two fixes on transmission: Fix A reduces ANC
treatment; Fix B increases symptomatic treatment. They partially
offset; the coverage check tells us which dominates.

**Plan.**
1. Both fixes are in `interventions.py` (committed alongside exp 22's
   scaffolding).
2. Generate 150 LHS prior draws across the now-12-parameter prior
   space from `priors.py`. New parameters added today (exp 22 scope):
   - `syph.p_symp_primary_f` ∈ (0.10, 0.60) — F chancre visibility
     (default `0.30`; large clinical uncertainty since most F primary
     chancres are internal).
   - `syph.p_symp_primary_m` ∈ (0.50, 0.95) — M chancre visibility
     (default `0.80`; less uncertain).
   - `syph_symp_test.rel_test` ∈ (0.30, 1.50) — care-seeking
     multiplier on the symptomatic syph testing pathway. Built-in
     `rel_test` parameter on stisim's STITest base class
     (`base_interventions.py:113`).
   Bumped from 100 to 150 draws to compensate for the higher
   dimensionality.
3. Run each draw at 10k agents, 1985-2040, single seed. ~30 min
   wall-clock at 24 workers.
4. Capture full time-series for every disease + syph new_infections
   + incidence so we can plot and audit.
5. Diagnostic outputs:
   - Per-draw sustainability flag: does the draw have non-zero
     new_infections in 2030-2040 AND prev_f at 2035-2040 ≥ 0.1%?
   - Per-target coverage: how many of 100 bracket each of the 10
     ZIMPHIA + STI targets within 50% of data?
   - Time-series plot (cf. exp 21 syph_dynamics_diagnostic), but
     for the full coverage cohort not just top 20.

**Configuration.**
- 100 LHS prior draws × 1 seed = 100 sims.
- 10k agents, 1985-2040 (extending to projection window).
- 24 workers, maxtasksperchild=10, JSONL append.
- `set_pars_local` includes the `time_to_undetectable` Dist-
  replacement special case (matches exp 19/20/21).

**Success criteria — the gate to exp 23.**
- **Primary:** ≥30 of 100 draws sustain syph through 2030-2040
  (non-zero mean new_infections in 2030-2040 AND
  prev_f_2035-2040 ≥ 0.001).
- **Secondary:** distribution of detect_15_64_f at 2016 across the
  sustaining draws — at least some should be in the ZIMPHIA band
  (data 1%, widened to 0.4-1.6%).
- **Tertiary:** non-syph targets (HIV, NG, CT, TV) still bracket
  data reasonably under the softened ramp. The ramp change only
  affects syph treatment so other diseases should be unaffected;
  this is a sanity check.

**Decision branches.**
- **If primary succeeds (≥30 sustain)** → close exp 22, proceed to
  exp 23 = HM with the new ramp, 9 parameters, 10 targets, plus
  the synthetic endemicity targets (`syph_detect_15_64_f_2010` and
  `_2020`, both at 0.010 ± 0.003) discussed today.
- **If primary fails (<30 sustain)** → don't go to HM. Diagnose
  further (treatment-side detectable clearing fix, soften ANC ramp
  further, examine p_symp_care, etc.) and re-coverage-check before
  any HM. Update memory if new structural insight surfaces.

**What this experiment does NOT do.**
- Does not run HM (that's exp 23).
- Does not reweight or compute ESS.
- Does not add new calibration parameters or new targets — only the
  intervention-side ramp adjustment.
- Does not invalidate exp 17-21 — those experiments' SUMMARY findings
  about HM convergence + the 19.6y time_to_undetectable anchor remain
  valid; what's invalidated is treating their outputs as projection-
  usable.
