"""
Trajectory selection: Bayesian resampling within the NROY region.

1. Load NROY samples from exp 09 wave 8.
2. Run each with multiple seeds at 10k agents.
3. Extract summary statistics for all calibration targets.
4. Filter extinct syphilis runs.
5. Weight by Gaussian pseudo-likelihood.
6. Resample to produce posterior ensemble.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import json
import numpy as np
import pandas as pd
import sciris as sc

from model import make_sim
from priors import calib_pars

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_SEEDS   = int(os.environ.get('N_SEEDS', 3))
N_WORKERS = int(os.environ.get('N_WORKERS', 75))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
OUTPUTS   = Path(__file__).parent / 'outputs'
NROY_CSV  = Path(__file__).resolve().parents[1] / '09_history_matching' / 'outputs' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'

# Log-scale parameters
LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}

# Observations: (mean, std)
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
    """Set parameters on pre-init sim modules."""
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
    """Extract summary statistics matching the observations."""
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

    # ANC prevalence
    r = sim.results['syph']
    anc_vals = r['pregnant_prevalence'].values
    tvec = r['pregnant_prevalence'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    mask = (years >= 2000) & (years < 2015)
    results['syph_anc_2000_2015'] = float(np.nanmean(anc_vals[mask])) if mask.any() else np.nan

    # Coinfection
    coinf = sim.results['syph_hiv_coinfection']
    tvec = coinf['syph_prev_has_hiv'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    idx_2016 = np.argmin(np.abs(years - 2016))
    results['syph_prev_hivpos_2016'] = float(coinf['syph_prev_has_hiv'].values[idx_2016])
    results['syph_prev_hivneg_2016'] = float(coinf['syph_prev_no_hiv'].values[idx_2016])

    return results


def run_one(sim_pars, seed):
    """Run a single sim and return target dict."""
    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        targets = extract_targets(sim)
        targets['seed'] = seed
        return targets
    except Exception as e:
        print(f'  Sim failed (seed={seed}): {e}')
        targets = {k: np.nan for k in OBSERVATIONS}
        targets['seed'] = seed
        return targets


def nroy_to_sim_pars(row):
    """Convert an NROY sample row to sim parameter dict."""
    sim_pars = {}
    for col, val in row.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = np.exp(val)
        else:
            sim_pars[col] = val
    return sim_pars


def compute_log_likelihood(result_row):
    """Gaussian pseudo-log-likelihood across all targets."""
    ll = 0.0
    for target, (mean, std) in OBSERVATIONS.items():
        val = result_row.get(target, np.nan)
        if np.isnan(val):
            return -np.inf
        ll += -0.5 * ((val - mean) / std) ** 2
    return ll


def filter_weight_resample(df):
    """Filter, weight, and resample from raw results DataFrame."""
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    # Filter extinct syphilis
    n_before = len(df)
    df_alive = df[df['syph_prev_f_2016'] > 0.005].copy()
    n_after = len(df_alive)
    print(f'Syphilis filter: {n_before} -> {n_after} ({n_after/n_before:.0%} survive)')

    # Compute log-likelihood for each surviving sim
    df_alive['log_lik'] = df_alive.apply(compute_log_likelihood, axis=1)
    df_alive = df_alive[np.isfinite(df_alive['log_lik'])].copy()

    # Importance weights
    log_w = df_alive['log_lik'].values.copy()
    log_w -= log_w.max()  # numerical stability
    w = np.exp(log_w)
    w /= w.sum()
    df_alive['weight'] = w

    # ESS
    ess = 1.0 / np.sum(w ** 2)
    ess_ratio = ess / len(w)
    print(f'ESS: {ess:.1f} / {len(w)} = {ess_ratio:.3f}')

    # Save weighted results
    df_alive.to_csv(OUTPUTS / 'weighted_results.csv', index=False)

    # Resample to get posterior ensemble
    n_posterior = min(500, len(df_alive))
    posterior_idx = np.random.choice(len(df_alive), size=n_posterior, replace=True, p=w)
    df_posterior = df_alive.iloc[posterior_idx].copy()
    df_posterior.to_csv(OUTPUTS / 'posterior_ensemble.csv', index=False)

    # Also save just the parameter columns for epi_plots
    par_cols = [c for c in df_posterior.columns
                if '.' in c and c not in ('log_lik',)]
    df_posterior[par_cols + ['seed', 'weight']].to_csv(
        OUTPUTS / 'posterior_params.csv', index=False)

    # Summary
    summary = {
        'n_raw_sims': n_before,
        'n_after_syph_filter': n_after,
        'n_after_lik_filter': len(df_alive),
        'ess': float(ess),
        'ess_ratio': float(ess_ratio),
        'n_posterior': n_posterior,
    }
    with open(OUTPUTS / 'summary.json', 'w') as f:
        json.dump(summary, f, indent=2)

    print(f'\nSummary: {json.dumps(summary, indent=2)}')
    print(f'Saved to {OUTPUTS}')
    return df_alive


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--reweight', action='store_true',
                        help='Re-run filtering/weighting from saved raw_results.csv '
                             '(no new simulations)')
    args = parser.parse_args()

    if args.reweight:
        sc.heading('Re-weighting from saved raw results')
        df = pd.read_csv(OUTPUTS / 'raw_results.csv')
        print(f'Loaded {len(df)} raw results')
        filter_weight_resample(df)
    else:
        sc.heading(f'Trajectory selection: {N_SEEDS} seeds/draw, '
                   f'n_agents={N_AGENTS}, {N_WORKERS} workers')

        # Load NROY samples
        nroy = pd.read_csv(NROY_CSV)
        n_draws = len(nroy)
        print(f'Loaded {n_draws} NROY samples from {NROY_CSV}')

        # Build task list: each NROY draw × N_SEEDS
        tasks = []
        for draw_idx, row in nroy.iterrows():
            sim_pars = nroy_to_sim_pars(row)
            for s in range(N_SEEDS):
                seed = draw_idx * 1000 + s
                tasks.append(dict(sim_pars=sim_pars, seed=seed))

        print(f'Running {len(tasks)} simulations ({n_draws} draws x {N_SEEDS} seeds)...')
        T = sc.timer()

        if N_WORKERS > 1:
            results = sc.parallelize(run_one, iterkwargs=tasks, ncpus=N_WORKERS)
        else:
            results = [run_one(**t) for t in sc.progressbar(tasks)]

        T.toc(f'Ran {len(tasks)} sims')

        # Build results DataFrame with draw index
        for i, r in enumerate(results):
            r['draw_idx'] = i // N_SEEDS
        df = pd.DataFrame(results)

        # Save raw results
        OUTPUTS.mkdir(parents=True, exist_ok=True)
        df.to_csv(OUTPUTS / 'raw_results.csv', index=False)
        print(f'Saved raw results: {len(df)} rows')

        filter_weight_resample(df)
