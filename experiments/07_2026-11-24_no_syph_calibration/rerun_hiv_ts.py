"""Rerun selected draws (same K seeds as the calibration) and save HIV time series, incl. deaths.

Usage: python rerun_hiv_ts.py <draws_csv> <out_parquet>   (N_WORKERS env, default 9)
Seeds are draw_idx*1000 + k, as in run.py, so the runs reproduce the calibration's sims.
"""
import multiprocessing as mp
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402

NAMES = ['new_infections', 'new_deaths', 'prevalence', 'prevalence_15_49']


def one(task):
    sim = run.build_sim(seed=task['seed'], sim_pars=task['sim_pars'], stop=run.STOP, n_agents=run.N_AGENTS)
    sim.run()
    rows = []
    for name in NAMES:
        ann = sim.results.hiv[name].annualize()
        rows += [dict(draw_idx=task['draw_idx'], sub_idx=task['sub_idx'], result_name=name, year=int(y), value=float(v))
                 for y, v in zip(np.asarray(ann.timevec.years).astype(int), ann.values)]
    return rows


if __name__ == '__main__':
    draws_csv, out = Path(sys.argv[1]), Path(sys.argv[2])
    draws = pd.read_csv(draws_csv)
    tasks = [dict(draw_idx=int(r['draw_idx']), sub_idx=k, seed=int(r['draw_idx']) * 1000 + k,
                  sim_pars=run.row_to_sim_pars(r)) for _, r in draws.iterrows() for k in range(run.K_SEEDS)]
    print(f'{len(tasks)} sims', flush=True)
    with mp.Pool(int(os.environ.get('N_WORKERS', 9))) as pool:
        rows = [r for rs in pool.imap_unordered(one, tasks) for r in rs]
    (pd.DataFrame(rows).groupby(['draw_idx', 'result_name', 'year'])['value'].mean()
       .reset_index().to_parquet(out, index=False))
    print('wrote', out, flush=True)
