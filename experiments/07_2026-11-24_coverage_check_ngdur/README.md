# Exp 07 coverage check, with the NG duration prior

**Question.** With NG's untreated asymptomatic duration opened (`ng.dur_asymp2clear`, 3–18 months, log-uniform, both sexes) and NG beta's floor lowered to 0.05, can NG prevalence and NG incidence now be in band together? Does coverage of the other targets hold?

**Why.** [`../07_2026-11-24_coverage_check/SUMMARY.md`](../07_2026-11-24_coverage_check/SUMMARY.md) found NG prevalence and incidence never jointly in band at default durations: 0 of the 13 draws with prevalence in band. Model NG infections cleared about 1.5–2× faster than the data's prevalence/incidence pair implies.

**Method.** Same as that check: 100 draws from exp 07's LHS (seed 47, now 9 dimensions), 1 seed per draw, 10k agents, 1985–2026. `run.py` and `plot.py` are copied unchanged. Env `stinotif`.

**Pass criteria.** Some draws have NG prevalence and NG incidence in band together, and the other targets stay marginally covered.

**Run** (from the repo root):
```bash
N_WORKERS=50 python experiments/07_2026-11-24_coverage_check_ngdur/run.py
python experiments/07_2026-11-24_coverage_check_ngdur/plot.py
```
