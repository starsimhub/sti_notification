"""
Prior predictive coverage check for Zimbabwe.

Draws N_DRAWS parameter sets uniformly from the calibration prior bounds
(see ``priors.py``) and runs the model end-to-end with each. Saves the
list of per-draw result dataframes for plotting by ``plot.py``.

Workflow:
  1. Sample N_DRAWS from priors.calib_pars (uniform / log-uniform).
  2. For each draw, build a fresh sim, apply the draw via
     ``sti.calibration.set_sim_pars``, run, extract the fields we'll
     calibrate against (NG/CT/TV/HIV/syph prevalence trajectories).
  3. Save results/coverage_dfs.obj for plotting.

Run locally with N_DRAWS=10 for a quick sanity check; on the IDM Azure
VM, set N_DRAWS=100 and N_WORKERS=75 (or whatever is free per
`who -u`).
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


def set_pars_local(sim, pars):
    """
    Set parameters by exact dot-notation lookup against the
    pre-init sim's pars dict. Avoids the upstream
    ``stisim.calibration.set_sim_pars`` ambiguity when a connector
    holds a reference to a disease module of the same short name
    (e.g. ``hiv_ng`` connector + ``ng`` disease).
    """
    for key, value in pars.items():
        if '.' not in key:
            continue
        mod_name, par_name = key.split('.', 1)
        for category in ('diseases', 'networks', 'interventions',
                         'connectors', 'analyzers', 'demographics',
                         'custom'):
            container = sim.pars.get(category)
            if container is None:
                continue
            mod = container.get(mod_name) if hasattr(container, 'get') else None
            if mod is not None:
                mod.pars[par_name] = value
                break
    return sim

RESULT_COLS = [
    'ng.prevalence',
    'ct.prevalence_f_25_30',
    'tv.prevalence',
    'hiv.prevalence',
    'syph.active_prevalence',
]
N_DRAWS   = int(os.environ.get('N_DRAWS', 10))      # bump via env var on VM
N_WORKERS = int(os.environ.get('N_WORKERS', 1))     # set to ~75 on the IDM VM
N_AGENTS  = int(os.environ.get('N_AGENTS', 5_000))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
RESULTS   = Path(__file__).parent / 'results'


def run_one(args):
    draw_pars, seed = args
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
    args = [(d, i) for i, d in enumerate(draw_list)]

    T = sc.timer()
    if N_WORKERS > 1:
        dfs = sc.parallelize(run_one, iterarg=args, ncpus=N_WORKERS)
    else:
        dfs = [run_one(a) for a in sc.progressbar(args)]
    T.toc(f'Ran {N_DRAWS} draws')

    RESULTS.mkdir(parents=True, exist_ok=True)
    sc.save(RESULTS / 'coverage_dfs.obj', dfs)
    sc.save(RESULTS / 'coverage_draws.obj', draw_list)
    print(f'Saved to {RESULTS}')
