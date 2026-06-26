"""Rerank exp 06 from results_raw.jsonl using the current TARGETS spec.

Use when the GoF target spec changes (e.g. HIV denominator switch from
whole-pop to 15-49) and we want a new per_draw_means.csv without
re-running 2500 sims. Recomputes the GoF + retention_rank in-place from
the cached per-sim scalars.

Outputs per_draw_means.csv (overwrites). Run.py's TS_RESULT_NAMES and
the saved parquets are unchanged — only the ranking moves.
"""
from __future__ import annotations

from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run import TARGETS, WEIGHTS, DISEASES, EXTINCTION_PENALTY, compute_gof  # noqa: E402

OUT = HERE / 'outputs'

raw = pd.DataFrame([json.loads(l) for l in (OUT / 'results_raw.jsonl').open()])
ok = raw[raw['status'] == 'ok'].copy()
print(f'{len(ok)}/{len(raw)} sims ok across {ok.draw_idx.nunique()} draws')

scalar_cols = list(TARGETS.keys())
missing = [c for c in scalar_cols if c not in ok.columns]
if missing:
    raise RuntimeError(f'Missing scalar(s) in raw archive: {missing}')

means = ok.groupby('draw_idx')[scalar_cols].mean()
seed_sustains = {}
for di, sub in ok.groupby('draw_idx'):
    seed_sustains[int(di)] = {d: sub[f'sustained_{d}'].astype(bool).tolist()
                               for d in DISEASES if f'sustained_{d}' in sub.columns}

gof_df = compute_gof(means, seed_sustains)
gof_df = gof_df.sort_values('gof').reset_index(drop=True)
gof_df['retention_rank'] = np.arange(1, len(gof_df) + 1)
per_draw = means.reset_index().merge(gof_df, on='draw_idx')

out_path = OUT / 'per_draw_means.csv'
per_draw.to_csv(out_path, index=False)
print(f'wrote {out_path}')

# Quick summary
print(f'\n=== New GoF distribution (TARGETS = {list(TARGETS.keys())}) ===')
mae_only = per_draw[per_draw.n_fully_extinct == 0]
print(f'  {len(mae_only)}/{len(per_draw)} draws all-sustaining')
print(f'  best GoF: {per_draw.gof.min():.3f}')
print(f'  Top-30 cutoff: {per_draw.sort_values("gof").head(30).gof.max():.2f}')
print(f'  Top-50 cutoff: {per_draw.sort_values("gof").head(50).gof.max():.2f}')

print(f'\n=== Top 10 by new rank ===')
print(per_draw[['draw_idx', 'retention_rank', 'mae', 'n_fully_extinct', 'gof']]
      .sort_values('retention_rank').head(10).to_string(index=False))
