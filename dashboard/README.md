# Dashboard

A static, serverless Quarto website presenting the STI-notification scenario results. No build step: `quarto render` reads the committed data tables and emits a static site to `_site/`. (This replaced an earlier React/Vite/Recharts/Tailwind dashboard.)

## Structure

- **`prep.py`** — loads the scalar scenario table `results/scenarios.kavg.csv` and the timeseries `data/timeseries.csv`, and does the median/IQR + cross-product aggregation.
- **`charts.py`** — Plotly builders for the narrative charts.
- **`index.qmd`** — the six sections. Narrative charts are **Plotly**; the interactive scenario explorer is **ObservableJS + Observable Plot** (reactive, client-side, no server).
- **`custom.scss`** — brand palette + table styling.
- **`figures/`** — the static PNGs (cascade, overtreatment, VDS etiology, calibration fits), embedded as plain images.
- **`data/timeseries.csv`** — pre-aggregated prevalence + new-infection trajectories (see below).
- **`scripts/export_timeseries.py`** — regenerates `data/timeseries.csv` from the scenario run.

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

- **Scalars / bars / overtreatment / notification** — `results/scenarios.kavg.csv` (65 cells, K=5-averaged, draws 75/78/236/263/343), read directly by `prep.py`.
- **Timeseries (prevalence + new infections)** — `data/timeseries.csv`, a compact table produced by `scripts/export_timeseries.py`. This is the only pre-aggregated input; every other quantity is read straight from the scalar table.

To refresh the timeseries after a new run:

```bash
python scripts/export_timeseries.py   # needs pandas + pyarrow; reads results/scenarios_timeseries.parquet
```

⚠️ **The old `results/scenarios_timeseries.parquet` was removed** because it was from a *different run* than the committed scalar table (draws 14/16/47, 126 cells, versus 75/78/236/263/343, 65 cells) — its trajectories did not match the bars (e.g. NG 2040 prevalence 0.049 vs 0.0176; CT inverted, 0.0098 vs 0.1089). `data/timeseries.csv`'s end-of-horizon values match the scalar table exactly. `scripts/export_timeseries.py` expects a freshly regenerated parquet from the current run before it is run again.

## Chart engines

- **Plotly** for the narrative charts (bars with IQR error bars, smoothed timeseries). Tooltips and legend-click show/hide come for free.
- **ObservableJS + Observable Plot** for the scenario explorer, so its additive cross-product controls run entirely client-side in the static page — no server, no Python kernel.

Two small notes:

- The scenario-explorer combo labels omit any ladder axis that has a single level selected (e.g. `moderate/none` rather than `baseline/moderate/none`), to keep the x-axis readable.
- Quarto pulls `plotly.min.js` from `cdn.plot.ly` at runtime (the Observable/Vega runtimes are vendored locally into `_site/site_libs/`). Fine for normal browsers; if you need a fully offline page, self-host `plotly.min.js`.
