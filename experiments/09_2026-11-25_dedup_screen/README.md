# Exp 09 — coverage check and per-pathogen screen on the corrected demography

**Question.** With AIDS deaths deduplicated from background mortality and migration on, does every target stay reachable under exp 07's (wide) priors? Where does each pathogen's beta put its own target in band? That gives the per-pathogen pools for building mix-and-match draws.

**Why.** The exp 07 targets separate by pathogen: each prevalence has R² 0.94–1.00 on its own parameters, and the network parameters add at most 0.02. So an LHS over all parameters at once wastes nearly every draw ([exp 07 SUMMARY](../07_2026-11-24_no_syph_calibration/SUMMARY.md)). The demography fix changes HIV mortality and the population, so exp 07's in-band ranges can't be reused.

**Method.**
- 300 draws from exp 07's LHS (seed 47; 9 priors, unchanged), 1 seed per draw, 10k agents, 1985–2026.
- `run.py` calls exp 07's `main()` with its output directory redirected.
- `plot.py` is the coverage plot from the first coverage check.
- Env `stinotif`.

**Next step (not in this folder).** Pool draws in band for each pathogen:
- HIV: `hiv.beta_m2f`, `hiv.rel_init_prev`
- NG: beta and duration
- CT: beta
- TV: beta

Combine them with network parameters taken from any draw, and re-simulate the combinations at K=5.

**Run** (from the repo root):
```bash
N_WORKERS=150 python experiments/09_2026-11-25_dedup_screen/run.py
python experiments/09_2026-11-25_dedup_screen/plot.py
```
