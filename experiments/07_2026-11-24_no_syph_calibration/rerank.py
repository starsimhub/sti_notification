"""Rerank exp 07 from outputs/results_raw.jsonl at a different ACCEPT_TOL, without rerunning sims.

Usage: ACCEPT_TOL=1.0 python rerank.py
Writes outputs/per_draw_means_tol<T>.csv and outputs/draws_used_tol<T>.csv; the originals are untouched.
"""
import os
import sys
from pathlib import Path

import pandas as pd

os.environ.setdefault('ACCEPT_TOL', '1.0')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import run  # noqa: E402

tol = run.ACCEPT_TOL
raw = pd.read_json(run.OUT_DIR / 'results_raw.jsonl', lines=True)
ok = raw[raw['status'] == 'ok']
per_draw = run.score(ok)
tag = f'tol{tol:g}'
per_draw.to_csv(run.OUT_DIR / f'per_draw_means_{tag}.csv', index=False)
keep = per_draw[per_draw.acceptable].head(run.N_KEEP)
priors = pd.read_csv(run.OUT_DIR / 'priors.csv')
(priors.merge(keep[['draw_idx', 'retention_rank', 'mae']], on='draw_idx')
       .sort_values('retention_rank').to_csv(run.OUT_DIR / f'draws_used_{tag}.csv', index=False))

sus_ok = per_draw.min_seeds_sustained >= run.MIN_SEEDS_SUSTAINED
print(f'ACCEPT_TOL={tol}: acceptable {int(per_draw.acceptable.sum())}/{len(per_draw)}; keeping {len(keep)}')
print(f'  sustained in >= {run.MIN_SEEDS_SUSTAINED}/{run.K_SEEDS} seeds: {int(sus_ok.sum())}/{len(per_draw)}')
print('  fraction of draws failing each prevalence target (dist > tol), all draws | sustained draws:')
for t in run.PREV_TARGETS:
    print(f'    {t:18s} {(per_draw[f"dist_{t}"] > tol).mean():.0%} | {(per_draw.loc[sus_ok, f"dist_{t}"] > tol).mean():.0%}')
if len(keep):
    print('  Spread across retained draws (min / median / max):')
    for t in run.TARGETS:
        print(f'    {t:22s} {keep[t].min():.4g} / {keep[t].median():.4g} / {keep[t].max():.4g}   band {run.TARGETS[t][0]}')
