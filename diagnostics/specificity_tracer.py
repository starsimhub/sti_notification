"""Person-level treatment/notification specificity, SOC vs POC.

The kavg PN/treatment 'over' metrics are per-disease and TV-blind, which
inflates the over-share (a CT+ woman false-positive for NG is counted 'over for
NG'; a TV+ index is counted 'no STI' because the metric omits TV). This measures
person-level specificity instead: a treated/notifying person is 'over' only if
they have NO STI at all -- not infected with NG, CT, TV, or syph (BV excluded).

Female-index -> male-partner direction. SOC vs POC-plain, draw 263 x 5 seeds,
2027-40. Writes results/specificity.csv (per arm/seed counts).

    conda run -n starsim python diagnostics/specificity_tracer.py
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
ARMS = {'SOC': dict(poc=None), 'POC': dict(poc=True)}
# tx -> disease state key for the "had a real STI" test (TV via metronidazole;
# BV deliberately omitted -- BV is not an STI).
TX_DISEASE = [('ng_tx', 'ng'), ('ct_tx', 'ct'), ('metronidazole', 'tv'), ('syph_tx', 'syph')]


class SpecAttribution(ss.Analyzer):
    """Per-step person-level: of those treated, who had no STI (any of
    ng/ct/tv/syph)? Split by sex. Also tracks PN attendees treated."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.c = {k: 0 for k in
                  ('f_tx', 'f_tx_over', 'm_tx', 'm_tx_over',
                   'pn_notified_m', 'pn_attend_m')}

    def step(self):
        sim = self.sim
        if sim.now < 2027 or sim.now > 2040:
            return
        ti = self.ti
        treated = ss.uids(); had_sti = ss.uids()
        for txn, dk in TX_DISEASE:
            tx = sim.interventions.get(txn)
            if tx is None:
                continue
            treated = treated | (tx.ti_treated == ti).uids
            out = getattr(tx, 'outcomes', None)
            if out is not None and dk in out and hasattr(out[dk], 'get'):
                had_sti = had_sti | out[dk].get('successful', ss.uids()) | out[dk].get('unsuccessful', ss.uids())
        over = treated.remove(had_sti)
        f = sim.people.female
        self.c['f_tx'] += int(f[treated].sum())
        self.c['m_tx'] += int((~f[treated]).sum())
        self.c['f_tx_over'] += int(f[over].sum())
        self.c['m_tx_over'] += int((~f[over]).sum())
        # PN volume to males (for stage-2 notification counts)
        pn = sim.interventions.get('pn')
        if pn is not None:
            for k, r in (('pn_notified_m', 'new_notified_m'), ('pn_attend_m', 'new_attending_m')):
                if r in pn.results:
                    self.c[k] += int(pn.results[r][ti])


def run_one(task):
    arm, seed, sp = task['arm'], task['seed'], task['sim_pars']
    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=10_000,
                   poc=ARMS[arm]['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [SpecAttribution(name='spec')]
    sim.run()
    a = sim.analyzers.get('spec').c
    return dict(arm=arm, seed=seed, **a)


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict(); sp = row_to_sim_pars(r0); di = int(r0['draw_idx'])
    tasks = [dict(arm=a, seed=di * 1000 + s, sim_pars=sp) for a in ARMS for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {len(tasks)} sims, person-level specificity', flush=True)
    with mp.Pool(len(tasks)) as pool:
        res = pool.map(run_one, tasks)
    df = pd.DataFrame(res)
    df.to_csv(REPO / 'results' / 'specificity.csv', index=False)
    for arm in ARMS:
        d = df[df.arm == arm]
        ftx, fov = d.f_tx.mean(), d.f_tx_over.mean()
        mtx, mov = d.m_tx.mean(), d.m_tx_over.mean()
        print(f'\n{arm}: female treated over (no STI): {100*fov/ftx:.0f}%  ({fov:.0f}/{ftx:.0f})', flush=True)
        print(f'{arm}: male treated over (no STI):   {100*mov/mtx:.0f}%  ({mov:.0f}/{mtx:.0f})', flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
