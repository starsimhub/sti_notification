# sti_notification

Zimbabwe-calibrated STIsim modelling study of co-transmitting HIV, syphilis, gonorrhea, chlamydia, trichomoniasis, and bacterial vaginosis. We ran a 4 × 4 × 4 factorial of three demand-side and prevention levers (symptomatic care-seeking, partner-notification intensity, and bundled prevention via condoms and counseling for the diagnosed) layered on top of a point-of-care (POC) NG/CT/TV diagnostic vs syndromic standard-of-care, over 2027–2040. Combined at high intensity these levers approximately halve cumulative new curable-STI infections in Zimbabwe; POC diagnostics also reduce unnecessary treatments by 75–85% and unnecessary partner notification by ~30%, the latter a floor determined by diagnostic specificity rather than PN reach.

Companion to [`syph_dx_zim`](https://github.com/starsimhub/syph_dx_zim) (overtreatment) and [`stisim_vddx_zim`](https://github.com/starsimhub/stisim_vddx_zim) (POC vs syndromic diagnostic accuracy for VDS). Built on [STIsim](https://github.com/starsimhub/stisim). Full findings in [`docs/sti_manuscript.md`](docs/sti_manuscript.md); scenario design and calibration state in [`SYNOPSIS.md`](SYNOPSIS.md).

## Status

Active calibration baseline: **exp 06** (500-draw LHS × K=5 sim-averaging, continuous weighted GoF, top-30 ensemble). Active scenario baseline: **65 cells × 10 draws × K=5 seeds = 3250 sims** (full factorial rerun 2026-07-22).

## Install

```bash
pip install -r requirements.txt
```

Tested against `stisim==1.5.7`, `starsim==3.3.2` on Python 3.11 (conda env `starsim`).

## Quick start

```bash
# Smoke-test the model (1985–1990, all 7 diseases)
python model.py

# Smoke-test the scenario factorial (5 cells × 5 draws × K=5 seeds = 125 sims)
conda run -n starsim env SMOKE=1 N_WORKERS=30 python run_scenarios.py
```

For the full pipeline (factorial + aggregation + figures), see
[Regenerating results and figures](#regenerating-results-and-figures) below.

## Project structure

| File / folder | Purpose |
|---|---|
| `model.py` | `make_sim()` — assembles the Zimbabwe sim (HIV + STIs + networks + interventions) |
| `hiv_model.py` | HIV module factory + HIV testing/ART/VMMC/PrEP interventions |
| `interventions.py` | Syndromic management, `SyndromicPN`/`POCPN`, syph testing, `CondomCounseling` (bundled prevention) |
| `pn.py` | Edge-stratified `PartnerNotification` base class + `pn_rates` helper |
| `scenarios.py` | The three scenario ladders: `CARE_SEEKING`, `PN_INTENSITY`, `BUNDLED_PREVENTION` |
| `run_scenarios.py` | **Scenario driver**: SOC + POC 3-factor full factorial over the calibrated ensemble. Writes fat outputs to `raw_results/` and the K=5-averaged scalar CSV to `results/`. |
| `process_results.py` | Aggregates `raw_results/*.parquet` (per-draw) into `results/*.parquet` (median + p25 + p75 across draws). Configurable at the top: `result_names`, `diseases`, `years`, `quantiles`. Re-processing does not require a factorial rerun. |
| `experiments/` | **Calibrations only** (dated, sequential): `01_2026-06-15_…` through `06_2026-06-24_kseed_calibration/` (active baseline) |
| `plotting/` | Deck plotting scripts (`plot_slide3.py` … `plot_slide14.py` + shared helpers; superseded scripts in `plotting/archive/`). See [plotting/README.md](plotting/README.md) |
| `exploratory/` | Superseded / one-off plot + analysis scripts (plus the supplementary `plot_epi.py` + `plot_pn_story.py`). See [exploratory/README.md](exploratory/README.md) |
| `dashboard/` | Static Quarto site presenting the scenario results. See [dashboard/README.md](dashboard/README.md) |
| `figures/` | Deck slide PNGs at the top level; `figures/archive/` = superseded figures; `figures/supplementary/` = supplementary materials. See [figures/README.md](figures/README.md) |
| `results/` | **Committable** scenario outputs: `scenarios.kavg.csv` (K=5-averaged scalars per (cell, draw)), `scenarios_timeseries.parquet` + `scenarios_snapshots.parquet` (aggregated median + p25 + p75 across draws — produced by `process_results.py`), plus small diagnostics CSVs (`specificity.csv`, `soc_overtreatment.csv`, `vds_etiology.csv`, `ppv_table.csv`, etc.). Safe on any clone. |
| `raw_results/` | **Gitignored, VM-only.** Fat per-sim outputs from `run_scenarios.py`: `scenarios.jsonl`, `scenarios_timeseries.parquet` + `scenarios_snapshots.parquet` (per-draw K-averaged, before cross-draw aggregation). Regenerable by re-running the factorial. |
| `archive/` | Superseded exploratory experiments (PN/condom ladders, wiring/story runs) |
| `data/` | Zimbabwe demographic + initial-prevalence CSVs |
| `diagnostics/` | Analysis / instrumentation scripts (`specificity_tracer.py`, `vds_etiology.py`) that produce derived CSVs for the deck plots |
| `SYNOPSIS.md` | Study synopsis: question, methods, headline findings, deliverables, reproduction |

Conventions:
- **Calibration** runs live under `experiments/` (each its own dated folder, with figures in that folder).
- **Scenario** runs go through the single root `run_scenarios.py`; the deck figures live in `figures/`.
- **Plotting** scripts live in `plotting/`; run them from the repo root (`conda run -n starsim python plotting/plot_slide6.py`).

## Scenario design

`SOC` (syndromic standard of care) and `POC` (etiological diagnostics) plus a **4 × 4 × 4 factorial** over three POC-layered levers — symptomatic care-seeking × partner notification × bundled prevention — each a 4-rung ladder (baseline/low/moderate/high) in `scenarios.py`. 64 POC cells + SOC = **65 distinct cells**, propagated through the calibrated ensemble with K=5 paired seeds. See [`SYNOPSIS.md`](SYNOPSIS.md).

## Regenerating results and figures

Three idempotent stages. Stage 1 needs the VM; stages 2 and 3 run anywhere with `results/` present.

### 1. Factorial simulation (VM, ~4h at N_DRAWS=10)

```bash
conda run -n starsim env \
  N_DRAWS=10 N_SEEDS=5 N_WORKERS=120 \
  python run_scenarios.py
```

Writes fat per-draw outputs to `raw_results/` (gitignored) and the small K=5-averaged scalar CSV to `results/scenarios.kavg.csv` (committable). At `N_DRAWS=10 × K=5 × 65 cells = 3250` sims, expect ~4 h on 120 workers or ~5.5 h on 80. Set `N_DRAWS=5` for the historical 2.5-h baseline; set `SMOKE=1` for a 125-sim ~15-min sanity run.

### 2. Aggregation (anywhere with `raw_results/`, ~5 s)

```bash
conda run -n starsim python process_results.py
```

Reads `raw_results/*.parquet`, aggregates across draws to `(median, p25, p75)` per `(cell, disease, result_name, year)`, and writes the committable slim parquets under `results/`. Filter constants at the top of the script (`DEFAULT_RESULT_NAMES`, `DEFAULT_DISEASES`, `DEFAULT_YEARS`, `DEFAULT_QUANTILES`) — a re-processing run only takes seconds, so widening quantiles or picking new result names is cheap. Widening beyond what `run_scenarios.py`'s `TS_RESULTS` extracts requires re-running the factorial.

### 3. Figures + dashboard (anywhere, ~1 min)

```bash
# Deck slides
for f in plotting/plot_slide*.py; do conda run -n starsim python "$f"; done

# Supplementary figures
conda run -n starsim python exploratory/plot_epi.py
conda run -n starsim python exploratory/plot_pn_story.py

# Static dashboard site (requires Quarto ≥ 1.4)
cd dashboard && quarto render     # -> _site/index.html
```

Everything reads only from `results/`, so a fresh clone can regenerate every committed figure without VM access.

## Diseases modeled

HIV, syphilis, NG, CT, TV, BV (+ GUD placeholder). Coinfection connectors auto-added by `sti.Sim`; `FetalHealth` wired via `custom=` for APO/ABO accounting.

## Settings

Zimbabwe (current). Kenya and South Africa deferred.

## License

[MIT](LICENSE)
