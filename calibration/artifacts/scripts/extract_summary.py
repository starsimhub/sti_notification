"""
Re-run the saved ensemble at multiple seeds and extract annualised
time series + 2016/2020 age × sex snapshots. Aggregate to ensemble
quantiles (median + 80% / 95% CI).

Adapted from experiments/41_pub_figures_final/run.py on the
archive/calibration-2026-06 branch. Use this script when you need to
regenerate the figures or refresh the quantile parquets — e.g.
because the saved raw parquets are no longer available, or after a
recalibration.
"""
from __future__ import annotations

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import argparse
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from _pipeline import (
    REPO_ROOT, build_sim, row_to_sim_pars,
    extract_time_series, extract_snapshots,
    compute_ts_quantiles, compute_snap_quantiles,
)

os.chdir(REPO_ROOT)


def run_one(task):
    di = task['draw_idx']
    seed = task['seed']
    sim_pars = task['sim_pars']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars)
        sim.run()
        return {'draw_idx': di, 'seed': seed, 'status': 'ok',
                'ts': extract_time_series(sim, di, seed),
                'snap': extract_snapshots(sim, di, seed)}
    except Exception as e:
        return {'draw_idx': di, 'seed': seed,
                'status': f'error: {type(e).__name__}: {e}',
                'ts': [], 'snap': []}


def _safe_write(df, path, label):
    try:
        df.to_parquet(path, index=False)
        print(f'  {label} -> {path.name}: {len(df)} rows')
    except (ImportError, ValueError) as e:
        pkl_path = path.with_suffix('.pkl')
        df.to_pickle(pkl_path)
        print(f'  {label} -> {pkl_path.name} (parquet engine missing: {e}): '
              f'{len(df)} rows')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--draws-csv', type=Path, required=True,
                    help='Posterior draws to re-run (typically draws_used.csv).')
    ap.add_argument('--out-dir', type=Path, required=True,
                    help='Directory for the parquet outputs.')
    ap.add_argument('--n-seeds', type=int, default=3)
    ap.add_argument('--n-workers', type=int, default=24)
    ap.add_argument('--keep-raw', action='store_true',
                    help='Also write per-(draw, seed) raw parquets '
                         '(~11 MB time series, ~1 MB snapshots). '
                         'Default: only the quantile parquets.')
    args = ap.parse_args()

    if not args.draws_csv.exists():
        sys.exit(f'draws CSV not found: {args.draws_csv}')
    args.out_dir.mkdir(parents=True, exist_ok=True)

    draws = pd.read_csv(args.draws_csv)
    print(f'Loaded {len(draws)} draws from {args.draws_csv}')

    SEED_BASE = 100_000
    tasks = []
    for _, row in draws.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row.to_dict())
        for s_idx in range(args.n_seeds):
            seed = SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di, 'seed': seed,
                          'sim_pars': sim_pars})
    print(f'Total sims: {len(tasks)} ({len(draws)} × {args.n_seeds} seeds)')
    print(f'Running on {args.n_workers} workers...')

    t0 = time.time()
    all_ts, all_snap = [], []
    n_ok = n_err = 0
    with mp.Pool(args.n_workers, maxtasksperchild=10) as pool:
        for i, res in enumerate(
                pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            if res['status'] == 'ok':
                all_ts.extend(res['ts'])
                all_snap.extend(res['snap'])
                n_ok += 1
            else:
                n_err += 1
                if n_err <= 5:
                    print(f'  ERROR draw {res["draw_idx"]} seed {res["seed"]}: '
                          f'{res["status"]}', flush=True)
            if i % 30 == 0 or i == len(tasks):
                elapsed = time.time() - t0
                eta = (len(tasks) - i) * elapsed / max(i, 1)
                print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s eta={eta:.0f}s '
                      f'ok={n_ok} err={n_err}', flush=True)

    print(f'\nDone in {time.time()-t0:.1f}s. OK: {n_ok}, errors: {n_err}')

    ts_df = pd.DataFrame(all_ts)
    snap_df = pd.DataFrame(all_snap)

    if args.keep_raw:
        if len(ts_df):
            _safe_write(ts_df, args.out_dir / 'time_series.parquet', 'time_series')
        if len(snap_df):
            _safe_write(snap_df, args.out_dir / 'snapshots.parquet', 'snapshots')

    if len(ts_df):
        ts_q = compute_ts_quantiles(ts_df)
        _safe_write(ts_q, args.out_dir / 'ensemble_ts_quantiles.parquet',
                    'ts quantiles')
    if len(snap_df):
        snap_q = compute_snap_quantiles(snap_df)
        _safe_write(snap_q, args.out_dir / 'ensemble_snapshots_quantiles.parquet',
                    'snap quantiles')


if __name__ == '__main__':
    main()
