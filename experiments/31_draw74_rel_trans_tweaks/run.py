"""
Exp 31 — draw 74 from exp 30 + rel_trans tweaks.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, json, pickle, time
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc
import starsim as ss

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(EXP24))

from model import make_sim
from interventions import ANC_PROBS_REALISTIC
from run import set_pars_local, grab  # noqa: E402

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
SERIES_PKL = OUTPUTS / 'series.pkl'
RESULTS    = OUTPUTS / 'results.json'

SEEDS = [101, 102, 103]
SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'

# Draw 74 + tweaks
CONFIG = {
    'hiv.beta_m2f':                    0.0270,
    'syph.beta_m2f':                   0.2370,
    'syph.rel_trans_primary':          4.0,    # was 1.73, bumped up
    'syph.rel_trans_latent_half_life': 1.2,    # was 1.0, bumped up (years)
    'syph.time_to_undetectable':       17.99,
    'syph.p_symp_primary_f':           0.5232,
    'syph.p_symp_primary_m':           0.6610,
    'syph.rel_init_prev':              0.3877,
    'syph_symp_test.rel_test':         1.0453,
    'ng.beta_m2f':                     0.1043,
    'ct.beta_m2f':                     0.0241,
    'tv.beta_m2f':                     0.4509,
    'structuredsexual.prop_f0':        0.8874,
    'structuredsexual.m1_conc':        0.2609,
    'structuredsexual.dur_sw':         11.48,
}


def run_one(seed):
    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=10_000,
                   pn_pars=None, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)

    # handle rel_trans_latent_half_life: needs to be ss.years(value)
    config_local = dict(CONFIG)
    half_life_y = config_local.pop('syph.rel_trans_latent_half_life')

    set_pars_local(sim, config_local)

    # Set rel_trans_latent_half_life as ss.years() Dist - need direct assignment
    for mod in sim.pars['diseases']:
        if getattr(mod, 'name', None) == 'syph':
            mod.pars['rel_trans_latent_half_life'] = ss.years(half_life_y)
            mod.store_sw = True
            break

    sim.init()
    syph = sim.diseases.syph

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
    _, fsw_prev = grab(r, 'prevalence_sw')
    _, nontrep_f = grab(r, 'nontrep_prevalence_15_64_f')
    _, trep_f = grab(r, 'trep_prevalence_15_64_f')

    def at(arr, y):
        return float(arr[np.argmin(np.abs(yrs - y))])

    def avg(arr, ys, y1, y2):
        m = (ys >= y1) & (ys < y2)
        return float(np.nanmean(arr[m])) if m.any() else np.nan

    plateau_years = [y for y in by_year if 2010 <= y < 2025]
    plateau = dict.fromkeys(stage_counter, 0)
    for y in plateau_years:
        for k, v in by_year[y].items():
            plateau[k] += v
    plateau_total = sum(v for k, v in plateau.items() if k != 'unknown_or_seed') or 1
    plateau_shares = {k: plateau[k] / plateau_total
                      for k in ['primary', 'secondary', 'early_latent', 'late_latent']}

    summary = {
        'seed': seed,
        'fsw_prev_2019':         at(fsw_prev, 2019),
        'nontrep_f_2016':        at(nontrep_f, 2016),
        'trep_f_2016':           at(trep_f, 2016),
        'primary_share':         plateau_shares['primary'],
        'secondary_share':       plateau_shares['secondary'],
        'early_lat_share':       plateau_shares['early_latent'],
        'late_lat_share':        plateau_shares['late_latent'],
        'new_inf_2030_2040_mean': avg(new_inf, yrs_inf, 2030, 2040),
        'overall_prev_f_2035_2040': avg(prev_f, yrs, 2035, 2040),
    }
    series = {'years': yrs, 'fsw_prev': fsw_prev,
              'nontrep_f': nontrep_f, 'trep_f': trep_f, 'overall_prev_f': prev_f}
    return summary, series


def main():
    sc.heading('Exp 31 — draw 74 + rel_trans_primary=4, half_life=1.2y')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    print('Config:')
    for k, v in CONFIG.items():
        flag = '  *' if k in ('syph.rel_trans_primary',
                              'syph.rel_trans_latent_half_life') else ''
        print(f'  {k:42s} = {v}{flag}')

    summaries, all_series = [], {}
    t0 = time.time()
    for seed in SEEDS:
        print(f'  -> seed {seed} ...', flush=True)
        s, ser = run_one(seed)
        summaries.append(s)
        all_series[seed] = ser
        print(f"     FSW={s['fsw_prev_2019']:.3f}  "
              f"nontrep_f={s['nontrep_f_2016']:.4f}  "
              f"trep_f={s['trep_f_2016']:.4f}  "
              f"prim={s['primary_share']:.2f} sec={s['secondary_share']:.2f} "
              f"el={s['early_lat_share']:.2f}")
    print(f'  {time.time()-t0:.0f}s')

    with SERIES_PKL.open('wb') as f:
        pickle.dump(all_series, f)

    df = pd.DataFrame(summaries)
    agg = {col: float(df[col].mean()) for col in df.columns if col != 'seed'}
    out = {'config': CONFIG, 'per_seed': summaries, 'mean': agg}
    RESULTS.write_text(json.dumps(out, indent=2))

    print('\n=== TARGETS (3-seed mean) ===')
    checks = [
        ('FSW prev 2019',         agg['fsw_prev_2019'],         (0.20, 0.40)),
        ('nontrep_f 2016',        agg['nontrep_f_2016'],        (0.01, 0.03)),
        ('trep_f 2016',           agg['trep_f_2016'],           (0.05, 0.10)),
        ('primary share',         agg['primary_share'],         (0.45, 0.65)),
        ('secondary share',       agg['secondary_share'],       (0.25, 0.45)),
    ]
    n_pass = 0
    for label, val, (lo, hi) in checks:
        ok = lo <= val <= hi
        n_pass += int(ok)
        print(f'  {label:24s}: {val:.4f}  [{lo}, {hi}]  {"PASS" if ok else "MISS"}')
    el_ok = agg['early_lat_share'] <= 0.15
    n_pass += int(el_ok)
    print(f'  early latent share      : {agg["early_lat_share"]:.4f}  [<=0.15]  {"PASS" if el_ok else "MISS"}')
    sust_ok = agg['new_inf_2030_2040_mean'] > 0 and agg['overall_prev_f_2035_2040'] >= 0.001
    n_pass += int(sust_ok)
    print(f'  sustained               : {agg["new_inf_2030_2040_mean"]:.2f}  {"PASS" if sust_ok else "MISS"}')
    print(f'\nN_PASS = {n_pass}/7')


if __name__ == '__main__':
    main()
