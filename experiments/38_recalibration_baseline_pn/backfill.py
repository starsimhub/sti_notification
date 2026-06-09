"""
Exp 38 backfill: bring robust ensemble from 93 → ~100.

Phase 1 produced 224 n_pass==4 sustained candidates not in Phase 2 (the
primary filter was n_pass>=5). Take a random 40, run with 3 seeds each
(same SEED_BASE so seeds match the existing ensemble), and append to
ensemble_results.jsonl + ensemble_summary.csv.

Expected yield ~15-25% pass robust gate → 6-10 additional robust → ~100.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json
import importlib.util
import multiprocessing as mp
from pathlib import Path
import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
HERE = THIS.parent
PROJECT_ROOT = HERE.parents[1]
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'

# Match the sys.path layout that run.py expects: EXP24 first (so its
# `from run import ...` resolves to EXP24/run.py, not back to this dir).
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP24))

# Load HERE/run.py under a unique module name to avoid the circular
# import (running `python backfill.py` puts HERE on sys.path, and
# 'from run import' inside run.py would otherwise find the partially-
# loaded HERE/run.py).
spec = importlib.util.spec_from_file_location("exp38_run", str(HERE / "run.py"))
exp38_run = importlib.util.module_from_spec(spec)
sys.modules['exp38_run'] = exp38_run
spec.loader.exec_module(exp38_run)

run_one          = exp38_run.run_one
row_to_sim_pars  = exp38_run.row_to_sim_pars
N_WORKERS        = exp38_run.N_WORKERS
P2_SEED_BASE     = exp38_run.P2_SEED_BASE
P2_SEEDS_PER_DRAW = exp38_run.P2_SEEDS_PER_DRAW
PHASE1_JSONL     = exp38_run.PHASE1_JSONL
PHASE1_CSV       = exp38_run.PHASE1_CSV
ENS_JSONL        = exp38_run.ENS_JSONL
ENS_SUMMARY      = exp38_run.ENS_SUMMARY
ENS_META         = exp38_run.ENS_META
ENS_DRAWS_CSV    = exp38_run.ENS_DRAWS_CSV

N_BACKFILL = int(os.environ.get('N_BACKFILL', 40))
BACKFILL_SEED = int(os.environ.get('BACKFILL_SEED', 44))


def pick_backfill_candidates():
    rows = [json.loads(l) for l in PHASE1_JSONL.open()]
    df = pd.DataFrame(rows)
    df = df[df['status'] == 'ok'].copy()
    df['sustained'] = df['passes'].apply(lambda p: p.get('sustained', False))

    already = set(pd.read_csv(ENS_DRAWS_CSV)['draw_idx'].astype(int))
    pool = df[(df['sustained']) & (df['n_pass'] == 4) &
              (~df['draw_idx'].isin(already))]
    print(f'Backfill pool (sustained AND n_pass==4, not in ensemble): {len(pool)}')

    rng = np.random.default_rng(BACKFILL_SEED)
    chosen = rng.choice(pool['draw_idx'].values,
                        size=min(N_BACKFILL, len(pool)),
                        replace=False)
    print(f'Picked {len(chosen)} candidates for backfill.')
    return sorted(int(i) for i in chosen)


def build_tasks(chosen_draws):
    priors = pd.read_csv(PHASE1_CSV)
    tasks = []
    for di in chosen_draws:
        row = priors[priors['draw_idx'] == di].iloc[0].to_dict()
        sp, pp = row_to_sim_pars(row)
        for s_idx in range(P2_SEEDS_PER_DRAW):
            seed = P2_SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di, 'sim_pars': sp, 'pn_pars': pp,
                          'seed': seed,
                          'save_events_as': f'events_{di:04d}_seed{s_idx}.json'})
    return tasks


def run_pool_append(tasks):
    import time
    print(f'\nBackfill: running {len(tasks)} sims on {N_WORKERS} workers...')
    t0 = time.time()
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with ENS_JSONL.open('a') as fout:
            for i, r in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(r) + '\n'); fout.flush()
                if i % 30 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s eta={eta:.0f}s',
                          flush=True)
    print(f'  done in {time.time()-t0:.1f}s')


def rebuild_summary():
    rows = [json.loads(l) for l in ENS_JSONL.open()]
    df = pd.DataFrame(rows)
    df_ok = df[df['status'] == 'ok'].copy()
    numeric = [c for c in df_ok.columns
               if c not in ('draw_idx', 'seed', 'passes', 'status') and
               pd.api.types.is_numeric_dtype(df_ok[c])]
    grouped = df_ok.groupby('draw_idx')[numeric].mean().reset_index()
    grouped['n_seeds_ok'] = df_ok.groupby('draw_idx').size().reset_index(drop=True)
    for t in ['fsw_band', 'nontrep_band', 'trep_band', 'primary_band',
              'secondary_band', 'early_lat_band', 'sustained',
              'hiv_pos_trep_band', 'hiv_trep_ratio_band']:
        grouped[f'pass_{t}'] = df_ok.groupby('draw_idx')['passes'].apply(
            lambda s: sum(p.get(t, False) for p in s) / len(s)).reset_index(drop=True)
    grouped['n_pass_mean'] = df_ok.groupby('draw_idx')['n_pass'].mean().reset_index(drop=True)
    grouped.to_csv(ENS_SUMMARY, index=False)
    print(f'\nRewrote {ENS_SUMMARY}: {len(grouped)} draws')
    robust = grouped[(grouped['pass_sustained'] == 1.0) & (grouped['n_pass_mean'] >= 4)]
    print(f'Robust (sustained 3/3 AND n_pass_mean>=4): {len(robust)}')
    return grouped, robust


def main():
    chosen = pick_backfill_candidates()
    tasks = build_tasks(chosen)
    run_pool_append(tasks)
    grouped, robust = rebuild_summary()

    priors = pd.read_csv(PHASE1_CSV)
    all_draws = set(pd.read_csv(ENS_DRAWS_CSV)['draw_idx'].astype(int)) | set(chosen)
    priors[priors['draw_idx'].isin(all_draws)].to_csv(ENS_DRAWS_CSV, index=False)

    meta = json.loads(ENS_META.read_text())
    meta['n_backfill_used'] = meta.get('n_backfill_used', 0) + len(chosen)
    meta['ensemble_size'] = int(len(grouped))
    meta['n_robust'] = int(len(robust))
    meta['backfill_seed'] = BACKFILL_SEED
    ENS_META.write_text(json.dumps(meta, indent=2))
    print(f'\nFinal: {len(grouped)} draws total, {len(robust)} robust')


if __name__ == '__main__':
    main()
