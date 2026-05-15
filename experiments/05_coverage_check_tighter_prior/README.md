# Exp 05 — Coverage check: tighter syphilis priors

**Question.** Exp 04 showed 7/100 draws sustain syphilis, with
`syph.beta_m2f` as the strongest predictor (sustaining mean 0.16 vs
extinct 0.09). The log-uniform prior (0.01–0.35) concentrates mass in
the low range where syphilis goes extinct. The `syph_dx_zim` posterior
for `beta_m2f` was 0.15–0.22 and `rel_trans_primary` was 6.9–9.7. Does
tightening both priors — informed by but wider than the `syph_dx_zim`
posterior — produce a coverage check where syphilis sustains?

**Plan.** Changes to `priors.py`:
- `syph.beta_m2f`: floor raised 0.01→0.10 (still below syph_dx_zim
  5th percentile of 0.15; ceiling stays at 0.35).
- `syph.rel_trans_primary`: floor raised 3→5 (below syph_dx_zim
  5th percentile of 6.9; ceiling stays at 10).

No model changes. Same 100-draw prior predictive check.

**Success criteria.** >30/100 draws sustain syphilis above 0.5% by
2020–2025 and trajectories bracket the ~1.7–2.2% data. All other
targets remain passing.
