# Exp 02 — Coverage check: syphilis seeding and config fix

**Question.** Exp 01 showed syphilis extinct in all 100 prior draws. Three
root causes were identified. Does the model now sustain syphilis and bracket
the observed active prevalence data (~2–3% from Zimbabwe surveys) after all
three are resolved?

**Fixes applied relative to exp 01:**

1. *Missing seed files.* `init_prev_syph.csv` and `init_prev_latent_syph.csv`
   ported from `syph_dx_zim/data/`. `rel_init_prev=0.2` set in `model.py`
   (fixed, matches `syph_dx_zim`).

2. *Syphilis module config misaligned with calibrated model.* `model.py`
   updated to match the `syph_dx_zim` configuration:
   - `rel_trans_primary=5`, `rel_trans_secondary=1`, `rel_trans_latent=0.1`
   - `rel_trans_latent_half_life=months(6)` (was `years(1)`)
   - `beta_m2c=0.075` (was `1.0`)
   - `p_symp_primary=[0.3, 0.8]`, `anc_detection=1.`

3. *Prior ceiling too low.* `syph.beta_m2f` upper bound widened from 0.20 to
   0.35 — aligns with the `syph_dx_zim` Optuna search range.

4. *STIsim 1.5.5 API change.* In 1.5.2 `active_prevalence` tracked total
   seropositive prevalence; in 1.5.5 it tracks only primary + secondary (near-zero
   in endemic equilibrium). The uncommented line was also missing. Fix: use
   `syph.prevalence` (total infected among sexually active adults 15–50) as the
   calibration target — this is what the ZIMPHIA Zimbabwe data (~2%) represents.
   Plot/run scripts updated accordingly.

**Plan.** Identical 100-draw prior predictive check: n_agents=5000, 1985–2025,
no PN, no FetalHealth. NG/CT/TV/HIV panels expected to be unchanged.

**Success criteria.** Syphilis active prevalence trajectories bracket the
Zimbabwe data points. Extinction across all draws would indicate further
model misspecification. If trajectories bracket but predominantly sit below
the data, the `rel_init_prev` or beta prior may need widening further.
