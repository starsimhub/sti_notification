"""Exp 07: syphilis-free recalibration (NG/CT/TV/BV + HIV).

Why
---
Syphilis was removed from the model after co-author review (Nov 2026). The
exp 06 ensemble cannot be reused: its GoF was dominated by syphilis targets
(trep/nontrep, stage shares, HIV-trep ratio; 8 of 14 targets), and the
retained top-10 draws spanned an implausible range on the endpoints this
paper is about (end-of-window CT prevalence 0.1%-17.7%, TV 1.9%-26.6%, NG
~0 in one draw). Two causes:
  1. NG/CT/TV fit was a minority of the GoF weight.
  2. Extinction was penalised only if *all* K=5 seeds went extinct, so a
     draw whose seeds were bimodal (some extinct, some hot) could average
     into band while behaving wildly in any given scenario run.

Design changes vs exp 06
------------------------
* Priors: syphilis and hiv_syph priors dropped. 8 parameters remain.
* Targets: NG/CT/TV prevalence + incidence over the data era 2015-2025 (exp
  06 used 2035-2040 projections from the same file) and HIV 15-49.
* Incidence targets are computed as the mean of calendar-year *sums* (exp 06
  averaged per-timestep values, which made the units ambiguous).
* Seed-level sustainability: a draw is ACCEPTABLE only if every disease
  sustains in >= MIN_SEEDS_SUSTAINED of K seeds AND every prevalence target
  lies within ACCEPT_TOL band-widths of its band. Acceptable draws are then
  ranked by weighted GoF and the top N_KEEP retained.
* Population: N_AGENTS default 20k (exp 06: 10k). At ~1.5% NG prevalence a
  10k-agent sim carries only a few dozen NG infections, so stochastic
  fade-out is likely a large part of the exp 06 between-seed bimodality.

Validation (not fitted; see validate.py once written / README):
  STICH 2020-21, ages 16-24: CT 14.7%, NG 2.8% (both sexes);
  any of CT/NG/TV in women 23.2% (Dziva Chikwari 2023, eClinicalMedicine).
  Zimbabwe STI Etiology Study VDS etiology (Chirenje 2018, STD).

Run (VM, repo root, `starsim` env):
    conda run -n starsim env N_DRAWS=500 N_WORKERS=120 python \
        experiments/07_2026-11-24_no_syph_calibration/run.py

Smoke:
    conda run -n starsim env N_DRAWS=4 K_SEEDS=2 N_AGENTS=5000 STOP=2026 \
        python experiments/07_2026-11-24_no_syph_calibration/run.py

Outputs (outputs/):
  priors.csv, results_raw.jsonl, per_draw_means.csv, draws_used.csv (top
  N_KEEP acceptable draws, in the format run_scenarios.py expects),
  timeseries.parquet.
"""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import sys
import time
from pathlib import Path

os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1')

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parent.parent
sys.path.insert(0, str(REPO_ROOT / 'calibration' / 'artifacts' / 'scripts'))
sys.path.insert(0, str(REPO_ROOT))

# --- Priors: drop syphilis + HIV-syph coupling; keep exp 06 NG beta floor ---
from priors import calib_pars  # noqa: E402
for k in [k for k in list(calib_pars.keys())
          if k.startswith('syph') or k.startswith('hiv_syph')]:
    del calib_pars[k]
calib_pars['ng.beta_m2f'] = ('NG β (M→F)', 0.10, 0.60, True)

from _pipeline import generate_prior_draws, row_to_sim_pars, build_sim  # noqa: E402
os.chdir(REPO_ROOT)

OUT_DIR = HERE / 'outputs'
OUT_DIR.mkdir(parents=True, exist_ok=True)

K_SEEDS = int(os.environ.get('K_SEEDS', 5))
LHS_SEED = 47
LHS_TOTAL = 500
N_DRAWS = int(os.environ.get('N_DRAWS', 20))
N_WORKERS = int(os.environ.get('N_WORKERS', 60))
N_AGENTS = int(os.environ.get('N_AGENTS', 20_000))
STOP = int(os.environ.get('STOP', 2030))
N_KEEP = int(os.environ.get('N_KEEP', 30))
MIN_SEEDS_SUSTAINED = int(os.environ.get('MIN_SEEDS_SUSTAINED', max(1, K_SEEDS - 1)))
ACCEPT_TOL = float(os.environ.get('ACCEPT_TOL', 0.5))  # band-widths outside band

DISEASES = ('hiv', 'ng', 'ct', 'tv')
WIN = (2015, 2025)          # data-era window for STI targets (inclusive)
HIV_WIN = (2010, 2020)

# TODO(Robyn): confirm denominators against data/zimbabwe_sti_data.csv.
# ct uses prevalence_f_25_30 to match the data column ct_prevalence_f_25_30.
# ng/tv use prevalence_f as in exp 06; the data columns are unlabelled by sex.
TARGETS = {
    # name                      (lo,      hi)        result key
    'hiv_prev_15_49':          ((0.115,   0.155),    ('hiv', 'prevalence_15_49', HIV_WIN, 'mean')),
    'ng_prev_f':               ((0.010,   0.025),    ('ng',  'prevalence_f',     WIN, 'mean')),
    'ct_prev_f_25_30':         ((0.09,    0.15),     ('ct',  'prevalence_f_25_30', WIN, 'mean')),
    'tv_prev_f':               ((0.07,    0.14),     ('tv',  'prevalence_f',     WIN, 'mean')),
    'ng_new_inf_per_yr':       ((200_000, 450_000),  ('ng',  'new_infections',   WIN, 'annual_sum')),
    'ct_new_inf_per_yr':       ((200_000, 450_000),  ('ct',  'new_infections',   WIN, 'annual_sum')),
    'tv_new_inf_per_yr':       ((700_000, 1_600_000), ('tv', 'new_infections',   WIN, 'annual_sum')),
}
WEIGHTS = {'ng_prev_f': 2.0, 'ct_prev_f_25_30': 2.0, 'tv_prev_f': 2.0,
           'ng_new_inf_per_yr': 0.5, 'ct_new_inf_per_yr': 0.5, 'tv_new_inf_per_yr': 0.5}
PREV_TARGETS = [k for k in TARGETS if 'prev' in k]

# Validation scalars (recorded, not fitted)
VALIDATION = {
    'ng_prev_15_25_2021': ('ng', ['prevalence_f_15_20', 'prevalence_f_20_25',
                                  'prevalence_m_15_20', 'prevalence_m_20_25'], (2020, 2021)),
    'ct_prev_15_25_2021': ('ct', ['prevalence_f_15_20', 'prevalence_f_20_25',
                                  'prevalence_m_15_20', 'prevalence_m_20_25'], (2020, 2021)),
}

TS_RESULT_NAMES = ['prevalence', 'prevalence_f', 'prevalence_m',
                   'prevalence_15_49', 'prevalence_f_25_30', 'new_infections']


def _years(res):
    return np.array([t.year for t in res.timevec])


def _stat(sim, disease, key, win, how):
    dres = sim.results.get(disease)
    if dres is None or key not in dres:
        return float('nan')
    res = dres[key]
    yrs = _years(res)
    v = np.asarray(res.values, dtype=float)
    m = (yrs >= win[0]) & (yrs <= win[1])
    if not m.any():
        return float('nan')
    if how == 'mean':
        return float(np.nanmean(v[m]))
    if how == 'annual_sum':
        per_year = [np.nansum(v[yrs == y]) for y in range(win[0], win[1] + 1)
                    if (yrs == y).any()]
        return float(np.mean(per_year))
    raise ValueError(how)


def extract(sim, draw_idx, seed):
    row = dict(draw_idx=int(draw_idx), seed=int(seed), status='ok')
    for name, (_band, (d, key, win, how)) in TARGETS.items():
        row[name] = _stat(sim, d, key, win, how)
    for name, (d, keys, win) in VALIDATION.items():
        vals = [_stat(sim, d, k, win, 'mean') for k in keys]
        row[name] = float(np.nanmean(vals)) if np.isfinite(vals).any() else float('nan')
    # Seed-level sustainability (same rule as exp 06 _disease_sustained, on
    # the last 5 simulated years so it works for short STOP).
    lo = STOP - 5
    for d in DISEASES:
        pf = _stat(sim, d, 'prevalence_f', (lo, STOP), 'mean')
        ni = _stat(sim, d, 'new_infections', (lo, STOP), 'annual_sum')
        row[f'sustained_{d}'] = bool(ni > 0 and pf >= 0.001)
    return row


def extract_timeseries(sim):
    rows = []
    for d in DISEASES:
        dres = sim.results.get(d)
        if dres is None:
            continue
        for rname in TS_RESULT_NAMES:
            if rname not in dres:
                continue
            try:
                ann = dres[rname].annualize()
                yrs = np.asarray(ann.timevec.years).astype(int)
                vals = np.asarray(ann.values, dtype=float)
            except Exception:
                continue
            rows += [{'disease': d, 'result_name': rname, 'year': int(y), 'value': float(v)}
                     for y, v in zip(yrs, vals)]
    return rows


def run_one(task):
    try:
        sim = build_sim(seed=task['seed'], sim_pars=task['sim_pars'],
                        stop=STOP, n_agents=N_AGENTS)
        sim.run()
        return {'scalars': extract(sim, task['draw_idx'], task['seed']),
                'ts': extract_timeseries(sim), **{k: task[k] for k in ('draw_idx', 'sub_idx')}}
    except Exception as e:
        return {'scalars': {'draw_idx': task['draw_idx'], 'seed': task['seed'],
                            'status': f'error: {type(e).__name__}: {e}'},
                'ts': [], 'draw_idx': task['draw_idx'], 'sub_idx': task['sub_idx']}


def band_distance(v, lo, hi):
    if not np.isfinite(v):
        return np.inf
    w = hi - lo
    return max(0.0, (lo - v) / w, (v - hi) / w)


def score(ok: pd.DataFrame) -> pd.DataFrame:
    means = ok.groupby('draw_idx')[list(TARGETS)].mean()
    sus = ok.groupby('draw_idx')[[f'sustained_{d}' for d in DISEASES]].sum()
    out = []
    for di, row in means.iterrows():
        dist = {t: band_distance(row[t], *TARGETS[t][0]) for t in TARGETS}
        wsum = sum(WEIGHTS.get(t, 1.0) for t in TARGETS)
        mae = sum(WEIGHTS.get(t, 1.0) * dist[t] for t in TARGETS) / wsum
        min_sus = int(sus.loc[di].min())
        acceptable = (min_sus >= MIN_SEEDS_SUSTAINED and
                      all(dist[t] <= ACCEPT_TOL for t in PREV_TARGETS))
        out.append(dict(draw_idx=int(di), mae=mae, min_seeds_sustained=min_sus,
                        acceptable=acceptable,
                        **{f'dist_{t}': dist[t] for t in TARGETS}))
    g = pd.DataFrame(out)
    g = g.sort_values(['acceptable', 'mae'], ascending=[False, True]).reset_index(drop=True)
    g['retention_rank'] = np.arange(1, len(g) + 1)
    return means.reset_index().merge(g, on='draw_idx')


def main():
    print(f'exp 07 — syphilis-free calibration | N_DRAWS={N_DRAWS} K={K_SEEDS} '
          f'N_AGENTS={N_AGENTS} STOP={STOP} | {len(calib_pars)} priors: '
          f'{list(calib_pars.keys())}', flush=True)
    priors = generate_prior_draws(LHS_TOTAL, LHS_SEED).head(N_DRAWS)
    priors.to_csv(OUT_DIR / 'priors.csv', index=False)

    tasks = [dict(draw_idx=int(r['draw_idx']), sub_idx=k,
                  seed=int(r['draw_idx']) * 1000 + k, sim_pars=row_to_sim_pars(r))
             for _, r in priors.iterrows() for k in range(K_SEEDS)]
    print(f'  {len(tasks)} sims on {N_WORKERS} workers', flush=True)

    t0 = time.time()
    raw_path = OUT_DIR / 'results_raw.jsonl'
    all_ts = []
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool, raw_path.open('w') as f:
        for i, p in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            f.write(json.dumps(p['scalars']) + '\n')
            f.flush()
            all_ts += [{**r, 'draw_idx': p['draw_idx'], 'sub_idx': p['sub_idx']} for r in p['ts']]
            if i % 20 == 0 or i == len(tasks):
                print(f'    [{i}/{len(tasks)}] {time.time()-t0:.0f}s', flush=True)

    raw = pd.read_json(raw_path, lines=True)
    ok = raw[raw['status'] == 'ok']
    print(f'  {len(ok)}/{len(raw)} sims ok', flush=True)
    if not len(ok):
        print(raw['status'].value_counts().head())
        return
    per_draw = score(ok)
    per_draw.to_csv(OUT_DIR / 'per_draw_means.csv', index=False)

    keep = per_draw[per_draw.acceptable].head(N_KEEP)
    print(f'  acceptable draws: {int(per_draw.acceptable.sum())}/{len(per_draw)}; '
          f'keeping {len(keep)}', flush=True)
    draws_used = priors.merge(keep[['draw_idx', 'retention_rank', 'mae']], on='draw_idx')
    draws_used.sort_values('retention_rank').to_csv(OUT_DIR / 'draws_used.csv', index=False)

    if all_ts:
        ts = pd.DataFrame(all_ts)
        (ts.groupby(['draw_idx', 'disease', 'result_name', 'year'])['value'].mean()
           .reset_index().to_parquet(OUT_DIR / 'timeseries.parquet', index=False))

    cols = ['draw_idx', 'retention_rank', 'acceptable', 'min_seeds_sustained', 'mae'] + list(TARGETS)
    print(per_draw[cols].head(15).to_string(index=False))
    if len(keep):
        print('\n  Spread across retained draws (min / median / max):')
        for t in TARGETS:
            print(f'    {t:22s} {keep[t].min():.4g} / {keep[t].median():.4g} / {keep[t].max():.4g}'
                  f'   band {TARGETS[t][0]}')


if __name__ == '__main__':
    main()
