# Quarto dashboard

A static, serverless rebuild of the React/Vite dashboard (`../dashboard/`) as a single Quarto website. Same results, same six-section narrative, no build step: `quarto render` reads the committed `results/` tables directly and emits a static site to `_site/`.

## Why this exists

The React version needed Node, Vite, React, Recharts, Tailwind, a `export_data.py` step, and four committed JSON intermediates. This version replaces all of that with:

- **`prep.py`** — loads the scalar scenario table `results/scenarios.kavg.csv` and the timeseries `data/timeseries.json`, and does the median/IQR + cross-product aggregation (the old `dataTransforms.js` + `export_data.py`, in one place).
- **`charts.py`** — Plotly builders for the static narrative charts.
- **`index.qmd`** — the six sections. Narrative charts are **Plotly**; the interactive scenario explorer is **ObservableJS + Observable Plot** (reactive, client-side, no server).
- **`custom.scss`** — brand palette + table styling ported from the Tailwind config.
- **`figures/`** — the static PNGs (cascade, overtreatment, VDS etiology, calibration fits), embedded as plain images.

## Local render

```bash
conda activate starsim            # provides pandas/pyarrow/plotly/jupyter
quarto render                     # -> _site/index.html
quarto preview                    # live-reloading dev server
```

Requires Quarto ≥ 1.4 and the packages in `requirements.txt`.

## Deploy

`../.github/workflows/deploy-dashboard-quarto.yml` renders and publishes to GitHub Pages. It is **manual-dispatch only** for now so it does not overwrite the live React dashboard (`deploy-dashboard.yml`) while both exist. To switch over: retire the React workflow, then enable the `push` trigger shown commented at the top of the Quarto workflow.

## Data sources (and a repo data-consistency warning)

- **Bars / scalars** come from `results/scenarios.kavg.csv` (65 cells, draws 75/78/236/263/343).
- **Timeseries** come from `data/timeseries.json` (a copy of the React dashboard's export).

⚠️ **`results/scenarios_timeseries.parquet` is NOT used** and should not be until it is regenerated. It is from a *different run* than the committed scalar table — draws 14/16/47, 126 cells, versus the scalar table's draws 75/78/236/263/343, 65 cells — so its trajectories do not match the bars (e.g. NG 2040 prevalence 0.049 in the parquet vs 0.0176 in the scalar table; CT is inverted, 0.0098 vs 0.1089). `data/timeseries.json`'s end-of-horizon values match the scalar table exactly, so it is the correct timeseries source. Once the parquet is regenerated from the current run, `prep.load_timeseries()` can be pointed back at it.

## Fidelity to the React version

Page content, prose, headings, tables, figures, and chart styles match the React dashboard. Two intentional deviations:

- **Methods** was an interactive accordion (Model / Calibration / Scenario design) in React; here it is static text with the same three labelled subsections. The *content* is identical — only the collapse/expand interaction is dropped.
- **Scenario explorer** combo labels omit any ladder axis that has a single level selected (e.g. `moderate/none` instead of `baseline/moderate/none`), per request, to keep the x-axis readable; the React version always wrote all three.

## Known caveat: Plotly loads from CDN

Quarto always pulls `plotly.min.js` from `cdn.plot.ly` at runtime (the Observable/Vega runtimes, by contrast, are vendored locally into `_site/site_libs/`). This is fine for normal browsers but means the page needs network access to that CDN. If you need a fully self-contained page, self-host Plotly by downloading `plotly.min.js` into the project and pointing the include at it, or render individual figures with `include_plotlyjs="…"`.
