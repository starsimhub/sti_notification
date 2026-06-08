"""
Exp 33 — LHS over 17 priors with FSW MF-concurrency multiplier.

Builds on exp 32 (16-dim LHS) by adding `structuredsexual.fsw_mf_conc_mult`
as a 17th prior (range [0.1, 1.0]). Scales FSW agents' MF (non-commercial)
partnership concurrency, leaving SW (client) partnerships untouched.
Tests whether reducing the F_fsw → M_other channel (8% of plateau
transmissions in exp 32) collapses the general-pop transmission engine
or leaves it self-sustaining via residual M↔F circulation.

300 LHS draws, single seed each, parallelised on 24 workers. Same 9
targets as exp 32.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json, time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
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
EVENTS_DIR = OUTPUTS / 'events'
JSONL_OUT  = OUTPUTS / 'results.jsonl'
PRIOR_CSV  = OUTPUTS / 'prior_draws.csv'
RESULTS    = OUTPUTS / 'results.json'

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_DRAWS   = int(os.environ.get('N_DRAWS', 300))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))

SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'

# Targets — see config.yaml for the band definitions
TARGET_BANDS = {
    'fsw_band':           (0.20, 0.40),
    'nontrep_band':       (0.01, 0.05),
    'trep_band':          (0.05, 0.10),
    'primary_band':       (0.45, 0.65),
    'secondary_band':     (0.25, 0.45),
    'hiv_pos_trep_band':  (0.05, 0.09),
    'hiv_trep_ratio_band': (3.0, 6.0),
}
EARLY_LAT_MAX = 0.15


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


def find_analyzer(sim, name):
    return getattr(sim.analyzers, name, None)


def stage_shares_from_matrix(matrix):
    """Aggregate (src_cat, dst_cat, stage) -> per-stage transmission counts."""
    by_stage = {'primary': 0, 'secondary': 0, 'early_latent': 0,
                'late_latent': 0, 'unknown': 0}
    for (_src, _dst, stage), n in matrix.items():
        by_stage[stage] = by_stage.get(stage, 0) + n
    total = sum(v for k, v in by_stage.items() if k != 'unknown') or 1
    return {k: v / total for k, v in by_stage.items() if k != 'unknown'}


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

        sim.run()

        r = sim.results['syph']
        yrs, prev_f      = grab(r, 'prevalence_f')
        yrs_inf, new_inf = grab(r, 'new_infections')
        _, fsw_prev      = grab(r, 'prevalence_sw')
        _, client_prev   = grab(r, 'prevalence_client')
        _, nontrep_f     = grab(r, 'nontrep_prevalence_15_64_f')
        _, trep_f        = grab(r, 'trep_prevalence_15_64_f')

        # HIV-stratified syph from the two new coinfection analyzers
        r_trep    = sim.results['syph_hiv_trep']
        r_nontrep = sim.results['syph_hiv_nontrep']
        yrs_ana, trep_has_hiv    = grab(r_trep, 'syph_prev_has_hiv')
        _, trep_no_hiv           = grab(r_trep, 'syph_prev_no_hiv')
        _, nontrep_has_hiv       = grab(r_nontrep, 'syph_prev_has_hiv')
        _, nontrep_no_hiv        = grab(r_nontrep, 'syph_prev_no_hiv')

        _, hiv_prev = grab(sim.results['hiv'], 'prevalence')
        _, ng_prev  = grab(sim.results['ng'],  'prevalence')
        _, ct_prev  = grab(sim.results['ct'],  'prevalence_f_25_30')
        _, tv_prev  = grab(sim.results['tv'],  'prevalence')

        def at(arr, ys, year):
            i = np.argmin(np.abs(ys - year))
            return float(arr[i])

        def avg(arr, ys, y1, y2):
            m = (ys >= y1) & (ys < y2)
            return float(np.nanmean(arr[m])) if m.any() else np.nan

        # Stage shares + transmission matrix from the analyzer
        ana = find_analyzer(sim, 'syph_transmission_events')
        matrix = dict(ana.matrix) if ana is not None else {}
        src_count = dict(ana.src_count) if ana is not None else {}
        plateau_shares = stage_shares_from_matrix(matrix)

        # Persist event log (compact JSON) for downstream Lorenz + matrix work
        if ana is not None:
            EVENTS_DIR.mkdir(parents=True, exist_ok=True)
            (EVENTS_DIR / f'events_{draw_idx:04d}.json').write_text(
                json.dumps(ana.as_dict()))

        # Headline metrics
        fsw_v    = at(fsw_prev, yrs, 2019)
        ntr_v    = at(nontrep_f, yrs, 2016)
        tr_v     = at(trep_f, yrs, 2016)
        prim_v   = plateau_shares.get('primary', 0.0)
        sec_v    = plateau_shares.get('secondary', 0.0)
        el_v     = plateau_shares.get('early_latent', 0.0)
        ll_v     = plateau_shares.get('late_latent', 0.0)
        ni_late  = avg(new_inf, yrs_inf, 2030, 2040)
        pf_late  = avg(prev_f, yrs, 2035, 2040)
        sust     = bool(ni_late > 0 and pf_late >= 0.001)

        hiv_pos_trep    = at(trep_has_hiv, yrs_ana, 2016)
        hiv_neg_trep    = at(trep_no_hiv, yrs_ana, 2016)
        hiv_pos_nontrep = at(nontrep_has_hiv, yrs_ana, 2016)
        hiv_neg_nontrep = at(nontrep_no_hiv, yrs_ana, 2016)
        hiv_trep_ratio = (hiv_pos_trep / hiv_neg_trep) if hiv_neg_trep > 0 else np.nan

        passes = {
            'fsw_band':       TARGET_BANDS['fsw_band'][0]      <= fsw_v <= TARGET_BANDS['fsw_band'][1],
            'nontrep_band':   TARGET_BANDS['nontrep_band'][0]  <= ntr_v <= TARGET_BANDS['nontrep_band'][1],
            'trep_band':      TARGET_BANDS['trep_band'][0]     <= tr_v  <= TARGET_BANDS['trep_band'][1],
            'primary_band':   TARGET_BANDS['primary_band'][0]  <= prim_v <= TARGET_BANDS['primary_band'][1],
            'secondary_band': TARGET_BANDS['secondary_band'][0] <= sec_v <= TARGET_BANDS['secondary_band'][1],
            'early_lat_band': el_v <= EARLY_LAT_MAX,
            'sustained':      sust,
            'hiv_pos_trep_band':  TARGET_BANDS['hiv_pos_trep_band'][0]  <= hiv_pos_trep    <= TARGET_BANDS['hiv_pos_trep_band'][1],
            'hiv_trep_ratio_band': (not np.isnan(hiv_trep_ratio)) and TARGET_BANDS['hiv_trep_ratio_band'][0] <= hiv_trep_ratio <= TARGET_BANDS['hiv_trep_ratio_band'][1],
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
            'late_lat_share':  ll_v,
            'client_prev_2016': at(client_prev, yrs, 2016),
            'overall_prev_f_2035_2040_mean': pf_late,
            'new_inf_2030_2040_mean': ni_late,
            'hiv_pos_trep_2016':    hiv_pos_trep,
            'hiv_neg_trep_2016':    hiv_neg_trep,
            'hiv_pos_nontrep_2016': hiv_pos_nontrep,
            'hiv_neg_nontrep_2016': hiv_neg_nontrep,
            'hiv_trep_ratio_2016':  float(hiv_trep_ratio) if not np.isnan(hiv_trep_ratio) else None,
            'hiv_prev_2000_2010':   avg(hiv_prev, yrs, 2000, 2010),
            'hiv_prev_2010_2020':   avg(hiv_prev, yrs, 2010, 2020),
            'ng_prev_2005_2015':    avg(ng_prev,  yrs, 2005, 2015),
            'ct_prev_2010':         at(ct_prev, yrs, 2010),
            'tv_prev_2005_2015':    avg(tv_prev,  yrs, 2005, 2015),
            'n_top_spreaders_50pct': top_spreader_count(src_count),
            'passes': passes,
            'n_pass': n_pass,
            'status': 'ok',
        }
    except Exception as e:
        import traceback
        return {'draw_idx': draw_idx,
                'status': f'error: {type(e).__name__}: {e}',
                'traceback': traceback.format_exc()[-500:]}


def top_spreader_count(src_count):
    """How many agents account for the top 50% of onward transmissions?
    Lorenz summary statistic."""
    if not src_count:
        return None
    counts = sorted(src_count.values(), reverse=True)
    total = sum(counts)
    if total == 0:
        return None
    cum = 0
    for i, c in enumerate(counts):
        cum += c
        if cum >= 0.5 * total:
            return i + 1
    return len(counts)


def main():
    sc.heading(f'Exp 33 — LHS sweep, {N_DRAWS} draws over {len(calib_pars)} priors')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)
    EVENTS_DIR.mkdir(parents=True, exist_ok=True)

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

    print('\n=== HIT-COUNT DISTRIBUTION (out of 9 targets) ===')
    for n in range(10):
        c = (df_ok['n_pass'] == n).sum()
        marker = '  <- definitive pass' if n >= 7 else ''
        print(f'  {n}/9 targets: {c} draws{marker}')

    six_plus = df_ok[df_ok['n_pass'] >= 6]
    print(f'\n=== TOP DRAWS (6+/9) ===')
    if len(six_plus) > 0:
        print(six_plus[['draw_idx', 'n_pass', 'fsw_prev_2019',
                        'nontrep_f_2016', 'trep_f_2016',
                        'hiv_pos_trep_2016', 'hiv_trep_ratio_2016',
                        'primary_share', 'secondary_share',
                        'new_inf_2030_2040_mean']
                       ].sort_values('n_pass', ascending=False).head(30)
                       .round(4).to_string(index=False))
    else:
        print('  None — definitive miss.')

    out = {'n_draws': N_DRAWS,
           'n_priors': len(calib_pars),
           'n_targets': 9,
           'n_ok': int(len(df_ok)),
           'n_pass_distribution': {int(n): int((df_ok['n_pass']==n).sum())
                                    for n in range(10)},
           'definitive_pass': int((df_ok['n_pass'] >= 7).sum() >= 1),
           'partial_pass':    int((df_ok['n_pass'] >= 6).sum() >= 1),
           'best_n_pass':     int(df_ok['n_pass'].max()) if len(df_ok) else 0}
    RESULTS.write_text(json.dumps(out, indent=2))


if __name__ == '__main__':
    main()
