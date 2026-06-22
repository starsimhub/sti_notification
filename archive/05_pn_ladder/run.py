"""Exp 05 — PN intensity ladder (+ EPT), POC arm, CT.

Sweeps PN coverage upward on draw 773 (POC etiological arm) and measures
the CT dose-response: prevalence, incidence, cohort reinfection, and PN
reach. One EPT rung (treat every notified partner, attend→1.0) isolates
whether attendance is the binding leak.

Rungs (notify+attend multipliers on the baseline edge rates; attend cap
0.99 so the ladder isn't clipped early):
  x0 (no PN), x1, x2, x3, x5, x8, EPT (notify x5, attend=1.0)

Output: outputs/ladder.csv (one row per rung), printed table.

Env: SEEDS=1 (default), DRAW=773.
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
for p in (str(REPO), str(SCRIPTS), str(EXP04)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from tracer import STIChainTracer                                     # noqa

DRAWS_CSV = REPO / 'experiments' / '03_calibration_rc1.5.7' / 'outputs' / 'draws_used.csv'
OUT = HERE / 'outputs'

BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}

# (label, notify/attend multiplier, EPT?)
RUNGS = [('x0', 0, False), ('x1', 1, False), ('x2', 2, False),
         ('x3', 3, False), ('x5', 5, False), ('x8', 8, False),
         ('EPT', 5, True)]


def pn_pars_for(mult, ept, attend_cap=0.99):
    if mult == 0:
        return dict(notify_rates={'stable': 0.0, 'casual': 0.0},
                    attendance_rates={'stable': {'f': 0.0, 'm': 0.0},
                                      'casual': {'f': 0.0, 'm': 0.0}})
    notify = {k: min(v * mult, 1.0) for k, v in BASELINE_NOTIFY.items()}
    if ept:
        attend = {e: {s: 1.0 for s in sr} for e, sr in BASELINE_ATTEND.items()}
    else:
        attend = {e: {s: min(v * mult, attend_cap) for s, v in sr.items()}
                  for e, sr in BASELINE_ATTEND.items()}
    return dict(notify_rates=notify, attendance_rates=attend)


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


def run_rung(label, mult, ept, draw_idx, seed, n_agents, start, stop,
             window, cohort_size, followup):
    draws = pd.read_csv(DRAWS_CSV)
    sim_pars = row_to_sim_pars(draws[draws.draw_idx == draw_idx].iloc[0].to_dict())
    pn_pars = pn_pars_for(mult, ept)
    tracer = STIChainTracer(disease='ct', tx_name='ct_tx', window=window)

    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   poc=True, pn_pars=pn_pars, fetal_health=False, verbose=0,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    sim.init()
    sim.interventions.pn.trace_events = []
    sim.run()

    pn = sim.interventions.pn
    yv = np.array([t.year for t in sim.t.timevec])
    lo, hi = window
    wm = (yv >= lo) & (yv < hi)

    def wsum(res):
        return float(np.nansum(np.asarray(res.values)[wm]))

    dr = sim.results['ct']
    dyads = pd.DataFrame(pn.trace_events,
                         columns=['ti', 'index', 'partner', 'notified', 'attended'])
    if len(dyads):
        g = dyads.groupby(['ti', 'index'])
        mean_partners = float(g.size().mean())
        mean_notified = float(g['notified'].sum().mean())
    else:
        mean_partners = mean_notified = 0.0
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    trans = pd.DataFrame(tracer.trans_events,
                         columns=['ti', 'source', 'target', 'src_cat'])
    reinf_rate, ncoh = cohort_reinf_rate(tx, trans, cohort_size, followup)

    return dict(
        rung=label, mult=mult, ept=ept,
        ct_prev_end=float(dr.prevalence.values[-1]),
        ct_prev_window_mean=float(np.nanmean(np.asarray(dr.prevalence.values)[wm])),
        ct_new_inf_window=wsum(dr['new_infections']),
        ct_tx_success_window=wsum(dr['new_treated_success']),
        pn_notified_window=wsum(pn.results['new_notified']),
        pn_attending_window=wsum(pn.results['new_attending']),
        mean_partners_per_index=mean_partners,
        mean_notified_per_index=mean_notified,
        cohort_reinf_rate=reinf_rate, cohort_n=ncoh,
    )


def main():
    draw_idx = int(os.environ.get('DRAW', 773))
    seed = int(os.environ.get('SEED', 0))
    n_agents, start, stop = 10_000, 1985, 2040
    window = (2030, 2034); cohort_size, followup = 100, 12

    OUT.mkdir(parents=True, exist_ok=True)
    print(f'[exp05] PN ladder, draw={draw_idx} seed={seed} '
          f'n_agents={n_agents} window={window}', flush=True)

    rows = []
    for label, mult, ept in RUNGS:
        print(f'[exp05] === rung {label} (mult={mult} ept={ept}) ===', flush=True)
        row = run_rung(label, mult, ept, draw_idx, seed, n_agents, start, stop,
                       window, cohort_size, followup)
        rows.append(row)
        print(f'[exp05]   ct_prev={row["ct_prev_window_mean"]:.3f} '
              f'reinf={row["cohort_reinf_rate"]:.2f} '
              f'mean_notified={row["mean_notified_per_index"]:.2f} '
              f'pn_attending={row["pn_attending_window"]:,.0f}', flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / 'ladder.csv', index=False)
    print('\n[exp05] === LADDER (CT, draw 773, window 2030-34) ===')
    with pd.option_context('display.width', 200,
                           'display.float_format', lambda v: f'{v:,.3f}'):
        print(df[['rung', 'ct_prev_window_mean', 'ct_new_inf_window',
                  'cohort_reinf_rate', 'mean_notified_per_index',
                  'pn_attending_window']].to_string(index=False))
    print('[exp05] done.')


if __name__ == '__main__':
    main()
