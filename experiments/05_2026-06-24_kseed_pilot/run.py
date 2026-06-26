"""K=5 sim-averaging pilot — 20 LHS draws × 5 seeds, no filtering.

Sanity check before committing to a full single-phase K=5 recalibration.
We want to see:
- Within-draw seed spread (the "0%, 15%, 0%, 0%, 0%" pattern the user
  described — does it actually happen?)
- Per-draw means after averaging
- How draws look without ANY filter applied

Matches exp 04 priors exactly (NG β floor lifted to 0.10) so the 20
draws here are the FIRST 20 of exp 04's 500-draw LHS — direct
comparability against exp 04's single-seed phase 1 results.

Output: results.jsonl (100 rows, one per sim), per_draw_summary.csv (20
rows). Console prints the readable table.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / 'calibration' / 'artifacts' / 'scripts'))
sys.path.insert(0, str(REPO_ROOT))

# Match exp 04 priors exactly (NG β floor at 0.10, others unchanged)
from priors import calib_pars  # noqa: E402
calib_pars['ng.beta_m2f'] = ('NG β (M→F)', 0.10, 0.60, True)

from _pipeline import (  # noqa: E402
    generate_prior_draws, row_to_sim_pars, build_sim,
    extract_calibration_summary, REPO_ROOT as PIPELINE_REPO,
)

os.chdir(PIPELINE_REPO)

OUT_DIR = HERE / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

N_DRAWS = 20
K_SEEDS = 5
N_WORKERS = 60
LHS_SEED = 45  # match exp 04
LHS_TOTAL = 500  # sample full exp 04 size, take first N_DRAWS for apples-to-apples

REPORT_COLS = [
    'hiv_prev_2010_2020', 'trep_f_2016', 'nontrep_f_2016',
    'hiv_trep_ratio_2016', 'fsw_prev_2019',
    'primary_share', 'secondary_share', 'early_lat_share',
    'pf_2035_2040_syph', 'pf_2035_2040_ng',
    'pf_2035_2040_ct', 'pf_2035_2040_tv',
    'sustained_hiv', 'sustained_syph', 'sustained_ng',
    'sustained_ct', 'sustained_tv',
]
TARGETS = {
    'hiv_prev_2010_2020':  (0.115, 0.155),
    'trep_f_2016':         (0.020, 0.040),
    'nontrep_f_2016':      (0.005, 0.015),
    'hiv_trep_ratio_2016': (3.0,   6.0),
    'fsw_prev_2019':       (0.40,  0.70),
    'primary_share':       (0.45,  0.65),
    'secondary_share':     (0.25,  0.45),
    'early_lat_share':     (0.05,  0.25),
}


def run_one(task):
    draw_idx = task['draw_idx']
    sub_idx = task['sub_idx']
    seed = task['seed']
    sim_pars = task['sim_pars']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars)
        sim.run()
        summary = extract_calibration_summary(sim, draw_idx, seed)
        summary['sub_idx'] = sub_idx
        return summary
    except Exception as e:
        return {'draw_idx': draw_idx, 'seed': seed, 'sub_idx': sub_idx,
                'status': f'error: {type(e).__name__}: {e}'}


def main():
    print(f'exp 05 pilot (2026-06-24) — K={K_SEEDS} sim-averaging, '
          f'{N_DRAWS} LHS draws, no filtering')
    priors = generate_prior_draws(LHS_TOTAL, LHS_SEED).head(N_DRAWS)
    priors_csv = OUT_DIR / 'priors.csv'
    priors.to_csv(priors_csv, index=False)
    print(f'  wrote {len(priors)} priors to {priors_csv}')

    tasks = []
    for _, row in priors.iterrows():
        di = int(row['draw_idx'])
        sp = row_to_sim_pars(row)
        for sub_idx in range(K_SEEDS):
            tasks.append({'draw_idx': di, 'sub_idx': sub_idx,
                          'sim_pars': sp, 'seed': di * 1000 + sub_idx})

    print(f'  {len(tasks)} sims on {N_WORKERS} workers...')
    t0 = time.time()
    results_jsonl = OUT_DIR / 'results.jsonl'
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with results_jsonl.open('w') as fout:
            for i, summary in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(summary) + '\n')
                fout.flush()
                if i % 20 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    print(f'    [{i:3d}/{len(tasks)}] {elapsed:.0f}s', flush=True)
    print(f'  done in {time.time()-t0:.0f}s')

    rows = [json.loads(l) for l in results_jsonl.open()]
    df = pd.DataFrame(rows)
    ok = df[df['status'] == 'ok'].copy()
    if len(ok) < len(df):
        print(f'  WARNING: {len(df) - len(ok)} sims errored')

    # Per-draw aggregation: mean across K seeds, plus per-seed spread
    numeric = [c for c in REPORT_COLS if c in ok.columns]
    means = ok.groupby('draw_idx')[numeric].mean()
    mins = ok.groupby('draw_idx')[numeric].min()
    maxs = ok.groupby('draw_idx')[numeric].max()

    # Build per-draw table
    per_draw = means.copy()
    per_draw.columns = [f'{c}_mean' for c in per_draw.columns]
    per_draw_csv = OUT_DIR / 'per_draw_means.csv'
    per_draw.to_csv(per_draw_csv)
    print(f'\nWrote {per_draw_csv}')

    # Console report
    print(f'\n=== Per-draw means (K={K_SEEDS} seeds) ===')
    print(f'{"draw":>5} | '
          f'{"HIV":>7} {"trep_F":>7} {"ntrep_F":>8} {"hiv_ratio":>10} {"FSW":>7} | '
          f'{"syph_pf":>8} {"ng_pf":>7} {"ct_pf":>7} {"tv_pf":>7} | '
          f'{"n_sus":>5}')
    for di in means.index:
        m = means.loc[di]
        n_sus = sum(m[f'sustained_{d}'] >= 0.5 for d in ('hiv','syph','ng','ct','tv')
                    if f'sustained_{d}' in m.index)
        print(f'{int(di):>5} | '
              f'{m["hiv_prev_2010_2020"]*100:>6.2f}% '
              f'{m["trep_f_2016"]*100:>6.2f}% '
              f'{m["nontrep_f_2016"]*100:>7.2f}% '
              f'{m["hiv_trep_ratio_2016"]:>9.2f} '
              f'{m["fsw_prev_2019"]*100:>6.1f}% | '
              f'{m["pf_2035_2040_syph"]*100:>7.2f}% '
              f'{m["pf_2035_2040_ng"]*100:>6.2f}% '
              f'{m["pf_2035_2040_ct"]*100:>6.2f}% '
              f'{m["pf_2035_2040_tv"]*100:>6.2f}% | '
              f'{n_sus}/5')

    # Show within-draw seed spreads (max - min across 5 seeds)
    spread = (maxs - mins)
    spread_csv = OUT_DIR / 'per_draw_spread.csv'
    spread.to_csv(spread_csv)
    print(f'\nWrote {spread_csv}')

    # Drama check: which draws had at least one extinct seed but mean > 0?
    print(f'\n=== Drama check — draws where some seeds extinct, others not ===')
    by_draw = ok.groupby('draw_idx')
    for d in ['syph', 'ng', 'ct', 'tv']:
        col = f'sustained_{d}'
        if col not in ok.columns:
            continue
        for di, sub in by_draw:
            vals = sub.sort_values('sub_idx')[col].astype(int).tolist()
            if 0 in vals and 1 in vals:
                seed_pf = sub.sort_values('sub_idx')[f'pf_2035_2040_{d}'].values * 100
                mean_pf = float(seed_pf.mean())
                print(f'  draw {int(di):>3} {d:>4}: seeds sustained {vals}  '
                      f'pf_2035_40 by seed = {[f"{v:.2f}%" for v in seed_pf]}  mean = {mean_pf:.2f}%')


if __name__ == '__main__':
    main()
