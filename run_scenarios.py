"""
Scenario driver: SOC reference + POC 3-factor full factorial.

Factors (each a 5-rung ladder in scenarios.py), layered on the POC diagnostic
arm and propagated through the calibrated ensemble:
  - care-seeking      CARE_SEEKING       (care_seek_mult on NG/CT/TV p_symp_care)
  - partner notif.    PN_INTENSITY       (pn_pars)
  - bundled prev.     BUNDLED_PREVENTION (CondomCounseling coverage)

Cells:
  SOC                          syndromic dx, all levers baseline (the reference)
  POC_c{C}_p{P}_b{B}           POC dx, 5 x 5 x 5 = 125 cells
                               (c=baseline,p=baseline,b=none is "POC plain")
Total 126 distinct cells x N_DRAWS x N_SEEDS sims. One JSON row per
(cell, draw, seed) -> results/scenarios.jsonl.

Run (repo root, `starsim` conda env, multi-core box):
    conda run -n starsim env N_SEEDS=1 N_WORKERS=60 python run_scenarios.py

Quick smoke test (few cells, small pop, 1 draw):
    conda run -n starsim env SMOKE=1 python run_scenarios.py

Prerequisite: DRAWS must point at the ACTIVE calibration baseline -- NG/CT/TV/
syph all sustaining AND calibrated with the BV-in-VDS model. Override with the
DRAWS env var. Endpoints summed over 2027-2040; POC + bundled prevention switch
on at intv_year (2027).
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
os.environ.setdefault('NUMEXPR_NUM_THREADS', '1')

import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import starsim as ss

REPO = Path(__file__).resolve().parent
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
for p in (str(REPO), str(SCRIPTS)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC, CondomCounseling       # noqa
from scenarios import CARE_SEEKING, PN_INTENSITY, BUNDLED_PREVENTION  # noqa

OUT = REPO / 'results'
INTV_YEAR = 2027
END_YEAR = 2040
N_AGENTS = 10_000

DRAWS_CSV = Path(os.environ.get(
    'DRAWS',
    REPO / 'experiments' / '03_2026-06-22_calibration_bv_in_vds' / 'outputs' / 'draws_used.csv'))


def build_cells():
    """SOC reference + POC 5x5x5 factorial (126 distinct cells)."""
    cells = [dict(label='SOC', poc=None, care='baseline', pn='baseline', bp='none')]
    for c in CARE_SEEKING:
        for p in PN_INTENSITY:
            for b in BUNDLED_PREVENTION:
                cells.append(dict(label=f'POC_c-{c}_p-{p}_b-{b}',
                                  poc=True, care=c, pn=p, bp=b))
    return cells


def build_sim(cell, seed, sim_pars):
    sim = make_sim(seed=seed, start=1985, stop=END_YEAR, n_agents=N_AGENTS,
                   poc=cell['poc'], pn_pars=PN_INTENSITY[cell['pn']],
                   care_seek_mult=CARE_SEEKING[cell['care']],
                   fetal_health=True, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    if cell['bp'] != 'none':
        bp = BUNDLED_PREVENTION[cell['bp']]
        cond = CondomCounseling(coverage=bp['coverage'], eff=bp['eff'],
                                dur=ss.months(bp['dur_months']), start=INTV_YEAR)
        sim.pars['interventions'] = list(sim.pars['interventions']) + [cond]
    return sim


def _wsum(res, yv):
    v = np.asarray(res.values)
    m = (yv >= INTV_YEAR) & (yv <= END_YEAR)
    return float(np.nansum(v[m]))


def extract(sim, cell, draw, seed):
    yv = np.array([t.year for t in sim.t.timevec])
    row = dict(cell=cell['label'], care=cell['care'], pn=cell['pn'], bp=cell['bp'],
               poc=bool(cell['poc']), draw=int(draw), seed=int(seed), status='ok')
    for d in ('hiv', 'ng', 'ct', 'tv', 'syph'):
        dr = sim.results.get(d)
        if dr is None:
            continue
        if 'new_infections' in dr:
            row[f'{d}_new_inf'] = _wsum(dr['new_infections'], yv)
        if 'prevalence' in dr:
            row[f'{d}_prev_end'] = float(dr.prevalence.values[-1])
        for k in ('new_treated', 'new_treated_success', 'new_treated_unnecessary'):
            if k in dr:
                row[f'{d}_{k}'] = _wsum(dr[k], yv)
    pn = sim.interventions.get('pn')
    if pn is not None:
        for k in ('new_notified', 'new_attending'):
            if k in pn.results:
                row[f'pn_{k}'] = _wsum(pn.results[k], yv)
    fh = sim.results.get('fetal_health')
    if fh is not None:
        for k in ('n_lbw', 'n_sga', 'n_svn', 'n_births'):
            if k in fh:
                row[f'fh_{k}'] = _wsum(fh[k], yv)
    sr = sim.results.get('syph')
    if sr is not None and 'new_congenital' in sr:
        row['syph_new_congenital'] = _wsum(sr['new_congenital'], yv)
    return row


def run_one(task):
    try:
        sim = build_sim(task['cell'], task['seed'], task['sim_pars'])
        sim.run()
        return extract(sim, task['cell'], task['draw'], task['seed'])
    except Exception as e:
        return dict(cell=task['cell']['label'], draw=int(task['draw']),
                    seed=int(task['seed']), status=f'error: {type(e).__name__}: {e}')


def main():
    global N_AGENTS
    smoke = os.environ.get('SMOKE')
    n_seeds = int(os.environ.get('N_SEEDS', 1))
    n_workers = int(os.environ.get('N_WORKERS', 60))
    OUT.mkdir(parents=True, exist_ok=True)
    if not DRAWS_CSV.exists():
        raise SystemExit(f'draws not found: {DRAWS_CSV} (set DRAWS env var)')
    draws = pd.read_csv(DRAWS_CSV)
    cells = build_cells()
    outfile = OUT / 'scenarios.jsonl'

    if smoke:
        # minimal wiring check: a spanning handful of cells, 1 draw, small pop.
        N_AGENTS = int(os.environ.get('N_AGENTS', 2000))
        keep = {'SOC', 'POC_c-baseline_p-baseline_b-none',
                'POC_c-maximum_p-baseline_b-none',
                'POC_c-baseline_p-maximum_b-none',
                'POC_c-baseline_p-baseline_b-maximum',
                'POC_c-maximum_p-maximum_b-maximum'}
        cells = [c for c in cells if c['label'] in keep]
        draws = draws.head(1)
        n_seeds, n_workers = 1, min(6, n_workers)
        outfile = OUT / 'scenarios_smoke.jsonl'
    else:
        n_draws_env = os.environ.get('N_DRAWS')
        if n_draws_env:
            draws = draws.head(int(n_draws_env))

    tasks = []
    for _, r in draws.iterrows():
        di = int(r['draw_idx'])
        sp = row_to_sim_pars(r.to_dict())
        for s in range(n_seeds):
            for cell in cells:
                tasks.append(dict(cell=cell, draw=di, seed=s, sim_pars=sp))
    print(f'[scenarios] {len(cells)} cells x {len(draws)} draws x {n_seeds} seeds '
          f'= {len(tasks)} sims | n_agents={N_AGENTS} | draws={DRAWS_CSV.name}'
          f'{" | SMOKE" if smoke else ""}', flush=True)

    t0 = time.time()
    n_ok = n_err = 0
    with mp.Pool(n_workers, maxtasksperchild=5) as pool, outfile.open('w') as f:
        for i, res in enumerate(pool.imap_unordered(run_one, tasks, chunksize=1), 1):
            f.write(json.dumps(res) + '\n')
            f.flush()
            if res.get('status') == 'ok':
                n_ok += 1
            else:
                n_err += 1
                if n_err <= 10:
                    print(f'  ERR {res.get("cell")} draw {res.get("draw")}: '
                          f'{res.get("status")}', flush=True)
            if i % 20 == 0 or i == len(tasks):
                el = time.time() - t0
                eta = (len(tasks) - i) * el / max(i, 1)
                print(f'  [{i}/{len(tasks)}] {el:.0f}s eta={eta:.0f}s '
                      f'ok={n_ok} err={n_err}', flush=True)
    print(f'[scenarios] done in {time.time()-t0:.0f}s. ok={n_ok} err={n_err} -> {outfile}')


if __name__ == '__main__':
    main()
