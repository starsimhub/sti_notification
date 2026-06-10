# Exp 03 — Publication figures from the Fix C 169-draw ensemble

**Question.** Regenerate the 5 publication figures from
[exp 02](../02_full_recalibration_fixc/SUMMARY.md)'s 169-draw robust
ensemble — direct analog of the old `archive/calibration-2026-06`
exp 41. Confirms what the Fix C ensemble looks like visually
(HIV + syph + NG/CT/TV), produces the figure set that the new
manuscript baseline references, and produces the slim quantile
parquets that get curated into `calibration/artifacts/` on the
release PR.

**Plan.**

- Run `calibration/artifacts/scripts/extract_summary.py` against
  exp 02's `draws_used.csv` to re-simulate 169 × 3 = 507 sims and
  produce time-series + age × sex snapshot quantile parquets.
- Run `calibration/artifacts/scripts/plot_figures.py` to render the
  5 publication figures.
- 60 workers; ~12 min wall.

**Success criteria.** All 5 figures regenerate. HIV stays in band on
both denominators. Syph absolute prev sits where the exp 02 scorecard
predicts (trep+ ~23%, nontrep+ ~13%) — the structural ceiling
re-confirmed visually. Stage breakdown internally consistent.

**Expected wall time:** ~12 min on 60 workers.
