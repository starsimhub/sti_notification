# Plot-data extract design

**Date:** 2026-07-20
**Status:** design (approved 2026-07-20)

## Problem

`run_scenarios.py` writes four artifacts to `results/` after a full factorial
run:

| Artifact | Full-run size | Consumers |
|---|---|---|
| `scenarios.jsonl` | ~5.7 MB | none (raw per-sim scalars) |
| `scenarios.kavg.csv` | ~340 KB | plot_slide 3, 5, 6, 9, 10, 11, 12, 13 |
| `scenarios_timeseries.parquet` | ~1.7 MB | plot_slide 6, 9, 10, 11; `exploratory/plot_epi.py` |
| `scenarios_snapshots.parquet` | ~880 KB | `exploratory/plot_epi.py` |

The K-avg CSV is small enough to commit and already tracked. The two parquets
and the jsonl are VM-only per the current CLAUDE.md convention — plots on a
Mac clone silently break because their data isn't there.

Goal: make the entire `results/` directory committable so any clone can
regenerate every committed figure without VM access, while keeping the fat
raw outputs out of git.

## Scope

**In:** the 8 committed `figures/fig_slide*.png` plots + the two
`figures/supplementary/*.png` figures. `fig_pn_story_grounding` needs no
scenarios data. `fig_epi_overview` needs the timeseries + snapshots parquets
for the SOC cell only.

**Out:** `exploratory/plot_layering*.py`, `plot_validation*.py`,
`plot_reinfection_tree.py`, etc. These read the same parquets but only run
on the VM; they get their path constants pointed at `raw_results/` in the
same changeset so they keep working there.

## Design

### Directory layout

Split the two roles `results/` currently plays:

```
raw_results/                        (NEW, gitignored — VM-only fat outputs)
├── scenarios.jsonl                 per-sim raw scalars
├── scenarios_timeseries.parquet    full 65-cell × 5-draw TS
├── scenarios_snapshots.parquet     full 65-cell × 5-draw age×sex snapshots
├── scenarios_smoke.jsonl / _timeseries.parquet / _snapshots.parquet
└── (run log files, .out files)

results/                            (existing, 100% committable)
├── scenarios.kavg.csv              unchanged, run_scenarios.py writes directly
├── scenarios_timeseries.parquet    NEW slim ~500 KB — build_plot_data.py writes
├── scenarios_snapshots.parquet     NEW slim ~30 KB — build_plot_data.py writes
├── scenarios_smoke.kavg.csv        unchanged
├── specificity.csv, ppv_table.csv, pn_story.json, ...   unchanged
```

Rule: everything in `results/` is safe to commit. Anything larger than the
low six-figure byte range belongs in `raw_results/`.

The slim parquets in `results/` land at the same paths the plots already
read (`results/scenarios_timeseries.parquet`,
`results/scenarios_snapshots.parquet`), so **no plot-script edits are needed**
for the 8 slide plots or `fig_epi_overview`.

### `build_plot_data.py`

New root-level script (~60 lines). Reads `raw_results/*.parquet`, filters,
downcasts, writes to `results/*.parquet`.

Filter constants at the top, single source of truth for "what the deck needs":

```python
# Cells needed by slides 6/9/10/11 + fig_epi_overview (SOC-only).
# Comments cite the specific plot script that pulls each cell.
PLOT_CELLS = {
    'SOC',                                          # all
    'POC_c-baseline_p-baseline_b-none',             # slide 6, 9
    'POC_c-baseline_p-low_b-none',                  # slide 9
    'POC_c-baseline_p-moderate_b-none',             # slide 9, 10
    'POC_c-baseline_p-high_b-none',                 # slide 9
    'POC_c-baseline_p-moderate_b-low',              # slide 10
    'POC_c-baseline_p-moderate_b-moderate',         # slide 10, 11
    'POC_c-baseline_p-moderate_b-high',             # slide 10
    'POC_c-low_p-moderate_b-moderate',              # slide 11
    'POC_c-moderate_p-moderate_b-moderate',         # slide 11
    'POC_c-high_p-moderate_b-moderate',             # slide 11
}
PLOT_RESULTS = {
    'prevalence',       # slide 6/9/10/11 row 0
    'new_infections',   # slide 6/9/10/11 row 1
    'prevalence_f',     # fig_epi_overview
    'prevalence_m',     # fig_epi_overview
}
PLOT_DISEASES = {'ng', 'ct', 'tv', 'syph', 'hiv'}
SNAP_YEAR = 2027       # fig_epi_overview cross-section year
```

Steps:
1. Read `raw_results/scenarios_timeseries.parquet`; filter to
   `PLOT_CELLS × PLOT_RESULTS × PLOT_DISEASES`; downcast `value` to float32;
   write to `results/scenarios_timeseries.parquet` (zstd compression).
2. Read `raw_results/scenarios_snapshots.parquet`; filter to
   `cell == 'SOC'` and `year == SNAP_YEAR`; downcast; write to
   `results/scenarios_snapshots.parquet` (zstd).
3. Print row count + byte size before/after per file so the operator can see
   the compression ratio at a glance.

Fails loudly with an actionable error if either raw parquet is missing (the
common case being "you ran this on a clone without the raw outputs").

Rejected alternative: static-analyse the plot scripts to auto-derive the cell
whitelist. Fragile — plots may use isin() lists, string-concat cell names,
or compute derived arms.

### `run_scenarios.py` edits

Two-line change to output routing:

```python
RAW_OUT = REPO / 'raw_results'    # was: OUT = REPO / 'results'
OUT     = REPO / 'results'        # kept for the small kavg CSV only
```

- `outfile`, `ts_parquet`, `snap_parquet` → `RAW_OUT`
- `scalars_csv` (K-avg) → `OUT`
- Same for the smoke variants.

`RAW_OUT.mkdir(parents=True, exist_ok=True)` alongside the existing
`OUT.mkdir`.

### `.gitignore`

Add `raw_results/`.

### Exploratory-script path updates

Six exploratory scripts still read `results/scenarios_timeseries.parquet` (or
snapshots). With the slim files at those paths they'd break silently because
the filtered data doesn't contain the cells/metrics they need. Point them at
the raw parquets in the same commit so they keep working on the VM:

- `exploratory/plot_epi.py` — reads both TS + SNAP. Keep on `results/` (SOC
  is in the slim TS and fig_epi_overview needs the slim SNAP). **No change.**
- `exploratory/plot_layering.py` — TS → `raw_results/`
- `exploratory/plot_layering_newinf.py` — TS → `raw_results/`
- `exploratory/plot_validation.py` — reads `scenarios_smoke_timeseries.parquet`
  and `scenarios_smoke.kavg.csv`. Smoke TS → `raw_results/`, smoke kavg stays
  in `results/`.
- `exploratory/plot_validation_pn.py` — smoke kavg only, stays in `results/`.
  **No change.**
- `exploratory/plot_validation_yield.py` — smoke kavg only. **No change.**

Net: 3 exploratory scripts get a path constant change, 3 need nothing.

### CLAUDE.md update

The current "VM-only data files (note for the local agent)" section
enumerates each parquet as VM-only. Replace with the new rule: `results/` is
always committable, `raw_results/` (if present) is VM-only. Note that
`build_plot_data.py` regenerates the slim `results/*.parquet` from
`raw_results/*.parquet` after each factorial run.

## Migration

One-time steps to land the change on a VM that already has full parquets in
`results/`:

1. `mkdir raw_results`
2. `mv results/scenarios.jsonl results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet raw_results/`
3. Same for `scenarios_smoke.{jsonl,_timeseries.parquet,_snapshots.parquet}` if present.
4. `git rm --cached results/scenarios_timeseries.parquet results/scenarios_snapshots.parquet` for any that were previously tracked. (The M-status parquets on `main` at design time were tracked earlier and now need un-tracking.)
5. Run `python build_plot_data.py`. New slim `results/*.parquet` land.
6. `git add results/*.parquet .gitignore run_scenarios.py build_plot_data.py exploratory/*.py CLAUDE.md`.
7. Commit.

On a fresh clone with no VM access: `results/*.parquet` are the committed
slim files. All 8 slide plots + `fig_epi_overview` run against them
unchanged. `raw_results/` is absent; `build_plot_data.py` errors with a
helpful message if invoked.

## Success criteria

- `results/` on a fresh clone contains everything needed to regenerate the 8
  `figures/fig_slide*.png` + both `figures/supplementary/*.png`.
- Total committed `results/` size stays under 2 MB even at N_DRAWS=5.
- `run_scenarios.py` still runs end-to-end and writes fat outputs to
  `raw_results/`, small K-avg to `results/`.
- `python build_plot_data.py` after `run_scenarios.py` refreshes the slim
  files.
- All 10 in-scope plots run cleanly against committed data with zero edits.
- Exploratory scripts run on the VM against `raw_results/`.

## Out of scope

- Refactoring plots to share common data-loading helpers.
- Migrating any other results/ file (specificity.csv, pn_story.json, etc.) —
  they're already small and committed.
- Alternative filter definitions driven by static analysis of plot scripts.
- Compressing kavg.csv further (it's fine).
