"""Aggregate raw K-averaged factorial outputs into committable slim parquets.

Reads ``raw_results/scenarios_timeseries.parquet`` (per-(cell,draw) K-averaged
per-sim rows) and writes ``results/scenarios_timeseries.parquet`` with one
row per ``(cell, care, pn, bp, poc, disease, result_name, year)`` and
``median`` + ``p_lo`` + ``p_hi`` columns.

Called on the VM after ``run_scenarios.py`` completes. Config lives at the
top of ``process_results()`` — change the whitelist and rerun, no factorial
rerun needed.

Design doc: docs/superpowers/specs/2026-07-20-plot-data-extract-design.md
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

REPO = Path(__file__).parent
RAW = REPO / 'raw_results'
OUT = REPO / 'results'

# What the current slide plots + dashboard actually consume. Widen without a
# factorial rerun as long as run_scenarios.py's TS_RESULTS / INTV_TS_RESULTS
# already extract it.
DEFAULT_RESULT_NAMES = ('prevalence', 'new_infections',
                        'prevalence_f', 'prevalence_m')
DEFAULT_DISEASES = ('ng', 'ct', 'tv', 'syph', 'hiv')
DEFAULT_YEARS = (1990, 2040)
DEFAULT_QUANTILES = (0.25, 0.75)   # None → median only

# Snapshot config — fig_epi_overview only wants SOC at 2027.
SNAP_CELL = 'SOC'
SNAP_YEAR = 2027


def _aggregate(df, group_cols, quantiles):
    """Groupby group_cols, compute median (+ p_lo/p_hi if quantiles given)."""
    g = df.groupby(list(group_cols))['value']
    out = pd.DataFrame({'median': g.median()})
    if quantiles is not None:
        lo, hi = quantiles
        out['p_lo'] = g.quantile(lo)
        out['p_hi'] = g.quantile(hi)
    return out.reset_index()


def process_results(
    result_names=DEFAULT_RESULT_NAMES,
    diseases=DEFAULT_DISEASES,
    years=DEFAULT_YEARS,
    quantiles=DEFAULT_QUANTILES,
):
    """Aggregate raw TS + snapshots → committable slim parquets."""
    OUT.mkdir(parents=True, exist_ok=True)

    ts_src = RAW / 'scenarios_timeseries.parquet'
    if not ts_src.exists():
        raise SystemExit(
            f'[process_results] missing {ts_src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    ts = pd.read_parquet(ts_src)
    ts = ts[
        ts.result_name.isin(result_names)
        & ts.disease.isin(diseases)
        & (ts.year >= years[0])
        & (ts.year <= years[1])
    ]
    assert len(ts) > 0, (
        f'no rows matched result_names={result_names}, diseases={diseases}, '
        f'years={years}. Raw result_names (sample): {sorted(ts.result_name.unique())[:10]}'
    )
    group_cols = ('cell', 'care', 'pn', 'bp', 'poc', 'disease', 'result_name', 'year')
    ts_agg = _aggregate(ts, group_cols, quantiles)
    ts_dst = OUT / 'scenarios_timeseries.parquet'
    ts_agg.to_parquet(ts_dst, index=False, compression='zstd')
    print(f'timeseries: {len(ts):>7d} raw rows -> {len(ts_agg):>7d} aggregated rows '
          f'({ts_dst.stat().st_size/1024:.0f} KB)')

    snap_src = RAW / 'scenarios_snapshots.parquet'
    if not snap_src.exists():
        raise SystemExit(
            f'[process_results] missing {snap_src}. '
            f'Run run_scenarios.py on the VM first, or scp the file from there.'
        )
    sn = pd.read_parquet(snap_src)
    sn = sn[(sn.cell == SNAP_CELL) & (sn.year == SNAP_YEAR)]
    assert len(sn) > 0, (
        f'no snapshot rows for cell={SNAP_CELL}, year={SNAP_YEAR}. '
        f'Raw cells (sample): {sorted(sn.cell.unique())[:5]}, '
        f'years: {sorted(sn.year.unique())}'
    )
    snap_group = ('cell', 'disease', 'result_name', 'sex', 'age_bin', 'year')
    sn_agg = _aggregate(sn, snap_group, quantiles)
    snap_dst = OUT / 'scenarios_snapshots.parquet'
    sn_agg.to_parquet(snap_dst, index=False, compression='zstd')
    print(f'snapshots:  {len(sn):>7d} raw rows -> {len(sn_agg):>7d} aggregated rows '
          f'({snap_dst.stat().st_size/1024:.0f} KB)')


if __name__ == '__main__':
    process_results()
