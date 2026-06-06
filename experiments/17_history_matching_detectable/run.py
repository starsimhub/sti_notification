"""
History matching against detectable_prevalence target mapping.

Mirror of exp 09's HM setup with three deliberate diffs:
  1. Syph active targets remap from prevalence_f/m to detectable_prevalence_f/m.
  2. Coinfection targets dropped (analyzer not yet patched for detectable).
  3. mp.Pool with maxtasksperchild=10 + 24 workers for memory safety (vs
     exp 09's sc.parallelize at 75 workers — too tight on 314 GB).

Resumable per wave via the history_matching package's checkpoint mechanism.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1',
                  TF_CPP_MIN_LOG_LEVEL='3')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import multiprocessing as mp
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
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
OUTPUT    = Path(__file__).parent / 'outputs'

# ---------- Parameter bounds ----------
LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}

parameter_bounds = {}
for name, (label, lo, hi, log_scale) in calib_pars.items():
    key = f'log_{name}' if log_scale else name
    parameter_bounds[key] = (np.log(lo), np.log(hi)) if log_scale else (lo, hi)

# ---------- Observations (mean, std) — 11 targets ----------
# Syph active targets now compared against detectable_prevalence
# (WHO 2021 Fig 7: dual-RDT misses late-latent with low non-trep titre).
# Coinfection (syph_prev_hivpos/hivneg) dropped — coinfection_stats analyzer
# still uses syph.infected and would emit artifact-driven implausibility.
observations = {
    'hiv_prev_2000_2010':     (0.116, 0.015),
    'hiv_prev_2010_2020':     (0.092, 0.010),
    'ng_prev_2005_2015':      (0.020, 0.003),
    'ct_prev_f2530':          (0.120, 0.020),
    'tv_prev_2005_2015':      (0.111, 0.015),
    'syph_detectable_f_2016': (0.010, 0.003),   # was syph_prev_f
    'syph_detectable_m_2016': (0.006, 0.002),   # was syph_prev_m
    'syph_seroprev_f_2016':   (0.030, 0.005),
    'syph_seroprev_m_2016':   (0.024, 0.005),
    'syph_anc_2000_2015':     (0.020, 0.005),
}


# ---------- Simulation glue ----------
def set_pars_local(sim, pars):
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        found = False
        for cat in ('diseases', 'networks', 'interventions',
                    'connectors', 'analyzers', 'demographics', 'custom'):
            container = sim.pars.get(cat)
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
    out = {}

    def mean_prev(d, y1, y2):
        r = sim.results[d]['prevalence']
        years = np.array([t.year + t.month/12 for t in r.timevec])
        m = (years >= y1) & (years < y2)
        return float(np.mean(r.values[m])) if m.any() else np.nan

    def prev_at(d, name, year):
        r = sim.results[d][name]
        years = np.array([t.year + t.month/12 for t in r.timevec])
        i = np.argmin(np.abs(years - year))
        return float(r.values[i])

    out['hiv_prev_2000_2010']     = mean_prev('hiv', 2000, 2010)
    out['hiv_prev_2010_2020']     = mean_prev('hiv', 2010, 2020)
    out['ng_prev_2005_2015']      = mean_prev('ng', 2005, 2015)
    out['ct_prev_f2530']          = prev_at('ct', 'prevalence_f_25_30', 2010)
    out['tv_prev_2005_2015']      = mean_prev('tv', 2005, 2015)
    out['syph_detectable_f_2016'] = prev_at('syph', 'detectable_prevalence_f', 2016)
    out['syph_detectable_m_2016'] = prev_at('syph', 'detectable_prevalence_m', 2016)
    out['syph_seroprev_f_2016']   = prev_at('syph', 'serological_prevalence_f', 2016)
    out['syph_seroprev_m_2016']   = prev_at('syph', 'serological_prevalence_m', 2016)

    r = sim.results['syph']['pregnant_prevalence']
    years = np.array([t.year + t.month/12 for t in r.timevec])
    m = (years >= 2000) & (years < 2015)
    out['syph_anc_2000_2015'] = float(np.nanmean(r.values[m])) if m.any() else np.nan

    return out


def _run_one(task):
    row_dict, seed = task['row_dict'], task['seed']
    sim_pars = {}
    for col, val in row_dict.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        else:
            sim_pars[col] = float(val)

    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        return extract_targets(sim)
    except Exception as e:
        return {k: np.nan for k in observations} | {'_error': f'{type(e).__name__}: {e}'}


def run_sim(params_df):
    """HM simulation function — DataFrame in, DataFrame out.

    Output row order MUST match input row order (the HM engine joins on
    positional index). Use ordered iteration; do NOT use imap_unordered.
    """
    row_dicts = [row.to_dict() for _, row in params_df.iterrows()]
    tasks = [dict(row_dict=rd, seed=i) for i, rd in enumerate(row_dicts)]

    if N_WORKERS > 1:
        with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
            results = list(pool.imap(_run_one, tasks, chunksize=1))
    else:
        results = [_run_one(t) for t in tasks]

    return pd.DataFrame(results)


if __name__ == '__main__':
    sc.heading(f'HM (detectable mapping): {N_SAMPLES} samples/wave, '
               f'{MAX_WAVES} waves, n_agents={N_AGENTS}, {N_WORKERS} workers')

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
