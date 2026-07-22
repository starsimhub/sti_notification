# sti_notification

Health-impact analysis of demand-generation and prevention strategies for STI **undertreatment** in sub-Saharan Africa: point-of-care (POC) etiological diagnostics, partner notification (PN), symptomatic care-seeking, and bundled prevention (condoms + counselling for the diagnosed).

Companion to [`syph_dx_zim`](https://github.com/starsimhub/syph_dx_zim) (which focused on **overtreatment** via syndromic management). Built on [STIsim](https://github.com/starsimhub/stisim).

## Status

Active calibration baseline: **exp 06** (500-draw LHS × K=5 sim-averaging, continuous weighted GoF, top-30 ensemble). First scenario factorial completed 2026-06-26 (65 cells × 5 draws × K=5 seeds = 1625 sims). See [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) for scope and endpoints.

## Install

```bash
pip install -r requirements.txt
```

Tested against `stisim==1.5.7`, `starsim==3.3.2` on Python 3.11 (conda env `starsim`).

## Quick start

```bash
# Smoke-test the model (1985–1990, all 7 diseases)
python model.py

# Smoke-test the scenario factorial (5 cells x 5 draws x K=5 seeds = 125 sims)
conda run -n starsim env SMOKE=1 N_WORKERS=30 python run_scenarios.py

# Full scenario factorial (65 cells x N_DRAWS x K=5 seeds; multi-core box).
# N_DRAWS=5 N_SEEDS=5 N_WORKERS=80 gives 1625 sims in ~2.5h on the IDM VM.
conda run -n starsim env N_DRAWS=5 N_SEEDS=5 N_WORKERS=80 python run_scenarios.py
```

## Project structure

| File / folder | Purpose |
|---|---|
| `model.py` | `make_sim()` — assembles the Zimbabwe sim (HIV + STIs + networks + interventions) |
| `hiv_model.py` | HIV module factory + HIV testing/ART/VMMC/PrEP interventions |
| `interventions.py` | Syndromic management, `SyndromicPN`/`POCPN`, syph testing, `CondomCounseling` (bundled prevention) |
| `pn.py` | Edge-stratified `PartnerNotification` base class + `pn_rates` helper |
| `scenarios.py` | The three scenario ladders: `CARE_SEEKING`, `PN_INTENSITY`, `BUNDLED_PREVENTION` |
| `run_scenarios.py` | **Scenario driver**: SOC + POC 3-factor full factorial over the calibrated ensemble |
| `experiments/` | **Calibrations only** (dated, sequential): `01_2026-06-15_…` through `06_2026-06-24_kseed_calibration/` (active baseline) |
| `plotting/` | Deck plotting scripts (`plot_slide3.py` … `plot_slide12.py` + shared helpers; superseded scripts in `plotting/archive/`). See [plotting/README.md](plotting/README.md) |
| `exploratory/` | Superseded / one-off plot + analysis scripts. See [exploratory/README.md](exploratory/README.md) |
| `figures/` | Deck slide PNGs at the top level; `figures/archive/` = superseded exploratory figures; `figures/supplementary/` = supplementary materials |
| `results/` | Scenario run outputs. `scenarios.kavg.csv` (K=5-averaged scalars) + `specificity.csv` + `soc_overtreatment.csv` committed; per-sim `scenarios.jsonl` + time-series / snapshot parquets are VM-only — see [CLAUDE.md](CLAUDE.md) §"VM-only data files" |
| `archive/` | Superseded exploratory experiments (PN/condom ladders, wiring/story runs) |
| `data/` | Zimbabwe demographic + initial-prevalence CSVs |
| `diagnostics/` | Analysis / instrumentation scripts (`specificity_tracer.py`, `vds_etiology.py`) that produce derived CSVs for the deck plots |
| `ANALYSIS_PLAN.md` | Scope, levers, factorial design, endpoints |

Conventions:
- **Calibration** runs live under `experiments/` (each its own dated folder, with figures in that folder).
- **Scenario** runs go through the single root `run_scenarios.py`; the deck figures live in `figures/`.
- **Plotting** scripts live in `plotting/`; run them from the repo root (`conda run -n starsim python plotting/plot_slide6.py`).

## Scenario design

`SOC` (syndromic standard of care) and `POC` (etiological diagnostics) plus a **4 × 4 × 4 factorial** over three POC-layered levers — symptomatic care-seeking × partner notification × bundled prevention — each a 4-rung ladder (baseline/low/moderate/high) in `scenarios.py`. 64 POC cells + SOC = **65 distinct cells**, propagated through the calibrated ensemble with K=5 paired seeds. See [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md).

## Diseases modeled

HIV, syphilis, NG, CT, TV, BV (+ GUD placeholder). Coinfection connectors auto-added by `sti.Sim`; `FetalHealth` wired via `custom=` for APO/ABO accounting.

## Settings

Zimbabwe (current). Kenya and South Africa deferred.

## License

[MIT](LICENSE)
