"""Exp 10: calibration on Starsim 4 (starsim 4.0.0rc6, stisim v4 with SimpleBV and condoms), with HIV deaths and young-women targets.

Why
---
Exp 07 ran on stisim 1.5.7, in which nobody on ART can die of HIV, so the post-ART HIV deaths could not be fitted
(model about a fifth of the data), and SimpleBV re-sought care every month. Exp 08/09 were superseded by the
mortality deduplication and migration. This experiment moves to the Starsim 4 prereleases and changes the targets:

* HIV: deaths become a target, with whole-population prevalence and new infections, each as the mean over 2000-09
  and 2010-21 (data/zimbabwe_hiv_calib.csv; nothing before 2000 is scored), plus the 15-49 band kept from exp 07.
* NG and TV IHME prevalence are compared with the model's prevalence among all adults (both sexes), as in
  stisim_vddx_zim. CT has no IHME prevalence target: the file's ct_prevalence_f_25_30 is a constant 0.12 in every
  year, and it cannot be met together with STICH's young women, since the model's CT rises with age (exp 11).
  CT prevalence is fitted to STICH alone.
* Young women: NG, CT, TV prevalence in women 18-24 from the STICH outcome survey (control arm, Oct 2021-Mar 2022;
  Dziva Chikwari 2025, Lancet Glob Health, table 3). The model's age groups are 15-20 and 20-25, weighted 2/7 and 5/7
  to approximate 18-24. Bands are the binomial 95% CI widened by a design effect of 2.
* NG incidence (IHME projections) is accepted within ACCEPT_TOL_NG_INC band-widths: approximately right, defensible.
* VDS presenters: the share of women presenting with vaginal discharge who have no NG/CT/TV, 2014-16 (Zimbabwe STI
  Etiology Study, Chirenje 2018: about 115/200 without NG/CT/TV, excluding M. genitalium). SimpleBV stands for every
  non-STI cause of discharge. Read from the PresenterEtiology recorder.
* Priors: exp 07's, plus hiv.rel_death (scales HIV mortality on and off ART; exists from stisim 1.5.11 / v4).

Acceptance: every disease sustains in >= MIN_SEEDS_SUSTAINED of K seeds; every prevalence target and both HIV death
targets within ACCEPT_TOL band-widths; NG incidence within ACCEPT_TOL_NG_INC. The rest are in the GoF only.

Validation (recorded, not fitted; see ValidationRecorder):
  PROMISE (early readout): ~27% of pregnant women have CT/NG/TV; <10% report symptoms.
  STICH control arm: any of CT/NG/TV in women 18-24, 425/1697 = 25.0%.

Run (repo root, env stinotif4):
    N_DRAWS=500 N_WORKERS=150 python experiments/10_2026-11-25_v4_calibration/run.py
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

# --- Priors: exp 07's (no syphilis; NG duration; NG beta floor 0.05), plus HIV mortality ---
from priors import calib_pars  # noqa: E402
for k in [k for k in list(calib_pars.keys())
          if k.startswith('syph') or k.startswith('hiv_syph')]:
    del calib_pars[k]
calib_pars['ng.beta_m2f'] = ('NG β (M→F)', 0.05, 0.60, True)
calib_pars['ng.dur_asymp2clear'] = ('NG untreated asymp duration (months)', 3, 18, True)
calib_pars['hiv.rel_death'] = ('HIV mortality multiplier', 0.5, 3.0, True)

import starsim as ss  # noqa: E402
from _pipeline import generate_prior_draws, row_to_sim_pars, build_sim  # noqa: E402
os.chdir(REPO_ROOT)

OUT_DIR = HERE / 'outputs'

K_SEEDS = int(os.environ.get('K_SEEDS', 5))
LHS_SEED = 47
LHS_TOTAL = 500
N_DRAWS = int(os.environ.get('N_DRAWS', 20))
N_WORKERS = int(os.environ.get('N_WORKERS', 60))
N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
STOP = int(os.environ.get('STOP', 2030))
N_KEEP = int(os.environ.get('N_KEEP', 30))
MIN_SEEDS_SUSTAINED = int(os.environ.get('MIN_SEEDS_SUSTAINED', max(1, K_SEEDS - 1)))
ACCEPT_TOL = float(os.environ.get('ACCEPT_TOL', 0.5))  # band-widths outside band
ACCEPT_TOL_NG_INC = float(os.environ.get('ACCEPT_TOL_NG_INC', 1.0))

DISEASES = ('hiv', 'ng', 'ct', 'tv')
WIN = (2015, 2025)    # IHME data era for STI targets (inclusive calendar years)
HIV_WIN = (2010, 2020)
STICH_WIN = (2021, 2022)
YOUNG = [('prevalence_f_15_20', 2/7), ('prevalence_f_20_25', 5/7)]  # ~women 18-24


def _band(mean, rel):
    return (mean * (1 - rel), mean * (1 + rel))


def _binom_band(k, n, deff=2.0):
    p = k / n
    half = 1.96 * np.sqrt(deff * p * (1 - p) / n)
    return (p - half, p + half)


_hiv = pd.read_csv(REPO_ROOT / 'data' / 'zimbabwe_hiv_calib.csv').set_index('time')
_hiv_mean = lambda col, lo, hi: float(_hiv.loc[lo:hi, col].mean())

TARGETS = {
    # name                     band                                      (disease, result key(s), window, how)
    'hiv_prev_15_49':        ((0.115, 0.155),                            ('hiv', 'prevalence_15_49', HIV_WIN, 'mean')),
    'hiv_prev_2000s':        (_band(_hiv_mean('hiv_prevalence', 2000, 2009), 0.15),     ('hiv', 'prevalence', (2000, 2009), 'mean')),
    'hiv_prev_2010s':        (_band(_hiv_mean('hiv_prevalence', 2010, 2021), 0.15),     ('hiv', 'prevalence', (2010, 2021), 'mean')),
    'hiv_inf_2000s':         (_band(_hiv_mean('hiv_new_infections', 2000, 2009), 0.25), ('hiv', 'new_infections', (2000, 2009), 'annual_sum')),
    'hiv_inf_2010s':         (_band(_hiv_mean('hiv_new_infections', 2010, 2021), 0.25), ('hiv', 'new_infections', (2010, 2021), 'annual_sum')),
    'hiv_deaths_2000s':      (_band(_hiv_mean('hiv_new_deaths', 2000, 2009), 0.25),     ('hiv', 'new_deaths', (2000, 2009), 'annual_sum')),
    'hiv_deaths_2010s':      (_band(_hiv_mean('hiv_new_deaths', 2010, 2021), 0.25),     ('hiv', 'new_deaths', (2010, 2021), 'annual_sum')),
    'ng_prev':               ((0.010, 0.025),                            ('ng', 'prevalence', WIN, 'mean')),
    'tv_prev':               ((0.07, 0.14),                              ('tv', 'prevalence', WIN, 'mean')),
    'ng_prev_f_18_24_stich': (_binom_band(57, 1686),                     ('ng', YOUNG, STICH_WIN, 'weighted')),
    'ct_prev_f_18_24_stich': (_binom_band(281, 1746),                    ('ct', YOUNG, STICH_WIN, 'weighted')),
    'tv_prev_f_18_24_stich': (_binom_band(166, 1746),                    ('tv', YOUNG, STICH_WIN, 'weighted')),
    'nonsti_share_vds_f':    (_binom_band(115, 200, deff=1.0),           ('presenters', 'nonsti', (2014, 2016), 'presenter_share')),
    'ng_new_inf_per_yr':     ((200_000, 450_000),                        ('ng', 'new_infections', WIN, 'annual_sum')),
    'ct_new_inf_per_yr':     ((200_000, 450_000),                        ('ct', 'new_infections', WIN, 'annual_sum')),
    'tv_new_inf_per_yr':     ((700_000, 1_600_000),                      ('tv', 'new_infections', WIN, 'annual_sum')),
}
WEIGHTS = {'ng_prev': 2.0, 'tv_prev': 2.0,
           'ng_prev_f_18_24_stich': 2.0, 'ct_prev_f_18_24_stich': 2.0, 'tv_prev_f_18_24_stich': 2.0, 'nonsti_share_vds_f': 2.0,
           'hiv_inf_2000s': 0.5, 'hiv_inf_2010s': 0.5,
           'ng_new_inf_per_yr': 0.5, 'ct_new_inf_per_yr': 0.5, 'tv_new_inf_per_yr': 0.5}
PREV_TARGETS = [k for k in TARGETS if 'prev' in k]
ACCEPT = {**{t: ACCEPT_TOL for t in PREV_TARGETS + ['hiv_deaths_2000s', 'hiv_deaths_2010s', 'nonsti_share_vds_f']},
          'ng_new_inf_per_yr': ACCEPT_TOL_NG_INC}

VALIDATION_DATA = dict(promise_any_sti_pregnant=0.27, promise_symp_share_pregnant=0.10, stich_any_sti_f_18_24=425/1697,
                       ngct_share_vds_f=0.33)  # Chirenje 2018: NG 24%, CT 14%, with some overlap

TS_RESULT_NAMES = ['prevalence', 'prevalence_f', 'prevalence_m', 'prevalence_15_49', 'prevalence_f_25_30',
                   'prevalence_f_15_20', 'prevalence_f_20_25', 'new_infections', 'new_deaths']


class ValidationRecorder(ss.Analyzer):
    """ Infection with any of NG/CT/TV among pregnant women (PROMISE, 2023-25) and women 18-24 (STICH, 2021-22) """

    def __init__(self, **kwargs):
        super().__init__(name='validation', **kwargs)
        self.counts = dict(preg=0, preg_inf=0, preg_symp=0, young=0, young_inf=0)
        return

    def step(self):
        year = self.sim.now.years
        ppl = self.sim.people
        dis = [self.sim.diseases[d] for d in ('ng', 'ct', 'tv')]
        infected = dis[0].infected | dis[1].infected | dis[2].infected
        symptomatic = dis[0].symptomatic | dis[1].symptomatic | dis[2].symptomatic
        n = lambda mask: len(mask.uids)
        if 2023 <= year < 2026:
            preg = self.sim.get_module(ss.Pregnancy).P
            self.counts['preg'] += n(preg)
            self.counts['preg_inf'] += n(preg & infected)
            self.counts['preg_symp'] += n(preg & infected & symptomatic)
        if 2021 <= year < 2023:
            young = ppl.female & (ppl.age >= 18) & (ppl.age < 25)
            self.counts['young'] += n(young)
            self.counts['young_inf'] += n(young & infected)
        return


def _years(res):
    return np.floor(np.array([float(t.years) for t in res.timevec]) + 1e-9).astype(int)


def _presenter_share(sim, key, win):
    """ Among female VDS presenters (PresenterEtiology, care channel) over the window: the share with no NG/CT/TV, or with NG or CT """
    pe = sim.interventions.get('presenter_etiology')
    if pe is None:
        return float('nan')
    res = pe.results
    yrs = _years(res.n_care_f)
    m = (yrs >= win[0]) & (yrs <= win[1])
    n = np.asarray(res.n_care_f.values)[m].sum()
    if not n:
        return float('nan')
    if key == 'nonsti':
        return float(1 - np.asarray(res.any_care_f.values)[m].sum() / n)
    return float(np.asarray(res.ngct_care_f.values)[m].sum() / n)


def _stat(sim, disease, key, win, how):
    if how == 'presenter_share':
        return _presenter_share(sim, key, win)
    dres = sim.results.get(disease)
    if dres is None:
        return float('nan')
    if how == 'weighted':
        vals = [w * _stat(sim, disease, k, win, 'mean') for k, w in key]
        return float(np.sum(vals))
    if key not in dres:
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
        per_year = [np.nansum(v[yrs == y]) for y in range(win[0], win[1] + 1) if (yrs == y).any()]
        return float(np.mean(per_year))
    raise ValueError(how)


def extract(sim, draw_idx, seed):
    row = dict(draw_idx=int(draw_idx), seed=int(seed), status='ok')
    for name, (_band_, (d, key, win, how)) in TARGETS.items():
        row[name] = _stat(sim, d, key, win, how)
    c = sim.analyzers.validation.counts
    row['promise_any_sti_pregnant'] = c['preg_inf'] / c['preg'] if c['preg'] else float('nan')
    row['promise_symp_share_pregnant'] = c['preg_symp'] / c['preg_inf'] if c['preg_inf'] else float('nan')
    row['stich_any_sti_f_18_24'] = c['young_inf'] / c['young'] if c['young'] else float('nan')
    row['ngct_share_vds_f'] = _presenter_share(sim, 'ngct', (2014, 2016))
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
                ann = dres[rname].resample('year')
                yrs = np.asarray(ann.timevec.years).astype(int)
                vals = np.asarray(ann.values, dtype=float)
            except Exception:
                continue
            rows += [{'disease': d, 'result_name': rname, 'year': int(y), 'value': float(v)}
                     for y, v in zip(yrs, vals)]
    return rows


def make_sim(seed, sim_pars):
    sim = build_sim(seed=seed, sim_pars=sim_pars, stop=STOP, n_agents=N_AGENTS)
    sim.pars['analyzers'] = list(sim.pars['analyzers'] or []) + [ValidationRecorder()]
    return sim


def run_one(task):
    try:
        sim = make_sim(task['seed'], task['sim_pars'])
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
    means = ok.groupby('draw_idx')[list(TARGETS) + list(VALIDATION_DATA)].mean()
    sus = ok.groupby('draw_idx')[[f'sustained_{d}' for d in DISEASES]].sum()
    out = []
    wsum = sum(WEIGHTS.get(t, 1.0) for t in TARGETS)
    for di, row in means.iterrows():
        dist = {t: band_distance(row[t], *TARGETS[t][0]) for t in TARGETS}
        mae = sum(WEIGHTS.get(t, 1.0) * dist[t] for t in TARGETS) / wsum
        min_sus = int(sus.loc[di].min())
        acceptable = (min_sus >= MIN_SEEDS_SUSTAINED and all(dist[t] <= tol for t, tol in ACCEPT.items()))
        out.append(dict(draw_idx=int(di), mae=mae, min_seeds_sustained=min_sus, acceptable=acceptable,
                        **{f'dist_{t}': dist[t] for t in TARGETS}))
    g = pd.DataFrame(out)
    g = g.sort_values(['acceptable', 'mae'], ascending=[False, True]).reset_index(drop=True)
    g['retention_rank'] = np.arange(1, len(g) + 1)
    return means.reset_index().merge(g, on='draw_idx')


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f'exp 10 — v4 calibration | N_DRAWS={N_DRAWS} K={K_SEEDS} N_AGENTS={N_AGENTS} STOP={STOP} | '
          f'{len(calib_pars)} priors: {list(calib_pars.keys())}', flush=True)
    priors = generate_prior_draws(LHS_TOTAL, LHS_SEED).head(N_DRAWS)
    priors.to_csv(OUT_DIR / 'priors.csv', index=False)
    pd.DataFrame([dict(target=t, lo=b[0], hi=b[1], accept_tol=ACCEPT.get(t), weight=WEIGHTS.get(t, 1.0))
                  for t, (b, _) in TARGETS.items()]).to_csv(OUT_DIR / 'targets.csv', index=False)

    tasks = [dict(draw_idx=int(r['draw_idx']), sub_idx=k, seed=int(r['draw_idx']) * 1000 + k, sim_pars=row_to_sim_pars(r))
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
    print(f'  acceptable draws: {int(per_draw.acceptable.sum())}/{len(per_draw)}; keeping {len(keep)}', flush=True)
    draws_used = priors.merge(keep[['draw_idx', 'retention_rank', 'mae']], on='draw_idx')
    draws_used.sort_values('retention_rank').to_csv(OUT_DIR / 'draws_used.csv', index=False)

    if all_ts:
        ts = pd.DataFrame(all_ts)
        (ts.groupby(['draw_idx', 'disease', 'result_name', 'year'])['value'].mean()
           .reset_index().to_parquet(OUT_DIR / 'timeseries.parquet', index=False))

    cols = ['draw_idx', 'retention_rank', 'acceptable', 'min_seeds_sustained', 'mae']
    print(per_draw[cols].head(15).to_string(index=False))
    print('\n  Validation (median over draws | data):')
    for v, d in VALIDATION_DATA.items():
        print(f'    {v:30s} {per_draw[v].median():.3f} | {d:.3f}')


if __name__ == '__main__':
    main()
