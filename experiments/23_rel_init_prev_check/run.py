"""
Initial-condition sensitivity + stratified diagnostic.

Generates 150 LHS prior draws across the now-13-param prior (priors.py
has syph.rel_init_prev added on log scale 0.02-1.00), runs each to
2040 with the syph module's FSW + risk-group result storage enabled.

Question 1: does any draw equilibrate inside the ZIMPHIA detect_f band
            [0.4%, 1.6%]?
Question 2: among sustainers, what fraction of plateau-era new
            infections (2010-2030) come from FSW + clients vs general?

Inherits all exp 22 v3 model + intervention settings.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, pickle, json, time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import starsim as ss
from scipy.stats import qmc

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from model import make_sim
from priors import calib_pars

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_DRAWS   = int(os.environ.get('N_DRAWS', 150))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))

OUTPUTS    = THIS.parent / 'outputs'
JSONL_OUT  = OUTPUTS / 'results.jsonl'
PRIOR_CSV  = OUTPUTS / 'prior_draws.csv'
SERIES_PKL = OUTPUTS / 'series.pkl'

STRATIFIED_SYPH_RESULTS = [
    'new_infections',
    'new_infections_sw',
    'new_infections_not_sw',
    'new_infections_client',
    'new_infections_not_client',
    'new_infections_risk_group_0_female',
    'new_infections_risk_group_1_female',
    'new_infections_risk_group_2_female',
    'new_infections_risk_group_0_male',
    'new_infections_risk_group_1_male',
    'new_infections_risk_group_2_male',
]

STANDARD_SERIES = [
    ('hiv',  'prevalence'),
    ('ng',   'prevalence'),
    ('ct',   'prevalence_f_25_30'),
    ('tv',   'prevalence'),
    ('syph', 'prevalence_f'),
    ('syph', 'prevalence_m'),
    ('syph', 'detectable_prevalence_15_64_f'),
    ('syph', 'detectable_prevalence_15_64_m'),
    ('syph', 'serological_prevalence_15_64_f'),
    ('syph', 'serological_prevalence_15_64_m'),
    ('syph', 'pregnant_prevalence'),
    ('syph', 'incidence'),
]


def generate_prior_draws():
    names = list(calib_pars.keys())
    bounds = []
    for name, (_, lo, hi, log_scale) in calib_pars.items():
        if log_scale:
            bounds.append((np.log(lo), np.log(hi)))
        else:
            bounds.append((lo, hi))
    sampler = qmc.LatinHypercube(d=len(names), seed=42)
    pts = sampler.random(N_DRAWS)
    rows = []
    for i in range(N_DRAWS):
        row = {'draw_idx': i}
        for j, name in enumerate(names):
            lo, hi = bounds[j]
            val = lo + pts[i, j] * (hi - lo)
            log_scale = calib_pars[name][3]
            if log_scale:
                row[f'log_{name}'] = val
            else:
                row[name] = val
        rows.append(row)
    return pd.DataFrame(rows)


def set_pars_local(sim, pars):
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        found = False
        for category in ('diseases', 'networks', 'interventions',
                         'connectors', 'analyzers', 'demographics', 'custom'):
            container = sim.pars.get(category)
            if container is None:
                continue
            if isinstance(container, list):
                for mod in container:
                    if hasattr(mod, 'name') and mod.name == mod_name:
                        if par_name == 'time_to_undetectable':
                            mod.pars[par_name] = ss.lognorm_ex(
                                ss.years(float(value)), ss.years(float(value)))
                        elif par_name == 'p_symp_primary_f':
                            mod.pars['p_symp_primary'][0] = float(value)
                        elif par_name == 'p_symp_primary_m':
                            mod.pars['p_symp_primary'][1] = float(value)
                        else:
                            existing = mod.pars.get(par_name)
                            if hasattr(existing, 'set'):
                                existing.set(mean=value)
                            else:
                                mod.pars[par_name] = value
                        found = True
                        break
            if found:
                break
    return sim


def row_to_sim_pars(row):
    sim_pars = {}
    for col, val in row.items():
        if col == 'draw_idx':
            continue
        if col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        elif '.' in col:
            sim_pars[col] = float(val)
    return sim_pars


def extract(sim):
    res = sim.results
    summary = {}
    series = {}

    def grab(disease, name):
        r = res[disease][name]
        years = np.array([t.year + t.month / 12 for t in r.timevec])
        return (years, np.array(r.values))

    def mean_prev(d, y1, y2):
        years, vals = grab(d, 'prevalence')
        m = (years >= y1) & (years < y2)
        return float(np.mean(vals[m])) if m.any() else np.nan

    def prev_at(d, name, year):
        years, vals = grab(d, name)
        i = np.argmin(np.abs(years - year))
        return float(vals[i])

    summary['hiv_prev_2000_2010']           = mean_prev('hiv', 2000, 2010)
    summary['hiv_prev_2010_2020']           = mean_prev('hiv', 2010, 2020)
    summary['ng_prev_2005_2015']            = mean_prev('ng', 2005, 2015)
    summary['ct_prev_f2530']                = prev_at('ct', 'prevalence_f_25_30', 2010)
    summary['tv_prev_2005_2015']            = mean_prev('tv', 2005, 2015)
    summary['syph_detectable_15_64_f_2016'] = prev_at('syph', 'detectable_prevalence_15_64_f', 2016)
    summary['syph_detectable_15_64_m_2016'] = prev_at('syph', 'detectable_prevalence_15_64_m', 2016)
    summary['syph_seroprev_15_64_f_2016']   = prev_at('syph', 'serological_prevalence_15_64_f', 2016)
    summary['syph_seroprev_15_64_m_2016']   = prev_at('syph', 'serological_prevalence_15_64_m', 2016)

    yrs_anc, vals_anc = grab('syph', 'pregnant_prevalence')
    m = (yrs_anc >= 2000) & (yrs_anc < 2015)
    summary['syph_anc_2000_2015'] = float(np.nanmean(vals_anc[m])) if m.any() else np.nan

    yrs_pf, prev_f = grab('syph', 'prevalence_f')
    yrs_ni, new_inf = grab('syph', 'new_infections')
    m_late = (yrs_pf >= 2035) & (yrs_pf < 2040)
    m_ni_late = (yrs_ni >= 2030) & (yrs_ni < 2040)
    summary['prev_f_2035_2040_mean']  = float(np.nanmean(prev_f[m_late])) if m_late.any() else np.nan
    summary['new_inf_2030_2040_mean'] = float(np.nanmean(new_inf[m_ni_late])) if m_ni_late.any() else np.nan
    summary['sustains'] = bool((summary['prev_f_2035_2040_mean'] >= 0.001)
                                and (summary['new_inf_2030_2040_mean'] > 0))

    def cum_sub(name, y1=2010, y2=2030):
        try:
            yrs, vals = grab('syph', name)
        except KeyError:
            return np.nan
        m = (yrs >= y1) & (yrs < y2)
        return float(np.sum(vals[m])) if m.any() else np.nan

    summary['cum_new_inf_2010_2030']            = cum_sub('new_infections')
    summary['cum_new_inf_sw_2010_2030']         = cum_sub('new_infections_sw')
    summary['cum_new_inf_not_sw_2010_2030']     = cum_sub('new_infections_not_sw')
    summary['cum_new_inf_client_2010_2030']     = cum_sub('new_infections_client')
    summary['cum_new_inf_not_client_2010_2030'] = cum_sub('new_infections_not_client')
    for sex in ('female', 'male'):
        for rg in (0, 1, 2):
            summary[f'cum_new_inf_rg{rg}_{sex}_2010_2030'] = cum_sub(
                f'new_infections_risk_group_{rg}_{sex}')

    for d, name in STANDARD_SERIES:
        series[f'{d}_{name}'] = grab(d, name)
    for name in STRATIFIED_SYPH_RESULTS:
        try:
            series[f'syph_{name}'] = grab('syph', name)
        except KeyError:
            series[f'syph_{name}'] = None

    return summary, series


def run_one(task):
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    seed = int(draw_idx) * 1000
    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)

        for mod in sim.pars['diseases']:
            if getattr(mod, 'name', None) == 'syph':
                mod.store_sw = True
                mod.store_risk_groups = True
                break

        sim.init()
        sim.run()
        summary, series = extract(sim)
        summary['draw_idx'] = draw_idx
        summary['status'] = 'ok'
        return summary, draw_idx, series
    except Exception as e:
        return ({'draw_idx': draw_idx,
                 'status': f'error: {type(e).__name__}: {e}'},
                draw_idx, None)


def main():
    sc.heading(f'Exp 23 — rel_init_prev sensitivity + stratified diagnostic: '
               f'{N_DRAWS} prior draws, n_agents={N_AGENTS}, stop={STOP}, '
               f'{N_WORKERS} workers')
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    prior_df = generate_prior_draws()
    prior_df.to_csv(PRIOR_CSV, index=False)
    print(f'LHS prior draws saved to {PRIOR_CSV}')
    print(f'priors ({len(calib_pars)}): {list(calib_pars.keys())}')

    tasks = []
    for _, row in prior_df.iterrows():
        tasks.append(dict(draw_idx=int(row['draw_idx']),
                          sim_pars=row_to_sim_pars(row)))

    print(f'Running {len(tasks)} sims to {STOP} on {N_WORKERS} workers...')
    t0 = time.time()
    summaries = []
    series_map = {}
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('w') as fout:
            for i, (summary, draw_idx, series) in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(summary) + '\n')
                fout.flush()
                summaries.append(summary)
                if series is not None:
                    series_map[draw_idx] = series
                if i % 10 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i}/{len(tasks)}] rate={rate:.2f}/s '
                          f'elapsed={elapsed:.0f}s eta={eta:.0f}s')

    with SERIES_PKL.open('wb') as f:
        pickle.dump(series_map, f)
    print(f'Series saved to {SERIES_PKL}')

    df = pd.DataFrame(summaries)
    df_ok = df[df['status'] == 'ok']
    n_sustain = int(df_ok['sustains'].sum()) if len(df_ok) else 0
    in_band = df_ok[(df_ok['sustains']) &
                    (df_ok['syph_detectable_15_64_f_2016'] >= 0.004) &
                    (df_ok['syph_detectable_15_64_f_2016'] <= 0.016)]
    print(f'\n=== RESULT ===')
    print(f'Sims ok: {len(df_ok)}/{len(df)}')
    print(f'Sustaining: {n_sustain}/{len(df_ok)}')
    print(f'Sustainers in ZIMPHIA detect_f band [0.4%, 1.6%]: {len(in_band)}')
    print(f'PRIMARY {"PASSES (>=1 in band)" if len(in_band) >= 1 else "FAILS - bifurcation likely structural"}')


if __name__ == '__main__':
    main()
