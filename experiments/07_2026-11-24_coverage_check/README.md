# Exp 07 coverage check (prior predictive)

**Question.** Before the exp 07 recalibration: under the exp 07 priors, can the syphilis-free model reach the fitted targets (HIV 15–49 prevalence 2010–20; NG/CT/TV prevalence and incidence 2015–25)?

**Why now.** This is the first run with the gonorrhoea treatment fix: seed infections no longer inherit a NaN `rel_treat`, so NG treatment now cures. With the fix, NG prevalence at default parameters fell from about 4.7% to 1.4%, so exp 06's sense of where the priors put NG no longer applies.

**Method.** This is the quick coverage check:
- 100 draws from the exp 07 LHS (seed 47, the first 100 of 500), 1 seed per draw.
- 10k agents, 1985–2026.
- `run.py` reuses exp 07's sim builder, priors, extractors and target bands unchanged.
- `plot.py` overlays the data (`data/zimbabwe_sti_data.csv`, `data/zimbabwe_hiv_calib.csv`) and target bands on the prior-predictive trajectories, and compares each scalar target with its prior-predictive distribution.

**Environment.** `stinotif` (stisim 1.5.7 + NG seed fix, branch `v1.5.7-ngseed`; starsim 3.3.2).

**Pass criteria.**
- Every target band overlaps the 5–95% range of the prior predictive.
- The data lie inside the trajectory envelope over the fit windows.
- Note any parameter piled against a prior edge among draws that land near the data.

**Run.**
```bash
conda activate stinotif; export PYTHONPATH=$PWD   # from repo root
N_WORKERS=50 python experiments/07_2026-11-24_coverage_check/run.py
python experiments/07_2026-11-24_coverage_check/plot.py
```
