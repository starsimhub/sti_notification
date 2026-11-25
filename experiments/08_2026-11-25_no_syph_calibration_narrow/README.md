# Exp 08 — exp 07 calibration with narrowed transmission betas

**Question.** Exp 07 (500 LHS draws × K=5) gave only 4 acceptable draws (9 at `ACCEPT_TOL=1.0`). Each pathogen's prevalence is set almost entirely by its own beta, so a draw passes only when all four betas land in their narrow in-band ranges together. If the betas are narrowed to the ranges where exp 07 put each target in band, does a same-sized LHS give at least 30 acceptable draws?

**Method.** Exp 07's `run.py`, unchanged apart from four priors and the output directory. Other priors, targets, weights, `ACCEPT_TOL=0.5` and `MIN_SEEDS_SUSTAINED=4` are unchanged.

| prior | exp 07 | exp 08 | exp 07 in-band range (min / median / max) |
|---|---|---|---|
| hiv.beta_m2f | 0.005–0.030 | 0.010–0.022 | 0.011 / 0.016 / 0.021 |
| ng.beta_m2f (log) | 0.05–0.60 | 0.05–0.40 | 0.057 / 0.126 / 0.390 |
| ct.beta_m2f (log) | 0.05–0.50 | 0.06–0.17 | 0.069 / 0.108 / 0.153 |
| tv.beta_m2f (log) | 0.02–0.60 | 0.05–0.17 | 0.056 / 0.094 / 0.156 |

Run: 500 draws × K=5, 10k agents, 1985–2030, env `stinotif`.

```bash
N_DRAWS=500 N_WORKERS=150 python experiments/08_2026-11-25_no_syph_calibration_narrow/run.py
```
