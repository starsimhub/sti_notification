"""
β sweep at exp 24 base config, with time_to_undetectable shortened to 15y.

Hypothesis: with time_to_undetectable=15 (shortening the late-latent
window during which agents remain non-trep positive), the nontrep_f
stock will drop substantially even at exp 24's β=0.20. The β sweep
maps the trade-off: lower β reduces FSW prev AND nontrep_f together;
find the value(s) where the loose targets (1-3% nontrep_f, 5-10% trep_f,
20-40% FSW prev, sustained, stage shares right) all land.
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
RESULTS    = OUTPUTS / 'results.json'

N_AGENTS   = int(os.environ.get('N_AGENTS', 10_000))
START      = int(os.environ.get('START', 1985))
STOP       = int(os.environ.get('STOP', 2040))
SEEDS      = [101, 102, 103]
BETA_GRID  = [0.08, 0.10, 0.12, 0.15, 0.20]

BASE_CONFIG = {
    'syph.time_to_undetectable':      15.0,    # reduced from exp 24's 20
    'syph.p_symp_primary_f':          0.50,
    'syph.p_symp_primary_m':          0.80,
    'syph.rel_init_prev':             0.20,
    'syph_symp_test.rel_test':        1.30,
    'structuredsexual.prop_f0':       0.55,
    'structuredsexual.m1_conc':       0.20,
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
    beta = task['beta_m2f']
    config = dict(BASE_CONFIG)
    config['syph.beta_m2f'] = beta

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
            'beta_m2f':              beta,
            'seed':                  seed,
            'nontrep_f_2016':        at(nontrep_f, 2016),
            'nontrep_m_2016':        at(nontrep_m, 2016),
            'trep_f_2016':           at(trep_f, 2016),
            'trep_m_2016':           at(trep_m, 2016),
            'fsw_prev_2019':         at(fsw_prev, 2019),
            'fsw_prev_2030_avg':     avg(fsw_prev, yrs, 2030, 2040),
            'client_prev_2016':      at(client_prev, 2016),
            'overall_prev_f_2016':   at(prev_f, 2016),
            'overall_prev_f_2035_2040_mean': avg(prev_f, yrs, 2035, 2040),
            'new_inf_2030_2040_mean': avg(new_inf, yrs_inf, 2030, 2040),
            'stage_share_primary_plateau':       plateau_shares['primary'],
            'stage_share_secondary_plateau':     plateau_shares['secondary'],
            'stage_share_early_latent_plateau':  plateau_shares['early_latent'],
            'stage_share_late_latent_plateau':   plateau_shares['late_latent'],
            'status': 'ok',
        }
        series = {
            'years': yrs, 'fsw_prev': fsw_prev, 'client_prev': client_prev,
            'nontrep_f': nontrep_f, 'trep_f': trep_f,
            'overall_prev_f': prev_f, 'new_inf': new_inf,
        }
        return summary, (beta, seed), series
    except Exception as e:
        return ({'beta_m2f': beta, 'seed': seed, 'status': f'error: {e}'},
                (beta, seed), None)


def main():
    sc.heading(f'Exp 27 — β sweep at exp 24 base + time_to_undetectable=15y')
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    tasks = [{'beta_m2f': b, 'seed': s} for b in BETA_GRID for s in SEEDS]
    print(f'{len(tasks)} sims on {min(15, len(tasks))} workers...')

    t0 = time.time()
    summaries = []
    series_map = {}
    with mp.Pool(min(15, len(tasks))) as pool:
        for i, (summary, key, series) in enumerate(
                pool.imap_unordered(run_one, tasks), 1):
            summaries.append(summary)
            if series is not None:
                series_map[key] = series
            print(f'  [{i:2d}/{len(tasks)}] β={summary["beta_m2f"]:.2f} '
                  f'seed={summary["seed"]} '
                  f'fsw={summary.get("fsw_prev_2019", np.nan):.3f} '
                  f'nontrep_f={summary.get("nontrep_f_2016", np.nan):.4f} '
                  f'trep_f={summary.get("trep_f_2016", np.nan):.4f}', flush=True)
    print(f'  total {time.time()-t0:.1f}s')

    with SERIES_PKL.open('wb') as f:
        pickle.dump(series_map, f)

    df = pd.DataFrame(summaries)
    df_ok = df[df['status'] == 'ok'].copy()
    df_ok['sustained'] = df_ok['new_inf_2030_2040_mean'] > 0

    agg = df_ok.groupby('beta_m2f').agg('mean', numeric_only=True).reset_index()
    agg.to_csv(OUTPUTS / 'sweep_summary_all.csv', index=False)

    agg_sus = (df_ok[df_ok['sustained']]
               .groupby('beta_m2f')
               .agg('mean', numeric_only=True)
               .reset_index())
    agg_sus.to_csv(OUTPUTS / 'sweep_summary_sustained.csv', index=False)

    print('\n=== ALL RUNS (3-seed mean) ===')
    print(f"{'beta':>6s}  {'FSW_2019':>9s}  {'nontrep_f':>10s}  {'trep_f':>8s}  "
          f"{'prim%':>6s}  {'sec%':>6s}  {'sustain':>8s}")
    for _, row in agg.iterrows():
        print(f"{row['beta_m2f']:>6.3f}  {row['fsw_prev_2019']:>9.3f}  "
              f"{row['nontrep_f_2016']:>10.4f}  {row['trep_f_2016']:>8.4f}  "
              f"{row['stage_share_primary_plateau']*100:>6.1f}  "
              f"{row['stage_share_secondary_plateau']*100:>6.1f}  "
              f"{row['new_inf_2030_2040_mean']:>8.2f}")

    print('\n=== SUSTAINED RUNS only ===')
    if not agg_sus.empty:
        for _, row in agg_sus.iterrows():
            print(f"{row['beta_m2f']:>6.3f}  {row['fsw_prev_2019']:>9.3f}  "
                  f"{row['nontrep_f_2016']:>10.4f}  {row['trep_f_2016']:>8.4f}  "
                  f"{row['stage_share_primary_plateau']*100:>6.1f}  "
                  f"{row['stage_share_secondary_plateau']*100:>6.1f}")
    else:
        print('  (none)')

    print('\n=== TARGET BANDS (loose) ===')
    for _, row in agg.iterrows():
        fsw_ok   = 0.20 <= row['fsw_prev_2019'] <= 0.40
        ntr_ok   = 0.01 <= row['nontrep_f_2016'] <= 0.03
        tr_ok    = 0.05 <= row['trep_f_2016'] <= 0.10
        pr_ok    = 0.50 <= row['stage_share_primary_plateau'] <= 0.65
        se_ok    = 0.25 <= row['stage_share_secondary_plateau'] <= 0.40
        su_ok    = row['new_inf_2030_2040_mean'] > 0
        n_pass = sum([fsw_ok, ntr_ok, tr_ok, pr_ok, se_ok, su_ok])
        print(f"  β={row['beta_m2f']:.2f}: {n_pass}/6 pass  "
              f"[fsw={'Y' if fsw_ok else 'n'} nontrep={'Y' if ntr_ok else 'n'} "
              f"trep={'Y' if tr_ok else 'n'} prim={'Y' if pr_ok else 'n'} "
              f"sec={'Y' if se_ok else 'n'} sust={'Y' if su_ok else 'n'}]")

    out = {
        'config': BASE_CONFIG,
        'beta_grid': BETA_GRID,
        'seeds': SEEDS,
        'per_run': summaries,
        'agg_all': agg.to_dict(orient='records'),
        'agg_sustained': agg_sus.to_dict(orient='records'),
    }
    RESULTS.write_text(json.dumps(out, indent=2, default=str))


if __name__ == '__main__':
    main()
