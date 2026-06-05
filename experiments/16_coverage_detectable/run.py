"""
Exp 16 — Coverage check with detectable_prevalence target mapping.

100 prior draws (uniform per priors.py), 10k agents, 1985-2025, against
the patched stisim that exposes detectable_prevalence (commit 24bdf58
on feat/syph-detectable-state). Active-syph targets remap from
prevalence_f/m to detectable_prevalence_f/m. Other targets unchanged.

Saves per-sim diagnostics including the (prevalence_f - detectable_prevalence_f)
gap to expose the invisible-to-survey reservoir size.
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

N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
N_DRAWS = int(os.environ.get('N_DRAWS', 100))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START = int(os.environ.get('START', 1985))
STOP = int(os.environ.get('STOP', 2025))
SEED_BASE = int(os.environ.get('SEED_BASE', 16_000))

HERE = Path(__file__).parent
OUTPUTS = HERE / 'outputs'
JSONL_OUT = OUTPUTS / 'results.jsonl'

# Targets: (mean, std). Active-syph rows now compared to detectable_prevalence.
OBSERVATIONS = {
    'hiv_prev_2000_2010':     (0.116, 0.015),
    'hiv_prev_2010_2020':     (0.092, 0.010),
    'ng_prev_2005_2015':      (0.020, 0.003),
    'ct_prev_f2530':          (0.120, 0.020),
    'tv_prev_2005_2015':      (0.111, 0.015),
    'syph_detectable_f_2016': (0.010, 0.002),   # was syph_prev_f_2016 / prevalence_f
    'syph_detectable_m_2016': (0.006, 0.0013),  # was syph_prev_m_2016 / prevalence_m
    'syph_seroprev_f_2016':   (0.030, 0.0033),
    'syph_seroprev_m_2016':   (0.024, 0.0033),
    'syph_anc_2000_2015':     (0.020, 0.0033),
    'syph_prev_hivpos_2016':  (0.029, 0.0053),  # still uses syph.infected — flagged in README
    'syph_prev_hivneg_2016':  (0.004, 0.0013),  # ditto
}


def sample_prior(n, seed=0):
    """Uniform draws within each parameter's [low, high] interval. Log-scale
    parameters are uniform-in-log."""
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(n):
        d = {}
        for name, (_, lo, hi, log) in calib_pars.items():
            if log:
                # Uniform in log space, return as the (already-log) value
                # consistent with priors.py convention. Convert back to linear
                # in set_pars_local.
                val = rng.uniform(np.log(lo), np.log(hi))
                d[f'log_{name}'] = val
            else:
                d[name] = rng.uniform(lo, hi)
        rows.append(d)
    return pd.DataFrame(rows)


def set_pars_local(sim, pars):
    for key, value in pars.items():
        if '.' not in key: continue
        mn, pn = key.split('.', 1)
        for cat in ('diseases', 'networks', 'interventions', 'connectors',
                    'analyzers', 'demographics', 'custom'):
            container = sim.pars.get(cat)
            if container is None: continue
            if isinstance(container, list):
                for mod in container:
                    if hasattr(mod, 'name') and mod.name == mn:
                        existing = mod.pars.get(pn)
                        if hasattr(existing, 'set'):
                            existing.set(mean=value)
                        else:
                            mod.pars[pn] = value
                        break


def nroy_to_sim_pars(row):
    """Same converter as exp 13: log_ prefix → exp back to linear."""
    out = {}
    for col, val in row.items():
        if col.startswith('log_'):
            out[col[4:]] = float(np.exp(val))
        else:
            out[col] = float(val)
    return out


def extract_targets(sim):
    results = {}

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

    results['hiv_prev_2000_2010'] = mean_prev('hiv', 2000, 2010)
    results['hiv_prev_2010_2020'] = mean_prev('hiv', 2010, 2020)
    results['ng_prev_2005_2015']  = mean_prev('ng', 2005, 2015)
    results['ct_prev_f2530']      = prev_at('ct', 'prevalence_f_25_30', 2010)
    results['tv_prev_2005_2015']  = mean_prev('tv', 2005, 2015)

    # NEW mapping: detectable_prevalence, not prevalence.
    results['syph_detectable_f_2016'] = prev_at('syph', 'detectable_prevalence_f', 2016)
    results['syph_detectable_m_2016'] = prev_at('syph', 'detectable_prevalence_m', 2016)
    results['syph_seroprev_f_2016']   = prev_at('syph', 'serological_prevalence_f', 2016)
    results['syph_seroprev_m_2016']   = prev_at('syph', 'serological_prevalence_m', 2016)

    # ANC — kept as existing mapping (see README caveats).
    r = sim.results['syph']['pregnant_prevalence']
    years = np.array([t.year + t.month/12 for t in r.timevec])
    mask = (years >= 2000) & (years < 2015)
    results['syph_anc_2000_2015'] = float(np.nanmean(r.values[mask])) if mask.any() else np.nan

    coinf = sim.results['syph_hiv_coinfection']
    years = np.array([t.year + t.month/12 for t in coinf['syph_prev_has_hiv'].timevec])
    i16 = np.argmin(np.abs(years - 2016))
    results['syph_prev_hivpos_2016'] = float(coinf['syph_prev_has_hiv'].values[i16])
    results['syph_prev_hivneg_2016'] = float(coinf['syph_prev_no_hiv'].values[i16])

    # Diagnostics: prevalence_f vs detectable_prevalence_f (invisible reservoir),
    # plus late-window detectable trajectory.
    syph = sim.results['syph']
    syph_years = np.array([t.year + t.month/12 for t in syph['prevalence_f'].timevec])
    i16 = np.argmin(np.abs(syph_years - 2016))
    results['prevalence_f_2016'] = float(syph['prevalence_f'].values[i16])
    results['active_prevalence_f_2016'] = float(syph['active_prevalence_f'].values[i16])
    results['invisible_reservoir_f_2016'] = (
        results['prevalence_f_2016'] - results['syph_detectable_f_2016']
    )
    late = (syph_years >= 2020) & (syph_years < 2025)
    results['syph_detectable_f_2020_2025'] = float(np.nanmean(syph['detectable_prevalence_f'].values[late])) if late.any() else np.nan
    results['prevalence_f_2020_2025'] = float(np.nanmean(syph['prevalence_f'].values[late])) if late.any() else np.nan

    return results


def run_one(task):
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
        out = {'seed': seed, 'draw_idx': draw_idx,
               'status': f'error: {type(e).__name__}: {e}'}
        return out


def load_done_seeds():
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


def main():
    sc.heading(f'Exp 16 coverage check: {N_DRAWS} prior draws, '
               f'n_agents={N_AGENTS}, {N_WORKERS} workers')
    OUTPUTS.mkdir(parents=True, exist_ok=True)

    draws = sample_prior(N_DRAWS, seed=SEED_BASE)
    draws.to_csv(OUTPUTS / 'prior_draws.csv', index=False)
    print(f'Sampled {len(draws)} prior draws → {OUTPUTS / "prior_draws.csv"}')

    tasks = []
    for di, row in draws.iterrows():
        sim_pars = nroy_to_sim_pars(row)
        seed = SEED_BASE + int(di)
        tasks.append(dict(sim_pars=sim_pars, seed=seed, draw_idx=int(di)))

    done = load_done_seeds()
    if done:
        before = len(tasks)
        tasks = [t for t in tasks if t['seed'] not in done]
        print(f'Resuming: {before - len(tasks)} already done, {len(tasks)} remaining.')

    if not tasks:
        print('Nothing to run.')
        return

    print(f'Running {len(tasks)} sims, {N_WORKERS} workers, '
          f'maxtasksperchild=10 for memory.')
    t0 = time.time()
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('a') as fout:
            for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(res) + '\n')
                fout.flush()
                if i % 10 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate else 0
                    print(f'  [{i}/{len(tasks)}] rate={rate:.2f}/s '
                          f'elapsed={elapsed:.0f}s eta={eta:.0f}s')

    print(f'\nFinished. Wrote {JSONL_OUT}')


if __name__ == '__main__':
    main()
