# Deck plotting scripts

Slide-by-slide plotting scripts for the STI-notification deck. Every
script reads from repo-root `results/` and writes PNGs into repo-root
`figures/`. Run each from the repo root:

```bash
conda run -n starsim python plotting/plot_slide6.py
```

## Deck slide index

| Slide | Script | Figure | Data |
|---|---|---|---|
| 3 | `plot_slide3.py` | `fig_slide3.png` | `scenarios.kavg.csv`, `soc_overtreatment.csv`, `specificity.csv` |
| 4 | `plot_slide4_etiology.py` | `fig_slide4_etiology.png` (4.25 × 5.88 portrait) | `vds_etiology.csv` |
| 5 | `plot_slide5.py` | `fig_slide5.png` | `scenarios.kavg.csv`, `specificity.csv` |
| 6 | `plot_slide6.py` | `fig_slide6.png` | `scenarios.kavg.csv`, `scenarios_timeseries.parquet` |
| 9 | `plot_slide9.py` | `fig_slide9.png` | same as slide 6 |
| 10 | `plot_slide10.py` | `fig_slide10.png` | same as slide 6 |
| 11 | `plot_slide11.py` | `fig_slide11.png` | same as slide 6 |
| 12 | `plot_slide12.py` | `fig_slide12.png` (4-panel heatmap: % reduction in cum. NG+CT+TV+syph infections vs SOC, care × PN, one panel per BP level) | `scenarios_timeseries.parquet` |

Slide 1's cascade figure (`fig_cascades_4panel_soc.png`) is produced by
`../exploratory/plot_cascade.py`. Slide 2 is text only. Slide 4's
PPV/NPV/FDR/FOR table is delivered inline (values in the slide's
commit / conversation history, not a rendered figure).

## Shared helpers

- `plot_result1.py` — legacy figure script whose `precision_panel`,
  `specificity_panel`, and `upset_panels` are imported by
  `plot_slide4_etiology.py` and `plot_slide5.py`. Its own standalone
  `main()` writes `figures/archive/fig_result1.png`.
- `plot_slide6.py::build_ts_grid_figure()` — the 2-row × 4-disease TS
  + endpoint-bar layout. Slides 6, 9, 10, 11 all call this with
  different arm dicts.

## Data prerequisites

- `results/scenarios.kavg.csv` — K=5-averaged scalars per (cell, draw).
  Committed. Produced by `run_scenarios.py`.
- `results/specificity.csv` — person-level SOC vs POC-plain treatment
  and PN over-rates (5 seeds). Produced by
  `diagnostics/specificity_tracer.py`.
- `results/soc_overtreatment.csv` — per-VDS-woman contingency of
  (n_drugs, n_actual_STIs). Produced by the same tracer.
- `results/vds_etiology.csv` — VDS coinfection composition for the
  upset. Produced by `diagnostics/vds_etiology.py`.
- `results/scenarios_timeseries.parquet` — annual per-disease time
  series. VM-only (see [../CLAUDE.md](../CLAUDE.md) §"VM-only data
  files").

If a plot needs a parquet that isn't in `results/` locally, either
`scp` it from the VM or regenerate on the VM via `run_scenarios.py`.
