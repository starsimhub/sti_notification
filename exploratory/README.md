# Exploratory scripts

Older / one-off plotting + analysis scripts that produced the figures now
sitting in `../figures/archive/` (or `../figures/supplementary/` for the two
that still see use as supplementary materials).

Kept for reproducibility — run any of these from the repo root
(`conda run -n starsim python exploratory/<script>.py`). Outputs land in
`../figures/archive/` or `../figures/supplementary/` as appropriate;
regenerating one won't clutter the deck-figure top level.

## Contents

| Script | Produces | Notes |
|---|---|---|
| `plot_cascade.py` | `figures/fig_cascades_4panel_soc.png` (deck Slide 1), `figures/archive/fig_cascade_ct_soc.png`, `figures/archive/fig_cascade_vds_soc.png` | Slide 1's cascade figure lives here. Assumes CWD = repo root (uses relative paths). |
| `plot_epi.py` | `figures/supplementary/fig_epi_overview.png` | HIV/STI overview time series (SOC, 1990–2040) + age × sex snapshots at 2027. Reads `results/scenarios_timeseries.parquet` + `results/scenarios_snapshots.parquet` (aggregated, committable). Deck-supplementary. |
| `plot_pn_story.py` | `figures/supplementary/fig_pn_story_grounding.png` | PN funnel volumes / under-vs-over notification. Deck-supplementary. |
| `plot_poc_alone.py` | `figures/archive/fig_poc_alone.png` | Precursor to Slide 6 (bars only, no time series). |
| `plot_pn_cascade.py` | `figures/archive/fig_pn_cascade.png` | Pre-restructuring PN cascade. Superseded by Slide 5. |
| `plot_layering.py` | `figures/archive/fig_layering_{1way,cumulative}.png` | Earlier layering exploration. Superseded by Slides 9–11. |
| `plot_layering_newinf.py` | `figures/archive/fig_layering_{1way,cumulative}_newinf.png` | Same but for new-infections. Superseded. |
| `plot_validation.py` | `figures/archive/fig_validation_overview.png` | Model-vs-data validation panel. |
| `plot_validation_pn.py` | `figures/archive/fig_validation_pn_cascade.png` | PN-cascade validation panel. |
| `plot_validation_yield.py` | `figures/archive/fig_validation_yield.png` | Yield validation panel. |
| `vds_viz.py` | `figures/archive/fig_vds_{upset,burden,cooccur}.png` | Original VDS-etiology viz. Superseded by `../plotting/plot_slide4_etiology.py`. |
| `plot_reinfection_tree.py` | ad-hoc reinfection-tree figure | Not tied to a deck slide. |
| `plot_sims.py` | ad-hoc per-sim time series | Debug/inspection tool. |
| `measure_pn_followups.py` | `results/pn_partner_counts.csv`, `results/pn_story.json` | One-off measurement script for PN partner distributions. |
| `partner_stats.py` | terminal output | One-off partner-network summary. |
| `profile_scenario.py` | terminal output / profiler | Runtime profiling utility. |
