"""
Run the LHS calibration pipeline that produces the robust posterior
ensemble. Two-phase:

  Phase 1 — LHS sample N draws from the prior in priors.py, run each
            at one seed, write per-sim summary stats + pass flags.
  Phase 2 — re-run candidates (sustained AND n_pass ≥ 5) at K seeds,
            aggregate per-draw seed-means, write final draws_used.csv.

Adapted from experiments/40_final_recalibration/run.py on the
archive/calibration-2026-06 branch. See calibration/methodology.md
for the design rationale and calibration/recalibration_guide.md for
when to use this script.
"""
from __future__ import annotations

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

from _pipeline import (
    REPO_ROOT, build_sim, generate_prior_draws, row_to_sim_pars,
    extract_calibration_summary, TARGET_BANDS,
)

os.chdir(REPO_ROOT)


def run_one(task):
    draw_idx = task['draw_idx']
    seed = task['seed']
    sim_pars = task['sim_pars']
    try:
        sim = build_sim(seed=seed, sim_pars=sim_pars)
        sim.run()
        return extract_calibration_summary(sim, draw_idx, seed)
    except Exception as e:
        return {'draw_idx': draw_idx, 'seed': seed,
                'status': f'error: {type(e).__name__}: {e}'}


def run_pool(tasks, out_jsonl: Path, label: str, n_workers: int):
    print(f'\n{label}: running {len(tasks)} sims on {n_workers} workers...')
    t0 = time.time()
    summaries = []
    with mp.Pool(n_workers, maxtasksperchild=10) as pool:
        with out_jsonl.open('w') as fout:
            for i, summary in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(summary) + '\n')
                fout.flush()
                summaries.append(summary)
                if i % 50 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i:4d}/{len(tasks)}] {elapsed:.0f}s  eta={eta:.0f}s',
                          flush=True)
    print(f'  done in {time.time()-t0:.1f}s')
    return summaries


def phase1(args, out_dir: Path):
    print(f'\n=== PHASE 1: {args.n_draws}-draw LHS, seed={args.seed} ===')
    prior_df = generate_prior_draws(args.n_draws, args.seed)
    priors_csv = out_dir / 'phase1_priors.csv'
    prior_df.to_csv(priors_csv, index=False)
    print(f'  wrote {len(prior_df)} prior rows to {priors_csv}')

    tasks = []
    for _, row in prior_df.iterrows():
        di = int(row['draw_idx'])
        sp = row_to_sim_pars(row)
        tasks.append({'draw_idx': di, 'sim_pars': sp,
                      'seed': di * 1000})

    run_pool(tasks, out_dir / 'phase1_results.jsonl',
             'Phase 1', args.n_workers)


def select_candidates(out_dir: Path, target_size: int) -> pd.DataFrame:
    print('\n=== CANDIDATE SELECTION ===')
    rows = [json.loads(l) for l in (out_dir / 'phase1_results.jsonl').open()]
    df = pd.DataFrame(rows)
    df = df[df['status'] == 'ok'].copy()
    df['sustained'] = df['passes'].apply(lambda p: p.get('sustained', False))
    sustained = df[df['sustained']]
    primary = sustained[sustained['n_pass'] >= 5]
    backfill = sustained[sustained['n_pass'] == 4]
    print(f'  Phase 1 ok:              {len(df)}')
    print(f'  sustained:               {len(sustained)}')
    print(f'  sustained AND 5+/9:      {len(primary)}')
    print(f'  sustained AND ==4/9:     {len(backfill)}')

    selected = primary.copy()
    if len(selected) < target_size:
        need = target_size - len(selected)
        selected = pd.concat([selected, backfill.head(need)],
                             ignore_index=True)
        print(f'  backfilled with 4/9:     {min(need, len(backfill))}')

    priors = pd.read_csv(out_dir / 'phase1_priors.csv')
    candidates = priors[priors['draw_idx'].isin(selected['draw_idx'])].copy()
    out_csv = out_dir / 'phase2_candidates.csv'
    candidates.to_csv(out_csv, index=False)
    print(f'  wrote {len(candidates)} candidates to {out_csv}')

    (out_dir / 'phase1_selection.json').write_text(json.dumps({
        'n_phase1_ok': int(len(df)),
        'n_sustained': int(len(sustained)),
        'n_pass_5plus': int(len(primary)),
        'n_candidates': int(len(candidates)),
        'target_size': int(target_size),
    }, indent=2))
    return candidates


def phase2(args, out_dir: Path, candidates: pd.DataFrame):
    print(f'\n=== PHASE 2: {len(candidates)} candidates × {args.n_seeds} seeds ===')
    SEED_BASE = 100_000
    tasks = []
    for _, row in candidates.iterrows():
        di = int(row['draw_idx'])
        sp = row_to_sim_pars(row)
        for s_idx in range(args.n_seeds):
            seed = SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di, 'sim_pars': sp, 'seed': seed})

    run_pool(tasks, out_dir / 'phase2_results.jsonl',
             'Phase 2', args.n_workers)

    rows = [json.loads(l) for l in (out_dir / 'phase2_results.jsonl').open()]
    df = pd.DataFrame(rows)
    df_ok = df[df['status'] == 'ok'].copy()
    numeric = [c for c in df_ok.columns
               if c not in ('draw_idx', 'seed', 'passes', 'status')
               and pd.api.types.is_numeric_dtype(df_ok[c])]
    grouped = df_ok.groupby('draw_idx')[numeric].mean().reset_index()
    grouped['n_seeds_ok'] = (df_ok.groupby('draw_idx').size()
                              .reset_index(drop=True))
    for t in list(TARGET_BANDS.keys()) + ['early_lat_band', 'sustained']:
        grouped[f'pass_{t}'] = (
            df_ok.groupby('draw_idx')['passes']
                 .apply(lambda s: sum(p.get(t, False) for p in s) / len(s))
                 .reset_index(drop=True))
    grouped['n_pass_mean'] = (df_ok.groupby('draw_idx')['n_pass']
                                .mean().reset_index(drop=True))
    summary_csv = out_dir / 'ensemble_summary.csv'
    grouped.to_csv(summary_csv, index=False)
    print(f'\nWrote per-draw summary to {summary_csv}')

    # Apply the robust filter: sustained 3/3 AND mean n_pass ≥ 4
    robust_mask = (grouped['pass_sustained'] == 1.0) & (grouped['n_pass_mean'] >= 4)
    robust_idxs = grouped.loc[robust_mask, 'draw_idx'].astype(int).tolist()
    robust_priors = candidates[candidates['draw_idx'].isin(robust_idxs)].copy()
    draws_csv = out_dir / 'draws_used.csv'
    robust_priors.to_csv(draws_csv, index=False)
    print(f'Robust ensemble (sustained 3/3 AND mean n_pass ≥ 4): '
          f'{len(robust_priors)} draws → {draws_csv}')

    print(f'\n=== ENSEMBLE STATS ===')
    print(f'  candidates evaluated:    {len(grouped)}')
    print(f'  robust draws:            {len(robust_priors)}')
    if len(grouped):
        print(f'  median nontrep_f:        {grouped["nontrep_f_2016"].median():.3f}')
        print(f'  median trep_f:           {grouped["trep_f_2016"].median():.3f}')
        print(f'  median fsw_prev_2019:    {grouped["fsw_prev_2019"].median():.3f}')
        print(f'  median HIV ratio:        {grouped["hiv_trep_ratio_2016"].median():.3f}')
        print(f'  median n_pass:           {grouped["n_pass_mean"].median():.2f}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--phase', choices=['1', '2', 'all'], default='all',
                    help='Run a single phase or both end-to-end.')
    ap.add_argument('--out-dir', type=Path, required=True,
                    help='Directory for all intermediate + final outputs.')
    ap.add_argument('--n-draws', type=int, default=5000,
                    help='Phase 1 LHS draws (default 5000).')
    ap.add_argument('--seed', type=int, default=45,
                    help='Phase 1 LHS seed (default 45).')
    ap.add_argument('--target-size', type=int, default=200,
                    help='Phase 2 ensemble target size (default 200).')
    ap.add_argument('--n-seeds', type=int, default=3,
                    help='Phase 2 seeds per draw (default 3).')
    ap.add_argument('--n-workers', type=int, default=24,
                    help='Worker processes (default 24).')
    ap.add_argument('--candidates-csv', type=Path,
                    help='Phase 2 only: candidates CSV from a prior '
                         'phase 1 run. Defaults to '
                         '{out-dir}/phase2_candidates.csv.')
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    if args.phase in ('1', 'all'):
        phase1(args, args.out_dir)
        candidates = select_candidates(args.out_dir, args.target_size)
    else:
        candidates_csv = args.candidates_csv or (args.out_dir / 'phase2_candidates.csv')
        if not candidates_csv.exists():
            sys.exit(f'Candidates CSV not found: {candidates_csv}. '
                     f'Either run --phase 1 first or pass --candidates-csv.')
        candidates = pd.read_csv(candidates_csv)
        print(f'Loaded {len(candidates)} candidates from {candidates_csv}')

    if args.phase in ('2', 'all'):
        phase2(args, args.out_dir, candidates)


if __name__ == '__main__':
    main()
