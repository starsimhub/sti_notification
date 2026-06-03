# Exp 08 — Coverage fix: TV prior, HIV prior, syphilis testing stratification

**Question.** Can we fix the three issues identified in exp 07 and achieve
coverage across all targets simultaneously?

1. **TV coverage failure** (0/100 draws reach ~10% data): widen TV beta
   prior upper bound.
2. **HIV systematic overshoot** (100/100 draws above data, model at
   20-25% vs observed peak ~13%): the `rel_init_prev` prior (2–15) is
   too high — at the upper end, FSW init prev of 20% x 15 saturates the
   high-risk core and drives unrealistic early prevalence. Tighten the
   range.
3. **Syphilis testing not stratified**: replace scalar `symp_test_prob=0.5`
   with the sex/risk-group/SW-stratified CSV from `syph_dx_zim`
   (`symp_test_prob_soc.csv`: females 15-45%, males 10%, FSW 45%).
   This changes syphilis equilibrium dynamics and affects all syphilis
   targets.

**Changes.**
- `priors.py`: widen TV beta upper bound; tighten HIV `rel_init_prev`.
- `data/symp_test_prob_soc.csv`: copied from `syph_dx_zim`.
- `interventions.py`: `make_syph_testing` loads stratified CSV instead of
  scalar.
- `hiv_model.py`: lower default `beta_m2f` to within the prior range.

**Plan.** 100 prior draws, 10k agents, 1985–2025. Same as exp 07 but
with the three fixes above.

**Success criteria.** All targets bracketable: NG/CT/TV/HIV non-syphilis
targets covered, plus all seven syphilis targets from exp 07. TV
specifically should have draws reaching ~10%. HIV should bracket the
observed ~13% peak and subsequent decline.
