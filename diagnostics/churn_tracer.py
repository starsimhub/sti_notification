"""Reinfection 'churn' tracer: why POC-alone doesn't cut prevalence/incidence.

For CT, runs SOC vs POC-plain on the exp 06 baseline (1 draw x 5 seeds) with
the STIChainTracer attached. For every agent successfully treated (cured) in
the cohort window, finds the next reinfection within a 36-month follow-up and
its source category. Output feeds plot_churn.py:
  - reinfection-free survival after cure (months since cure)
  - source of reinfection (sex-work reservoir vs general partners)

    conda run -n starsim python diagnostics/churn_tracer.py

Writes results/churn_ct.csv (one row per cured cohort member).
"""
from __future__ import annotations

import os, sys, multiprocessing as mp
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')
from pathlib import Path
import numpy as np, pandas as pd

REPO = Path(__file__).resolve().parent.parent
for p in (str(REPO), str(REPO / 'calibration' / 'artifacts' / 'scripts'),
          str(REPO / 'archive' / '04_soc_vs_poc_pn_wiring')):
    sys.path.insert(0, p)
os.chdir(REPO)
from _pipeline import row_to_sim_pars, set_pars_local  # noqa
from model import make_sim                             # noqa
from scenarios import PN_INTENSITY                     # noqa
from tracer import STIChainTracer                      # noqa

DRAWS = REPO / 'experiments' / '06_2026-06-24_kseed_calibration' / 'outputs' / 'draws_used.csv'
# CT is the churn exemplar: cures succeed (~81%, no resistance mechanic), so a
# 'reinfection after cure' cohort is well-populated. (NG cures are draw-
# dependent under its rel_treat resistance dynamic -- a treatment-failure story,
# not a reinfection-churn one.)
DISEASE, TX = 'ct', 'ct_tx'
STOP = int(os.environ.get('STOP', 2040))
WINDOW = (2028, STOP)        # transmissions + treatments recorded here
COHORT_HI = int(os.environ.get('COHORT_HI', 2037))  # cures up to this year
FUP = int(os.environ.get('FUP', 36))   # follow-up months per cure (monthly dt)
N_AGENTS = int(os.environ.get('N_AGENTS', 10_000))
N_SEEDS = int(os.environ.get('N_SEEDS', 5))
ARMS = {'SOC': dict(poc=None), 'POC': dict(poc=True)}


def run_one(task):
    arm, seed, sp = task['arm'], task['seed'], task['sim_pars']
    tracer = STIChainTracer(disease=DISEASE, tx_name=TX, window=WINDOW)
    sim = make_sim(seed=seed, start=1985, stop=STOP, n_agents=N_AGENTS,
                   poc=ARMS[arm]['poc'], pn_pars=PN_INTENSITY['baseline'],
                   care_seek_mult=1.0, fetal_health=False, verbose=-1)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    sim.run()

    print(f'  [{arm} s{seed}] tx_events={len(tracer.tx_events)} '
          f'trans_events={len(tracer.trans_events)}', flush=True)
    years = np.array([t.year for t in sim.t.timevec])
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    trans = pd.DataFrame(tracer.trans_events, columns=['ti', 'src', 'tgt', 'src_cat'])
    rows = []
    if len(tx):
        succ = tx[tx.outcome == 'success'].copy()
        succ['year'] = years[succ.ti.to_numpy()]
        succ = succ[(succ.year >= WINDOW[0]) & (succ.year <= COHORT_HI)]
        first = succ.groupby('uid').ti.min()  # first cure per agent
        for uid, t0 in first.items():
            re = trans[(trans.tgt == uid) & (trans.ti > t0) & (trans.ti <= t0 + FUP)]
            if len(re):
                r0 = re.sort_values('ti').iloc[0]
                rows.append(dict(arm=arm, seed=seed, uid=int(uid),
                                 t0_year=int(years[t0]), reinfected=True,
                                 months=int(r0.ti - t0), src_cat=r0.src_cat))
            else:
                rows.append(dict(arm=arm, seed=seed, uid=int(uid),
                                 t0_year=int(years[t0]), reinfected=False,
                                 months=np.nan, src_cat='none'))
    return rows


def main():
    draws = pd.read_csv(DRAWS)
    r0 = draws.iloc[0].to_dict()
    sp = row_to_sim_pars(r0)
    di = int(r0['draw_idx'])
    tasks = [dict(arm=a, seed=di * 1000 + s, sim_pars=sp)
             for a in ARMS for s in range(N_SEEDS)]
    print(f'draw_idx={di}, {len(tasks)} sims (SOC/POC x {N_SEEDS} seeds), CT churn', flush=True)
    with mp.Pool(len(tasks)) as pool:
        out = []
        for rows in pool.map(run_one, tasks):
            out.extend(rows)
    df = pd.DataFrame(out)
    df.to_csv(REPO / 'results' / 'churn_ct.csv', index=False)

    for arm in ARMS:
        d = df[df.arm == arm]
        n = len(d); reinf = d.reinfected.sum()
        for mo in (12, 24, 36):
            print(f'  {arm}: reinfected within {mo}mo: '
                  f'{100*((d.months <= mo) & d.reinfected).sum()/max(n,1):.0f}%', flush=True)
        med = d.loc[d.reinfected, 'months'].median()
        print(f'  {arm}: cohort {n}, reinfected {100*reinf/max(n,1):.0f}%, '
              f'median months-to-reinf {med:.0f}', flush=True)
        src = d.loc[d.reinfected, 'src_cat'].value_counts(normalize=True) * 100
        print(f'  {arm} source: ' + '  '.join(f'{k} {v:.0f}%' for k, v in src.items()), flush=True)
    print('DONE', flush=True)


if __name__ == '__main__':
    main()
