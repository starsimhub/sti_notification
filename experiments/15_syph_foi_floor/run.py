"""
Exp 15 — Background syphilis case imports: coverage sweep.

Sweeps a small background importation rate (Poisson per month) across
six values × 50 NROY draws, runs each at 10k agents 1985-2025, and
tracks both the bifurcation diagnostic and the import fraction of
total new acquisitions.
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
import starsim as ss

from model import make_sim
from priors import calib_pars

N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
N_DRAWS_PER_RATE = int(os.environ.get('N_DRAWS_PER_RATE', 50))
START = int(os.environ.get('START', 1985))
STOP = int(os.environ.get('STOP', 2025))
IMPORT_RATES = [0.0, 0.1, 0.5, 1.0, 2.0, 5.0]   # mean imports per month per 10k

HERE = Path(__file__).parent
OUTPUTS = HERE / 'outputs'
JSONL_OUT = OUTPUTS / 'results.jsonl'
NROY_CSV = HERE.parent / '09_history_matching' / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv'

LOG_PARS = {name for name, (_, _, _, log) in calib_pars.items() if log}


class SyphilisImports(ss.Intervention):
    """Background syphilis case importation: each month, infect Poisson(rate)
    susceptible adults independent of network state. Tracks per-step
    import counts and per-step total syphilis incidence so the
    import fraction can be computed post hoc."""

    def __init__(self, mean_imports_per_month=0.0, age_min=15.0, name='syph_imports'):
        super().__init__(name=name)
        self.mean_imports_per_month = float(mean_imports_per_month)
        self.age_min = age_min
        self._cumulative_imports = 0
        self._cumulative_incidence_start = None

    def init_pre(self, sim):
        super().init_pre(sim)
        self.sim = sim

    def step(self):
        sim = self.sim
        syph = sim.diseases.syph
        if self.mean_imports_per_month <= 0:
            return

        susceptible = syph.susceptible.uids
        if len(susceptible) == 0:
            return

        ages = sim.people.age[susceptible]
        eligible = susceptible[ages >= self.age_min]
        if len(eligible) == 0:
            return

        n_to_import = int(np.random.poisson(self.mean_imports_per_month))
        if n_to_import <= 0:
            return
        n_to_import = min(n_to_import, len(eligible))

        chosen = np.random.choice(eligible, size=n_to_import, replace=False)
        chosen_uids = ss.uids(chosen)
        syph.set_prognoses(chosen_uids, source_uids=None)
        self._cumulative_imports += n_to_import


def set_pars_local(sim, pars):
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


def extract_targets(sim, imports_obj):
    results = {}

    def mean_prev(disease, y1, y2):
        r = sim.results[disease]['prevalence']
        years = np.array([t.year + t.month / 12 for t in r.timevec])
        mask = (years >= y1) & (years < y2)
        return float(np.mean(r.values[mask])) if mask.any() else np.nan

    def prev_at(disease, name, year):
        r = sim.results[disease][name]
        years = np.array([t.year + t.month / 12 for t in r.timevec])
        idx = np.argmin(np.abs(years - year))
        return float(r.values[idx])

    results['hiv_prev_2000_2010'] = mean_prev('hiv', 2000, 2010)
    results['hiv_prev_2010_2020'] = mean_prev('hiv', 2010, 2020)
    results['ng_prev_2005_2015'] = mean_prev('ng', 2005, 2015)
    results['ct_prev_f2530'] = prev_at('ct', 'prevalence_f_25_30', 2010)
    results['tv_prev_2005_2015'] = mean_prev('tv', 2005, 2015)
    results['syph_prev_f_2016'] = prev_at('syph', 'prevalence_f', 2016)
    results['syph_prev_m_2016'] = prev_at('syph', 'prevalence_m', 2016)
    results['syph_seroprev_f_2016'] = prev_at('syph', 'serological_prevalence_f', 2016)
    results['syph_seroprev_m_2016'] = prev_at('syph', 'serological_prevalence_m', 2016)

    r = sim.results['syph']['pregnant_prevalence']
    years = np.array([t.year + t.month / 12 for t in r.timevec])
    mask = (years >= 2000) & (years < 2015)
    results['syph_anc_2000_2015'] = float(np.nanmean(r.values[mask])) if mask.any() else np.nan

    coinf = sim.results['syph_hiv_coinfection']
    years = np.array([t.year + t.month / 12 for t in coinf['syph_prev_has_hiv'].timevec])
    idx_2016 = np.argmin(np.abs(years - 2016))
    results['syph_prev_hivpos_2016'] = float(coinf['syph_prev_has_hiv'].values[idx_2016])
    results['syph_prev_hivneg_2016'] = float(coinf['syph_prev_no_hiv'].values[idx_2016])

    syph_f = sim.results['syph']['prevalence_f']
    syph_tvec = np.array([t.year + t.month / 12 for t in syph_f.timevec])
    late_mask = (syph_tvec >= 2020) & (syph_tvec < 2025)
    results['syph_prev_f_2020_2025'] = float(np.nanmean(syph_f.values[late_mask])) if late_mask.any() else np.nan

    # Imports + total acquisitions for the policy-defensibility diagnostic.
    new_infections = sim.results['syph']['new_infections']
    n_total_new = float(np.nansum(new_infections.values))
    n_imported = int(imports_obj._cumulative_imports)
    results['n_imported_total'] = n_imported
    results['n_new_acquisitions_total'] = n_total_new
    results['import_fraction'] = (n_imported / n_total_new) if n_total_new > 0 else float('nan')

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
    seed = task['seed']
    draw_idx = task['draw_idx']
    rate = task['import_rate']
    sim_pars = task['sim_pars']
    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        imports = SyphilisImports(mean_imports_per_month=rate)
        sim.pars['interventions'].append(imports)
        set_pars_local(sim, sim_pars)
        sim.init()
        sim.run()
        out = extract_targets(sim, imports)
        out['seed'] = seed
        out['draw_idx'] = draw_idx
        out['import_rate'] = rate
        out['status'] = 'ok'
        return out
    except Exception as e:
        return {
            'seed': seed, 'draw_idx': draw_idx, 'import_rate': rate,
            'status': f'error: {type(e).__name__}: {e}',
        }


def load_done_keys():
    """Return set of (seed, import_rate) for resumption."""
    if not JSONL_OUT.exists():
        return set()
    done = set()
    with JSONL_OUT.open() as f:
        for line in f:
            try:
                r = json.loads(line)
                done.add((r['seed'], r['import_rate']))
            except Exception:
                pass
    return done


def main():
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    nroy = pd.read_csv(NROY_CSV)
    nroy = nroy.head(N_DRAWS_PER_RATE).reset_index(drop=True)
    print(f'Using first {len(nroy)} NROY draws (deterministic order from CSV).')

    tasks = []
    for rate in IMPORT_RATES:
        for draw_idx, row in nroy.iterrows():
            sim_pars = nroy_to_sim_pars(row)
            # Encode rate into seed so the 0-rate sweep doesn't share a seed
            # with the 5-rate sweep for the same NROY draw.
            seed = int(draw_idx) * 1000 + int(rate * 10)
            tasks.append(dict(sim_pars=sim_pars, seed=seed,
                              draw_idx=int(draw_idx), import_rate=float(rate)))

    done = load_done_keys()
    if done:
        before = len(tasks)
        tasks = [t for t in tasks if (t['seed'], t['import_rate']) not in done]
        print(f'Resuming: {before - len(tasks)} already done, {len(tasks)} remaining.')

    if not tasks:
        print('Nothing to run.')
        return

    print(f'Running {len(tasks)} sims across {len(IMPORT_RATES)} rates '
          f'× {N_DRAWS_PER_RATE} NROY draws, {N_WORKERS} workers.')
    t0 = time.time()
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('a') as fout:
            for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(res) + '\n')
                fout.flush()
                if i % 25 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate_per_s = i / elapsed
                    eta = (len(tasks) - i) / rate_per_s if rate_per_s else 0
                    print(f'  [{i}/{len(tasks)}] rate={rate_per_s:.2f}/s '
                          f'elapsed={elapsed:.0f}s eta={eta:.0f}s')

    print(f'\nFinished. Wrote {JSONL_OUT}')


if __name__ == '__main__':
    main()
