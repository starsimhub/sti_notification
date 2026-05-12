# Exp 02 — Coverage check: syphilis seeding fix

**Question.** Exp 01 showed syphilis extinct across all 100 prior draws. The
root cause was missing `init_prev_syph.csv` and `init_prev_latent_syph.csv` in
`sti_notification/data/` — STIsim silently seeded near-zero and clearance won.
Does the model now sustain syphilis and bracket the observed active prevalence
data (~3–8% from ZIMPHIA) when those files are present?

**Plan.** Port the two init_prev files from `syph_dx_zim/data/` (active:
0.001–0.02 by risk group/sex/SW; latent: 0.02 uniform) and set
`rel_init_prev=0.2` in `model.py` to match the `syph_dx_zim` configuration.
Re-run the identical 100-draw prior predictive check (n_agents=5000, 1985–2025,
no PN, no FetalHealth). NG/CT/TV/HIV panels expected to be unchanged.

One flag to watch: `syph_dx_zim`'s posterior for `syph.beta_m2f` ran 0.15–0.35,
while the current prior ceiling is 0.20. If syphilis trajectories just barely
bracket the data in this run, exp 03 should widen the prior to 0.35.

**Success criteria.** Syphilis active prevalence trajectories from prior draws
visually bracket the ZIMPHIA data points (~3–8%). Extinction across draws would
indicate model misspecification or `rel_init_prev` too aggressive a scale-down.
