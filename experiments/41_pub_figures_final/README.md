# Exp 41 — Publication figures from the exp 40 final ensemble

**Question.** Regenerate the publication figures (HIV/STI time series,
syph time series, syph stage definitions, syph age × sex 2016) from
the 200-draw robust ensemble produced by [exp
40](../40_final_recalibration/SUMMARY.md). Confirms the HIV calibration
win visually and serves as the baseline reference for downstream
PN-intervention scenarios.

**Plan.**

- Fork [exp 39](../39_pub_figures_baseline_pn/README.md)'s pipeline
  (same `run.py` + `plot.py`, repointed to exp 40 outputs).
- 200 draws × 3 seeds = 600 sims, ~30 min wall.
- Same time-series + 2016/2020 snapshot extraction; same 5-figure
  output set.

**Success criteria.** All 5 figures regenerate. HIV time series tracks
UNAIDS (both whole-pop and 15-49 with ZIMPHIA overlay). Syph figures
show the unchanged-from-exp-39 absolute-prev overshoot (now documented
as a structural ceiling in exp 40 SUMMARY, not a calibration miss to
fix).

**Expected wall time:** ~30 min.

## Forward reference

After this lands: manuscript figure set is ready. PN-intervention
scenarios (exp 42+) overlay onto this baseline.
