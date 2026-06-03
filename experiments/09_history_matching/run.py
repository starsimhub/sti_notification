"""
History matching — wave runner.

Uses the IDM history_matching package to iteratively narrow parameter
space via emulator-based implausibility scoring.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')  # suppress TF noise

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import pandas as pd
import sciris as sc
import history_matching as hm

from model import make_sim
from priors import calib_pars

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
N_SAMPLES = int(os.environ.get('N_SAMPLES', 1000))
MAX_WAVES = int(os.environ.get('MAX_WAVES', 8))
OUTPUT    = Path(__file__).parent / 'outputs'

# ---------- Parameter bounds ----------
# Log-scale parameters: transform to log space for HM
LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}

parameter_bounds = {}
for name, (label, lo, hi, log_scale) in calib_pars.items():
    key = f'log_{name}' if log_scale else name
    if log_scale:
        parameter_bounds[key] = (np.log(lo), np.log(hi))
    else:
        parameter_bounds[key] = (lo, hi)

# ---------- Observations (mean, std) ----------
# Stds are deliberately generous — data uncertainty + stochastic noise
observations = {
    'hiv_prev_2000_2010':     (0.116, 0.015),
    'hiv_prev_2010_2020':     (0.092, 0.010),
    'ng_prev_2005_2015':      (0.020, 0.003),
    'ct_prev_f2530':          (0.120, 0.020),
    'tv_prev_2005_2015':      (0.111, 0.015),
    'syph_prev_f_2016':       (0.010, 0.003),
    'syph_prev_m_2016':       (0.006, 0.002),
    'syph_seroprev_f_2016':   (0.030, 0.005),
    'syph_seroprev_m_2016':   (0.024, 0.005),
    'syph_anc_2000_2015':     (0.020, 0.005),
    'syph_prev_hivpos_2016':  (0.029, 0.008),
    'syph_prev_hivneg_2016':  (0.004, 0.002),
}


# ---------- Simulation function ----------
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
    """Extract summary statistics matching the HM observations."""
    results = {}

    def mean_prev(disease, y1, y2):
        """Mean prevalence over [y1, y2) from yearly results."""
        r = sim.results[disease]
        prev = r['prevalence'].values
        tvec = r['prevalence'].timevec
        years = np.array([t.year + t.month / 12 for t in tvec])
        mask = (years >= y1) & (years < y2)
        return float(np.mean(prev[mask])) if mask.any() else np.nan

    def prev_at(disease, result_name, year):
        """Prevalence at a specific year."""
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
    # ANC prevalence — use pregnant_prevalence, not overall prevalence
    r = sim.results['syph']
    anc_vals = r['pregnant_prevalence'].values
    tvec = r['pregnant_prevalence'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    mask = (years >= 2000) & (years < 2015)
    results['syph_anc_2000_2015'] = float(np.nanmean(anc_vals[mask])) if mask.any() else np.nan

    # Coinfection analyzer
    coinf = sim.results['syph_hiv_coinfection']
    coinf_hp = coinf['syph_prev_has_hiv'].values
    coinf_hn = coinf['syph_prev_no_hiv'].values
    tvec = coinf['syph_prev_has_hiv'].timevec
    years = np.array([t.year + t.month / 12 for t in tvec])
    idx_2016 = np.argmin(np.abs(years - 2016))
    results['syph_prev_hivpos_2016'] = float(coinf_hp[idx_2016])
    results['syph_prev_hivneg_2016'] = float(coinf_hn[idx_2016])

    return results


N_WORKERS = int(os.environ.get('N_WORKERS', 75))


def _run_one(row_dict, seed):
    """Run a single sim from a dict of (possibly log-transformed) parameters."""
    sim_pars = {}
    for col, val in row_dict.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = np.exp(val)
        else:
            sim_pars[col] = val

    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        return extract_targets(sim)
    except Exception as e:
        print(f'  Sim failed: {e}')
        return {k: np.nan for k in observations}


def run_sim(params_df):
    """HM simulation function: takes DataFrame of params, returns DataFrame of outputs."""
    row_dicts = [row.to_dict() for _, row in params_df.iterrows()]

    if N_WORKERS > 1:
        iter_kwargs = [dict(row_dict=rd, seed=i) for i, rd in enumerate(row_dicts)]
        results = sc.parallelize(_run_one, iterkwargs=iter_kwargs, ncpus=N_WORKERS)
    else:
        results = [_run_one(rd, i) for i, rd in enumerate(row_dicts)]

    return pd.DataFrame(results)


# ---------- Main ----------
if __name__ == '__main__':
    sc.heading(f'History matching: {N_SAMPLES} samples/wave, {MAX_WAVES} waves, '
               f'n_agents={N_AGENTS}')

    engine = (
        hm.HistoryMatchingBuilder
        .from_data(
            parameter_bounds=parameter_bounds,
            observations=observations,
        )
        .with_emulator_type('bayes_linear')
        .with_sampling_strategy('lhs')
        .with_samples_per_iteration(N_SAMPLES)
        .with_max_iterations(MAX_WAVES)
        .with_implausibility_threshold(3.0)
        .with_output_dir(str(OUTPUT))
        .with_run_name('hm_zim')
        .build()
    )

    engine.set_simulation_function(run_sim)
    results = engine.run()

    print(f'\nHistory matching complete. Results in {OUTPUT}')
