"""
Two partner-notification slide follow-ups, from one SOC run (draw 773):
  1. Annual partner counts for women 15-30 (distinct partners over a year, by type).
  2. Unnecessary partner-notification rate: notifications whose index case had no
     true STI at treatment (treated for NG/CT/TV/syph while susceptible to all of
     them, e.g. BV-only or fully uninfected women over-treated under syndromic VDS).
"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import starsim as ss

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / 'calibration/artifacts/scripts')]
os.chdir(REPO)
from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV
from model import make_sim
from interventions import ANC_PROBS_REALISTIC

STI_TX = [('ng_tx', 'ng'), ('ct_tx', 'ct'), ('metronidazole', 'tv'), ('syph_tx', 'syph')]


class AnnualPartners(ss.Analyzer):
    def __init__(self, window=(2019, 2020), name='annual_partners', *a, **k):
        super().__init__(*a, **k); self.name = name; self.window = window
        self.partners = defaultdict(set)
        self.by = defaultdict(lambda: defaultdict(set))
        self.cohort = None

    def step(self):
        yr = self.sim.t.timevec[self.ti].year
        lo, hi = self.window
        if not (lo <= yr < hi):
            return
        ppl = self.sim.people; nw = self.sim.networks.structuredsexual
        if self.cohort is None:
            age = ppl.age.values
            m = ppl.female.values & ppl.alive.values & (age >= 15) & (age < 30)
            self.cohort = set(int(u) for u in ppl.uid[m])
        int2name = {int(v): k for k, v in nw.edge_types.items()}
        for a, b, e in zip(np.asarray(nw.p1), np.asarray(nw.p2),
                           np.asarray(nw.edges.edge_type)):
            a, b, nm = int(a), int(b), int2name.get(int(e))
            if a in self.cohort:
                self.partners[a].add(b); self.by[nm][a].add(b)
            if b in self.cohort:
                self.partners[b].add(a); self.by[nm][b].add(a)


class UnnecessaryPNCapture(ss.Analyzer):
    def __init__(self, window=(2010, 2020), name='unnec_pn', *a, **k):
        super().__init__(*a, **k); self.name = name; self.window = window
        self.no_sti_by_ti = {}

    def step(self):
        yr = self.sim.t.timevec[self.ti].year
        lo, hi = self.window
        if not (lo <= yr < hi):
            return
        intv = self.sim.interventions
        treated_all, treated_sti = set(), set()
        for tx_name, dis in STI_TX:
            tx = intv.get(tx_name)
            if tx is None:
                continue
            if hasattr(tx, 'ti_treated'):
                treated_all |= set(int(u) for u in (tx.ti_treated == tx.ti).uids)
            out = getattr(tx, 'outcomes', None)
            o = out.get(dis) if out is not None and hasattr(out, 'get') else None
            if o is not None:
                treated_sti |= set(int(u) for u in o.get('successful', ss.uids()))
                treated_sti |= set(int(u) for u in o.get('unsuccessful', ss.uids()))
        self.no_sti_by_ti[int(self.ti)] = treated_all - treated_sti


def main():
    draws = pd.read_csv('experiments/01_2026-06-15_calibration_rc1.5.7/outputs/draws_used.csv')
    sp = row_to_sim_pars(draws[draws.draw_idx == 773].iloc[0].to_dict())
    ap = AnnualPartners(window=(2019, 2020))
    up = UnnecessaryPNCapture(window=(2010, 2020))
    sim = make_sim(seed=0, start=1985, stop=2020, n_agents=10_000, poc=None,
                   pn_pars=None, fetal_health=False, verbose=0,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [ap, up]
    sim.init()
    sim.interventions.pn.trace_events = []
    sim.run()

    # --- 1. Annual partners ---
    cohort = ap.cohort or set()
    counts = np.array([len(ap.partners.get(u, ())) for u in cohort])
    def stats(arr):
        return (f'mean {arr.mean():.2f}, median {np.median(arr):.0f}, '
                f'IQR {np.percentile(arr,25):.0f}-{np.percentile(arr,75):.0f}, '
                f'max {arr.max()}, %0 {100*(arr==0).mean():.0f}, %>=2 {100*(arr>=2).mean():.0f}')
    print(f'[annual] women 15-30 in cohort: {len(cohort)}')
    print(f'[annual] distinct partners over 12 months (all): {stats(counts)}')
    active = counts[counts >= 1]
    if len(active):
        print(f'[annual] distinct partners (active, >=1): {stats(active)}')
    for nm in sim.networks.structuredsexual.edge_types:
        arr = np.array([len(ap.by[nm].get(u, ())) for u in cohort])
        if arr.sum() > 0:
            print(f'  type "{nm}": mean {arr.mean():.2f}, share with >=1 {100*(arr>=1).mean():.0f}%')

    # --- 2. Unnecessary notification rate ---
    pn = sim.interventions.pn
    dy = pd.DataFrame(pn.trace_events, columns=['ti', 'index', 'partner', 'notified', 'attended'])
    yv = {i: sim.t.timevec[i].year for i in dy.ti.unique()} if len(dy) else {}
    dy['yr'] = dy.ti.map(yv)
    notif = dy[(dy.notified == 1) & (dy.yr >= 2010) & (dy.yr < 2020)].copy()
    no_sti = up.no_sti_by_ti
    notif['idx_no_sti'] = [row.index in no_sti.get(int(row.ti), set())
                           for row in notif.itertuples()]
    n_tot = len(notif)
    n_unnec = int(notif.idx_no_sti.sum())
    print(f'\n[unnecessary PN] notifications 2010-2020: {n_tot}')
    if n_tot:
        print(f'[unnecessary PN] index had NO true STI: {n_unnec} ({100*n_unnec/n_tot:.0f}%)')
        # by edge type of the notifying partnership is not tracked here; report overall
    print('done.')


if __name__ == '__main__':
    main()
