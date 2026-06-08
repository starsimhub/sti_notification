"""
Concentrated-sustained hypothesis test (hand-picked).

Single parameter configuration, 3 seeds, full instrumentation:
  - FSW + risk-group result storage on (prevalence_sw, etc)
  - syph.set_prognoses wrapped to record source-stage per transmission
  - Defensible ANC ramp (peak 70% by 2018, 85% by 2030)
  - Boosted FSW/RG2 women + 0.20 men care-seeking CSV

Success: FSW prev 2019 in [0.20, 0.40] AND nontrep_15_64_f 2016
in [0.004, 0.016] AND stage shares primary 50-65% / sec 25-40% AND
sustained through 2040.
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
sys.path.insert(0, str(PROJECT_ROOT))

from model import make_sim
from interventions import ANC_PROBS_REALISTIC

HERE       = THIS.parent
OUTPUTS    = HERE / 'outputs'
SERIES_PKL = OUTPUTS / 'series.pkl'
STAGE_CSV  = OUTPUTS / 'stage_shares.csv'
RESULTS    = OUTPUTS / 'results.json'

N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
START    = int(os.environ.get('START', 1985))
STOP     = int(os.environ.get('STOP', 2040))
SEEDS    = [101, 102, 103]

# Hand-picked configuration
CONFIG = {
    'syph.beta_m2f':              0.20,
    'syph.time_to_undetectable':  20.0,
    'syph.p_symp_primary_f':      0.50,
    'syph.p_symp_primary_m':      0.80,
    'syph.rel_init_prev':         0.20,
    'syph_symp_test.rel_test':    1.30,
    'structuredsexual.prop_f0':   0.55,
    'structuredsexual.m1_conc':   0.20,
    'structuredsexual.dur_sw':    15.0,
    'hiv.beta_m2f':               0.025,
    'ng.beta_m2f':                0.10,
    'ct.beta_m2f':                0.10,
    'tv.beta_m2f':                0.20,
}

SYMP_TEST_CSV = HERE / 'data' / 'symp_test_prob_concentrated.csv'


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
                        elif par_name == 'rel_trans_latent_half_life':
                            # ss.dur required so starsim does the timestep conversion
                            mod.pars[par_name] = ss.years(float(value))
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


def grab(r, name):
    res = r[name]
    years = np.array([t.year + t.month / 12 for t in res.timevec])
    return (years, np.array(res.values))


def run_one(seed):
    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                   pn_pars=None, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, CONFIG)

    # FSW + risk-group result storage
    for mod in sim.pars['diseases']:
        if getattr(mod, 'name', None) == 'syph':
            mod.store_sw = True
            mod.store_risk_groups = True
            break

    sim.init()
    syph = sim.diseases.syph

    # Instrument set_prognoses to record source-stage of every transmission
    stage_counter = {'primary': 0, 'secondary': 0, 'early_latent': 0,
                     'late_latent': 0, 'unknown_or_seed': 0}
    by_year = {}
    original_set_prognoses = syph.set_prognoses

    def instrumented(uids, source_uids=None, ti=None):
        if source_uids is not None and len(source_uids) > 0:
            current_ti = ti if ti is not None else syph.ti
            try:
                year = int(syph.t.timevec[current_ti].year)
            except Exception:
                year = -1
            yk = by_year.setdefault(year, dict.fromkeys(stage_counter, 0))
            for s_uid in np.atleast_1d(source_uids):
                if syph.primary[s_uid]:
                    stage_counter['primary'] += 1; yk['primary'] += 1
                elif syph.secondary[s_uid]:
                    stage_counter['secondary'] += 1; yk['secondary'] += 1
                elif syph.early[s_uid]:
                    stage_counter['early_latent'] += 1; yk['early_latent'] += 1
                elif syph.late[s_uid]:
                    stage_counter['late_latent'] += 1; yk['late_latent'] += 1
                else:
                    stage_counter['unknown_or_seed'] += 1
                    yk['unknown_or_seed'] += 1
        return original_set_prognoses(uids, source_uids, ti)

    syph.set_prognoses = instrumented
    sim.run()

    r = sim.results['syph']
    yrs, prev_f = grab(r, 'prevalence_f')
    yrs_inf, new_inf = grab(r, 'new_infections')
    _, fsw_prev = grab(r, 'prevalence_sw')
    _, client_prev = grab(r, 'prevalence_client')
    _, nontrep_f = grab(r, 'nontrep_prevalence_15_64_f')
    _, nontrep_m = grab(r, 'nontrep_prevalence_15_64_m')
    _, trep_f = grab(r, 'trep_prevalence_15_64_f')
    _, trep_m = grab(r, 'trep_prevalence_15_64_m')
    _, anc_prev = grab(r, 'pregnant_prevalence')

    def at(arr, year):
        i = np.argmin(np.abs(yrs - year))
        return float(arr[i])

    def avg(arr, ys, y1, y2):
        m = (ys >= y1) & (ys < y2)
        return float(np.nanmean(arr[m])) if m.any() else np.nan

    # Plateau-era stage shares (2010-2025)
    plateau_years = [y for y in by_year if 2010 <= y < 2025]
    plateau = dict.fromkeys(stage_counter, 0)
    for y in plateau_years:
        for k, v in by_year[y].items():
            plateau[k] += v
    plateau_total = sum(v for k, v in plateau.items() if k != 'unknown_or_seed') or 1
    plateau_shares = {k: plateau[k] / plateau_total for k in
                       ['primary', 'secondary', 'early_latent', 'late_latent']}

    summary = {
        'seed': seed,
        'nontrep_f_2016':       at(nontrep_f, 2016),
        'nontrep_m_2016':       at(nontrep_m, 2016),
        'trep_f_2016':          at(trep_f, 2016),
        'trep_m_2016':          at(trep_m, 2016),
        'fsw_prev_2019':        at(fsw_prev, 2019),
        'fsw_prev_2016':        at(fsw_prev, 2016),
        'fsw_prev_2030_avg':    avg(fsw_prev, yrs, 2030, 2040),
        'client_prev_2016':     at(client_prev, 2016),
        'anc_prev_2010':        at(anc_prev, 2010),
        'overall_prev_f_2016':  at(prev_f, 2016),
        'overall_prev_f_2035_2040_mean': avg(prev_f, yrs, 2035, 2040),
        'new_inf_2030_2040_mean': avg(new_inf, yrs_inf, 2030, 2040),
        'stage_share_primary_plateau':  plateau_shares['primary'],
        'stage_share_secondary_plateau': plateau_shares['secondary'],
        'stage_share_early_latent_plateau': plateau_shares['early_latent'],
        'stage_share_late_latent_plateau': plateau_shares['late_latent'],
    }
    series = {
        'years': yrs,
        'prev_f': prev_f, 'fsw_prev': fsw_prev, 'client_prev': client_prev,
        'nontrep_f': nontrep_f, 'nontrep_m': nontrep_m,
        'trep_f': trep_f, 'trep_m': trep_m,
        'anc_prev': anc_prev, 'new_inf': new_inf,
    }
    stage_rows = []
    for year in sorted(by_year):
        total = sum(v for k, v in by_year[year].items() if k != 'unknown_or_seed') or 1
        for stage in ['primary', 'secondary', 'early_latent', 'late_latent']:
            stage_rows.append({'seed': seed, 'year': year, 'stage': stage,
                               'n': by_year[year][stage],
                               'share': by_year[year][stage] / total})
    return summary, series, stage_rows


def main():
    sc.heading('Exp 24 — concentrated-sustained hand-picked, 3 seeds')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    print('Config:')
    for k, v in CONFIG.items():
        print(f'  {k:42s} = {v}')
    print(f'  symp_test CSV: {SYMP_TEST_CSV.name}')
    print(f'  anc_probs: {ANC_PROBS_REALISTIC} at years [1980,1990,1999,2008,2012,2018,2040]')

    summaries, all_series, all_stage_rows = [], {}, []
    t0 = time.time()
    for seed in SEEDS:
        print(f'  -> seed {seed} ...', flush=True)
        summary, series, stage_rows = run_one(seed)
        summaries.append(summary)
        all_series[seed] = series
        all_stage_rows.extend(stage_rows)
        print(f'     FSW prev 2019 = {summary["fsw_prev_2019"]:.3f}  '
              f'nontrep_f 2016 = {summary["nontrep_f_2016"]:.4f}  '
              f"primary={summary['stage_share_primary_plateau']:.2f} "
              f"sec={summary['stage_share_secondary_plateau']:.2f}")
    print(f'  total {time.time()-t0:.1f}s')

    pd.DataFrame(all_stage_rows).to_csv(STAGE_CSV, index=False)
    with SERIES_PKL.open('wb') as f:
        pickle.dump(all_series, f)

    df = pd.DataFrame(summaries)
    aggregates = {col: float(df[col].mean()) for col in df.columns if col != 'seed'}
    out = {'config': CONFIG,
           'anc_probs': ANC_PROBS_REALISTIC,
           'seeds': SEEDS,
           'per_seed': summaries,
           'mean': aggregates}
    RESULTS.write_text(json.dumps(out, indent=2))

    # Success check
    print('\n=== TARGETS ===')
    fsw_pass    = (0.20 <= aggregates['fsw_prev_2019'] <= 0.40)
    nontrep_pass = (0.004 <= aggregates['nontrep_f_2016'] <= 0.016)
    primary_pass = (0.50 <= aggregates['stage_share_primary_plateau'] <= 0.65)
    secondary_pass = (0.25 <= aggregates['stage_share_secondary_plateau'] <= 0.40)
    sustain_pass = (aggregates['new_inf_2030_2040_mean'] > 0 and
                    aggregates['overall_prev_f_2035_2040_mean'] >= 0.001)
    for label, val, ok in [
        ('FSW prev 2019',          aggregates['fsw_prev_2019'],            fsw_pass),
        ('nontrep_f 2016',         aggregates['nontrep_f_2016'],           nontrep_pass),
        ('primary share plateau',  aggregates['stage_share_primary_plateau'], primary_pass),
        ('secondary share plateau', aggregates['stage_share_secondary_plateau'], secondary_pass),
        ('sustained to 2040',      aggregates['new_inf_2030_2040_mean'],   sustain_pass)]:
        print(f'  {label:28s}: {val:.4f}  {"PASS" if ok else "MISS"}')
    overall = all([fsw_pass, nontrep_pass, primary_pass, secondary_pass, sustain_pass])
    print(f'\nOVERALL: {"PASS" if overall else "FAIL"}')


if __name__ == '__main__':
    main()
