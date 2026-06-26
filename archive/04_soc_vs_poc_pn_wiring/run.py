"""Exp 04 — named NG partner-notification chain trace (arm B).

Runs ONE calibrated draw (default draw_idx=773, the median-n_pass row of
the rc1.5.7 baseline) × one seed in the counterfactual arm (POC
etiological dx for VDS + GUD, PN scaled ×3), instruments the PN cascade
at the dyad level, and reconstructs named A→B(→C) chains for a cohort of
~100 successfully-NG-treated index cases.

This is a wiring/mechanism trace, NOT a science run. It answers: when an
index case A is cured of NG, what actually happens to A and to A's
partners over the following months — and when reinfection occurs, who is
the source?

Outputs (to outputs/):
  pn_dyads.csv        — (ti, index, partner, notified, attended)
  ng_tx_events.csv    — (ti, uid, outcome)
  ng_trans.csv        — (ti, source, target)
  chains.csv          — one row per cohort index, all branch flags
  chain_tree.json     — aggregated counts at each tree node

Env overrides for a quick smoke test:
  SMOKE=1   → n_agents=2000, stop=2032, window=(2030,2032), cohort target 40
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

THIS = Path(__file__).resolve()
HERE = THIS.parent
REPO = THIS.parents[2]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(HERE))
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from tracer import STIChainTracer                                     # noqa

DRAWS_CSV = REPO / 'experiments' / '03_2026-06-22_calibration_bv_in_vds' / 'outputs' / 'draws_used.csv'
OUT = HERE / 'outputs'

# Baseline PN rates (mirror interventions.make_pn defaults).
BASELINE_NOTIFY = {'stable': 0.20, 'casual': 0.10}
BASELINE_ATTEND = {'stable': {'f': 0.80, 'm': 0.50},
                   'casual': {'f': 0.50, 'm': 0.25}}


def scale_pn(mult, attend_cap=0.95):
    notify = {k: v * mult for k, v in BASELINE_NOTIFY.items()}
    attend = {edge: {sex: min(v * mult, attend_cap) for sex, v in sr.items()}
              for edge, sr in BASELINE_ATTEND.items()}
    return {'notify_rates': notify, 'attendance_rates': attend}


ARMS = {
    # SOC baseline: syndromic management + baseline (low) PN.
    'A': dict(poc=None, pn_pars=None),
    # Counterfactual: POC etiological dx (VDS+GUD) + PN scaled ×3.
    'B': dict(poc=True, pn_pars=scale_pn(3.0)),
}


def build_arm(arm, seed, sim_pars, start, stop, n_agents, tracer):
    """Build one arm with the chain tracer attached. arm in {'A','B'}."""
    cfg = ARMS[arm]
    symp_test = pd.read_csv(SYMP_TEST_CSV)
    sim = make_sim(seed=seed, start=start, stop=stop, n_agents=n_agents,
                   poc=cfg['poc'], pn_pars=cfg['pn_pars'],
                   fetal_health=False, verbose=1/12,
                   syph_symp_test_prob=symp_test,
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    return sim


# ---------------------------------------------------------------------------
# Chain reconstruction
# ---------------------------------------------------------------------------
def reconstruct(dyads, tx, trans, cohort_size, followup_steps):
    """Build per-index chain rows + aggregated tree counts.

    Cohort = first `cohort_size` distinct agents with a successful NG
    treatment (their first such event is T0). For each, classify the
    notify/attend branches at T0 and the reinfection outcome over
    (T0, T0+followup_steps].
    """
    succ = tx[tx.outcome == 'success'].sort_values('ti')
    first_succ = succ.groupby('uid', as_index=False).first()  # uid, ti, outcome
    cohort = first_succ.head(cohort_size)

    succ_by_uid_ti = succ[['uid', 'ti']].values  # for partner-cure lookup
    succ_uids = set(succ.uid)

    rows = []
    for _, c in cohort.iterrows():
        A = int(c.uid)
        T0 = int(c.ti)
        d = dyads[(dyads['index'] == A) & (dyads.ti == T0)]
        partners = set(int(p) for p in d.partner)
        notified = set(int(p) for p in d[d.notified == 1].partner)
        attended = set(int(p) for p in d[d.attended == 1].partner)
        had_partner = len(partners) > 0
        notified_any = len(notified) > 0
        attended_any = len(attended) > 0

        # A reinfected within followup?
        rA = trans[(trans.target == A) & (trans.ti > T0) & (trans.ti <= T0 + followup_steps)]
        A_reinf = len(rA) > 0
        src0 = int(rA.iloc[0].source) if A_reinf else -1
        src_cat0 = rA.iloc[0].src_cat if A_reinf else 'none'
        src_is_partner = src0 in partners
        src_is_unattended_partner = src0 in (partners - attended)

        # Of A's attended partners, did at least one get cured (NG success) after T0?
        partner_cured = False
        for p in attended:
            pc = succ[(succ.uid == p) & (succ.ti > T0) & (succ.ti <= T0 + followup_steps + 2)]
            if len(pc) > 0:
                partner_cured = True
                break

        rows.append(dict(
            index=A, t0=T0, had_partner=had_partner,
            n_partners=len(partners), n_notified=len(notified),
            n_attended=len(attended),
            notified_any=notified_any, attended_any=attended_any,
            A_reinfected=A_reinf, reinf_source=src0, reinf_src_cat=src_cat0,
            reinf_by_partner=src_is_partner,
            reinf_by_unattended_partner=src_is_unattended_partner,
            partner_cured=partner_cured,
        ))
    chains = pd.DataFrame(rows)

    # Aggregate the tree.
    def n(mask):
        return int(mask.sum())

    notified_m = chains.notified_any
    not_notified_m = ~notified_m
    tree = dict(
        cohort=len(chains),
        not_notified=dict(
            total=n(not_notified_m),
            no_partner=n(not_notified_m & ~chains.had_partner),
            had_partner_silent=n(not_notified_m & chains.had_partner),
            reinfected=n(not_notified_m & chains.A_reinfected),
            stayed_clear=n(not_notified_m & ~chains.A_reinfected),
        ),
        notified=dict(
            total=n(notified_m),
            partner_attended=n(notified_m & chains.attended_any),
            partner_not_attended=n(notified_m & ~chains.attended_any),
            # attended sub-branch
            attended_partner_cured=n(notified_m & chains.attended_any & chains.partner_cured),
            attended_partner_not_cured=n(notified_m & chains.attended_any & ~chains.partner_cured),
            # not-attended sub-branch
            notattend_reinf_index=n(notified_m & ~chains.attended_any & chains.A_reinfected),
            notattend_reinf_by_that_partner=n(notified_m & ~chains.attended_any & chains.reinf_by_unattended_partner),
            notattend_clear=n(notified_m & ~chains.attended_any & ~chains.A_reinfected),
        ),
    )
    return chains, tree


def run_arm(arm, draw_idx, seed, disease, tx_name, n_agents, start, stop,
            window, cohort_size, followup):
    """Build + run one arm; return (dyads, tx, trans, agg, chains, tree)."""
    draws = pd.read_csv(DRAWS_CSV)
    row = draws[draws.draw_idx == draw_idx]
    if len(row) == 0:
        raise SystemExit(f'draw_idx {draw_idx} not in {DRAWS_CSV}')
    sim_pars = row_to_sim_pars(row.iloc[0].to_dict())

    tracer = STIChainTracer(disease=disease, tx_name=tx_name, window=window)
    sim = build_arm(arm, seed, sim_pars, start, stop, n_agents, tracer)
    sim.init()
    sim.interventions.pn.trace_events = []   # enable dyad log on live module
    sim.run()

    pn = sim.interventions.pn
    dyads = pd.DataFrame(pn.trace_events,
                         columns=['ti', 'index', 'partner', 'notified', 'attended'])
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    trans = pd.DataFrame(tracer.trans_events,
                         columns=['ti', 'source', 'target', 'src_cat'])

    # Aggregate, arm-level outcomes for the traced disease over the window.
    yv = np.array([t.year for t in sim.t.timevec])
    lo, hi = window
    wmask = (yv >= lo) & (yv < hi)
    dr = sim.results[disease]
    agg = dict(
        arm=arm,
        prev_end=float(dr.prevalence.values[-1]),
        prev_window_mean=float(np.nanmean(np.asarray(dr.prevalence.values)[wmask])),
        new_inf_window=float(np.nansum(np.asarray(dr['new_infections'].values)[wmask])),
        tx_total_window=float(np.nansum(np.asarray(dr['new_treated'].values)[wmask])),
        tx_success_window=float(np.nansum(np.asarray(dr['new_treated_success'].values)[wmask])),
        pn_notified_window=float(np.nansum(np.asarray(pn.results['new_notified'].values)[wmask])),
        pn_attending_window=float(np.nansum(np.asarray(pn.results['new_attending'].values)[wmask])),
    )

    chains, tree = reconstruct(dyads, tx, trans, cohort_size, followup)
    agg['cohort_reinfected'] = int(chains.A_reinfected.sum()) if len(chains) else 0
    agg['cohort_n'] = int(len(chains))
    return dyads, tx, trans, agg, chains, tree


def main():
    smoke = os.environ.get('SMOKE') == '1'
    draw_idx = int(os.environ.get('DRAW', 773))
    seed = int(os.environ.get('SEED', 0))
    disease = os.environ.get('DISEASE', 'ct')
    tx_name = {'ng': 'ng_tx', 'ct': 'ct_tx', 'tv': 'metronidazole'}[disease]
    if smoke:
        n_agents, start, stop = 2000, 1985, 2032
        window = (2030, 2032); cohort_size, followup = 40, 8
    else:
        n_agents, start, stop = 10_000, 1985, 2040
        window = (2030, 2034); cohort_size, followup = 100, 12

    OUT.mkdir(parents=True, exist_ok=True)
    print(f'[exp04] draw={draw_idx} seed={seed} disease={disease} '
          f'n_agents={n_agents} {start}-{stop} window={window}', flush=True)

    CATS = ['fsw', 'client', 'f_other', 'm_other']
    aggs = []
    pop_src = {}     # arm -> Series of all-transmission source-cat shares
    reinf_src = {}   # arm -> Series of cohort-reinfection source-cat shares
    for arm in ('A', 'B'):
        print(f'[exp04] === arm {arm} ({"SOC+baseline PN" if arm=="A" else "POC+PN x3"}) ===',
              flush=True)
        dyads, tx, trans, agg, chains, tree = run_arm(
            arm, draw_idx, seed, disease, tx_name, n_agents, start, stop,
            window, cohort_size, followup)
        dyads.to_csv(OUT / f'pn_dyads_{arm}.csv', index=False)
        tx.to_csv(OUT / f'tx_events_{arm}.csv', index=False)
        trans.to_csv(OUT / f'trans_events_{arm}.csv', index=False)
        chains.to_csv(OUT / f'chains_{arm}.csv', index=False)
        with open(OUT / f'chain_tree_{arm}.json', 'w') as f:
            json.dump(tree, f, indent=2)
        aggs.append(agg)
        # source attribution
        pop_src[arm] = (trans.src_cat.value_counts().reindex(CATS).fillna(0).astype(int))
        reinf = chains[chains.A_reinfected]
        reinf_src[arm] = (reinf.reinf_src_cat.value_counts().reindex(CATS).fillna(0).astype(int))
        print(f'[exp04] arm {arm}: dyads={len(dyads)} cohort={agg["cohort_n"]} '
              f'reinfected={agg["cohort_reinfected"]}', flush=True)

    comp = pd.DataFrame(aggs).set_index('arm')
    comp.to_csv(OUT / 'arm_comparison.csv')
    pop_df = pd.DataFrame(pop_src)      # rows=cats, cols=arms (counts)
    reinf_df = pd.DataFrame(reinf_src)
    pop_df.to_csv(OUT / 'source_breakdown_population.csv')
    reinf_df.to_csv(OUT / 'source_breakdown_cohort_reinf.csv')

    print('\n[exp04] === ARM COMPARISON (disease='
          f'{disease}, window {window}) ===')
    with pd.option_context('display.float_format', lambda v: f'{v:,.3f}'):
        print(comp.T)
    print(f'\n[exp04] === {disease.upper()} TRANSMISSION SOURCES (all events, window) ===')
    print('counts:'); print(pop_df)
    print('shares:'); print((pop_df / pop_df.sum()).round(3))
    print(f'\n[exp04] === COHORT REINFECTION SOURCES (per 100 index) ===')
    print('counts:'); print(reinf_df)
    print('shares:'); print((reinf_df / reinf_df.sum().replace(0, np.nan)).round(3))
    print('[exp04] done.')


if __name__ == '__main__':
    main()
