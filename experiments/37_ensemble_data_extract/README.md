# Exp 37 — Ensemble data extraction for publication figures

**Note on scope.** This is a data-extraction run over the established
125-draw ensemble (exp 36 robust output), not a new calibration
experiment. It exists to produce annualized time series + 2016/2020
age × sex snapshots in a format ready for ensemble-quantile
publication figures.

The question of whether to keep operating under the `experiments/`
folder for downstream scenarios work — or merge the calibration to
`main` and branch a `scenarios` track — is open and deferred until
after this run lands.

**Question.** Take the 125-draw working ensemble (sustained 3/3 +
mean n_pass ≥ 4 from exp 36) and re-run each with 3 seeds, saving:

- **Annualized time series** for all the headline epi variables: HIV
  prevalence + new infections, NG/CT/TV prevalence + new infections,
  syph (FSW prev, client prev, trep prev 15-64, nontrep prev 15-64,
  active/sexually-transmissible/symptomatic/primary prev, new
  infections scaled).
- **2016 and 2020 age × sex snapshots** for each disease and each
  syph prev type — matches ZIMPHIA 2015-16 and 2020 survey rounds for
  direct overlay.

**Plan.**

1. Filter `experiments/36_ensemble_robust_extend/outputs/full_summary.csv`
   to `pass_sustained == 1.0 AND n_pass_mean >= 4` → 125 draws.
2. Pull their 20-prior values from
   `experiments/35_ensemble_build/outputs/phase1_priors.csv`.
3. Run each × 3 seeds (same seed scheme as exp 35/36 Phase 2:
   `seed = 100_000 + draw_idx * 10 + s_idx`) at 10k agents,
   1985-2040, no PN, no fetal_health.
4. For each sim, save:
   - `time_series.parquet` row per (draw, seed, year, disease,
     result_name, value) — annualised via `Result.annualize().to_df()`
   - `snapshots.parquet` row per (draw, seed, year, disease, sex,
     age_bin, result_name, value) for year ∈ {2016, 2020}.
5. After the run, aggregate to ensemble quantile DataFrames
   (`ensemble_ts_quantiles.parquet`, `ensemble_snapshots_quantiles.parquet`)
   keyed by (year, result_name) with median + 80% + 95% CI bands —
   ready for `plot_sims.py` style plotting.

**Cost estimate.** 125 × 3 = 375 sims at 24 workers ≈ 17 min wall.
Plus aggregation ~1 min.

**Outputs.**

- `outputs/time_series.parquet` — all annual time series, all sims
- `outputs/snapshots.parquet` — 2016 + 2020 age × sex breakdowns
- `outputs/ensemble_ts_quantiles.parquet` — median + 80%/95% CI per year
- `outputs/ensemble_snapshots_quantiles.parquet` — median + CI per
  (year, age_bin, sex)
- `outputs/draws_used.csv` — the 125 draws + their priors

**Forward reference.** After this run, decide:
- Workflow track: stay in `experiments/` or branch `scenarios`?
- Plot styling — `plot_sims.py` already has HIV + STI series plotters
  that take quantile DFs; minor adapter needed to read these outputs.
