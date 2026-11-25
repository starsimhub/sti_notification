"""Exp 10: mix-and-match calibration.

Builds combined parameter sets from exp 09's per-pathogen in-band draws and runs them
through exp 07's calibration machinery (K seeds, scoring and acceptance unchanged).
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent / '09_2026-11-25_dedup_screen' / 'outputs'
N_COMBOS = int(os.environ.get('N_COMBOS', 100))
POOL_TOL = float(os.environ.get('POOL_TOL', 0.5))  # band-widths, as exp 07's ACCEPT_TOL
os.environ.setdefault('N_DRAWS', str(N_COMBOS))

spec = importlib.util.spec_from_file_location(
    'exp07', HERE.parent / '07_2026-11-24_no_syph_calibration' / 'run.py')
exp07 = sys.modules['exp07'] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp07)

# Parameter groups: each pathogen's prevalence depends (R2 >= 0.94) only on its own group.
# Network parameters travel with the HIV draw (they barely affect any target).
GROUPS = {
    'hiv': (['hiv.beta_m2f', 'hiv.rel_init_prev', 'structuredsexual.prop_f0',
             'structuredsexual.m2_conc', 'structuredsexual.dur_sw'], 'hiv_prev_15_49'),
    'ng': (['log_ng.beta_m2f', 'log_ng.dur_asymp2clear'], 'ng_prev_f'),
    'ct': (['log_ct.beta_m2f'], 'ct_prev_f_25_30'),
    'tv': (['log_tv.beta_m2f'], 'tv_prev_f'),
}


def build_combos(n, seed=1):
    priors = pd.read_csv(SCREEN / 'priors.csv').set_index('draw_idx')
    raw = pd.read_json(SCREEN / 'results_raw.jsonl', lines=True)
    raw = raw[raw.status == 'ok'].set_index('draw_idx')
    rng = np.random.default_rng(seed)
    pools, picks = {}, {}
    for g, (cols, target) in GROUPS.items():
        (lo, hi), _ = exp07.TARGETS[target]
        dist = raw[target].apply(lambda v: exp07.band_distance(v, lo, hi))
        ok = (dist <= POOL_TOL) & raw[f'sustained_{g}'].astype(bool)
        pools[g] = raw.index[ok].tolist()
        picks[g] = rng.choice(pools[g], size=n, replace=len(pools[g]) < n)
    rows = []
    for i in range(n):
        row = {'draw_idx': 10_000 + i}
        for g, (cols, _) in GROUPS.items():
            row.update(priors.loc[picks[g][i], cols].to_dict())
            row[f'src_{g}'] = int(picks[g][i])
        rows.append(row)
    combos = pd.DataFrame(rows)
    return combos, {g: len(p) for g, p in pools.items()}


combos, pool_sizes = build_combos(N_COMBOS)
exp07.generate_prior_draws = lambda *_a, **_k: combos[[c for c in combos.columns if not c.startswith('src_')]]
exp07.OUT_DIR = HERE / 'outputs'
exp07.OUT_DIR.mkdir(exist_ok=True)

if __name__ == '__main__':
    print(f'exp 10 pools (tol {POOL_TOL}): {pool_sizes}; {N_COMBOS} combos', flush=True)
    combos.to_csv(exp07.OUT_DIR / 'combos.csv', index=False)
    exp07.main()
