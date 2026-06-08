# Exp 37 — Ensemble data extraction for publication figures

**Date:** 2026-06-08.

**Question.** With the 125-draw working ensemble locked in (sustained 3/3
+ mean n_pass ≥ 4 from exp 36) and the new syph prevalence definitions
patched into stisim, re-run each draw × 3 seeds and extract annualized
time series + 2016/2020 age × sex snapshots for the headline epi
variables — so the publication figures don't need any further sim runs.

**Result.** 375 sims (125 draws × 3 seeds), 0 errors, ~17 min wall.
All five output files written; ensemble-quantile (median + 80% + 95%
CI) DataFrames generated for both time series and snapshots.

## Headline ensemble metrics (median + 80% CI)

| metric | 2016 | 2020 | 2030 |
|---|---|---|---|
| FSW syph prev | 0.64 (0.51, 0.73) | 0.62 (0.49, 0.73) | 0.61 (0.49, 0.72) |
| trep+ 15-64 | 0.21 (0.19, 0.23) | 0.21 (0.19, 0.23) | 0.21 (0.19, 0.23) |
| nontrep+ 15-64 | 0.13 (0.10, 0.15) | 0.12 (0.10, 0.14) | 0.11 (0.09, 0.13) |
| Sexually transmissible | 0.038 (0.027, 0.052) | 0.035 (0.024, 0.047) | 0.036 (0.025, 0.046) |
| Symptomatic (prim+sec) | 0.0074 (0.0045, 0.011) | 0.0074 (0.0043, 0.011) | 0.0076 (0.0043, 0.011) |
| Primary only | 0.0023 (0.0014, 0.0035) | 0.0022 (0.0013, 0.0033) | 0.0023 (0.0013, 0.0034) |
| New infections (×1000/yr) | 157 (94, 248) | 173 (97, 246) | 209 (127, 309) |

## Snapshot — syph trep+ by age × sex at 2016 (median %)

| age | F | M |
|---|---|---|
| 15-19 | 1.2 | 0.1 |
| 20-24 | 12.1 | 3.3 |
| 25-29 | 26.3 | 14.4 |
| 30-34 | 36.0 | 27.9 |
| 35-49 | 35.1 | 35.3 |
| 50-64 | 21.1 | 26.9 |
| 65+ | 11.6 | 12.4 |

Qualitative shape correct — F prev rises earlier than M (younger
sexual debut + older male partners), monotone with age through 40s,
modest decline at 50+. Absolute levels remain ~10× hotter than
ZIMPHIA at every age, consistent with the architectural ceiling
documented in exps 32-34.

## Outputs (all in `outputs/`)

| file | format | rows | contents |
|---|---|---|---|
| `time_series.parquet` | raw | 882K | per-(draw, seed, year, disease, result_name) |
| `snapshots.parquet` | raw | 120K | per-(draw, seed, year, sex, age_bin, result_name) at 2016/2020 |
| `ensemble_ts_quantiles.parquet` | aggregated | 2,352 | median + 80%/95% CI per (year, disease, result_name) |
| `ensemble_snapshots_quantiles.parquet` | aggregated | 320 | same per (year, sex, age_bin, result_name) |
| `draws_used.csv` | metadata | 125 | the 125 draws + their 20-prior values |

## Coverage

- **Diseases:** HIV, NG, CT, TV, syph (BV and GUDp excluded — not focal
  for PN work)
- **Syph prevalence types (all sex- and age-stratified):**
  - `active_prevalence` (primary | secondary — stisim default)
  - `sexually_transmissible_prevalence` (primary | secondary | early latent — WHO EIS)
  - `symptomatic_prevalence` (primary | secondary)
  - `primary_prevalence` (primary only)
  - `trep_prevalence`, `nontrep_prevalence` (with 15-64 variants for time series)
- **Time series years:** 1985 to 2040 (annualized via `Result.annualize()`)
- **Snapshot years:** 2016 and 2020 (ZIMPHIA rounds)
- **Age bins:** 0-15, 15-20, 20-25, 25-30, 30-35, 35-50, 50-65, 65-100

## Scaling

- `total_pop = 8686` (thousands; matches Zimbabwe 1985 ~8.7M)
- `pop_scale = 0.8686` per agent (in thousands of people)
- Results defined with `scale=True` (e.g. `new_infections`) are
  auto-multiplied by `pop_scale` — so values are in **thousands of
  people**. Multiply by 1000 to read as raw counts, or report as-is
  in figures with a "thousands" label.

## Acceptance

Working dataset for publication figures. `plot_sims.py`'s
quantile-band style plots can read `ensemble_ts_quantiles.parquet`
with a tiny adapter — the format matches what the existing
`plot_hiv_sims` / `plot_sti_sims` functions expect.

## Next

Pending decision (deferred from before this run): workflow choice
between staying in `experiments/` for downstream PN scenarios work,
or merging the calibration commits to `main` and branching a
`scenarios/` track. Now's the time — calibration is closed; what
comes next is scenarios analysis on this ensemble.

## Artifacts

- See `outputs/` directory listing above
- `run.py`, `config.yaml`, `README.md`
