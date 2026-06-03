"""
Prior predictive coverage check — corrected syphilis targets.

Same setup as exp 06 (100 draws, 10k agents, 1985–2025) but with
expanded result columns: by-sex syphilis prevalence, seroprevalence,
ANC prevalence, symptomatic prevalence, and HIV coinfection.
"""

import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', MKL_NUM_THREADS='1')

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np
import sciris as sc
from stisim.calibration import make_df

from model import make_sim
from priors import calib_pars


RESULT_COLS = [
    # Non-syphilis
    'ng.prevalence',
    'ct.prevalence_f_25_30',
    'tv.prevalence',
    'hiv.prevalence',
    # Syphilis: current infection by sex
    'syph.prevalence_f',
    'syph.prevalence_m',
    # Syphilis: seroprevalence by sex
    'syph.serological_prevalence_f',
    'syph.serological_prevalence_m',
    # Syphilis: ANC prevalence
    'syph.pregnant_prevalence',
    # Syphilis: symptomatic (primary + secondary)
    'syph.active_prevalence',
    # HIV-syphilis coinfection
    'syph_hiv_coinfection.syph_prev_has_hiv',
    'syph_hiv_coinfection.syph_prev_no_hiv',
]

N_DRAWS   = int(os.environ.get('N_DRAWS', 10))
N_WORKERS = int(os.environ.get('N_WORKERS', 1))
N_AGENTS  = int(os.environ.get('N_AGENTS', 5_000))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
RESULTS   = Path(__file__).parent / 'results'


def set_pars_local(sim, pars):
    """Set parameters by exact dot-notation lookup against pre-init sim modules."""
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        found = False
        for category in ('diseases', 'networks', 'interventions',
                         'connectors', 'analyzers', 'demographics',
                         'custom'):
            container = sim.pars.get(category)
            if container is None:
                continue
            # Handle both list and dict containers
            if isinstance(container, list):
                for mod in container:
                    if hasattr(mod, 'name') and mod.name == mod_name:
                        # Distributional pars: update mean rather than replace
                        existing = mod.pars.get(par_name)
                        if hasattr(existing, 'set'):
                            existing.set(mean=value)
                        else:
                            mod.pars[par_name] = value
                        found = True
                        break
            elif hasattr(container, 'get'):
                mod = container.get(mod_name)
                if mod is not None:
                    existing = mod.pars.get(par_name)
                    if hasattr(existing, 'set'):
                        existing.set(mean=value)
                    else:
                        mod.pars[par_name] = value
                    found = True
            if found:
                break
    return sim


def run_one(draw_pars, seed):
    sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                   pn_pars=None, fetal_health=False, verbose=-1)
    set_pars_local(sim, draw_pars)
    sim.init()
    sim.run()
    return make_df(sim, df_res_list=RESULT_COLS)


def sample_draws(n, seed=42):
    rng = np.random.default_rng(seed)
    draws = []
    for name, (label, low, high, log_scale) in calib_pars.items():
        vals = (np.exp(rng.uniform(np.log(low), np.log(high), n))
                if log_scale else rng.uniform(low, high, n))
        draws.append((name, vals))
    return [{name: float(vals[i]) for name, vals in draws} for i in range(n)]


if __name__ == '__main__':
    sc.heading(f'Coverage check: {N_DRAWS} prior draws | n_agents={N_AGENTS} '
               f'| {START}-{STOP}')
    draw_list = sample_draws(N_DRAWS)

    T = sc.timer()
    if N_WORKERS > 1:
        iter_kwargs = [dict(draw_pars=d, seed=i) for i, d in enumerate(draw_list)]
        dfs = sc.parallelize(run_one, iterkwargs=iter_kwargs, ncpus=N_WORKERS)
    else:
        dfs = [run_one(d, i) for i, d in enumerate(sc.progressbar(draw_list))]
    T.toc(f'Ran {N_DRAWS} draws')

    RESULTS.mkdir(parents=True, exist_ok=True)
    sc.save(RESULTS / 'coverage_dfs.obj', dfs)
    sc.save(RESULTS / 'coverage_draws.obj', draw_list)
    print(f'Saved to {RESULTS}')
