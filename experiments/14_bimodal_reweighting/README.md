# Exp 14 — Bimodal-aware reweighting of exp 13's JSONL

**Question.** Can a likelihood that treats extinction as missing data
(NaN) and uses heavier tails (Student-t) rescue a usable posterior from
exp 13's existing 1000-sim batch, or is the bifurcation a structural
model problem that no reweighting will fix?

**Motivation.** Exp 13 hit ESS = 7.3 / 600 (1.2%) under a Gaussian
likelihood applied to the alive-only pool after dropping extinct draws.
See [`../13_trajectory_selection_post_anc_fix/SUMMARY.md`](../13_trajectory_selection_post_anc_fix/SUMMARY.md).
The diagnostic figure showed two failure mechanisms layered together:

1. Filtering extinct draws and scoring them as "out" throws away
   information — those draws share parameter space with sustaining
   draws at the same coordinates (different seed). NaN treatment keeps
   the parameters in the marginal while propagating the seed-driven
   uncertainty into widened posterior bounds, instead of letting the
   extinction filter act as a hard rejection.
2. The Gaussian likelihood, with widened stds tuned in exp 10, still
   concentrates weight on the floor-of-filter draws because most
   sustaining draws sit at 5–25% prevalence — far in the Gaussian
   tail. Heavier tails (Student-t with low df) let more draws
   contribute non-trivial weight, reducing concentration.

If both treatments together still produce single-digit ESS, the
bifurcation is structural — the model's stable transmission level on
the hot branch is genuinely incompatible with the data — and exp 15
will need a model fix (FOI floor / waning immunity / network turnover).
If ESS jumps into the usable range (≥ 5%), the failure was a
likelihood-form problem and exp 13's raw sims become a usable
posterior, with no new simulations needed.

**Plan.** No new simulations. Operate entirely on
`../13_trajectory_selection_post_anc_fix/outputs/results.jsonl`.

1. Load 1000 raw target dicts. Keep all draws (no extinction filter).
2. For draws where syphilis went extinct (define: `syph_prev_f_2016 ≤
   0.001`, the histogram's clear gap), replace every syphilis-related
   target value with NaN: `syph_prev_f_2016`, `syph_prev_m_2016`,
   `syph_seroprev_f_2016`, `syph_seroprev_m_2016`, `syph_anc_2000_2015`,
   `syph_prev_hivpos_2016`, `syph_prev_hivneg_2016`. Leave non-syph
   targets (HIV, NG, CT, TV) intact, since extinction doesn't carry
   information about those.
3. Compute per-draw log-likelihood under a Student-t observation model
   with df = 3 (heavier-tailed than Gaussian without being pathological).
   NaN target values contribute zero to the log-likelihood (equivalent
   to marginalising over that target for that draw).
4. Convert to normalised importance weights; compute ESS.
5. Resample 500 draws weighted by the new likelihood.
6. Re-plot the three diagnostic figures from exp 13 (posterior
   predictive, parameter marginals, bifurcation) using the new
   weights, alongside exp 13's Gaussian weights for comparison.

**Variants to run.** Three weighting schemes, all on the same JSONL:

- **(A) Gaussian, alive-only (baseline = exp 13's verdict).** Reproduces
  ESS = 7.3 as a sanity check.
- **(B) Gaussian, NaN-for-extinction.** Isolates the contribution of
  the NaN treatment.
- **(C) Student-t df=3, NaN-for-extinction.** The full proposal.

Compare ESS, posterior predictive coverage, and the alive-pool vs
posterior predictive gap across the three.

**Success criteria.**

- **Primary:** Under (C), ESS / N ≥ 0.05. If so, the posterior is
  usable and we can move to decision analysis (exp 15) instead of a
  structural model fix.
- **Secondary:** The alive-pool predictive mean and the posterior
  predictive mean for `syph_prev_f_2020_2025` agree to within a factor
  of ~2. Currently 0.092 vs 0.001 — a 75× gap. If reweighting closes
  this to single-digit ratio, weight is no longer collapsing onto the
  filter floor.
- **Diagnostic:** ESS under (B) tells us how much of the failure was
  the filter-and-Gaussian combo vs the Gaussian alone.

**What this experiment does not test.** Whether the model's hot branch
at 5–25% is "correct" for Zimbabwe syphilis. The hot branch may be
wrong on epidemiological grounds (over-sustained transmission would
have been visible in seroprevalence data). Even if (C) gives a
usable ESS, exp 13's posterior predictive sero F undershoot (0.012 vs
0.030) suggests the rescued posterior may still be biased — it would
be telling us "the data favours the floor of the bifurcation", not
"the model fits the data".
