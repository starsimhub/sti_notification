"""Exp 06 — condoms/counselling-for-diagnosed coverage ladder, POC + baseline PN.

Base arm: POC etiological dx + baseline PN (×1) on draw 773 (the common
base with exp 05 rung x1). Ladders the CondomCounseling coverage and
measures the CT dose-response. Comparable head-to-head with exp 05's PN
ladder from the same base.

Rungs: coverage 0.0, 0.25, 0.5, 0.75, 1.0 (eff=0.5, dur=6mo).
Output: outputs/ladder.csv, printed table.
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
HERE = THIS.parent
REPO = THIS.parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
EXP04 = REPO / 'experiments' / '04_soc_vs_poc_pn_wiring'
for p in (str(REPO), str(SCRIPTS), str(EXP04), str(HERE)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from tracer import STIChainTracer                                     # noqa
from cond import CondomCounseling                                     # noqa

DRAWS_CSV = REPO / 'experiments' / '03_calibration_rc1.5.7' / 'outputs' / 'draws_used.csv'
OUT = HERE / 'outputs'

COVERAGES = [0.0, 0.25, 0.5, 0.75, 1.0]
EFF = 0.5


def cohort_reinf_rate(tx, trans, cohort_size, followup):
    succ = tx[tx.outcome == 'success']
    if len(succ) == 0:
        return float('nan'), 0
    first = (succ.groupby('uid', as_index=False).ti.min()
             .sort_values('ti').head(cohort_size))
    reinf = 0
    for uid, t0 in zip(first.uid, first.ti):
        r = trans[(trans.target == uid) & (trans.ti > t0) & (trans.ti <= t0 + followup)]
        if len(r):
            reinf += 1
    return reinf / len(first), len(first)


def run_rung(coverage, draw_idx, seed, n_agents, start, stop,
             window, cohort_size, followup):
    draws = pd.read_csv(DRAWS_CSV)
    sim_pars = row_to_sim_pars(draws[draws.draw_idx == draw_idx].iloc[0].to_dict())
    tracer = STIChainTracer(disease='ct', tx_name='ct_tx', window=window)

    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   poc=True, pn_pars=None, fetal_health=False, verbose=0,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    cond = CondomCounseling(coverage=coverage, eff=EFF, dur=__import__('starsim').months(6),
                            start=2027)
    sim.pars['interventions'] = list(sim.pars['interventions']) + [cond]
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    sim.init()
    sim.run()

    yv = np.array([t.year for t in sim.t.timevec])
    lo, hi = window
    wm = (yv >= lo) & (yv < hi)

    def wsum(res):
        return float(np.nansum(np.asarray(res.values)[wm]))

    dr = sim.results['ct']
    cc = sim.interventions.get('condom_counseling')
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    trans = pd.DataFrame(tracer.trans_events,
                         columns=['ti', 'source', 'target', 'src_cat'])
    reinf_rate, ncoh = cohort_reinf_rate(tx, trans, cohort_size, followup)

    return dict(
        coverage=coverage,
        ct_prev_end=float(dr.prevalence.values[-1]),
        ct_prev_window_mean=float(np.nanmean(np.asarray(dr.prevalence.values)[wm])),
        ct_new_inf_window=wsum(dr['new_infections']),
        ct_tx_success_window=wsum(dr['new_treated_success']),
        mean_protected=float(np.nanmean(np.asarray(cc.results['n_protected'].values)[wm]))
        if cc is not None else 0.0,
        cohort_reinf_rate=reinf_rate, cohort_n=ncoh,
    )


def main():
    draw_idx = int(os.environ.get('DRAW', 773))
    seed = int(os.environ.get('SEED', 0))
    n_agents, start, stop = 10_000, 1985, 2040
    window = (2030, 2034); cohort_size, followup = 100, 12

    OUT.mkdir(parents=True, exist_ok=True)
    print(f'[exp06] condom ladder, draw={draw_idx} seed={seed} '
          f'n_agents={n_agents} window={window} eff={EFF}', flush=True)

    rows = []
    for cov in COVERAGES:
        print(f'[exp06] === coverage {cov} ===', flush=True)
        row = run_rung(cov, draw_idx, seed, n_agents, start, stop,
                       window, cohort_size, followup)
        rows.append(row)
        print(f'[exp06]   ct_prev={row["ct_prev_window_mean"]:.3f} '
              f'reinf={row["cohort_reinf_rate"]:.2f} '
              f'protected={row["mean_protected"]:,.0f}', flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'ladder.csv', index=False)
    print('\n[exp06] === CONDOM LADDER (CT, draw 773, POC+baseline PN) ===')
    with pd.option_context('display.width', 200,
                           'display.float_format', lambda v: f'{v:,.3f}'):
        print(df[['coverage', 'ct_prev_window_mean', 'ct_new_inf_window',
                  'cohort_reinf_rate', 'mean_protected']].to_string(index=False))
    print('[exp06] done.')


if __name__ == '__main__':
    main()
