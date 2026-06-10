# Calibration artifacts

The minimum object set required to reproduce, audit, or recalibrate
this work without checking out `archive/calibration-2026-06`.

## Contents

| File | What it is | Size |
|---|---|---|
| `draws_used.csv` | 200 robust posterior draws × 19 prior columns. Each row is a parameter set that produced a sustained, in-band simulation across 3 seeds. | 73 KB |
| `ensemble_ts_quantiles.parquet` | Ensemble median + 80% / 95% CI per (disease, result_name, year), 1985–2040. 2,408 rows. | 122 KB |
| `ensemble_snapshots_quantiles.parquet` | Ensemble quantiles per (disease, result_name, year, sex, age_bin) at 2016 and 2020. 320 rows. | 19 KB |
| `figures/*.png` | The 5 publication figures. | ~800 KB total |
| `scripts/_pipeline.py` | Shared utilities: priors → sim, target bands, time-series / snapshot extraction, quantile aggregation. | ~ |
| `scripts/run_ensemble.py` | LHS calibration pipeline (Phase 1 + Phase 2). Produces a new `draws_used.csv` from priors. | ~ |
| `scripts/extract_summary.py` | Re-runs saved draws × N seeds, extracts time series + snapshots, writes quantile parquets. | ~ |
| `scripts/plot_figures.py` | Quantile parquets → 5 publication figures. | ~ |
| `scripts/reproduce_check.py` | Re-runs a random sample of saved draws, checks fraction outside saved 95% CI. | ~ |

## What is *not* here

- **Per-(draw, seed) raw parquets** (~11 MB time_series.parquet, ~1 MB
  snapshots.parquet). They live only on `archive/calibration-2026-06`
  under `experiments/41_pub_figures_final/outputs/`. They can be
  regenerated from `draws_used.csv` by running:

  ```bash
  python scripts/extract_summary.py --draws-csv draws_used.csv \
                                    --out-dir . --keep-raw
  ```

- The full 5,000-draw Phase 1 results, candidate selection, and per-event
  transmission JSONs from exp 40. These are the raw materials behind
  `draws_used.csv` and are preserved on the archival branch only.

## Quick start

Each script is self-contained — run with `python scripts/<name>.py
--help` for the full argument list. Common operations:

**Regenerate the 5 figures from the saved quantile parquets:**
```bash
python scripts/plot_figures.py
```

**Verify the saved calibration is still valid against the current STIsim:**
```bash
python scripts/reproduce_check.py --n-draws 10 --n-seeds 3
```
Exits 0 if the sample's fraction of (sim, year, result) points outside
the saved 95% CI is ≤ 15%. Expected baseline ~5% by chance.

**Re-run the ensemble + regenerate quantiles (e.g. after a CSV refresh):**
```bash
python scripts/extract_summary.py --draws-csv draws_used.csv --out-dir .
python scripts/plot_figures.py
```

**Full recalibration from scratch:**
See [`../recalibration_guide.md`](../recalibration_guide.md) for the
step-by-step pipeline. Quick summary:
```bash
python scripts/run_ensemble.py --phase all --out-dir new_calibration/
python scripts/extract_summary.py --draws-csv new_calibration/draws_used.csv \
                                  --out-dir new_calibration/
python scripts/plot_figures.py --ts-quantiles new_calibration/ensemble_ts_quantiles.parquet \
                               --snap-quantiles new_calibration/ensemble_snapshots_quantiles.parquet \
                               --fig-dir new_calibration/figures/
```

## Compatibility

These scripts depend on the model code at the repo root
([`../../model.py`](../../model.py),
[`../../priors.py`](../../priors.py),
[`../../interventions.py`](../../interventions.py)) and the locked
data CSVs at [`../../data/`](../../data/). They `chdir` to the repo
root on startup so the model's relative path lookups for `data/` work
from any invocation directory.

Runtime environment requirements are in
[`../recalibration_guide.md`](../recalibration_guide.md#prerequisites).
