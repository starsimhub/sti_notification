"""
Decision analysis: run calibrated scenario sweeps.

For each posterior draw, runs a baseline (no PN, baseline care-seeking)
and each scenario variant, then computes impact as scenario − baseline.
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
import starsim as ss

from model import make_sim
from priors import calib_pars
from run_sweeps import PN_LEVELS, build_scenarios

N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_DRAWS   = int(os.environ.get('N_DRAWS', 50))
N_WORKERS = int(os.environ.get('N_WORKERS', 40))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2030))
OUTPUTS   = Path(__file__).parent / 'outputs'

POSTERIOR_CSV = Path(__file__).resolve().parents[1] / '10_trajectory_selection' / 'outputs' / 'posterior_ensemble.csv'
NROY_CSV = Path(__file__).resolve().parents[1] / '09_history_matching' / 'outputs' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'

# Log-scale parameters
LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}


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


def nroy_row_to_sim_pars(row):
    """Convert NROY-format row (with log_ prefixes) to sim parameter dict."""
    sim_pars = {}
    for col, val in row.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = np.exp(val)
        else:
            sim_pars[col] = val
    return sim_pars


def extract_outcomes(sim):
    """Extract annual outcome totals over the intervention period (2020–2030)."""
    results = sim.results
    yearvec = sim.t.yearvec
    mask = (yearvec >= 2020) & (yearvec < 2030)

    def total(arr):
        return float(np.asarray(arr)[mask].sum())

    out = dict(
        ng_inf=total(results.ng.new_infections),
        ct_inf=total(results.ct.new_infections),
        tv_inf=total(results.tv.new_infections),
        syph_inf=total(results.syph.new_infections),
        hiv_inf=total(results.hiv.new_infections),
        ng_tx=total(results.ng_tx.new_treated) if 'ng_tx' in results else 0,
        ct_tx=total(results.ct_tx.new_treated) if 'ct_tx' in results else 0,
    )

    # PN results
    if 'pn' in sim.interventions:
        out['pn_notified'] = total(results.pn.new_notified)
        out['pn_attending'] = total(results.pn.new_attending)
    else:
        out['pn_notified'] = 0
        out['pn_attending'] = 0

    # Fetal health
    if sim.custom and 'fetal_health' in sim.custom:
        fh = results.fetal_health
        out['lbw'] = total(fh.n_lbw)
        out['sga'] = total(fh.n_sga)
        out['svn'] = total(fh.n_svn)
        out['births'] = total(fh.n_births)
    else:
        out['lbw'] = out['sga'] = out['svn'] = out['births'] = 0

    # Syphilis congenital
    out['syph_congenital'] = total(results.syph.new_congenital)
    out['syph_congenital_deaths'] = total(results.syph.new_congenital_deaths)

    return out


def run_one(sim_pars, sweep, scen, scen_kwargs, draw_idx):
    """Run a single scenario for a single posterior draw."""
    try:
        sim = make_sim(seed=draw_idx, start=START, stop=STOP,
                       n_agents=N_AGENTS, verbose=-1, **scen_kwargs)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        out = extract_outcomes(sim)
        out['sweep'] = sweep
        out['scen'] = scen
        out['draw_idx'] = draw_idx
        return out
    except Exception as e:
        print(f'  Failed: {sweep}/{scen}/draw{draw_idx}: {e}')
        return dict(sweep=sweep, scen=scen, draw_idx=draw_idx)


if __name__ == '__main__':
    sc.heading(f'Decision analysis: {N_DRAWS} draws × 17 scenarios, '
               f'n_agents={N_AGENTS}')

    # Load posterior draws (map back to NROY param space)
    posterior = pd.read_csv(POSTERIOR_CSV)
    nroy = pd.read_csv(NROY_CSV)

    # Resample to N_DRAWS unique draws
    unique_draws = posterior['draw_idx'].unique()
    if len(unique_draws) > N_DRAWS:
        rng = np.random.default_rng(42)
        selected = rng.choice(unique_draws, size=N_DRAWS, replace=False)
    else:
        selected = unique_draws[:N_DRAWS]
    print(f'Using {len(selected)} posterior draws')

    # Build scenario list: baseline + all sweep scenarios
    scenarios = [('baseline', 'baseline',
                  dict(pn_pars=None, care_seek_mult=1.0, poc=None))]
    scenarios += build_scenarios()
    print(f'{len(scenarios)} scenarios per draw')

    # Build full task list
    tasks = []
    for draw_idx in selected:
        nroy_row = nroy.iloc[draw_idx]
        sim_pars = nroy_row_to_sim_pars(nroy_row.to_dict())
        for sweep, scen, scen_kwargs in scenarios:
            tasks.append(dict(sim_pars=sim_pars, sweep=sweep, scen=scen,
                              scen_kwargs=scen_kwargs, draw_idx=int(draw_idx)))

    print(f'Total sims: {len(tasks)}')

    T = sc.timer()
    if N_WORKERS > 1:
        results = sc.parallelize(run_one, iterkwargs=tasks, ncpus=N_WORKERS)
    else:
        results = [run_one(**t) for t in sc.progressbar(tasks)]
    T.toc(f'Ran {len(tasks)} sims')

    df = pd.DataFrame(results)
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUTS / 'scenario_results.csv', index=False)
    print(f'Saved {len(df)} results to {OUTPUTS / "scenario_results.csv"}')

    # Quick summary
    outcome_cols = ['ng_inf', 'ct_inf', 'tv_inf', 'syph_inf', 'hiv_inf',
                    'syph_congenital', 'pn_notified']
    summary = df.groupby(['sweep', 'scen'])[outcome_cols].mean().round(1)
    print(summary)
