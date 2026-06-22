"""
Ensemble scenario run: PN-intensity ladder + bundled-prevention ladder + SOC
reference, propagated through the sustained calibration ensemble.

10 cells x N_DRAWS x N_SEEDS sims. Each cell is one (poc, PN intensity,
bundled-prevention) combination, layered on a calibrated draw. Per-(cell, draw,
seed) endpoints are written to outputs/results.jsonl.

The 10 cells (see scenarios.py for the ladders):
  SOC                  syndromic dx, baseline PN, no bundled prevention
  POC_pn_baseline      POC dx, baseline PN              | the POC reference
  POC_pn_low/.../maximum   POC dx, PN intensity ladder  | (BP none)
  POC_bp_low/.../maximum   POC dx, baseline PN, BP ladder

Run (from repo root, in the `starsim` conda env):
    conda run -n starsim env N_SEEDS=1 N_WORKERS=60 \
        python experiments/08_pn_bp_scenarios/run.py

Prerequisite: DRAWS_CSV must point at the ACTIVE calibration baseline, which
must (a) have NG/CT/TV/syphilis all sustaining and (b) have been calibrated
with the BV-in-VDS model (re-fire calibration after the BV edit). Override the
path with the DRAWS env var if the re-fired ensemble lands in a new folder.

Caveat: PN intensity and bundled prevention are applied for the whole sim;
the POC switch happens at intv_year (2027); endpoints are summed over
2027-2040. This matches exps 05-07. A strict from-2027 counterfactual would
gate PN intensity at 2027 too; deferred.
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

THIS = Path(__file__).resolve()
HERE = THIS.parent
REPO = THIS.parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
EXP06 = REPO / 'experiments' / '06_condom_ladder'   # CondomCounseling (the rel_sus lever)
for p in (str(REPO), str(SCRIPTS), str(EXP06)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from cond import CondomCounseling                                     # noqa
from scenarios import PN_INTENSITY, BUNDLED_PREVENTION                # noqa

OUT = HERE / 'outputs'
INTV_YEAR = 2027
END_YEAR = 2040
N_AGENTS = 10_000

# Active calibration baseline. Override with the DRAWS env var after re-firing.
DRAWS_CSV = Path(os.environ.get(
    'DRAWS',
    REPO / 'experiments' / '04_calibration_per_disease_sustain' / 'outputs' / 'draws_used.csv'))


def build_cells():
    cells = [dict(label='SOC', poc=None, pn='baseline', bp='none')]
    for lvl in PN_INTENSITY:                      # baseline, low, moderate, high, maximum
        cells.append(dict(label=f'POC_pn_{lvl}', poc=True, pn=lvl, bp='none'))
    for lvl in BUNDLED_PREVENTION:
        if lvl == 'none':
            continue                              # == POC_pn_baseline (no duplicate cell)
        cells.append(dict(label=f'POC_bp_{lvl}', poc=True, pn='baseline', bp=lvl))
    return cells


def build_sim(cell, seed, sim_pars):
    sim = make_sim(seed=seed, start=1985, stop=END_YEAR, n_agents=N_AGENTS,
                   poc=cell['poc'], pn_pars=PN_INTENSITY[cell['pn']],
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
    row = dict(cell=cell['label'], pn=cell['pn'], bp=cell['bp'],
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
    n_seeds = int(os.environ.get('N_SEEDS', 1))
    n_workers = int(os.environ.get('N_WORKERS', 60))
    OUT.mkdir(parents=True, exist_ok=True)
    if not DRAWS_CSV.exists():
        raise SystemExit(f'draws not found: {DRAWS_CSV} (set DRAWS env var)')
    draws = pd.read_csv(DRAWS_CSV)
    cells = build_cells()
    tasks = []
    for _, r in draws.iterrows():
        di = int(r['draw_idx'])
        sp = row_to_sim_pars(r.to_dict())
        for s in range(n_seeds):
            for cell in cells:
                tasks.append(dict(cell=cell, draw=di, seed=s, sim_pars=sp))
    print(f'[exp08] {len(cells)} cells x {len(draws)} draws x {n_seeds} seeds '
          f'= {len(tasks)} sims | draws={DRAWS_CSV}', flush=True)

    out = OUT / 'results.jsonl'
    t0 = time.time()
    n_ok = n_err = 0
    with mp.Pool(n_workers, maxtasksperchild=5) as pool, out.open('w') as f:
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
    print(f'[exp08] done in {time.time()-t0:.0f}s. ok={n_ok} err={n_err} -> {out}')


if __name__ == '__main__':
    main()
