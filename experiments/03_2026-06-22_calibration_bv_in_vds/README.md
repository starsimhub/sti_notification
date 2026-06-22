# Exp 03 (2026-06-22) — calibration re-fire with BV-in-VDS

**Question.** Exp 02's 26-draw per-disease-sustaining ensemble was calibrated
against the pre-BV-in-VDS model. Commit `169adc5` then routed symptomatic BV
through VDS care (`SimpleBV` + `bv_care` clause in
`interventions.seeking_care_vds`), which adds care-seeking volume for some
agents and shifts the unnecessary-treatment rate up. Does re-firing the same
LHS sweep against the BV-in-VDS model produce a comparable ensemble, and how
much do the calibrated betas shift?

**Plan.** Identical to exp 02 — institutional LHS pipeline at
[calibration/artifacts/scripts/run_ensemble.py](../../calibration/artifacts/scripts/run_ensemble.py),
17 priors from [priors.py](../../priors.py), per-disease sustainability filter
in `_pipeline.extract_calibration_summary`, same LHS seed (45) for direct
draw-by-draw comparability with exp 02.

1. **Phase 1** — 500-draw LHS (half of exp 02 to halve wall), single seed each. Writes
   `outputs/phase1_results.jsonl` with per-disease sustainability flags
   (`sustained_hiv`, `sustained_syph`, `sustained_ng`, `sustained_ct`,
   `sustained_tv`) and late-window diagnostics.
2. **Phase 2** — re-run candidates (sustained AND n_pass ≥ 5) at 3 seeds,
   targeting ~50 draws.
3. **Selection** — sustained 3/3 AND mean n_pass ≥ 4. Output:
   `outputs/draws_used.csv` (the new active calibration baseline if it
   passes review).

## How to run

From the repo root, in the `starsim` conda env:

```bash
conda run -n starsim python experiments/03_2026-06-22_calibration_bv_in_vds/run.py
```

Expected wall time on 60 cores (extrapolated from exp 02's actual log:
phase 1 = 9616 s for 1000 sims, phase 2 = 1367 s for 150 sims):
- Phase 1: ~80 min (500 sims, half of exp 02)
- Phase 2: ~25 min (≤150 sims, same as exp 02)
- Total: ~1.5–2 h.

## Success criteria

- Phase-1 sustained pass rate within a factor of 2 of exp 02 (exp 02
  selected 26/1000 = 2.6% through both phases; this run has half the
  LHS budget, so expect ~10–15 retained at the same rate). If pass
  rate collapses, BV edit is structurally important — re-fire at full
  budget after prior tuning.
- Phase-2 ensemble size ≥ 20 draws. Exp 02 got 26; aim for similar.
- Distribution of calibrated betas: report the median shift per parameter
  vs exp 02 in `SUMMARY.md`.
- All five STIs sustain in 3/3 seeds for every retained draw.

## Next

- If ensemble lands cleanly: replace exp 08's `DRAWS` with this run's
  `outputs/draws_used.csv` and re-run the PN × bundled-prevention sweep.
  Diff ladder shape vs exp 08's first pass.
- If not: investigate which disease's sustainability rate fell (likely
  NG/CT, since BV-in-VDS routes more agents through unnecessary tx for
  those pathogens).
