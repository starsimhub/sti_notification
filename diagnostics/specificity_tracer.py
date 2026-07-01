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


class SocOvertreatmentTracer(ss.Analyzer):
    """SOC-only: per VDS-presenting woman, count (n_drugs, n_actual_STIs).

    Drugs counted: ng_tx, ct_tx, metronidazole (the syndromic_vds routing set;
    syph_tx doesn't fire from VDS in practice). Actual STIs: NG/CT/TV/syph
    (BV excluded -- BV is not an STI, and a BV-only VDS woman getting
    metronidazole shows here as n_drugs=1, n_stis=0).

    Only active while syndromic_vds is running (SOC arm, or POC pre-intv_year).
    Aggregates into a (n_drugs, n_stis_bucket) counter with buckets {0, 1, 2+}.
    """
    _DRUGS = ('ng_tx', 'ct_tx', 'metronidazole')
    _DISEASE_TX = (('ng', 'ng_tx'), ('ct', 'ct_tx'),
                   ('tv', 'metronidazole'), ('syph', 'syph_tx'))

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # counts[(n_drugs, n_stis_bucket)] -> int
        self.counts = {}

    def step(self):
        sim = self.sim
        if sim.now < 2027 or sim.now > 2040:
            return
        vds = sim.interventions.get('syndromic_vds')
        if vds is None or not hasattr(vds, 'ti_tested'):
            return
        ti = self.ti
        # Snapshot of women SyndromicManagement.step actually routed this ti.
        # Cannot re-invoke vds.eligibility() -- successful treatments clear
        # disease.symptomatic in the same step, so the callable would miss
        # treated women.
        elig_f = (vds.ti_tested == ti).uids
        if len(elig_f) == 0:
            return
        f = sim.people.female
        # Belt-and-braces: syndromic_vds's eligibility already restricts to
        # females, but filter again in case the pattern changes.
        elig_f = elig_f[f[elig_f]]
        if len(elig_f) == 0:
            return
        elig_arr = np.asarray(elig_f)
        n = len(elig_arr)

        # Drug-fired flags per woman
        got = np.zeros((len(self._DRUGS), n), dtype=bool)
        for i, txn in enumerate(self._DRUGS):
            tx = sim.interventions.get(txn)
            if tx is None:
                continue
            fired = np.asarray((tx.ti_treated == ti).uids)
            got[i] = np.isin(elig_arr, fired)
        n_drugs = got.sum(axis=0)  # {0..3}

        # Actual-STI flags per woman: from tx.outcomes (frozen pre-clearance)
        # for treated diseases; disease.infected for untreated.
        has_sti = np.zeros((len(self._DISEASE_TX), n), dtype=bool)
        for i, (d, txn) in enumerate(self._DISEASE_TX):
            tx = sim.interventions.get(txn)
            had_from_tx = ss.uids()
            if tx is not None:
                out = getattr(tx, 'outcomes', None)
                if out is not None and d in out and hasattr(out[d], 'get'):
                    had_from_tx = (out[d].get('successful', ss.uids())
                                   | out[d].get('unsuccessful', ss.uids()))
            in_tx = np.isin(elig_arr, np.asarray(had_from_tx))
            dis = sim.diseases.get(d)
            if dis is not None and hasattr(dis, 'infected'):
                inf = np.asarray(dis.infected[elig_f])
                has_sti[i] = in_tx | inf
            else:
                has_sti[i] = in_tx
        n_stis = has_sti.sum(axis=0)  # {0..4}
        n_stis_bucket = np.minimum(n_stis, 2)  # {0, 1, 2+}

        for nd, ns in zip(n_drugs.tolist(), n_stis_bucket.tolist()):
            key = (int(nd), int(ns))
            self.counts[key] = self.counts.get(key, 0) + 1


def run_one(task):
    arm, seed, sp = task['arm'], task['seed'], task['sim_pars']
    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=10_000,
                   poc=ARMS[arm]['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1)
    set_pars_local(sim, sp)
    analyzers = [SpecAttribution(name='spec'),
                 SocOvertreatmentTracer(name='soc_ot')]
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + analyzers
    sim.run()
    spec = sim.analyzers.get('spec').c
    ot = sim.analyzers.get('soc_ot').counts
    return dict(arm=arm, seed=seed, spec=spec, ot=ot)


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict(); sp = row_to_sim_pars(r0); di = int(r0['draw_idx'])
    tasks = [dict(arm=a, seed=di * 1000 + s, sim_pars=sp) for a in ARMS for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {len(tasks)} sims, person-level specificity', flush=True)
    with mp.Pool(len(tasks)) as pool:
        res = pool.map(run_one, tasks)
    spec_df = pd.DataFrame([dict(arm=r['arm'], seed=r['seed'], **r['spec'])
                            for r in res])
    spec_df.to_csv(REPO / 'results' / 'specificity.csv', index=False)
    # SOC overtreatment contingency table (SOC arm only; POC counts = 0
    # because syndromic_vds is a no-op after intv_year in POC).
    ot_rows = []
    for r in res:
        if r['arm'] != 'SOC':
            continue
        for (nd, ns), c in r['ot'].items():
            ot_rows.append(dict(arm=r['arm'], seed=r['seed'],
                                n_drugs=nd, n_stis_bucket=ns, count=c))
    ot_df = pd.DataFrame(ot_rows)
    ot_df.to_csv(REPO / 'results' / 'soc_overtreatment.csv', index=False)
    for arm in ARMS:
        d = spec_df[spec_df.arm == arm]
        ftx, fov = d.f_tx.mean(), d.f_tx_over.mean()
        mtx, mov = d.m_tx.mean(), d.m_tx_over.mean()
        print(f'\n{arm}: female treated over (no STI): {100*fov/ftx:.0f}%  ({fov:.0f}/{ftx:.0f})', flush=True)
        print(f'{arm}: male treated over (no STI):   {100*mov/mtx:.0f}%  ({mov:.0f}/{mtx:.0f})', flush=True)
    print('\nSOC overtreatment contingency (aggregated across seeds):')
    if len(ot_df):
        agg = ot_df.groupby(['n_drugs', 'n_stis_bucket'])['count'].sum().unstack(fill_value=0)
        print(agg)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
