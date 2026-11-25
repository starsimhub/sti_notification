"""Attribute POC-arm unnecessary syphilis treatments to their triggering test.

'Unnecessary' (STITreatment: treated while susceptible = a false-positive test
result) for syph_tx is fed by several channels in the POC arm. This runs the
POC-plain cell for one calibrated draw x 5 seeds (K=5) and, each step in
2027-40, assigns every unnecessarily-treated agent to the pathway whose test
flagged them positive this step (priority: ANC -> PN -> ulcer -> rash).

    conda run -n starsim python diagnostics/syph_unnec.py
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
# Treatment-triggering tests grouped by pathway, in priority order.
PATHWAYS = [
    ('anc',   ['syph_anc_confirm', 'syph_anc_rpr', 'syph_anc_rdt']),
    ('pn',    ['syph_pn_test']),
    ('ulcer', ['syph_symp_test_poc', 'syph_symp_test']),
    ('rash',  ['syph_rash_test']),
]


class SyphUnnecAttribution(ss.Analyzer):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.counts = dict(total=0, anc=0, pn=0, ulcer=0, rash=0, other=0)

    def step(self):
        sim = self.sim
        yr = sim.now
        if yr < 2027 or yr > 2040:
            return
        tx = sim.interventions.get('syph_tx')
        if tx is None or 'syph' not in getattr(tx, 'outcomes', {}):
            return
        unnec = tx.outcomes['syph'].get('unnecessary', ss.uids())
        if not len(unnec):
            return
        self.counts['total'] += len(unnec)
        remaining = unnec
        for name, tests in PATHWAYS:
            pos = ss.uids()
            for tn in tests:
                t = sim.interventions.get(tn)
                if t is not None and hasattr(t, 'ti_positive'):
                    pos = pos | (t.ti_positive == t.ti).uids
            hit = remaining & pos
            self.counts[name] += len(hit)
            remaining = remaining.remove(hit)
        self.counts['other'] += len(remaining)


def run_one(task):
    sim = make_sim(seed=task['seed'], start=1985, stop=2040, n_agents=10_000,
                   poc=True, pn_pars=PN_INTENSITY['baseline'], care_seek_mult=1.0,
                   fetal_health=False, verbose=-1)
    set_pars_local(sim, task['sim_pars'])
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [SyphUnnecAttribution(name='syph_unnec')]
    sim.run()
    return sim.analyzers.get('syph_unnec').counts


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict()
    sp = row_to_sim_pars(r0)
    di = int(r0['draw_idx'])
    tasks = [dict(seed=di * 1000 + s, sim_pars=sp) for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {N_SEEDS} seeds, POC-plain, attributing 2027-40 syph unnecessary tx', flush=True)
    with mp.Pool(N_SEEDS) as pool:
        res = pool.map(run_one, tasks)

    df = pd.DataFrame(res)
    mean = df.mean()
    tot = mean['total']
    print('\n=== unnecessary syph treatments 2027-40 (mean over 5 seeds, cumulative counts) ===')
    print(f'  total: {tot:,.0f}')
    for k in ('anc', 'pn', 'ulcer', 'rash', 'other'):
        print(f'  {k:6s}: {mean[k]:>10,.0f}  ({100*mean[k]/tot:5.1f}%)')
    print('\nper-seed totals:', [int(x) for x in df.total])


if __name__ == '__main__':
    main()
