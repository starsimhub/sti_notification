# Exp 38 — Recalibration with baseline PN

**Question.** Re-run the calibration with three changes:

1. **Baseline partner notification** is always on, with stratified
   rates: stable partnerships 20%/{F:80%, M:50%}, casual 10%/{F:50%,
   M:25%}. These rates are also opened as priors.
2. **total_pop=8.7e6** in `make_sim` so per-agent count outputs scale
   to absolute Zimbabwe-population numbers (previously a presentation
   bug — demographics CSV in thousands but starsim read as raw, off
   by ~1000×).
3. **18-dim prior space.** Dropped 4 weak priors from exp 34's
   correlation analysis (`syph.rel_trans_latent_half_life`,
   `structuredsexual.m1_conc`, `structuredsexual.f1_conc`,
   `structuredsexual.fsw_mf_conc_mult` — all max|r|<0.20 against
   sustained-cluster metrics). Added 2 PN priors
   (`pn.p_notify_stable`, `pn.p_notify_casual`).

**Plan.**

- Phase 1: 1500 LHS draws over 18 priors, seed=44 (fresh, orthogonal
  to exps 35/36's seed=43). Single seed each. ~70 min wall.
- Filter: sustained AND n_pass ≥ 5. Backfill from 4/9 sustained if
  fewer than ~100.
- Phase 2: re-run each selected candidate with 3 seeds. ~70 min wall.
- Output: per-(draw, seed) records + per-draw seed-means; new working
  ensemble for the publication-figure run and downstream PN scenarios.

**Expected total wall time:** ~2.5 hr.

**Success criteria.** ≥100 robust draws (sustained 3/3 across 3 seeds
AND mean n_pass ≥ 4), with closer-to-data absolute prev than exp 36's
ensemble — the drift check on 6 representative draws showed baseline PN
systematically cools all prev metrics by 5-30%.

## Open questions for after this lands

- Does the new ensemble still miss HIV trep ratio in [3, 6]? Drift
  showed median ratio ~4.8 across drift-check draws — should now sit
  comfortably in band.
- Are p_notify_stable and p_notify_casual identifiable? Phase 1
  correlations will tell us if the LHS gives signal here or if these
  parameters wash out.

## Forward reference

After this lands:
1. Re-run exp 37-style data extraction on the new ensemble with
   `prevalence_15_49` in the extraction list (the only thing we still
   need for the HIV calibration check that was missing).
2. Regenerate publication figures.
3. Open PN-intervention scenarios off the new baseline.
