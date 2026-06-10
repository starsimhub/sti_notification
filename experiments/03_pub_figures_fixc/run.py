"""
Exp 03 — Publication figures from the Fix C 169-draw ensemble.

Drives extract_summary.py (re-runs sims, writes quantile parquets)
then plot_figures.py (renders the 5 figures).
"""
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'

EXP02_DRAWS = REPO / 'experiments' / '02_full_recalibration_fixc' / 'outputs' / 'draws_used.csv'
OUT = HERE / 'outputs'
FIG = HERE / 'figures'

if __name__ == '__main__':
    env = os.environ.copy()

    # 1) Extract time series + snapshots + quantiles from the 169-draw ensemble
    extract = [
        sys.executable, str(SCRIPTS / 'extract_summary.py'),
        '--draws-csv', str(EXP02_DRAWS),
        '--out-dir', str(OUT),
        '--n-seeds', '3',
        '--n-workers', '60',
    ]
    print('Running:', ' '.join(extract), flush=True)
    rc = subprocess.call(extract, env=env, cwd=str(REPO))
    if rc != 0:
        sys.exit(rc)

    # 2) Generate the 5 publication figures
    plot = [
        sys.executable, str(SCRIPTS / 'plot_figures.py'),
        '--ts-quantiles', str(OUT / 'ensemble_ts_quantiles.parquet'),
        '--snap-quantiles', str(OUT / 'ensemble_snapshots_quantiles.parquet'),
        '--fig-dir', str(FIG),
    ]
    print('\nRunning:', ' '.join(plot), flush=True)
    sys.exit(subprocess.call(plot, env=env, cwd=str(REPO)))
