"""Build the committable slim `results/*.parquet` slices from the full
`raw_results/*.parquet` fat outputs of run_scenarios.py.

Filters are the union of what the 8 committed slide plots + fig_epi_overview
actually pull. Any slide adding a new arm or metric requires updating the
constants below.

Consumers of the slim files (do not edit paths — they align with these):
  - plotting/plot_slide{6,9,10,11}.py  reads results/scenarios_timeseries.parquet
  - exploratory/plot_epi.py            reads results/scenarios_timeseries.parquet
                                        + results/scenarios_snapshots.parquet

Design doc: docs/superpowers/specs/2026-07-20-plot-data-extract-design.md
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).parent
RAW = REPO / 'raw_results'
OUT = REPO / 'results'

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
SNAP_YEAR = 2027  # fig_epi_overview cross-section year


def slim_timeseries():
    src = RAW / 'scenarios_timeseries.parquet'
    dst = OUT / 'scenarios_timeseries.parquet'
    if not src.exists():
        raise SystemExit(
            f'[build_plot_data] missing {src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    ts = pd.read_parquet(src)
    slim = ts[
        ts.cell.isin(PLOT_CELLS)
        & ts.result_name.isin(PLOT_RESULTS)
        & ts.disease.isin(PLOT_DISEASES)
    ].reset_index(drop=True)
    # Self-verify: every whitelisted cell that appears in raw must appear in slim.
    raw_cells = set(ts.cell.unique()) & PLOT_CELLS
    slim_cells = set(slim.cell.unique())
    missing = raw_cells - slim_cells
    assert not missing, f'lost cells during filter: {missing}'
    assert set(slim.cell.unique()) <= PLOT_CELLS, 'extra cells leaked through'
    assert set(slim.result_name.unique()) <= PLOT_RESULTS, 'extra result_names leaked'
    slim.to_parquet(dst, index=False, compression='zstd')
    print(f'timeseries: {len(ts):>7d} rows ({src.stat().st_size/1024:>6.0f} KB) '
          f'-> {len(slim):>7d} rows ({dst.stat().st_size/1024:>6.0f} KB)')


def slim_snapshots():
    src = RAW / 'scenarios_snapshots.parquet'
    dst = OUT / 'scenarios_snapshots.parquet'
    if not src.exists():
        raise SystemExit(
            f'[build_plot_data] missing {src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    sn = pd.read_parquet(src)
    slim = sn[(sn.cell == 'SOC') & (sn.year == SNAP_YEAR)].reset_index(drop=True)
    assert (slim.cell == 'SOC').all(), 'non-SOC cells leaked'
    assert (slim.year == SNAP_YEAR).all(), 'non-SNAP_YEAR rows leaked'
    slim.to_parquet(dst, index=False, compression='zstd')
    print(f'snapshots:  {len(sn):>7d} rows ({src.stat().st_size/1024:>6.0f} KB) '
          f'-> {len(slim):>7d} rows ({dst.stat().st_size/1024:>6.0f} KB)')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    slim_timeseries()
    slim_snapshots()


if __name__ == '__main__':
    main()
