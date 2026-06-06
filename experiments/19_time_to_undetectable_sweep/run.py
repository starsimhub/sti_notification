"""
Sensitivity sweep on `time_to_undetectable` mean.

For each of 15 NROY draws (5 top-weighted from exp 18 posterior, 5
lowest sero/detect-ratio alive, 5 uniform) and each of 5 grid points
on time_to_undetectable mean (2y / 5y / 10y / 20y / 30y, std tracking
mean), run one sim and record:

  - 10 standard targets on the corrected 15-64 denominator
  - Sero/detect ratio
  - Per-age-band detectable prevalence at 2016 (diagnostic for the
    Ruangtragool 2022 age ORs)
  - Late-window (2020-2025) prev_f, so the extinction-rate report can
    be derived per grid point

JSONL append per sim; resumable.

stisim required: feat/syph-detectable-state @ 7c2feb8 or later (the
15-64 all-adult results are introduced in 7c2feb8).
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
import starsim as ss

from model import make_sim

# ---------- Config ----------
N_AGENTS  = int(os.environ.get('N_AGENTS', 10_000))
N_WORKERS = int(os.environ.get('N_WORKERS', 24))
START     = int(os.environ.get('START', 1985))
STOP      = int(os.environ.get('STOP', 2025))
OUTPUTS   = Path(__file__).parent / 'outputs'
JSONL_OUT = OUTPUTS / 'results.jsonl'

NROY_CSV  = (Path(__file__).resolve().parents[1]
             / '17_history_matching_detectable'
             / 'nroy' / 'hm_zim' / 'wave8' / 'nroy_samples.csv')
EXP18_WEIGHTED = (Path(__file__).resolve().parents[1]
                  / '18_trajectory_selection_detectable'
                  / 'outputs' / 'weighted_results.csv')

# 5-point grid on time_to_undetectable median (lognorm_ex's mean param).
# std tracks mean (so lognormal shape stays fixed; pure mean-shift).
TTU_GRID_YEARS = [2.0, 5.0, 10.0, 20.0, 30.0]

# Calibration targets on the corrected 15-64 denominator. Coinfection still
# dropped (coinfection_stats analyzer not yet patched).
OBSERVATIONS = {
    'hiv_prev_2000_2010':         (0.116, 0.015),
    'hiv_prev_2010_2020':         (0.092, 0.010),
    'ng_prev_2005_2015':          (0.020, 0.003),
    'ct_prev_f2530':              (0.120, 0.020),
    'tv_prev_2005_2015':          (0.111, 0.015),
    'syph_detectable_15_64_f_2016': (0.010, 0.003),
    'syph_detectable_15_64_m_2016': (0.006, 0.002),
    'syph_seroprev_15_64_f_2016':   (0.030, 0.005),
    'syph_seroprev_15_64_m_2016':   (0.024, 0.005),
    'syph_anc_2000_2015':           (0.020, 0.005),
}

AGE_BANDS = [(15, 25), (25, 35), (35, 50), (50, 65)]


# ---------- Cohort selection ----------
def pick_cohort():
    """Return (draw_idx, label) tuples for the 15-draw cohort."""
    nroy = pd.read_csv(NROY_CSV)
    nroy['draw_idx'] = nroy.index
    weighted = pd.read_csv(EXP18_WEIGHTED)

    # Cohort 1: top 5 by exp 18 posterior weight.
    top5 = weighted.nlargest(5, 'weight')['draw_idx'].tolist()

    # Cohort 2: 5 alive draws with lowest sero/detect ratio.
    alive = weighted.copy()
    alive['ratio'] = alive['syph_seroprev_f_2016'] / alive['syph_detectable_f_2016'].replace(0, np.nan)
    low5 = alive.dropna(subset=['ratio']).nsmallest(5, 'ratio')['draw_idx'].tolist()

    # Cohort 3: 5 uniform NROY draws (use prior column rank, deterministic).
    rng = np.random.default_rng(0)
    all_ids = list(range(len(nroy)))
    used = set(top5) | set(low5)
    unused = [i for i in all_ids if i not in used]
    uniform5 = sorted(rng.choice(unused, size=5, replace=False).tolist())

    cohort = ([(d, 'top_weighted') for d in top5]
              + [(d, 'low_ratio')    for d in low5]
              + [(d, 'uniform')      for d in uniform5])
    return cohort


# ---------- Model glue ----------
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


def set_time_to_undetectable(sim, mean_years):
    """Replace the syph.time_to_undetectable Dist with one parameterised
    on the new mean (std tracks mean for pure mean-shift sensitivity)."""
    for mod in sim.pars.diseases:
        if getattr(mod, 'name', None) == 'syph':
            mod.pars.time_to_undetectable = ss.lognorm_ex(ss.years(mean_years),
                                                         ss.years(mean_years))
            return
    raise RuntimeError('syph module not found in sim.pars.diseases')


def nroy_to_sim_pars(row):
    sim_pars = {}
    for col, val in row.items():
        if col.startswith('log_'):
            sim_pars[col[4:]] = float(np.exp(val))
        elif '.' in col:
            sim_pars[col] = float(val)
    return sim_pars


def extract_targets(sim):
    out = {}
    res = sim.results

    def mean_prev(disease, y1, y2):
        r = res[disease]['prevalence']
        years = np.array([t.year + t.month/12 for t in r.timevec])
        m = (years >= y1) & (years < y2)
        return float(np.mean(r.values[m])) if m.any() else np.nan

    def prev_at(disease, name, year):
        r = res[disease][name]
        years = np.array([t.year + t.month/12 for t in r.timevec])
        i = np.argmin(np.abs(years - year))
        return float(r.values[i])

    out['hiv_prev_2000_2010']           = mean_prev('hiv', 2000, 2010)
    out['hiv_prev_2010_2020']           = mean_prev('hiv', 2010, 2020)
    out['ng_prev_2005_2015']            = mean_prev('ng', 2005, 2015)
    out['ct_prev_f2530']                = prev_at('ct', 'prevalence_f_25_30', 2010)
    out['tv_prev_2005_2015']            = mean_prev('tv', 2005, 2015)
    out['syph_detectable_15_64_f_2016'] = prev_at('syph', 'detectable_prevalence_15_64_f', 2016)
    out['syph_detectable_15_64_m_2016'] = prev_at('syph', 'detectable_prevalence_15_64_m', 2016)
    out['syph_seroprev_15_64_f_2016']   = prev_at('syph', 'serological_prevalence_15_64_f', 2016)
    out['syph_seroprev_15_64_m_2016']   = prev_at('syph', 'serological_prevalence_15_64_m', 2016)

    # ANC mean over 2000-2015 from pregnant_prevalence.
    r = res['syph']['pregnant_prevalence']
    years = np.array([t.year + t.month/12 for t in r.timevec])
    m = (years >= 2000) & (years < 2015)
    out['syph_anc_2000_2015'] = float(np.nanmean(r.values[m])) if m.any() else np.nan

    # Diagnostics — late-window prev_f (extinction signal) and prev_f at 2016
    # (invisible-reservoir denominator for the sero/detect interpretation).
    out['syph_prev_f_2016'] = prev_at('syph', 'prevalence_f', 2016)
    syph_f = res['syph']['prevalence_f']
    yrs = np.array([t.year + t.month/12 for t in syph_f.timevec])
    lm = (yrs >= 2020) & (yrs < 2025)
    out['syph_prev_f_2020_2025'] = float(np.nanmean(syph_f.values[lm])) if lm.any() else np.nan

    # Age-stratified detectable counts at 2016 — for the Ruangtragool 2022 OR
    # diagnostic. Use sim.people directly because stisim doesn't expose
    # age-banded detectable results.
    ppl = sim.people
    syph = sim.diseases.syph
    age = np.array(ppl.age)
    alive = np.array(ppl.alive)
    detectable = np.array(syph.detectable)
    for (lo, hi) in AGE_BANDS:
        for sex_lab, sex_mask in [('F', np.array(ppl.female)), ('M', ~np.array(ppl.female))]:
            band = (age >= lo) & (age < hi) & alive & sex_mask
            n = int(band.sum())
            d = int(detectable[band].sum())
            out[f'detect_{sex_lab}_{lo}_{hi}_n']  = n
            out[f'detect_{sex_lab}_{lo}_{hi}_pos'] = d
    return out


def run_one(task):
    draw_idx = task['draw_idx']
    cohort   = task['cohort']
    seed     = task['seed']
    ttu_mean = task['ttu_mean']
    sim_pars = task['sim_pars']

    try:
        sim = make_sim(seed=seed, start=START, stop=STOP, n_agents=N_AGENTS,
                       pn_pars=None, fetal_health=False, verbose=-1)
        set_pars_local(sim, sim_pars)
        set_time_to_undetectable(sim, ttu_mean)
        sim.init()
        sim.run()
        out = extract_targets(sim)
        out['draw_idx'] = draw_idx
        out['cohort']   = cohort
        out['ttu_mean'] = ttu_mean
        out['seed']     = seed
        out['status']   = 'ok'
        return out
    except Exception as e:
        return {
            'draw_idx': draw_idx, 'cohort': cohort, 'ttu_mean': ttu_mean,
            'seed': seed, 'status': f'error: {type(e).__name__}: {e}',
        }


def load_done():
    if not JSONL_OUT.exists():
        return set()
    done = set()
    with JSONL_OUT.open() as f:
        for line in f:
            try:
                r = json.loads(line)
                done.add((r['draw_idx'], r['ttu_mean']))
            except Exception:
                pass
    return done


def main():
    sc.heading(f'time_to_undetectable sweep: 15 draws x {len(TTU_GRID_YEARS)} grid points, '
               f'n_agents={N_AGENTS}, {N_WORKERS} workers')

    OUTPUTS.mkdir(parents=True, exist_ok=True)
    cohort = pick_cohort()
    print(f'Cohort: {cohort}')

    nroy = pd.read_csv(NROY_CSV)
    nroy['draw_idx'] = nroy.index

    tasks = []
    for draw_idx, label in cohort:
        row = nroy[nroy['draw_idx'] == draw_idx].iloc[0]
        sp = nroy_to_sim_pars(row)
        for ttu in TTU_GRID_YEARS:
            tasks.append(dict(draw_idx=int(draw_idx), cohort=label,
                              ttu_mean=float(ttu),
                              seed=int(draw_idx) * 1000 + int(ttu * 100),
                              sim_pars=sp))

    done = load_done()
    if done:
        before = len(tasks)
        tasks = [t for t in tasks if (t['draw_idx'], t['ttu_mean']) not in done]
        print(f'Resuming: {before - len(tasks)} done, {len(tasks)} remaining')

    if not tasks:
        print('All sims already complete.')
        return

    print(f'Running {len(tasks)} sims on {N_WORKERS} workers...')
    t0 = time.time()
    with mp.Pool(N_WORKERS, maxtasksperchild=10) as pool:
        with JSONL_OUT.open('a') as fout:
            for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
                fout.write(json.dumps(res) + '\n')
                fout.flush()
                if i % 10 == 0 or i == len(tasks):
                    elapsed = time.time() - t0
                    rate = i / elapsed
                    eta = (len(tasks) - i) / rate if rate > 0 else 0
                    print(f'  [{i}/{len(tasks)}] rate={rate:.2f}/s elapsed={elapsed:.0f}s eta={eta:.0f}s')

    print(f'\nFinished. JSONL: {JSONL_OUT}')


if __name__ == '__main__':
    main()
