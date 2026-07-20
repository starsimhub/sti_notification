"""Regenerate the dashboard's timeseries table from the scenario run.

Reads the per-draw timeseries parquet produced by ``run_scenarios.py`` and
writes the compact, committed ``dashboard/data/timeseries.csv`` that the
dashboard reads (via ``prep.load_timeseries``). This is the only pre-aggregated
input the dashboard needs — every other quantity is read directly from
``results/scenarios.kavg.csv``.

    conda activate starsim   # needs pandas + pyarrow
    python dashboard/scripts/export_timeseries.py

NOTE: as of this writing ``results/scenarios_timeseries.parquet`` is from a
different run than ``results/scenarios.kavg.csv`` (see dashboard/README.md), so
running this now would overwrite the committed CSV with mismatched trajectories.
Only run it once the parquet has been regenerated from the current run.
"""

from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
PARQUET = REPO_ROOT / 'results' / 'scenarios_timeseries.parquet'
DEST = Path(__file__).resolve().parents[1] / 'data' / 'timeseries.csv'

DISEASES = ['ng', 'ct', 'tv', 'syph']
# Which parquet result_name gives each disease's "prevalence" trajectory.
PREV_RESULT = {d: 'prevalence' for d in DISEASES}
PREV_RESULT['syph'] = 'sexually_transmissible_prevalence'
YEAR_START, YEAR_END = 2027, 2040


def main():
    if not PARQUET.exists():
        raise SystemExit(f'Missing {PARQUET} — regenerate it with run_scenarios.py first.')
    df = pd.read_parquet(PARQUET)
    df = df[(df['year'] >= YEAR_START) & (df['year'] <= YEAR_END)]

    out = []
    for d in DISEASES:
        for metric, rname in (('prevalence', PREV_RESULT[d]), ('new_inf', 'new_infections')):
            sub = df[(df['disease'] == d) & (df['result_name'] == rname)]
            g = (sub.groupby(['care', 'pn', 'bp', 'poc', 'year'])['value']
                 .median().reset_index())
            g['disease'] = d
            g['metric'] = metric
            out.append(g)

    result = pd.concat(out, ignore_index=True)[
        ['care', 'pn', 'bp', 'poc', 'disease', 'metric', 'year', 'value']]
    DEST.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(DEST, index=False)
    print(f'Wrote {len(result)} rows to {DEST}')


if __name__ == '__main__':
    main()
