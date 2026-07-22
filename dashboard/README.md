# Dashboard

A static, serverless Quarto website presenting the STI-notification scenario results. No build step: `quarto render` reads the committed data tables and emits a static site to `_site/`. (This replaced an earlier React/Vite/Recharts/Tailwind dashboard.)

## Structure

- **`prep.py`** — loads the scalar scenario table `results/scenarios.kavg.csv` and the timeseries `results/scenarios_timeseries.parquet`, and does the median/IQR + cross-product aggregation.
- **`charts.py`** — Plotly builders for the narrative charts.
- **`index.qmd`** — the six sections. Narrative charts are **Plotly**; the interactive scenario explorer is **ObservableJS + Observable Plot** (reactive, client-side, no server).
- **`custom.scss`** — brand palette + table styling.
- **`figures/`** — the static PNGs (cascade, overtreatment, VDS etiology, calibration fits), embedded as plain images.

## Local render

```bash
conda activate starsim            # provides pandas / plotly / jupyter
quarto render                     # -> _site/index.html
quarto preview                    # live-reloading dev server
```

Requires Quarto ≥ 1.4 and the packages in `requirements.txt`.

## Deploy

`../.github/workflows/deploy-dashboard.yml` renders and publishes to GitHub Pages on every push to `main` that touches `dashboard/**` (or the two source tables it reads), and can also be run manually via *workflow_dispatch*.

## Data sources

Everything the dashboard shows is derived from two committed tables:

- **Scalars / bars / overtreatment / notification** — `results/scenarios.kavg.csv` (65 cells × N_DRAWS × K=5-averaged), read directly by `prep.py`.
- **Timeseries (prevalence + new infections + ribbons)** — `results/scenarios_timeseries.parquet`, produced by `process_results.py`. Columns: `median`, `p_lo`, `p_hi` per `(cell, disease, result_name, year)`, aggregated across draws. Read directly by `prep.py`; drives the IQR ribbons in `ts_grid`.

The pipeline is: `run_scenarios.py` → `raw_results/*.parquet` (VM-only, per-sim) → `process_results.py` → `results/*.parquet` (committable, aggregated) → `dashboard/prep.py` reads directly. See [../README.md](../README.md#regenerating-results-and-figures) for regeneration commands.

## Chart engines

- **Plotly** for the narrative charts (bars with IQR error bars, smoothed timeseries). Tooltips and legend-click show/hide come for free.
- **ObservableJS + Observable Plot** for the scenario explorer, so its additive cross-product controls run entirely client-side in the static page — no server, no Python kernel.

Two small notes:

- The scenario-explorer combo labels omit any ladder axis that has a single level selected (e.g. `moderate/none` rather than `baseline/moderate/none`), to keep the x-axis readable.
- Quarto pulls `plotly.min.js` from `cdn.plot.ly` at runtime (the Observable/Vega runtimes are vendored locally into `_site/site_libs/`). Fine for normal browsers; if you need a fully offline page, self-host `plotly.min.js`.
