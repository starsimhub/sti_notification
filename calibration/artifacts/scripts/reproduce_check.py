"""
Reproduce-check: re-run a small random sample of the saved ensemble
and verify the resulting trajectories sit inside the saved 95% CI
band of the full 600-sim ensemble at a rate consistent with chance.

Per-sample test: for each sampled (sim, year, result_name) value, ask
whether it falls inside [ci95_lo, ci95_hi] of the saved
ensemble_ts_quantiles. Expected violation rate ≈ 5% by chance; flag
if global violations exceed --max-violation-rate (default 15%).

Used to detect calibration drift after software upgrades. See
calibration/recalibration_guide.md.

Exit codes:
  0 — violation rate within tolerance
  1 — violation rate beyond tolerance
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
    extract_time_series,
)

# Model code uses repo-root-relative paths for data/ CSVs; chdir
# so sims work regardless of where this script is invoked.
os.chdir(REPO_ROOT)

HERE       = Path(__file__).resolve().parent
ARTIFACTS  = HERE.parent
DRAWS_CSV  = ARTIFACTS / 'draws_used.csv'
SAVED_TS_Q = ARTIFACTS / 'ensemble_ts_quantiles.parquet'


def run_one(task):
    draw_idx = task['draw_idx']
    seed = task['seed']
    sim_pars = task['sim_pars']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars)
        sim.run()
        return {'draw_idx': draw_idx, 'seed': seed, 'status': 'ok',
                'ts': extract_time_series(sim, draw_idx, seed)}
    except Exception as e:
        return {'draw_idx': draw_idx, 'seed': seed,
                'status': f'error: {type(e).__name__}: {e}',
                'ts': []}


def check_in_band(reproduced_ts: pd.DataFrame,
                  saved_q: pd.DataFrame) -> pd.DataFrame:
    """For each reproduced (sim, year, result) row, flag whether the
    value falls inside the saved [ci95_lo, ci95_hi] band. Returns the
    joined frame with an `in_band` column."""
    key = ['disease', 'result_name', 'year']
    merged = reproduced_ts.merge(
        saved_q[key + ['ci95_lo', 'ci95_hi', 'median']],
        on=key, how='inner')
    merged['in_band'] = (merged['value'] >= merged['ci95_lo']) & \
                       (merged['value'] <= merged['ci95_hi'])
    return merged


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--draws-csv', type=Path, default=DRAWS_CSV)
    ap.add_argument('--saved-quantiles', type=Path, default=SAVED_TS_Q)
    ap.add_argument('--n-draws', type=int, default=10,
                    help='How many draws to sample.')
    ap.add_argument('--n-seeds', type=int, default=3,
                    help='Seeds per draw.')
    ap.add_argument('--n-workers', type=int, default=24)
    ap.add_argument('--max-violation-rate', type=float, default=0.15,
                    help='Failure threshold on fraction of (sim, year, '
                         'result) points falling outside the saved 95%% '
                         'CI band. Chance baseline is ~5%%; default 15%% '
                         'allows ~3x slack.')
    ap.add_argument('--seed', type=int, default=12345,
                    help='RNG seed for the draw sample.')
    args = ap.parse_args()

    if not args.draws_csv.exists():
        sys.exit(f'draws CSV not found: {args.draws_csv}')
    if not args.saved_quantiles.exists():
        sys.exit(f'saved quantiles not found: {args.saved_quantiles}')

    rng = np.random.default_rng(args.seed)
    draws = pd.read_csv(args.draws_csv)
    n_take = min(args.n_draws, len(draws))
    idx = rng.choice(len(draws), n_take, replace=False)
    sampled = draws.iloc[sorted(idx.tolist())].reset_index(drop=True)
    print(f'Sampled {len(sampled)} draws (seed={args.seed}) from {args.draws_csv}')
    print(f'Re-running each with {args.n_seeds} seeds on {args.n_workers} workers')

    SEED_BASE = 100_000  # matches the exp 40 / 41 convention
    tasks = []
    for _, row in sampled.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row)
        for s_idx in range(args.n_seeds):
            seed = SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di, 'seed': seed,
                          'sim_pars': sim_pars})

    all_ts = []
    t0 = time.time()
    n_ok = n_err = 0
    with mp.Pool(args.n_workers, maxtasksperchild=10) as pool:
        for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            if res['status'] == 'ok':
                all_ts.extend(res['ts'])
                n_ok += 1
            else:
                n_err += 1
                print(f'  ERROR draw {res["draw_idx"]} seed {res["seed"]}: {res["status"]}',
                      flush=True)
            if i % 10 == 0 or i == len(tasks):
                print(f'  [{i}/{len(tasks)}] elapsed={time.time()-t0:.0f}s '
                      f'ok={n_ok} err={n_err}', flush=True)

    if not all_ts:
        sys.exit('No successful sims — nothing to compare.')

    ts_df = pd.DataFrame(all_ts)
    saved_q = pd.read_parquet(args.saved_quantiles)
    joined = check_in_band(ts_df, saved_q)

    n_total = len(joined)
    n_violations = int((~joined['in_band']).sum())
    rate = n_violations / n_total if n_total else 0.0
    print(f'\nChecked {n_total} (sim, year, result) points against saved 95% CI')
    print(f'Violations: {n_violations} ({rate:.1%}; chance baseline ~5%)')

    # Where do violations concentrate?
    if n_violations:
        per_result = (joined[~joined['in_band']]
                      .groupby(['disease', 'result_name']).size()
                      .sort_values(ascending=False).head(10))
        print(f'\nTop violators by (disease, result_name):')
        print(per_result.to_string())

    if rate <= args.max_violation_rate:
        print(f'\nPASS — violation rate {rate:.1%} ≤ {args.max_violation_rate:.1%}')
        sys.exit(0)
    print(f'\nFAIL — violation rate {rate:.1%} > {args.max_violation_rate:.1%}')
    sys.exit(1)


if __name__ == '__main__':
    main()
