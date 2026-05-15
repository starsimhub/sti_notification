# Exp 04 — Coverage check: mid-risk concurrency

**Question.** Exps 02–03 showed syphilis seeds but crashes to zero
regardless of high-risk group size or primary transmissibility. The
mid-risk group — where the bulk of sexually active adults sit — has
`f1_conc=0.05`, far below the 0.15 used in `syph_dx_zim`. Does raising
`f1_conc` to 0.15 sustain syphilis through the data window?

**Plan.** Single change to `model.py`: `f1_conc` 0.05→0.15. All other
settings carried forward from exp 03 (network: `prop_f2=0.05`,
`prop_m2=0.15`, `f2_conc=0.25`, `m2_conc=0.50`; priors: 10 parameters
including `rel_trans_primary` 3–10 and `eff_condom` 0.30–0.70). Same
100-draw prior predictive check (n_agents=5000, 1985–2025).

**Success criteria.** A meaningful fraction of draws (>20/100) sustain
syphilis prevalence above 0.5% through 2020–2025, and trajectories
bracket the ~1.7–2.2% data. If this works, the coverage check is clear
and we proceed to method selection. If not, the next lever is the
HIV-syphilis coinfection connectors.
