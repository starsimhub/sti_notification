# sti_notification

Health-impact analysis of demand-generation and prevention strategies for STI **undertreatment** in sub-Saharan Africa: point-of-care (POC) etiological diagnostics, partner notification (PN), symptomatic care-seeking, and bundled prevention (condoms + counselling for the diagnosed).

Companion to [`syph_dx_zim`](https://github.com/starsimhub/syph_dx_zim) (which focused on **overtreatment** via syndromic management). Built on [STIsim](https://github.com/starsimhub/stisim).

## Status

Calibrated baseline in hand (26-draw sustained ensemble, stisim rc1.5.7); scenario factorial scaffolded and smoke-tested. See [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) for scope and endpoints.

## Install

```bash
pip install -r requirements.txt
```

Tested against `stisim==1.5.7`, `starsim==3.3.2` on Python 3.11 (conda env `starsim`).

## Quick start

```bash
# Smoke-test the model (1985–1990, all 7 diseases)
python model.py

# Smoke-test the scenario factorial (6 spanning cells, 2k agents, 1 draw)
conda run -n starsim env SMOKE=1 python run_scenarios.py

# Full scenario factorial (126 cells x ensemble x seeds; multi-core box)
conda run -n starsim env N_SEEDS=1 N_WORKERS=60 python run_scenarios.py
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
| `experiments/` | **Calibrations only** (dated, sequential): `01_2026-06-15_…`, `02_2026-06-22_…` |
| `figures/` | Scenario figures (PNGs) and their generating scripts |
| `results/` | Scenario run outputs (`scenarios.jsonl`; gitignored — regenerable) |
| `archive/` | Superseded exploratory experiments (PN/condom ladders, wiring/story runs) |
| `data/` | Zimbabwe demographic + initial-prevalence CSVs |
| `ANALYSIS_PLAN.md` | Scope, levers, factorial design, endpoints |

Convention: only **calibration** runs live under `experiments/` (each its own dated folder, with figures in that folder). Scenario runs go through the single root `run_scenarios.py`; their figures live in `figures/`.

## Scenario design

`SOC` (syndromic standard of care) and `POC` (etiological diagnostics) plus a full **5 × 5 × 5 factorial** over three POC-layered levers — symptomatic care-seeking × partner notification × bundled prevention — each a 5-rung ladder in `scenarios.py`. 126 distinct cells, propagated through the calibrated ensemble. See [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md).

## Diseases modeled

HIV, syphilis, NG, CT, TV, BV (+ GUD placeholder). Coinfection connectors auto-added by `sti.Sim`; `FetalHealth` wired via `custom=` for APO/ABO accounting.

## Settings

Zimbabwe (current). Kenya and South Africa deferred.

## License

[MIT](LICENSE)
