"""
Exp 30 — definitive LHS sweep over 14-dim prior with all structural fixes in place.

300 LHS draws, single seed each, parallelized on 24 workers. For each draw:
  - Standard summary metrics (HIV/NG/CT/TV prev, FSW prev, client prev,
    nontrep_f, trep_f, ANC prev, sustainability)
  - By-stage transmission attribution (primary / secondary / early latent /
    late latent) — per feedback-stage-share-check memory
  - Pass/fail across 7 loose targets

Answers: does ANY prior draw produce reasonable concentrated-sustained dynamics?
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json, pickle, time
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
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
sys.path.insert(0, str(EXP24))

from model import make_sim
from priors import calib_pars
from interventions import ANC_PROBS_REALISTIC
from run import set_pars_local, grab  # noqa: E402

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
JSONL_OUT  = OUTPUTS / 'results.jsonl'
PRIOR_CSV  = OUTPUTS / 'prior_draws.csv'
SERIES_PKL = OUTPUTS / 'series.pkl'
RESULTS    = OUTPUTS / 'results.json'

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_DRAWS   = int(os.environ.get('N_DRAWS', 300))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))

SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'


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
            if calib_pars[name][3]:  # log_scale
                row[f'log_{name}'] = val
            else:
                row[name] = val
        rows.append(row)
    return pd.DataFrame(rows)


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


def run_one(task):
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    seed = int(draw_idx) * 1000
    try:
        symp_test = pd.read_csv(SYMP_TEST_CSV)
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1,
                       syph_symp_test_prob=symp_test,
                       syph_anc_probs=ANC_PROBS_REALISTIC)
        set_pars_local(sim, sim_pars)

        for mod in sim.pars['diseases']:
            if getattr(mod, 'name', None) == 'syph':
                mod.store_sw = True
                break

        sim.init()
        syph = sim.diseases.syph

        # Stage-share instrumentation
        stage_counter = {'primary': 0, 'secondary': 0, 'early_latent': 0,
                         'late_latent': 0, 'unknown_or_seed': 0}
        by_year = {}
        original = syph.set_prognoses

        def instrumented(uids, source_uids=None, ti=None):
            if source_uids is not None and len(source_uids) > 0:
                cti = ti if ti is not None else syph.ti
                try:
                    year = int(syph.t.timevec[cti].year)
                except Exception:
                    year = -1
                yk = by_year.setdefault(year, dict.fromkeys(stage_counter, 0))
                for s in np.atleast_1d(source_uids):
                    if syph.primary[s]:
                        stage_counter['primary'] += 1; yk['primary'] += 1
                    elif syph.secondary[s]:
                        stage_counter['secondary'] += 1; yk['secondary'] += 1
                    elif syph.early[s]:
                        stage_counter['early_latent'] += 1; yk['early_latent'] += 1
                    elif syph.late[s]:
                        stage_counter['late_latent'] += 1; yk['late_latent'] += 1
                    else:
                        stage_counter['unknown_or_seed'] += 1
                        yk['unknown_or_seed'] += 1
            return original(uids, source_uids, ti)

        syph.set_prognoses = instrumented
        sim.run()

        r = sim.results['syph']
        yrs, prev_f = grab(r, 'prevalence_f')
        yrs_inf, new_inf = grab(r, 'new_infections')
        _, fsw_prev    = grab(r, 'prevalence_sw')
        _, client_prev = grab(r, 'prevalence_client')
        _, nontrep_f   = grab(r, 'nontrep_prevalence_15_64_f')
        _, trep_f      = grab(r, 'trep_prevalence_15_64_f')
        _, hiv_prev = grab(sim.results['hiv'], 'prevalence')
        _, ng_prev  = grab(sim.results['ng'],  'prevalence')
        _, ct_prev  = grab(sim.results['ct'],  'prevalence_f_25_30')
        _, tv_prev  = grab(sim.results['tv'],  'prevalence')

        def at(arr, year):
            i = np.argmin(np.abs(yrs - year))
            return float(arr[i])

        def avg(arr, ys, y1, y2):
            m = (ys >= y1) & (ys < y2)
            return float(np.nanmean(arr[m])) if m.any() else np.nan

        plateau_years = [y for y in by_year if 2010 <= y < 2025]
        plateau = dict.fromkeys(stage_counter, 0)
        for y in plateau_years:
            for k, v in by_year[y].items():
                plateau[k] += v
        plateau_total = sum(v for k, v in plateau.items() if k != 'unknown_or_seed') or 1
        plateau_shares = {k: plateau[k] / plateau_total for k in
                          ['primary', 'secondary', 'early_latent', 'late_latent']}

        # Loose target pass/fail
        fsw_v   = at(fsw_prev, 2019)
        ntr_v   = at(nontrep_f, 2016)
        tr_v    = at(trep_f, 2016)
        prim_v  = plateau_shares['primary']
        sec_v   = plateau_shares['secondary']
        el_v    = plateau_shares['early_latent']
        ni_late = avg(new_inf, yrs_inf, 2030, 2040)
        pf_late = avg(prev_f, yrs, 2035, 2040)
        sust = bool(ni_late > 0 and pf_late >= 0.001)

        passes = {
            'fsw_band':       0.20 <= fsw_v <= 0.40,
            'nontrep_band':   0.01 <= ntr_v <= 0.03,
            'trep_band':      0.05 <= tr_v <= 0.10,
            'primary_band':   0.45 <= prim_v <= 0.65,
            'secondary_band': 0.25 <= sec_v <= 0.45,
            'early_lat_band': el_v <= 0.15,
            'sustained':      sust,
        }
        n_pass = sum(passes.values())

        return {
            'draw_idx': draw_idx,
            'fsw_prev_2019':   fsw_v,
            'nontrep_f_2016':  ntr_v,
            'trep_f_2016':     tr_v,
            'primary_share':   prim_v,
            'secondary_share': sec_v,
            'early_lat_share': el_v,
            'late_lat_share':  plateau_shares['late_latent'],
            'client_prev_2016': at(client_prev, 2016),
            'overall_prev_f_2035_2040_mean': pf_late,
            'new_inf_2030_2040_mean': ni_late,
            'hiv_prev_2000_2010':  avg(hiv_prev, yrs, 2000, 2010),
            'hiv_prev_2010_2020':  avg(hiv_prev, yrs, 2010, 2020),
            'ng_prev_2005_2015':   avg(ng_prev,  yrs, 2005, 2015),
            'ct_prev_2010':        at(ct_prev, 2010),
            'tv_prev_2005_2015':   avg(tv_prev,  yrs, 2005, 2015),
            'passes': passes,
            'n_pass': n_pass,
            'status': 'ok',
        }
    except Exception as e:
        return {'draw_idx': draw_idx,
                'status': f'error: {type(e).__name__}: {e}'}


def main():
    sc.heading(f'Exp 30 — definitive LHS sweep, {N_DRAWS} draws over {len(calib_pars)} priors')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    prior_df = generate_prior_draws()
    prior_df.to_csv(PRIOR_CSV, index=False)
    print(f'Priors ({len(calib_pars)}): {list(calib_pars.keys())}')
    print(f'Draws saved to {PRIOR_CSV}')

    tasks = []
    for _, row in prior_df.iterrows():
        tasks.append({'draw_idx': int(row['draw_idx']),
                      'sim_pars': row_to_sim_pars(row)})

    print(f'\nRunning {len(tasks)} sims on {N_WORKERS} workers...')
    t0 = time.time()
    summaries = []
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('w') as fout:
            for i, summary in enumerate(
                    pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(summary) + '\n')
                fout.flush()
                summaries.append(summary)
                if i % 20 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    n_pass_distrib = {}
                    for s in summaries:
                        if s.get('status') == 'ok':
                            n = s.get('n_pass', 0)
                            n_pass_distrib[n] = n_pass_distrib.get(n, 0) + 1
                    distrib_str = ' '.join(f'{k}:{v}' for k, v in
                                            sorted(n_pass_distrib.items()))
                    print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s eta={eta:.0f}s  '
                          f'n_pass histogram: {distrib_str}', flush=True)
    print(f'\nTotal {time.time()-t0:.1f}s')

    df = pd.DataFrame(summaries)
    df_ok = df[df['status'] == 'ok'].copy()
    print(f'\nOK: {len(df_ok)}/{len(df)}')

    print('\n=== HIT-COUNT DISTRIBUTION ===')
    for n in range(8):
        c = (df_ok['n_pass'] == n).sum()
        marker = '  <- definitive pass' if n >= 6 else ''
        print(f'  {n}/7 targets: {c} draws{marker}')

    six_plus = df_ok[df_ok['n_pass'] >= 6]
    print(f'\n=== TOP DRAWS (6+/7) ===')
    if len(six_plus) > 0:
        print(six_plus[['draw_idx', 'n_pass', 'fsw_prev_2019', 'nontrep_f_2016',
                        'trep_f_2016', 'primary_share', 'secondary_share',
                        'early_lat_share', 'new_inf_2030_2040_mean']
                       ].sort_values('n_pass', ascending=False).head(20)
                       .round(4).to_string(index=False))
    else:
        print('  None — definitive miss.')

    # Best of best (n_pass=7)
    seven = df_ok[df_ok['n_pass'] == 7]
    if len(seven) > 0:
        print(f'\n=== FULL-PASS DRAWS (7/7) ===')
        priors = pd.read_csv(PRIOR_CSV)
        merged = seven.merge(priors, on='draw_idx')
        param_cols = [c for c in merged.columns if c.startswith('log_') or '.' in c]
        print(f'  {len(seven)} draws hit all 7 targets')
        print('  Mean parameter values among these draws:')
        for c in param_cols:
            vals = merged[c]
            if c.startswith('log_'):
                print(f'    {c[4:]:36s} = {np.exp(vals.mean()):.4f}  '
                      f'(range exp: [{np.exp(vals.min()):.4f}, {np.exp(vals.max()):.4f}])')
            else:
                print(f'    {c:36s} = {vals.mean():.4f}  '
                      f'(range: [{vals.min():.4f}, {vals.max():.4f}])')

    out = {'n_draws': N_DRAWS,
           'n_ok': int(len(df_ok)),
           'n_pass_distribution': {int(n): int((df_ok['n_pass']==n).sum())
                                    for n in range(8)},
           'definitive_pass': int((df_ok['n_pass'] >= 6).sum() >= 5),
           'partial_pass':    int((df_ok['n_pass'] >= 6).sum() >= 1),
           'best_n_pass':     int(df_ok['n_pass'].max()) if len(df_ok) else 0}
    RESULTS.write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
