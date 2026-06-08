"""
Exp 37 — Ensemble data extraction for publication figures.

Takes the 125-draw working ensemble (sustained 3/3 + mean n_pass >= 4
from exp 36) and re-runs each with 3 seeds, saving:
  - Annualized time series for HIV, NG/CT/TV, syph (incl. all 4 prev
    types: active, sexually_transmissible, symptomatic, primary)
  - 2016 and 2020 age x sex snapshots (ZIMPHIA survey years)

Outputs parquet files ready for ensemble-quantile plotting.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys, time
import multiprocessing as mp
from pathlib import Path

import numpy as np
import pandas as pd
import sciris as sc

THIS = Path(__file__).resolve()
PROJECT_ROOT = THIS.parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
EXP24 = PROJECT_ROOT / 'experiments' / '24_concentrated_sustained_handpick'
EXP35 = PROJECT_ROOT / 'experiments' / '35_ensemble_build'
EXP36 = PROJECT_ROOT / 'experiments' / '36_ensemble_robust_extend'
sys.path.insert(0, str(EXP24))

import starsim as ss
from model import make_sim
from interventions import ANC_PROBS_REALISTIC


def set_pars_local(sim, pars):
    """Inlined from experiments/24_concentrated_sustained_handpick/run.py to
    avoid a circular import (both files are named run.py)."""
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

HERE          = THIS.parent
OUTPUTS       = HERE / 'outputs'
DRAWS_CSV     = OUTPUTS / 'draws_used.csv'
TS_PARQUET    = OUTPUTS / 'time_series.parquet'
SNAP_PARQUET  = OUTPUTS / 'snapshots.parquet'
TS_Q_PARQUET  = OUTPUTS / 'ensemble_ts_quantiles.parquet'
SNAP_Q_PARQUET = OUTPUTS / 'ensemble_snapshots_quantiles.parquet'

EXP36_SUMMARY = EXP36 / 'outputs' / 'full_summary.csv'
EXP35_PRIORS  = EXP35 / 'outputs' / 'phase1_priors.csv'

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2040))
N_SEEDS   = 3
SEED_BASE = 100_000

SNAPSHOT_YEARS = (2016, 2020)

SYMP_TEST_CSV = EXP24 / 'data' / 'symp_test_prob_concentrated.csv'


# Result keys to extract per disease ----------------------------------
# Each base name listed gets time-series extraction; for snapshots we
# also auto-discover its `_{sex}_{age1}_{age2}` age-binned variants.

TIME_SERIES_RESULTS = {
    'hiv':  ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'ng':   ['prevalence', 'prevalence_f', 'prevalence_m',
             'prevalence_f_25_30', 'new_infections'],
    'ct':   ['prevalence', 'prevalence_f', 'prevalence_m',
             'prevalence_f_25_30', 'new_infections'],
    'tv':   ['prevalence', 'prevalence_f', 'prevalence_m', 'new_infections'],
    'syph': [
        'new_infections',
        'prevalence', 'prevalence_f', 'prevalence_m',
        'prevalence_sw', 'prevalence_client',
        'trep_prevalence_15_64',
        'trep_prevalence_15_64_f', 'trep_prevalence_15_64_m',
        'nontrep_prevalence_15_64',
        'nontrep_prevalence_15_64_f', 'nontrep_prevalence_15_64_m',
        'active_prevalence', 'active_prevalence_f', 'active_prevalence_m',
        'sexually_transmissible_prevalence',
        'sexually_transmissible_prevalence_f',
        'sexually_transmissible_prevalence_m',
        'symptomatic_prevalence',
        'symptomatic_prevalence_f', 'symptomatic_prevalence_m',
        'primary_prevalence',
        'primary_prevalence_f', 'primary_prevalence_m',
    ],
}

# For snapshots: list of base names whose `_{sex}_{age1}_{age2}` variants
# we want at 2016 and 2020.
SNAPSHOT_BASES = {
    'hiv':  ['prevalence'],
    'ng':   ['prevalence'],
    'ct':   ['prevalence'],
    'tv':   ['prevalence'],
    'syph': [
        'trep_prevalence',
        'nontrep_prevalence',
        'active_prevalence',
        'sexually_transmissible_prevalence',
        'symptomatic_prevalence',
        'primary_prevalence',
    ],
}


def row_to_sim_pars(row):
    sim_pars = {}
    for col, val in row.items():
        if col in ('draw_idx', 'seed'):
            continue
        if isinstance(col, str) and col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        elif isinstance(col, str) and '.' in col:
            sim_pars[col] = float(val)
    return sim_pars


def annualize_safe(result):
    """Return (years_array, values_array) for the annualised result. None on failure."""
    try:
        ann = result.annualize()
        years = np.asarray(ann.timevec.years).astype(int)
        values = np.asarray(ann.values, dtype=float)
        return years, values
    except Exception:
        return None, None


def extract_time_series(sim, draw_idx, seed):
    rows = []
    for disease_name, result_names in TIME_SERIES_RESULTS.items():
        disease_results = sim.results.get(disease_name)
        if disease_results is None:
            continue
        for rname in result_names:
            if rname not in disease_results:
                continue
            years, values = annualize_safe(disease_results[rname])
            if years is None:
                continue
            for y, v in zip(years, values):
                rows.append({
                    'draw_idx': int(draw_idx), 'seed': int(seed),
                    'disease': disease_name, 'result_name': rname,
                    'year': int(y), 'value': float(v),
                })
    return rows


def extract_snapshots(sim, draw_idx, seed):
    """Find {base}_{sex}_{age1}_{age2} variants of each base + extract 2016/2020."""
    rows = []
    for disease_name, bases in SNAPSHOT_BASES.items():
        disease_results = sim.results.get(disease_name)
        if disease_results is None:
            continue
        all_keys = list(disease_results.keys())
        for base in bases:
            prefix = base + '_'
            for key in all_keys:
                if not key.startswith(prefix):
                    continue
                suffix = key[len(prefix):]
                parts = suffix.split('_')
                if len(parts) != 3 or parts[0] not in ('f', 'm'):
                    continue
                try:
                    age1 = int(parts[1])
                    age2 = int(parts[2])
                except ValueError:
                    continue
                years, values = annualize_safe(disease_results[key])
                if years is None:
                    continue
                for snap_year in SNAPSHOT_YEARS:
                    if snap_year not in years:
                        continue
                    idx = int(np.where(years == snap_year)[0][0])
                    rows.append({
                        'draw_idx': int(draw_idx), 'seed': int(seed),
                        'disease': disease_name, 'result_name': base,
                        'sex': parts[0], 'age_bin': f'{age1}_{age2}',
                        'year': int(snap_year),
                        'value': float(values[idx]),
                    })
    return rows


def run_one(task):
    draw_idx = task['draw_idx']
    seed = task['seed']
    sim_pars = task['sim_pars']
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

        ts_rows = extract_time_series(sim, draw_idx, seed)
        snap_rows = extract_snapshots(sim, draw_idx, seed)

        return {'draw_idx': draw_idx, 'seed': seed, 'status': 'ok',
                'ts': ts_rows, 'snap': snap_rows}
    except Exception as e:
        return {'draw_idx': draw_idx, 'seed': seed,
                'status': f'error: {type(e).__name__}: {e}',
                'ts': [], 'snap': []}


def load_ensemble():
    """Filter exp 36 full_summary to sustained 3/3 + mean n_pass >= 4."""
    df = pd.read_csv(EXP36_SUMMARY)
    mask = (df['pass_sustained'] == 1.0) & (df['n_pass_mean'] >= 4)
    ensemble_idxs = df.loc[mask, 'draw_idx'].tolist()
    priors = pd.read_csv(EXP35_PRIORS)
    ensemble_priors = priors[priors['draw_idx'].isin(ensemble_idxs)].copy()
    return ensemble_priors


def aggregate_quantiles(ts_df, snap_df):
    """Compute median + 80%/95% CI bands across (draw, seed) for each
    (year, disease, result_name) and each (year, disease, result_name,
    sex, age_bin)."""
    if len(ts_df) > 0:
        ts_q = (ts_df.groupby(['disease', 'result_name', 'year'])['value']
                .agg(median='median',
                     ci80_lo=lambda s: np.quantile(s, 0.10),
                     ci80_hi=lambda s: np.quantile(s, 0.90),
                     ci95_lo=lambda s: np.quantile(s, 0.025),
                     ci95_hi=lambda s: np.quantile(s, 0.975),
                     mean='mean',
                     n='count')
                .reset_index())
        _safe_write(ts_q, TS_Q_PARQUET, 'ts quantiles')
    if len(snap_df) > 0:
        snap_q = (snap_df.groupby(['disease', 'result_name', 'year',
                                    'sex', 'age_bin'])['value']
                  .agg(median='median',
                       ci80_lo=lambda s: np.quantile(s, 0.10),
                       ci80_hi=lambda s: np.quantile(s, 0.90),
                       ci95_lo=lambda s: np.quantile(s, 0.025),
                       ci95_hi=lambda s: np.quantile(s, 0.975),
                       mean='mean',
                       n='count')
                  .reset_index())
        _safe_write(snap_q, SNAP_Q_PARQUET, 'snap quantiles')


def main():
    sc.heading(f'Exp 37 — ensemble data extraction')
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    HERE.joinpath('figures').mkdir(exist_ok=True)

    ensemble_priors = load_ensemble()
    ensemble_priors.to_csv(DRAWS_CSV, index=False)
    print(f'Ensemble: {len(ensemble_priors)} draws (sustained 3/3 + mean n_pass >= 4)')

    tasks = []
    for _, row in ensemble_priors.iterrows():
        di = int(row['draw_idx'])
        sim_pars = row_to_sim_pars(row.to_dict())
        for s_idx in range(N_SEEDS):
            seed = SEED_BASE + di * 10 + s_idx
            tasks.append({'draw_idx': di, 'seed': seed, 'sim_pars': sim_pars})

    print(f'Total sims: {len(tasks)} ({len(ensemble_priors)} draws x {N_SEEDS} seeds)')
    print(f'Running on {N_WORKERS} workers...')

    t0 = time.time()
    all_ts = []
    all_snap = []
    n_ok = n_err = 0
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        for i, result in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            if result.get('status') == 'ok':
                all_ts.extend(result['ts'])
                all_snap.extend(result['snap'])
                n_ok += 1
            else:
                n_err += 1
                if n_err <= 5:
                    print(f'  ERROR draw {result["draw_idx"]} seed {result["seed"]}: '
                          f'{result.get("status")}', flush=True)
            if i % 30 == 0 or i == len(tasks):
                elapsed = time.time() - t0
                eta = (len(tasks) - i) * elapsed / i
                print(f'  [{i:3d}/{len(tasks)}] {elapsed:.0f}s  eta={eta:.0f}s  '
                      f'ok={n_ok} err={n_err}', flush=True)

    print(f'\nDone in {time.time()-t0:.1f}s. OK: {n_ok}, errors: {n_err}')

    # Persist raw rows — fall back to pickle if parquet engine is missing
    ts_df = pd.DataFrame(all_ts)
    snap_df = pd.DataFrame(all_snap)
    if len(ts_df):
        _safe_write(ts_df, TS_PARQUET, 'time_series')
    if len(snap_df):
        _safe_write(snap_df, SNAP_PARQUET, 'snapshots')

    # Aggregate quantiles
    aggregate_quantiles(ts_df, snap_df)


def _safe_write(df, path, label):
    try:
        df.to_parquet(path, index=False)
        print(f'  {label} -> {path.name}: {len(df)} rows')
    except (ImportError, ValueError) as e:
        pkl_path = path.with_suffix('.pkl')
        df.to_pickle(pkl_path)
        print(f'  {label} -> {pkl_path.name} (parquet engine missing: {e}): {len(df)} rows')


if __name__ == '__main__':
    main()
