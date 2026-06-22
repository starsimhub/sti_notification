"""Exp 07 — PN × condom combined grid (POC arm, CT, draw 773, 1 seed).

3×3 grid: PN multiplier {1,3,8} × condom coverage {0,0.5,1.0}. Tests
whether the two orthogonal levers (exp 05/06) combine to push CT
prevalence AND incidence down together.

Output: outputs/grid.csv, printed table.
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
import starsim as ss

THIS = Path(__file__).resolve()
HERE = THIS.parent
REPO = THIS.parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
EXP04 = REPO / 'experiments' / '04_soc_vs_poc_pn_wiring'
EXP06 = REPO / 'experiments' / '06_condom_ladder'
for p in (str(REPO), str(SCRIPTS), str(EXP04), str(EXP06)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from tracer import STIChainTracer                                     # noqa
from cond import CondomCounseling                                     # noqa

DRAWS_CSV = REPO / 'experiments' / '03_calibration_rc1.5.7' / 'outputs' / 'draws_used.csv'
OUT = HERE / 'outputs'

BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}
PN_MULTS = [1, 3, 8]
COVERAGES = [0.0, 0.5, 1.0]
EFF = 0.5


def pn_pars_for(mult, attend_cap=0.99):
    notify = {k: min(v * mult, 1.0) for k, v in BASELINE_NOTIFY.items()}
    attend = {e: {s: min(v * mult, attend_cap) for s, v in sr.items()}
              for e, sr in BASELINE_ATTEND.items()}
    return dict(notify_rates=notify, attendance_rates=attend)


def cohort_reinf_rate(tx, trans, cohort_size, followup):
    succ = tx[tx.outcome == 'success']
    if len(succ) == 0:
        return float('nan')
    first = (succ.groupby('uid', as_index=False).ti.min()
             .sort_values('ti').head(cohort_size))
    reinf = sum(len(trans[(trans.target == u) & (trans.ti > t0) &
                          (trans.ti <= t0 + followup)]) > 0
                for u, t0 in zip(first.uid, first.ti))
    return reinf / len(first)


def run_cell(mult, coverage, sim_pars, seed, n_agents, start, stop,
             window, cohort_size, followup):
    tracer = STIChainTracer(disease='ct', tx_name='ct_tx', window=window)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   poc=True, pn_pars=pn_pars_for(mult), fetal_health=False,
                   verbose=0, syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    if coverage > 0:
        cond = CondomCounseling(coverage=coverage, eff=EFF,
                                dur=ss.months(6), start=2027)
        sim.pars['interventions'] = list(sim.pars['interventions']) + [cond]
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    sim.init()
    sim.run()

    yv = np.array([t.year for t in sim.t.timevec])
    lo, hi = window
    wm = (yv >= lo) & (yv < hi)
    dr = sim.results['ct']
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    trans = pd.DataFrame(tracer.trans_events,
                         columns=['ti', 'source', 'target', 'src_cat'])
    return dict(
        pn_mult=mult, condom_cov=coverage,
        ct_prev_window_mean=float(np.nanmean(np.asarray(dr.prevalence.values)[wm])),
        ct_new_inf_window=float(np.nansum(np.asarray(dr['new_infections'].values)[wm])),
        cohort_reinf_rate=cohort_reinf_rate(tx, trans, cohort_size, followup),
    )


def main():
    draw_idx = int(os.environ.get('DRAW', 773))
    seed = int(os.environ.get('SEED', 0))
    n_agents, start, stop = 10_000, 1985, 2040
    window = (2030, 2034); cohort_size, followup = 100, 12

    OUT.mkdir(parents=True, exist_ok=True)
    draws = pd.read_csv(DRAWS_CSV)
    sim_pars = row_to_sim_pars(draws[draws.draw_idx == draw_idx].iloc[0].to_dict())
    print(f'[exp07] PN×condom grid, draw={draw_idx} seed={seed}', flush=True)

    rows = []
    for mult in PN_MULTS:
        for cov in COVERAGES:
            print(f'[exp07] === PN×{mult}, condom {cov} ===', flush=True)
            row = run_cell(mult, cov, sim_pars, seed, n_agents, start, stop,
                           window, cohort_size, followup)
            rows.append(row)
            print(f'[exp07]   prev={row["ct_prev_window_mean"]:.3f} '
                  f'inc={row["ct_new_inf_window"]:,.0f} '
                  f'reinf={row["cohort_reinf_rate"]:.2f}', flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'grid.csv', index=False)
    print('\n[exp07] === PREVALENCE grid (rows=PN, cols=condom cov) ===')
    print(df.pivot(index='pn_mult', columns='condom_cov',
                   values='ct_prev_window_mean').round(3))
    print('\n[exp07] === INCIDENCE grid (millions) ===')
    print((df.pivot(index='pn_mult', columns='condom_cov',
                    values='ct_new_inf_window') / 1e6).round(2))
    print('[exp07] done.')


if __name__ == '__main__':
    main()
