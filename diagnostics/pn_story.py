"""Capture the partner-notification story quantities from one SOC run (draw 66).

Caches to results/pn_story.json + results/pn_partner_counts.csv:
  - annual distinct partner counts by sex (adults 15-49)
  - per-index notification completeness (all / some / none of partners) -> UNDER-notification
  - of notifications / attendances: share where the index had no true STI -> OVER-notification / -attendance
  - of treatments: share given to someone with no STI -> OVER-treatment

    conda run -n starsim python diagnostics/pn_story.py
"""
from __future__ import annotations

import os, sys, json
os.environ.setdefault('OMP_NUM_THREADS', '1')
from collections import defaultdict
from pathlib import Path
import numpy as np
import pandas as pd
import starsim as ss

REPO = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(REPO), str(REPO / 'calibration/artifacts/scripts')]
os.chdir(REPO)
from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV
from model import make_sim
from interventions import ANC_PROBS_REALISTIC
from scenarios import PN_INTENSITY

DRAWS = REPO / 'experiments' / '03_2026-06-22_calibration_bv_in_vds' / 'outputs' / 'draws_used.csv'
DRAW = 66
PARTNER_WIN = (2024, 2025)     # annual distinct partners, a stable endemic year
PN_WIN = (2027, 2040)          # over/under notification window
STI_TX = [('ng_tx', 'ng'), ('ct_tx', 'ct'), ('metronidazole', 'tv'), ('syph_tx', 'syph')]


class AnnualPartnersBySex(ss.Analyzer):
    def __init__(self, window=PARTNER_WIN, name='annual_partners', *a, **k):
        super().__init__(*a, **k); self.name = name; self.window = window
        self.partners = defaultdict(set); self.sex = {}

    def step(self):
        yr = self.sim.t.timevec[self.ti].year
        lo, hi = self.window
        if not (lo <= yr < hi):
            return
        ppl = self.sim.people; nw = self.sim.networks.structuredsexual
        if not self.sex:
            age = ppl.age.values
            m = ppl.alive.values & (age >= 15) & (age < 50)
            for u in ppl.uid[m]:
                self.sex[int(u)] = 'f' if ppl.female.values[int(u)] else 'm'
        for a, b in zip(np.asarray(nw.p1), np.asarray(nw.p2)):
            a, b = int(a), int(b)
            if a in self.sex:
                self.partners[a].add(b)
            if b in self.sex:
                self.partners[b].add(a)


class UnnecCapture(ss.Analyzer):
    def __init__(self, window=PN_WIN, name='unnec', *a, **k):
        super().__init__(*a, **k); self.name = name; self.window = window
        self.no_sti_by_ti = {}; self.n_treated = 0; self.n_treated_no_sti = 0

    def step(self):
        yr = self.sim.t.timevec[self.ti].year
        lo, hi = self.window
        if not (lo <= yr < hi):
            return
        intv = self.sim.interventions
        treated_all, treated_sti = set(), set()
        for tx_name, dis in STI_TX:
            tx = intv.get(tx_name)
            if tx is None or not hasattr(tx, 'ti_treated'):
                continue
            treated_all |= set(int(u) for u in (tx.ti_treated == tx.ti).uids)
            out = getattr(tx, 'outcomes', None)
            o = out.get(dis) if out is not None and hasattr(out, 'get') else None
            if o is not None:
                treated_sti |= set(int(u) for u in o.get('successful', ss.uids()))
                treated_sti |= set(int(u) for u in o.get('unsuccessful', ss.uids()))
        no_sti = treated_all - treated_sti
        self.no_sti_by_ti[int(self.ti)] = no_sti
        self.n_treated += len(treated_all)
        self.n_treated_no_sti += len(no_sti)


def main():
    sp = row_to_sim_pars(pd.read_csv(DRAWS).query('draw_idx == @DRAW').iloc[0].to_dict())
    ap = AnnualPartnersBySex(); up = UnnecCapture()
    print(f'[pn_story] SOC sim draw {DRAW} ...', flush=True)
    sim = make_sim(seed=0, start=1985, stop=2040, n_agents=10_000, poc=None,
                   pn_pars=PN_INTENSITY['baseline'], fetal_health=False, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [ap, up]
    sim.init(); sim.interventions.pn.trace_events = []; sim.run()

    # --- partner counts by sex ---
    rows = [dict(uid=u, sex=s, n=len(ap.partners.get(u, ()))) for u, s in ap.sex.items()]
    pc = pd.DataFrame(rows)
    (REPO / 'results').mkdir(exist_ok=True)
    pc.to_csv(REPO / 'results' / 'pn_partner_counts.csv', index=False)

    # --- PN dyads, windowed ---
    pn = sim.interventions.pn
    dy = pd.DataFrame(pn.trace_events, columns=['ti', 'index', 'partner', 'notified', 'attended'])
    dy['yr'] = dy.ti.map({i: sim.t.timevec[i].year for i in dy.ti.unique()}) if len(dy) else None
    dy = dy[(dy.yr >= PN_WIN[0]) & (dy.yr < PN_WIN[1])].copy()

    # under-notification: per index, fraction of partners notified -> all/some/none
    g = dy.groupby(['ti', 'index'])
    frac = g.notified.mean()
    n_index = len(frac)
    under = dict(all=int((frac == 1).sum()), some=int(((frac > 0) & (frac < 1)).sum()),
                 none=int((frac == 0).sum()), n_index=n_index)

    # over-notification / -attendance: index had no STI at that ti
    no_sti = up.no_sti_by_ti
    dy['idx_no_sti'] = [row.index in no_sti.get(int(row.ti), set()) for row in dy.itertuples()]
    notif = dy[dy.notified == 1]; att = dy[dy.attended == 1]
    over = dict(n_notified=int(len(notif)), n_notified_no_sti=int(notif.idx_no_sti.sum()),
                n_attended=int(len(att)), n_attended_no_sti=int(att.idx_no_sti.sum()))
    overtx = dict(n_treated=up.n_treated, n_treated_no_sti=up.n_treated_no_sti)

    stats = dict(draw=DRAW, partner_win=PARTNER_WIN, pn_win=PN_WIN,
                 partner_median={s: float(pc[pc.sex == s].n.median()) for s in ('f', 'm')},
                 partner_mean={s: float(pc[pc.sex == s].n.mean()) for s in ('f', 'm')},
                 under=under, over=over, overtx=overtx)
    (REPO / 'results' / 'pn_story.json').write_text(json.dumps(stats, indent=2))

    print(json.dumps(stats, indent=2))
    print(f'over-notified: {100*over["n_notified_no_sti"]/max(over["n_notified"],1):.0f}% | '
          f'over-attended: {100*over["n_attended_no_sti"]/max(over["n_attended"],1):.0f}% | '
          f'over-treated: {100*overtx["n_treated_no_sti"]/max(overtx["n_treated"],1):.0f}% | '
          f'index notifying none: {100*under["none"]/max(under["n_index"],1):.0f}%')


if __name__ == '__main__':
    main()
