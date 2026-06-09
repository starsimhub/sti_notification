# Exp 39 — Publication figures from baseline-PN ensemble

**Question.** Regenerate the publication figures (HIV/STI time series,
syph time series, syph stage definitions, syph age × sex 2016) from
the new 101-draw robust ensemble produced by exp 38, with two
corrections relative to exp 37:

1. `total_pop=8.7e6` is now wired into `make_sim`, so per-agent count
   outputs (new_infections) scale to absolute Zimbabwe-population
   numbers. Exp 37's figures were ~1000× off on counts.
2. Add `prevalence_15_49` to the HIV time-series extraction list so
   the model HIV prev plot can be compared on UNAIDS' standard
   denominator (15-49) rather than whole-population, fixing the ~3pp
   shift Robyn flagged on the exp 37 HIV figure.

**Plan.**

- Fork exp 37's extraction pipeline. Source ensemble: exp 38
  `outputs/ensemble_summary.csv`, filter sustained 3/3 AND mean
  n_pass≥4 → 101 draws (same as committed exp 38 robust set).
- Run each draw with 3 seeds (same SEED_BASE=100000 so seeds match
  exp 38 calibration), passing the calibrated `pn_pars` per-draw so
  baseline PN runs at the calibrated rates rather than defaults.
- Extract annualised time series for HIV / NG / CT / TV / syph, plus
  2016 + 2020 age × sex snapshots for the full set of syph prev types
  (active, sexually_transmissible, symptomatic, primary, trep,
  nontrep) and HIV/NG/CT/TV prev.
- Aggregate to ensemble quantiles (median + 80%/95% CI).
- Replot the 5 publication figures using the new quantile parquets.

**Success criteria.** All 5 publication figures regenerate without
manual quantile fixups, HIV time series tracks UNAIDS data on the
15-49 denominator (within visual tolerance), and STI count outputs
are on the correct absolute scale (HIV new infections ~40-50K/yr in
the late-1990s peak, not 50/yr).

**Expected wall time:** ~40 min (101 × 3 = 303 sims).

## Forward reference

After this lands, the publication-figure pipeline is ready for the
PN-intervention scenarios (exp 40+): each scenario re-runs the same
101 draws under counterfactual PN rates and overlays scenario
quantiles on this baseline.
