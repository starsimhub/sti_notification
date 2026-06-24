"""Exp 06 single-phase K=5 calibration.

LHS sample N_DRAWS from exp 04 prior (NG β floor at 0.10). Run K=5 seeds per
draw. Extract per-sim scalars + time series + age × sex snapshots. Aggregate
to per-draw means (5-seed average is the unit of signal). Compute weighted
GoF + extinction penalty. Rank ascending; assign retention rank.

Outputs (in `outputs/`):
  priors.csv            LHS draws
  results_raw.jsonl     per-sim scalars (archive)
  per_draw_means.csv    K=5 averaged scalars + GoF + rank
  timeseries.parquet    per-draw averaged year × disease × {prev_f, prev_m, new_inf}
  snapshots.parquet     per-draw averaged age × sex × disease at snapshot years

Env vars:
  N_DRAWS    default 20 (smoke). Use 100 for compute check, 500 for full.
  N_WORKERS  default 60.
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

# Match exp 04 prior (NG β floor lifted to 0.10) before _pipeline reads calib_pars
from priors import calib_pars  # noqa: E402
calib_pars['ng.beta_m2f'] = ('NG β (M→F)', 0.10, 0.60, True)

from _pipeline import (  # noqa: E402
    generate_prior_draws, row_to_sim_pars, build_sim,
    extract_calibration_summary, REPO_ROOT as PIPELINE_REPO,
)
os.chdir(PIPELINE_REPO)

OUT_DIR = HERE / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

K_SEEDS = 5
LHS_SEED = 45
LHS_TOTAL = 500
N_DRAWS = int(os.environ.get('N_DRAWS', 20))
N_WORKERS = int(os.environ.get('N_WORKERS', 60))

DISEASES = ('hiv', 'syph', 'ng', 'ct', 'tv')
TS_RESULT_NAMES = ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections']
SNAP_YEARS = (2016, 2027, 2035, 2040)
SNAP_AGES = ['15_20', '20_25', '25_30', '30_35', '35_50', '50_65']
SNAP_BASES = {'ng': ['prevalence'], 'ct': ['prevalence'], 'tv': ['prevalence'],
              'hiv': ['prevalence'], 'syph': ['trep_prevalence', 'prevalence']}

TARGETS = {
    'hiv_prev_2010_2020':  (0.115, 0.155),
    'trep_f_2016':         (0.020, 0.040),
    'nontrep_f_2016':      (0.005, 0.015),
    'hiv_trep_ratio_2016': (3.0,   6.0),
    'fsw_prev_2019':       (0.40,  0.70),
    'primary_share':       (0.45,  0.65),
    'secondary_share':     (0.25,  0.45),
    'early_lat_share':     (0.05,  0.25),
    'pf_2035_2040_ng':     (0.010,    0.025),
    'pf_2035_2040_ct':     (0.09,     0.15),
    'pf_2035_2040_tv':     (0.07,     0.14),
    'ni_2030_2040_ng':     (200_000,   400_000),
    'ni_2030_2040_ct':     (300_000,   600_000),
    'ni_2030_2040_tv':     (1_100_000, 2_200_000),
}
WEIGHTS = {
    'trep_f_2016':         2.0,
    'nontrep_f_2016':      2.0,
    'hiv_trep_ratio_2016': 2.0,
    'pf_2035_2040_ng':     2.0,
    'pf_2035_2040_ct':     2.0,
    'ni_2030_2040_ng':     0.5,
    'ni_2030_2040_ct':     0.5,
    'ni_2030_2040_tv':     0.5,
}  # all others default to 1.0
EXTINCTION_PENALTY = 100.0


def _annualize(result):
    try:
        ann = result.annualize()
        return (np.asarray(ann.timevec.years).astype(int),
                np.asarray(ann.values, dtype=float))
    except Exception:
        return None, None


def extract_timeseries(sim):
    rows = []
    for d in DISEASES:
        dres = sim.results.get(d)
        if dres is None:
            continue
        for rname in TS_RESULT_NAMES:
            if rname not in dres:
                continue
            years, values = _annualize(dres[rname])
            if years is None:
                continue
            for y, v in zip(years, values):
                rows.append({'disease': d, 'result_name': rname,
                             'year': int(y), 'value': float(v)})
    return rows


def extract_snapshots(sim):
    """Per-year, per-age, per-sex prevalence at SNAP_YEARS for each disease."""
    rows = []
    yv = np.array([t.year for t in sim.t.timevec])
    for d, bases in SNAP_BASES.items():
        dres = sim.results.get(d)
        if dres is None:
            continue
        for base in bases:
            for age in SNAP_AGES:
                for sex in ('f', 'm'):
                    key = f'{base}_{sex}_{age}'
                    if key not in dres:
                        continue
                    vals = np.asarray(dres[key].values, dtype=float)
                    for yr in SNAP_YEARS:
                        idx = int(np.argmin(np.abs(yv - yr)))
                        rows.append({'disease': d, 'base': base, 'age': age,
                                     'sex': sex, 'year': yr,
                                     'value': float(vals[idx])})
    return rows


def run_one(task):
    di = task['draw_idx']
    sub_idx = task['sub_idx']
    seed = task['seed']
    sp = task['sim_pars']
    try:
        sim = build_sim(seed=seed, sim_pars=sp)
        sim.run()
        scalars = extract_calibration_summary(sim, di, seed)
        scalars['sub_idx'] = sub_idx
        ts = extract_timeseries(sim)
        snap = extract_snapshots(sim)
        return {'scalars': scalars, 'ts': ts, 'snap': snap, 'di': di, 'sub_idx': sub_idx, 'seed': seed}
    except Exception as e:
        return {'scalars': {'draw_idx': di, 'sub_idx': sub_idx, 'seed': seed,
                            'status': f'error: {type(e).__name__}: {e}'},
                'ts': [], 'snap': [], 'di': di, 'sub_idx': sub_idx, 'seed': seed}


def compute_gof(per_draw_means: pd.DataFrame,
                seed_sustains: dict) -> pd.DataFrame:
    out = []
    for di, row in per_draw_means.iterrows():
        weights_sum = 0.0
        weighted_dist = 0.0
        for t, (lo, hi) in TARGETS.items():
            v = row[t]
            scale = hi - lo
            if v < lo:
                d = (lo - v) / scale
            elif v > hi:
                d = (v - hi) / scale
            else:
                d = 0.0
            w = WEIGHTS.get(t, 1.0)
            weighted_dist += w * d
            weights_sum += w
        mae = weighted_dist / weights_sum
        n_ext = sum(1 for dz in DISEASES
                    if di in seed_sustains and dz in seed_sustains[di]
                    and all(not s for s in seed_sustains[di][dz]))
        out.append({'draw_idx': int(di), 'mae': mae,
                    'n_fully_extinct': n_ext,
                    'gof': mae + EXTINCTION_PENALTY * n_ext})
    return pd.DataFrame(out)


def main():
    print(f'exp 06 (2026-06-24) — K={K_SEEDS} single-phase calibration, '
          f'N_DRAWS={N_DRAWS}, weighted GoF + extinction penalty', flush=True)
    priors = generate_prior_draws(LHS_TOTAL, LHS_SEED).head(N_DRAWS)
    (OUT_DIR / 'priors.csv').write_text(priors.to_csv(index=False))
    print(f'  wrote {len(priors)} priors', flush=True)

    tasks = []
    for _, row in priors.iterrows():
        di = int(row['draw_idx'])
        sp = row_to_sim_pars(row)
        for sub_idx in range(K_SEEDS):
            tasks.append({'draw_idx': di, 'sub_idx': sub_idx, 'sim_pars': sp,
                          'seed': di * 1000 + sub_idx})
    print(f'  {len(tasks)} sims on {N_WORKERS} workers...', flush=True)

    t0 = time.time()
    raw_jsonl = OUT_DIR / 'results_raw.jsonl'
    all_ts = []
    all_snap = []
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with raw_jsonl.open('w') as fout:
            for i, payload in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(payload['scalars']) + '\n')
                fout.flush()
                di, sub_idx = payload['di'], payload['sub_idx']
                for r in payload['ts']:
                    all_ts.append({**r, 'draw_idx': di, 'sub_idx': sub_idx})
                for r in payload['snap']:
                    all_snap.append({**r, 'draw_idx': di, 'sub_idx': sub_idx})
                if i % 20 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    print(f'    [{i:3d}/{len(tasks)}] {elapsed:.0f}s', flush=True)
    print(f'  done in {time.time()-t0:.0f}s', flush=True)

    # Per-draw averages of scalars
    raw = pd.read_json(raw_jsonl, lines=True)
    ok = raw[raw['status'] == 'ok'].copy()
    print(f'  {len(ok)}/{len(raw)} sims ok', flush=True)

    scalar_cols = list(TARGETS.keys())
    means = ok.groupby('draw_idx')[scalar_cols].mean()
    # Per-disease seed-sustainability
    seed_sustains = {}
    for di, sub in ok.groupby('draw_idx'):
        seed_sustains[int(di)] = {d: sub[f'sustained_{d}'].astype(bool).tolist()
                                   for d in DISEASES if f'sustained_{d}' in sub.columns}
    gof_df = compute_gof(means, seed_sustains)
    gof_df = gof_df.sort_values('gof').reset_index(drop=True)
    gof_df['retention_rank'] = np.arange(1, len(gof_df) + 1)
    per_draw = means.reset_index().merge(gof_df, on='draw_idx')
    per_draw_csv = OUT_DIR / 'per_draw_means.csv'
    per_draw.to_csv(per_draw_csv, index=False)
    print(f'  wrote {per_draw_csv}', flush=True)

    # Per-draw averaged time series + snapshots
    ts_df = pd.DataFrame(all_ts)
    ts_avg = ts_df.groupby(['draw_idx', 'disease', 'result_name', 'year'])['value'].mean().reset_index()
    ts_parquet = OUT_DIR / 'timeseries.parquet'
    ts_avg.to_parquet(ts_parquet, index=False)
    print(f'  wrote {ts_parquet} ({len(ts_avg)} rows)', flush=True)

    snap_df = pd.DataFrame(all_snap)
    snap_avg = snap_df.groupby(['draw_idx', 'disease', 'base', 'age', 'sex', 'year'])['value'].mean().reset_index()
    snap_parquet = OUT_DIR / 'snapshots.parquet'
    snap_avg.to_parquet(snap_parquet, index=False)
    print(f'  wrote {snap_parquet} ({len(snap_avg)} rows)', flush=True)

    # Quick GoF summary
    print(f'\n=== GoF distribution ===', flush=True)
    print(per_draw[['draw_idx', 'mae', 'n_fully_extinct', 'gof', 'retention_rank']]
          .head(min(20, len(per_draw))).to_string(index=False))
    if len(per_draw) > 20:
        print('...')
        print(per_draw[['draw_idx', 'mae', 'n_fully_extinct', 'gof', 'retention_rank']]
              .tail(5).to_string(index=False))


if __name__ == '__main__':
    main()
