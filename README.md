# sti_notification

Health-impact analysis of demand-generation strategies — partner notification (PN) and outreach-driven care-seeking — for STI **undertreatment** in sub-Saharan Africa.

Companion to [`syph_dx_zim`](https://github.com/starsimhub/syph_dx_zim) (which focused on **overtreatment** via syndromic management). Built on [STIsim](https://github.com/starsimhub/stisim).

## Status

Project is in **Phase 0** — repo modernized for STIsim v1.5.5; minimal sim with all 7 diseases (HIV, syphilis, GUD placeholder, NG, CT, TV, BV) runs end-to-end on Zimbabwe defaults. Calibration, full scenario sweeps, and APO/ABO/DALY accounting are **not yet wired**. See [`ANALYSIS_PLAN.md`](ANALYSIS_PLAN.md) for scope, timeline, and the prioritized task list.

## Install

```bash
pip install -r requirements.txt
```

Tested against `stisim==1.5.5`, `starsim==3.3.2`, `sciris==3.2.9` on Python 3.11 (conda env `starsim`).

## Quick start

```bash
# Smoke-test the model (1000 agents, 1985–1990, all 7 diseases, ~1s)
python model.py
```

Once Phase 1 lands:

```bash
python run_pn_scens.py        # Partner-notification scenario sweep
```

## Project structure

| File / folder | Purpose |
|---|---|
| `model.py` | `make_sim()` — assembles the Zimbabwe sim (HIV + STIs + networks + interventions) |
| `hiv_model.py` | HIV module factory + HIV testing/ART/VMMC/PrEP interventions |
| `interventions.py` | Syndromic management + custom `PartnerNotification` (current + previous partner channels) + minimal syph testing stub |
| `data/` | Zimbabwe demographic + initial-prevalence CSVs (matches STIsim convention `zimbabwe_*.csv`) |
| `run_pn_scens.py` | Scenario runner (partner-notification sweep) |
| `plot_*.py` | Plotting scripts |
| `utils.py` | Shared helpers |
| `ANALYSIS_PLAN.md` | Scope, levers, scenarios, endpoints, three-phase timeline |

## Diseases modeled

HIV, syphilis, **other GUD** (placeholder), NG, CT, TV, BV. Coinfection connectors are auto-added by `sti.Sim`.

## Settings

Zimbabwe (current). Kenya and South Africa to follow once Phase 1 stabilizes.

## License

[MIT](LICENSE)
