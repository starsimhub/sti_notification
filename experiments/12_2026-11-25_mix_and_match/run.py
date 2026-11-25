"""Exp 12: mix-and-match calibration on Starsim 4.

Each target depends almost only on its own pathogen's parameters (exp 07: R2 0.94-1.00 on them; the network parameters
add at most 0.02), so a single LHS over all of them rarely lands every pathogen in band at once. This builds combined
parameter sets from the per-pathogen pools of exp 11's screen (draws that sustained, with all of that pathogen's
targets within their acceptance tolerance), and runs them through exp 10's calibration machinery (K seeds, scoring
and acceptance unchanged).
"""
import importlib.util
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
SCREEN = HERE.parent / '11_2026-11-25_v4_coverage' / 'outputs'
N_COMBOS = int(os.environ.get('N_COMBOS', 200))
os.environ.setdefault('N_DRAWS', str(N_COMBOS))

spec = importlib.util.spec_from_file_location('exp10', HERE.parent / '10_2026-11-25_v4_calibration' / 'run.py')
exp10 = sys.modules['exp10'] = importlib.util.module_from_spec(spec)  # workers unpickle run_one by module name
spec.loader.exec_module(exp10)

# Parameter groups and the targets that select each pool. The network parameters travel with the HIV draw.
GROUPS = {
    'hiv': (['hiv.beta_m2f', 'hiv.rel_init_prev', 'log_hiv.rel_death', 'structuredsexual.prop_f0',
             'structuredsexual.m2_conc', 'structuredsexual.dur_sw'],
            ['hiv_prev_15_49', 'hiv_prev_2000s', 'hiv_prev_2010s', 'hiv_deaths_2000s', 'hiv_deaths_2010s']),
    'ng': (['log_ng.beta_m2f', 'log_ng.dur_asymp2clear'], ['ng_prev', 'ng_prev_f_18_24_stich', 'ng_new_inf_per_yr']),
    'ct': (['log_ct.beta_m2f'], ['ct_prev_f_18_24_stich']),
    'tv': (['log_tv.beta_m2f'], ['tv_prev', 'tv_prev_f_18_24_stich']),
}


def pools(raw):
    """ For each pathogen, the screen draws that sustained, with all its targets within their acceptance tolerance """
    out = {}
    for g, (_cols, targets) in GROUPS.items():
        ok = raw[f'sustained_{g}'].astype(bool)
        for t in targets:
            (lo, hi), _ = exp10.TARGETS[t]
            ok &= raw[t].apply(lambda v: exp10.band_distance(v, lo, hi)) <= exp10.ACCEPT.get(t, exp10.ACCEPT_TOL)
        out[g] = raw.index[ok].tolist()
    return out


def build_combos(n, seed=1):
    priors = pd.read_csv(SCREEN / 'priors.csv').set_index('draw_idx')
    raw = pd.read_json(SCREEN / 'results_raw.jsonl', lines=True)
    raw = raw[raw.status == 'ok'].set_index('draw_idx')
    rng = np.random.default_rng(seed)
    pool = pools(raw)
    picks = {g: rng.choice(p, size=n, replace=len(p) < n) for g, p in pool.items()}
    rows = []
    for i in range(n):
        row = {'draw_idx': 10_000 + i}
        for g, (cols, _) in GROUPS.items():
            row.update(priors.loc[picks[g][i], cols].to_dict())
            row[f'src_{g}'] = int(picks[g][i])
        rows.append(row)
    return pd.DataFrame(rows)[['draw_idx'] + list(priors.columns) + [f'src_{g}' for g in GROUPS]], {g: len(p) for g, p in pool.items()}


combos, pool_sizes = build_combos(N_COMBOS)
exp10.generate_prior_draws = lambda *_a, **_k: combos[[c for c in combos.columns if not c.startswith('src_')]]
exp10.OUT_DIR = HERE / 'outputs'

if __name__ == '__main__':
    exp10.OUT_DIR.mkdir(exist_ok=True)
    print(f'exp 12 pools: {pool_sizes}; {N_COMBOS} combos', flush=True)
    combos.to_csv(exp10.OUT_DIR / 'combos.csv', index=False)
    exp10.main()
