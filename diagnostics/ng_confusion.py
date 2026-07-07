"""NG detection 2x2 in women (VDS pathway), SOC vs POC -> PPV/NPV/FDR/FOR.

The 'test' is the care-pathway treatment decision for NG among women who present
with vaginal discharge (symptomatic + seeking care). For each female presenter
we record her true NG status (infected = treatable) and whether she ends up
treated for NG (ng_tx fires within 3 steps of presenting). That gives the 2x2:

  TP infected & treated   FP not-infected & treated
  FN infected & not       TN not-infected & not

from which PPV = TP/(TP+FP), NPV = TN/(TN+FN), FDR = FP/(TP+FP) = 1-PPV,
FOR = FN/(TN+FN) = 1-NPV.

SOC (syndromic) vs POC-plain (panel), draw 263 x 5 seeds, presentations 2027-40.

    conda run -n starsim python diagnostics/ng_confusion.py
"""
from __future__ import annotations

import os, sys, multiprocessing as mp
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
from pathlib import Path
import numpy as np, pandas as pd
import starsim as ss

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / 'calibration' / 'artifacts' / 'scripts')):
    sys.path.insert(0, p)
os.chdir(REPO)
from _pipeline import row_to_sim_pars, set_pars_local  # noqa
from model import make_sim                             # noqa
from scenarios import PN_INTENSITY                     # noqa

DRAWS = REPO / 'experiments' / '06_2026-06-24_kseed_calibration' / 'outputs' / 'draws_used.csv'
N_SEEDS = 5
MATCH = 1   # treatment is deferred one step; tight window avoids cross-episode leakage
ARMS = {'SOC': dict(poc=None), 'POC': dict(poc=True)}


class NGConfusion(ss.Analyzer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.presenters = []      # (ti, uid, ng_infected)
        self.ng_treat = {}        # uid -> list of ti treated

    def step(self):
        sim = self.sim
        if sim.now < 2027 or sim.now > 2040:
            return
        d = sim.diseases
        female = sim.people.female
        present = ss.uids()
        for dis in ('ng', 'ct', 'tv', 'bv'):
            m = d[dis]
            present = present | (m.symptomatic & (m.ti_seeks_care == m.ti) & female).uids
        # 'treatable' = infected OR exposed/incubating -- this is what the test
        # and treatment act on, so it's the correct "true positive" status.
        ngpos = d.ng.treatable
        ti = self.ti
        for u in present:
            self.presenters.append((ti, int(u), bool(ngpos[u])))
        ng_tx = sim.interventions.get('ng_tx')
        if ng_tx is not None:
            for u in (ng_tx.ti_treated == ti).uids:
                self.ng_treat.setdefault(int(u), []).append(ti)

    def confusion(self):
        TP = FP = FN = TN = 0
        for ti, u, inf in self.presenters:
            tt = self.ng_treat.get(u, ())
            treated = any(ti <= t <= ti + MATCH for t in tt)
            if inf and treated: TP += 1
            elif inf and not treated: FN += 1
            elif (not inf) and treated: FP += 1
            else: TN += 1
        return dict(TP=TP, FP=FP, FN=FN, TN=TN)


def run_one(task):
    arm, seed, sp = task['arm'], task['seed'], task['sim_pars']
    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=10_000,
                   poc=ARMS[arm]['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [NGConfusion(name='ngconf')]
    sim.run()
    c = sim.analyzers.get('ngconf').confusion()
    return dict(arm=arm, seed=seed, **c)


def metrics(d):
    TP, FP, FN, TN = d['TP'], d['FP'], d['FN'], d['TN']
    ppv = TP / (TP + FP) if TP + FP else np.nan
    npv = TN / (TN + FN) if TN + FN else np.nan
    return dict(PPV=ppv, NPV=npv, FDR=1 - ppv, FOR=1 - npv)


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict(); sp = row_to_sim_pars(r0); di = int(r0['draw_idx'])
    tasks = [dict(arm=a, seed=di * 1000 + s, sim_pars=sp) for a in ARMS for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {len(tasks)} sims, NG detection 2x2 in women', flush=True)
    with mp.Pool(len(tasks)) as pool:
        res = pool.map(run_one, tasks)
    df = pd.DataFrame(res)
    df.to_csv(REPO / 'results' / 'ng_confusion.csv', index=False)

    print(f'\n{"":6s}{"PPV":>8s}{"NPV":>8s}{"FDR":>8s}{"FOR":>8s}   (mean over 5 seeds; TP/FP/FN/TN summed)')
    for arm in ARMS:
        d = df[df.arm == arm]
        agg = {k: int(d[k].sum()) for k in ('TP', 'FP', 'FN', 'TN')}
        m = metrics(agg)
        print(f'{arm:6s}' + ''.join(f'{100*m[k]:7.1f}%' for k in ('PPV', 'NPV', 'FDR', 'FOR'))
              + f'   TP={agg["TP"]} FP={agg["FP"]} FN={agg["FN"]} TN={agg["TN"]}', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
