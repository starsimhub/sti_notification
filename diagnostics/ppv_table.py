"""PPV of NG/CT/TV treatment in women, SOC vs POC, overall vs among VDS.

For each disease and arm, over 2027-40 on a scenario draw (263) x 5 seeds:
  - prevalence overall   (treatable among adult women 15-49)
  - prevalence among VDS (treatable among women symptomatic for ng/ct/tv/bv)
  - PPV overall          (of all female D-treatments, fraction truly infected)
  - PPV among VDS        (restricted to treatments via the VDS care pathway:
                          woman sought VDS care within 2 steps of treatment)

PPV = (treated & treatable) / treated. 'treatable' = infected or incubating.

    conda run -n starsim python diagnostics/ppv_table.py
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
AGE = (15, 49)
DIS = [('ng', 'ng_tx'), ('ct', 'ct_tx'), ('tv', 'metronidazole')]
VDS = ('ng', 'ct', 'tv', 'bv')   # vaginal-discharge-causing
ARMS = {'SOC': dict(poc=None), 'POC': dict(poc=True)}


class PPVTable(ss.Analyzer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        z = lambda: {d: 0 for d, _ in DIS}
        self.n_adult = 0; self.n_vds = 0
        self.prev_all = z(); self.prev_vds = z()
        self.tx_all = z(); self.tp_all = z()
        self.tx_vds = z(); self.tp_vds = z()

    def step(self):
        sim = self.sim
        if sim.now < 2027 or sim.now > 2040:
            return
        ppl = sim.people; d = sim.diseases; ti = self.ti
        adult = ppl.female & (ppl.age >= AGE[0]) & (ppl.age <= AGE[1])
        symp_any = adult.copy()
        symp_any[:] = False
        for dis in VDS:
            symp_any = symp_any | (d[dis].symptomatic & adult)
        self.n_adult += int(adult.sum())
        self.n_vds += int(symp_any.sum())
        for dz, _ in DIS:
            tb = d[dz].treatable
            self.prev_all[dz] += int((tb & adult).sum())
            self.prev_vds[dz] += int((tb & symp_any).sum())
        # treatments this step -- read from tx.outcomes (frozen at treatment
        # time, BEFORE clear_infection runs), not from live treatable state.
        # TP = had infection (successful|unsuccessful); FP = unnecessary (susceptible).
        def recent_vds(uu):
            r = np.zeros(len(uu), bool)
            for dis in VDS:
                sc = d[dis].ti_seeks_care[uu]
                r |= (sc >= ti - 2) & (sc <= ti)
            return r
        for dz, txn in DIS:
            tx = sim.interventions.get(txn)
            out = getattr(tx, 'outcomes', None)
            if out is None or dz not in out:
                continue
            o = out[dz]
            tp = o.get('successful_f', ss.uids()) | o.get('unsuccessful_f', ss.uids())
            fp = o.get('unnecessary_f', ss.uids())
            treated = tp | fp
            if not len(treated):
                continue
            is_tp = np.isin(treated, tp)
            rv = recent_vds(treated)
            self.tx_all[dz] += len(treated); self.tp_all[dz] += int(is_tp.sum())
            self.tx_vds[dz] += int(rv.sum()); self.tp_vds[dz] += int((is_tp & rv).sum())


def run_one(task):
    arm, seed, sp = task['arm'], task['seed'], task['sim_pars']
    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=10_000,
                   poc=ARMS[arm]['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1)
    set_pars_local(sim, sp)
    a = PPVTable(name='ppv')
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [a]
    sim.run()
    row = dict(arm=arm, seed=seed, n_adult=a.n_adult, n_vds=a.n_vds)
    for dz, _ in DIS:
        row[f'{dz}_prev_all'] = a.prev_all[dz]
        row[f'{dz}_prev_vds'] = a.prev_vds[dz]
        row[f'{dz}_tx_all'] = a.tx_all[dz]; row[f'{dz}_tp_all'] = a.tp_all[dz]
        row[f'{dz}_tx_vds'] = a.tx_vds[dz]; row[f'{dz}_tp_vds'] = a.tp_vds[dz]
    return row


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict(); sp = row_to_sim_pars(r0); di = int(r0['draw_idx'])
    tasks = [dict(arm=a, seed=di * 1000 + s, sim_pars=sp) for a in ARMS for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {len(tasks)} sims, PPV table (overall vs VDS)', flush=True)
    with mp.Pool(len(tasks)) as pool:
        df = pd.DataFrame(pool.map(run_one, tasks))
    df.to_csv(REPO / 'results' / 'ppv_table.csv', index=False)

    def agg(arm):
        d = df[df.arm == arm].sum(numeric_only=True)
        out = {}
        for dz, _ in DIS:
            out[dz] = dict(
                prev_all=d[f'{dz}_prev_all'] / d['n_adult'],
                prev_vds=d[f'{dz}_prev_vds'] / d['n_vds'],
                ppv_all=d[f'{dz}_tp_all'] / max(d[f'{dz}_tx_all'], 1),
                ppv_vds=d[f'{dz}_tp_vds'] / max(d[f'{dz}_tx_vds'], 1))
        return out

    S, P = agg('SOC'), agg('POC')
    print('\nNG/CT/TV detection in women (draw 263 x 5 seeds, 2027-40)')
    print(f'{"":4s} {"prev":>6s} {"prev":>6s} | {"PPV overall":>22s} | {"PPV among VDS":>22s}')
    print(f'{"dis":4s} {"all":>6s} {"VDS":>6s} | {"SOC":>10s} {"POC":>10s} | {"SOC":>10s} {"POC":>10s}')
    for dz, _ in DIS:
        print(f'{dz.upper():4s} {100*S[dz]["prev_all"]:5.1f}% {100*S[dz]["prev_vds"]:5.1f}% | '
              f'{100*S[dz]["ppv_all"]:9.1f}% {100*P[dz]["ppv_all"]:9.1f}% | '
              f'{100*S[dz]["ppv_vds"]:9.1f}% {100*P[dz]["ppv_vds"]:9.1f}%', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
