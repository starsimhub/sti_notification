"""
Exp 01 — Coverage check on the Fix C corrected baseline.

50 LHS draws (1 seed each) from priors.py through the model, extract
key time series, write per-(draw, year, disease, result_name) parquet
+ ensemble quantiles.

Companion plotting in plot.py overlays surveillance data on the
ensemble bands.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
import time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))
os.chdir(REPO)

from _pipeline import (  # noqa: E402
    build_sim, generate_prior_draws, row_to_sim_pars,
    extract_time_series, compute_ts_quantiles,
)

HERE = Path(__file__).parent
OUT  = HERE / 'outputs'
OUT.mkdir(parents=True, exist_ok=True)

N_DRAWS  = int(os.environ.get('N_DRAWS', 50))
LHS_SEED = int(os.environ.get('LHS_SEED', 2026))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
SIM_SEED_BASE = 200_000


def run_one(task):
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    seed = task['seed']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars)
        sim.run()
        return {
            'draw_idx': draw_idx, 'seed': seed, 'status': 'ok',
            'ts': extract_time_series(sim, draw_idx, seed),
        }
    except Exception as e:
        return {
            'draw_idx': draw_idx, 'seed': seed,
            'status': f'error: {type(e).__name__}: {e}',
            'ts': [],
        }


def main():
    prior_df = generate_prior_draws(N_DRAWS, LHS_SEED)
    prior_df.to_csv(OUT / 'priors.csv', index=False)
    print(f'Prior: {len(prior_df)} draws on {len(prior_df.columns)-1} params, '
          f'seed={LHS_SEED}')

    tasks = []
    for _, row in prior_df.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row)
        tasks.append({
            'draw_idx': di,
            'sim_pars': sim_pars,
            'seed': SIM_SEED_BASE + di,
        })
    print(f'Running {len(tasks)} sims on {N_WORKERS} workers...')

    t0 = time.time()
    all_ts = []
    n_ok = n_err = 0
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        for i, res in enumerate(
                pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            if res['status'] == 'ok':
                all_ts.extend(res['ts'])
                n_ok += 1
            else:
                n_err += 1
                if n_err <= 5:
                    print(f'  ERROR draw {res["draw_idx"]}: {res["status"]}',
                          flush=True)
            if i % 10 == 0 or i == len(tasks):
                elapsed = time.time() - t0
                eta = (len(tasks) - i) * elapsed / max(i, 1)
                print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s eta={eta:.0f}s '
                      f'ok={n_ok} err={n_err}', flush=True)

    print(f'\nDone in {time.time()-t0:.1f}s. OK: {n_ok}, errors: {n_err}')

    if not all_ts:
        print('No successful sims, aborting.')
        return

    ts_df = pd.DataFrame(all_ts)
    ts_df.to_parquet(OUT / 'time_series.parquet', index=False)
    print(f'  Wrote {len(ts_df)} time-series rows -> outputs/time_series.parquet')

    ts_q = compute_ts_quantiles(ts_df)
    ts_q.to_parquet(OUT / 'ensemble_ts_quantiles.parquet', index=False)
    print(f'  Wrote ensemble quantiles -> outputs/ensemble_ts_quantiles.parquet')


if __name__ == '__main__':
    main()
