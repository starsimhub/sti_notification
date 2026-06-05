"""
Trajectory selection (post-ANC-fix): resample within the wave-8 NROY.

Differences from exp 10:
- NROY source: post-fix HM (exp 09 re-run, 1.2% retained).
- 1 seed per draw by default (matches exp 10 pre-fix).
- 24 workers default (was 75 — that OOM'd the VM).
- Results appended to outputs/results.jsonl per sim, so progress
  survives interruption and the run is resumable.

Usage:
  python run.py                # full simulation pass + reweight
  python run.py --reweight     # skip sims, re-derive posterior from JSONL
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import multiprocessing as mp
import time

import numpy as np
import pandas as pd
import sciris as sc

from model import make_sim
from priors import calib_pars

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_SEEDS   = int(os.environ.get('N_SEEDS', 1))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
OUTPUTS   = Path(__file__).parent / 'outputs'
NROY_CSV  = Path(__file__).resolve().parents[1] / '09_history_matching' / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'
JSONL_OUT = OUTPUTS / 'results.jsonl'

LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}

OBSERVATIONS = {
    'hiv_prev_2000_2010':     (0.116, 0.015),
    'hiv_prev_2010_2020':     (0.092, 0.010),
    'ng_prev_2005_2015':      (0.020, 0.003),
    'ct_prev_f2530':          (0.120, 0.020),
    'tv_prev_2005_2015':      (0.111, 0.015),
    'syph_prev_f_2016':       (0.010, 0.002),
    'syph_prev_m_2016':       (0.006, 0.0013),
    'syph_seroprev_f_2016':   (0.030, 0.0033),
    'syph_seroprev_m_2016':   (0.024, 0.0033),
    'syph_anc_2000_2015':     (0.020, 0.0033),
    'syph_prev_hivpos_2016':  (0.029, 0.0053),
    'syph_prev_hivneg_2016':  (0.004, 0.0013),
}


def set_pars_local(sim, pars):
    """Set parameters on pre-init sim modules (stisim stores modules as lists)."""
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


def extract_targets(sim):
    """Extract summary statistics matching OBSERVATIONS."""
    results = {}

    def mean_prev(disease, y1, y2):
        r = sim.results[disease]
        prev = r['prevalence']
        vals = prev.values
        tvec = prev.timevec
        years = np.array([t.year + t.month / 12 for t in tvec])
        mask = (years >= y1) & (years < y2)
        return float(np.mean(vals[mask])) if mask.any() else np.nan

    def prev_at(disease, result_name, year):
        r = sim.results[disease]
        vals = r[result_name].values
        tvec = r[result_name].timevec
        years = np.array([t.year + t.month / 12 for t in tvec])
        idx = np.argmin(np.abs(years - year))
        return float(vals[idx])

    results['hiv_prev_2000_2010'] = mean_prev('hiv', 2000, 2010)
    results['hiv_prev_2010_2020'] = mean_prev('hiv', 2010, 2020)
    results['ng_prev_2005_2015'] = mean_prev('ng', 2005, 2015)
    results['ct_prev_f2530'] = prev_at('ct', 'prevalence_f_25_30', 2010)
    results['tv_prev_2005_2015'] = mean_prev('tv', 2005, 2015)
    results['syph_prev_f_2016'] = prev_at('syph', 'prevalence_f', 2016)
    results['syph_prev_m_2016'] = prev_at('syph', 'prevalence_m', 2016)
    results['syph_seroprev_f_2016'] = prev_at('syph', 'serological_prevalence_f', 2016)
    results['syph_seroprev_m_2016'] = prev_at('syph', 'serological_prevalence_m', 2016)

    r = sim.results['syph']
    anc_vals = r['pregnant_prevalence'].values
    tvec = r['pregnant_prevalence'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    mask = (years >= 2000) & (years < 2015)
    results['syph_anc_2000_2015'] = float(np.nanmean(anc_vals[mask])) if mask.any() else np.nan

    coinf = sim.results['syph_hiv_coinfection']
    tvec = coinf['syph_prev_has_hiv'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    idx_2016 = np.argmin(np.abs(years - 2016))
    results['syph_prev_hivpos_2016'] = float(coinf['syph_prev_has_hiv'].values[idx_2016])
    results['syph_prev_hivneg_2016'] = float(coinf['syph_prev_no_hiv'].values[idx_2016])

    # Diagnostic: late-window syphilis prevalence — was zero in exp 10 pre-fix.
    syph_f = sim.results['syph']['prevalence_f']
    syph_tvec = np.array([t.year + t.month / 12 for t in syph_f.timevec])
    late_mask = (syph_tvec >= 2020) & (syph_tvec < 2025)
    results['syph_prev_f_2020_2025'] = float(np.nanmean(syph_f.values[late_mask])) if late_mask.any() else np.nan

    return results


def nroy_to_sim_pars(row):
    sim_pars = {}
    for col, val in row.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        else:
            sim_pars[col] = float(val)
    return sim_pars


def run_one(task):
    """Run one sim. Returns dict (never raises — exceptions become NaN rows)."""
    seed = task['seed']
    draw_idx = task['draw_idx']
    sim_pars = task['sim_pars']
    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        out = extract_targets(sim)
        out['seed'] = seed
        out['draw_idx'] = draw_idx
        out['status'] = 'ok'
        return out
    except Exception as e:
        out = {k: float('nan') for k in OBSERVATIONS}
        out['seed'] = seed
        out['draw_idx'] = draw_idx
        out['status'] = f'error: {type(e).__name__}: {e}'
        return out


def compute_log_likelihood(row):
    ll = 0.0
    # Widened stds: 2x for non-syph, 3x for syph (matches exp 10).
    for target, (mean, std) in OBSERVATIONS.items():
        mult = 3.0 if 'syph' in target else 2.0
        val = row.get(target, np.nan)
        if pd.isna(val):
            return -np.inf
        ll += -0.5 * ((val - mean) / (std * mult)) ** 2
    return ll


def filter_weight_resample(df):
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    n_total = len(df)
    df = df[df['status'] == 'ok'].copy()
    n_ok = len(df)
    print(f'Sim status: {n_ok}/{n_total} ok')

    n_before = len(df)
    df_alive = df[df['syph_prev_f_2016'] > 0.005].copy()
    n_after = len(df_alive)
    pct = (n_after / n_before * 100) if n_before else 0
    print(f'Syphilis filter (prev_f_2016 > 0.005): {n_before} -> {n_after} ({pct:.0f}% survive)')

    df_alive['log_lik'] = df_alive.apply(compute_log_likelihood, axis=1)
    df_alive = df_alive[np.isfinite(df_alive['log_lik'])].copy()
    n_lik = len(df_alive)
    print(f'Finite log-lik: {n_lik}')

    if n_lik == 0:
        print('No surviving draws — nothing to weight.')
        return df_alive

    log_w = df_alive['log_lik'].values.copy()
    log_w -= log_w.max()
    w = np.exp(log_w)
    w /= w.sum()
    df_alive['weight'] = w

    ess = 1.0 / np.sum(w ** 2)
    ess_ratio = ess / len(w)
    print(f'ESS: {ess:.1f} / {len(w)} = {ess_ratio:.3f}')

    df_alive.to_csv(OUTPUTS / 'weighted_results.csv', index=False)

    n_posterior = min(500, len(df_alive))
    rng = np.random.default_rng(0)
    posterior_idx = rng.choice(len(df_alive), size=n_posterior, replace=True, p=w)
    df_posterior = df_alive.iloc[posterior_idx].copy()
    df_posterior.to_csv(OUTPUTS / 'posterior_ensemble.csv', index=False)

    summary = {
        'n_raw_sims': n_total,
        'n_ok': n_ok,
        'n_after_syph_filter': n_after,
        'n_after_lik_filter': n_lik,
        'syph_late_window_mean_alive': float(df_alive['syph_prev_f_2020_2025'].mean()),
        'syph_late_window_mean_posterior': float(df_posterior['syph_prev_f_2020_2025'].mean()),
        'ess': float(ess),
        'ess_ratio': float(ess_ratio),
        'n_posterior': n_posterior,
    }
    with open(OUTPUTS / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'\nSummary: {json.dumps(summary, indent=2)}')
    print(f'Saved to {OUTPUTS}')
    return df_alive


def load_done_seeds():
    """Return the set of seeds already present in results.jsonl, for resumption."""
    if not JSONL_OUT.exists():
        return set()
    seeds = set()
    with JSONL_OUT.open() as f:
        for line in f:
            try:
                seeds.add(json.loads(line)['seed'])
            except Exception:
                pass
    return seeds


def main_sim():
    sc.heading(f'Trajectory selection (post-ANC-fix): '
               f'{N_SEEDS} seed/draw, n_agents={N_AGENTS}, {N_WORKERS} workers')

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    nroy = pd.read_csv(NROY_CSV)
    n_draws = len(nroy)
    print(f'Loaded {n_draws} NROY samples from {NROY_CSV}')

    tasks = []
    for draw_idx, row in nroy.iterrows():
        sim_pars = nroy_to_sim_pars(row)
        for s in range(N_SEEDS):
            seed = int(draw_idx) * 1000 + s
            tasks.append(dict(sim_pars=sim_pars, seed=seed, draw_idx=int(draw_idx)))

    done = load_done_seeds()
    if done:
        before = len(tasks)
        tasks = [t for t in tasks if t['seed'] not in done]
        print(f'Resuming: {before - len(tasks)} sims already in JSONL, '
              f'{len(tasks)} remaining')

    if not tasks:
        print('All sims already complete. Skipping to reweight.')
        return

    print(f'Running {len(tasks)} simulations across {N_WORKERS} workers '
          f'(maxtasksperchild=10 to bound per-worker memory growth)...')
    t0 = time.time()

    with mp.Pool(processes=N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('a') as fout:
            for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(res) + '\n')
                fout.flush()
                if i % 25 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i}/{len(tasks)}] rate={rate:.2f}/s elapsed={elapsed:.0f}s eta={eta:.0f}s')

    print(f'\nFinished sims. JSONL: {JSONL_OUT}')


def load_jsonl_as_df():
    rows = []
    with JSONL_OUT.open() as f:
        for line in f:
            rows.append(json.loads(line))
    return pd.DataFrame(rows)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--reweight', action='store_true',
                        help='Skip sims; re-derive posterior from existing results.jsonl.')
    args = parser.parse_args()

    if not args.reweight:
        main_sim()

    if JSONL_OUT.exists():
        df = load_jsonl_as_df()
        print(f'\nLoaded {len(df)} rows from {JSONL_OUT}')
        filter_weight_resample(df)
    else:
        print(f'No results.jsonl at {JSONL_OUT} — nothing to reweight.')
