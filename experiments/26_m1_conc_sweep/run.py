"""
m1_conc sweep — find the sweet spot at v3 base config.

Sweeps `structuredsexual.m1_conc` over a small grid, 3 seeds each,
parallelized. Holds prop_f0=0.85 (insulate rg0 women) and
client_shares=0.20 (preserve client→FSW bridge); all other knobs
from exp 24's hand-pick.
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

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
sys.path.insert(0, str(EXP24))
from run import set_pars_local, grab  # noqa: E402

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
M1_CONC_GRID = [0.05, 0.08, 0.10, 0.12, 0.15, 0.20]

BASE_CONFIG = {
    'syph.beta_m2f':                  0.20,
    'syph.time_to_undetectable':      20.0,
    'syph.p_symp_primary_f':          0.50,
    'syph.p_symp_primary_m':          0.80,
    'syph.rel_init_prev':             0.20,
    'syph_symp_test.rel_test':        1.30,
    'structuredsexual.prop_f0':       0.85,
    'structuredsexual.client_shares': 0.20,
    'structuredsexual.dur_sw':        15.0,
    'hiv.beta_m2f':                   0.025,
    'ng.beta_m2f':                    0.10,
    'ct.beta_m2f':                    0.10,
    'tv.beta_m2f':                    0.20,
}
SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'


def run_one(task):
    seed = task['seed']
    m1_conc = task['m1_conc']
    config = dict(BASE_CONFIG)
    config['structuredsexual.m1_conc'] = m1_conc

    try:
        symp_test = pd.read_csv(SYMP_TEST_CSV)
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1,
                       syph_symp_test_prob=symp_test,
                       syph_anc_probs=ANC_PROBS_REALISTIC)
        set_pars_local(sim, config)

        for mod in sim.pars['diseases']:
            if getattr(mod, 'name', None) == 'syph':
                mod.store_sw = True
                mod.store_risk_groups = True
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
        _, fsw_prev    = grab(r, 'prevalence_sw')
        _, client_prev = grab(r, 'prevalence_client')
        _, nontrep_f   = grab(r, 'nontrep_prevalence_15_64_f')
        _, nontrep_m   = grab(r, 'nontrep_prevalence_15_64_m')
        _, trep_f      = grab(r, 'trep_prevalence_15_64_f')
        _, trep_m      = grab(r, 'trep_prevalence_15_64_m')

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

        summary = {
            'm1_conc':                m1_conc,
            'seed':                   seed,
            'nontrep_f_2016':         at(nontrep_f, 2016),
            'nontrep_m_2016':         at(nontrep_m, 2016),
            'trep_f_2016':            at(trep_f, 2016),
            'trep_m_2016':            at(trep_m, 2016),
            'fsw_prev_2019':          at(fsw_prev, 2019),
            'fsw_prev_2030_avg':      avg(fsw_prev, yrs, 2030, 2040),
            'client_prev_2016':       at(client_prev, 2016),
            'overall_prev_f_2016':    at(prev_f, 2016),
            'overall_prev_f_2035_2040_mean': avg(prev_f, yrs, 2035, 2040),
            'new_inf_2030_2040_mean': avg(new_inf, yrs_inf, 2030, 2040),
            'stage_share_primary_plateau':   plateau_shares['primary'],
            'stage_share_secondary_plateau': plateau_shares['secondary'],
            'stage_share_early_latent_plateau': plateau_shares['early_latent'],
            'stage_share_late_latent_plateau':  plateau_shares['late_latent'],
            'status': 'ok',
        }
        series = {
            'years': yrs, 'fsw_prev': fsw_prev,
            'nontrep_f': nontrep_f, 'trep_f': trep_f,
            'overall_prev_f': prev_f,
        }
        return summary, (m1_conc, seed), series, []
    except Exception as e:
        return ({'m1_conc': m1_conc, 'seed': seed, 'status': f'error: {e}'},
                (m1_conc, seed), None, [])


def main():
    sc.heading(f'Exp 26 — m1_conc sweep ({len(M1_CONC_GRID)} values x {len(SEEDS)} seeds)')
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    tasks = [{'m1_conc': m, 'seed': s} for m in M1_CONC_GRID for s in SEEDS]
    print(f'{len(tasks)} sims on {min(18, len(tasks))} workers...')

    t0 = time.time()
    summaries = []
    series_map = {}
    with mp.Pool(min(18, len(tasks))) as pool:
        for i, (summary, key, series, _) in enumerate(
                pool.imap_unordered(run_one, tasks), 1):
            summaries.append(summary)
            if series is not None:
                series_map[key] = series
            print(f'  [{i:2d}/{len(tasks)}] m1_conc={summary["m1_conc"]:.2f} '
                  f'seed={summary["seed"]} '
                  f'fsw={summary.get("fsw_prev_2019", np.nan):.3f} '
                  f'nontrep_f={summary.get("nontrep_f_2016", np.nan):.4f} '
                  f'trep_f={summary.get("trep_f_2016", np.nan):.4f}', flush=True)
    print(f'  total {time.time()-t0:.1f}s')

    with SERIES_PKL.open('wb') as f:
        pickle.dump(series_map, f)

    df = pd.DataFrame(summaries)
    df_ok = df[df['status'] == 'ok']
    agg = df_ok.groupby('m1_conc').agg('mean', numeric_only=True).reset_index()
    agg.to_csv(OUTPUTS / 'sweep_summary.csv', index=False)

    print('\n=== SWEEP SUMMARY (3-seed mean per m1_conc) ===')
    print(f"{'m1_conc':>8s}  {'FSW_2019':>9s}  {'nontrep_f':>10s}  {'trep_f':>8s}  "
          f"{'prim%':>6s}  {'sec%':>6s}  {'sustain':>8s}")
    for _, row in agg.iterrows():
        print(f"{row['m1_conc']:>8.3f}  {row['fsw_prev_2019']:>9.3f}  "
              f"{row['nontrep_f_2016']:>10.4f}  {row['trep_f_2016']:>8.4f}  "
              f"{row['stage_share_primary_plateau']*100:>6.1f}  "
              f"{row['stage_share_secondary_plateau']*100:>6.1f}  "
              f"{row['new_inf_2030_2040_mean']:>8.2f}")

    print('\n=== TARGET BANDS ===')
    for _, row in agg.iterrows():
        fsw_ok    = 0.20 <= row['fsw_prev_2019'] <= 0.40
        nontr_ok  = 0.004 <= row['nontrep_f_2016'] <= 0.016
        trep_ok   = 0.027 <= row['trep_f_2016'] <= 0.05
        prim_ok   = 0.50 <= row['stage_share_primary_plateau'] <= 0.65
        sec_ok    = 0.25 <= row['stage_share_secondary_plateau'] <= 0.40
        sust_ok   = row['new_inf_2030_2040_mean'] > 0
        n_pass    = sum([fsw_ok, nontr_ok, trep_ok, prim_ok, sec_ok, sust_ok])
        print(f"  m1_conc={row['m1_conc']:.3f}: {n_pass}/6 pass  "
              f"[fsw={'Y' if fsw_ok else 'n'} nontrep={'Y' if nontr_ok else 'n'} "
              f"trep={'Y' if trep_ok else 'n'} prim={'Y' if prim_ok else 'n'} "
              f"sec={'Y' if sec_ok else 'n'} sust={'Y' if sust_ok else 'n'}]")

    sweet = agg.assign(
        n_pass=lambda d: ((d['fsw_prev_2019'].between(0.20, 0.40)) +
                          (d['nontrep_f_2016'].between(0.004, 0.016)) +
                          (d['trep_f_2016'].between(0.027, 0.05)) +
                          (d['stage_share_primary_plateau'].between(0.50, 0.65)) +
                          (d['stage_share_secondary_plateau'].between(0.25, 0.40)) +
                          (d['new_inf_2030_2040_mean'] > 0))
    ).sort_values('n_pass', ascending=False)
    best = sweet.iloc[0]
    out = {'config': BASE_CONFIG,
           'm1_conc_grid': M1_CONC_GRID,
           'seeds': SEEDS,
           'per_run': summaries,
           'best_m1_conc': float(best['m1_conc']),
           'best_n_pass': int(best['n_pass'])}
    RESULTS.write_text(json.dumps(out, indent=2, default=str))
    print(f'\nBest m1_conc by hit-count: {best["m1_conc"]:.3f}  ({best["n_pass"]}/6 targets)')


if __name__ == '__main__':
    main()
