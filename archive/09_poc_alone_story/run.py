"""
POC-alone story (local, not for committing): SOC vs POC with baseline PN held
fixed, one draw from the 26-draw ensemble, one seed. Isolates the diagnostic
lever to show POC improves correct treatment but does not move prevalence or
incidence. Reuses exp 04's STIChainTracer + reconstruct.

Writes outputs/poc_alone_results.json for the figure script.
"""
import os, sys, json
os.environ.setdefault('OMP_NUM_THREADS', '1')
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path('/Users/robynstuart/gf/sti_notification')
EXP04 = REPO / 'experiments' / '04_soc_vs_poc_pn_wiring'
for p in (str(REPO), str(REPO / 'calibration/artifacts/scripts'), str(EXP04)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV
from model import make_sim
from interventions import ANC_PROBS_REALISTIC
from tracer import STIChainTracer
import importlib.util
spec = importlib.util.spec_from_file_location('exp04run', EXP04 / 'run.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)  # for reconstruct

HERE = Path(__file__).resolve().parent
OUT = HERE / 'outputs'
DRAWS = REPO / 'experiments/04_calibration_per_disease_sustain/outputs/draws_used.csv'
ENS = REPO / 'experiments/04_calibration_per_disease_sustain/outputs/ensemble_summary.csv'
WINDOW = (2030, 2034)
SEED = 0


def pick_draw():
    used = pd.read_csv(DRAWS)
    summ = pd.read_csv(ENS)
    col = 'n_pass_mean' if 'n_pass_mean' in summ.columns else 'n_pass'
    sel = (summ[summ.draw_idx.isin(used.draw_idx)][['draw_idx', col]]
           .sort_values(col).reset_index(drop=True))
    return int(sel.iloc[len(sel) // 2].draw_idx)


def build(arm, sim_pars, tracer):
    poc = True if arm == 'POC' else None
    sim = make_sim(seed=SEED, start=1985, stop=2040, n_agents=10_000,
                   poc=poc, pn_pars=None, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sim_pars)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [tracer]
    return sim


def extract(sim, tracer):
    yv = np.array([t.year for t in sim.t.timevec])
    wm = (yv >= 2027) & (yv <= 2040)
    ct = sim.results.ct
    def wsum(k):
        return float(np.nansum(np.asarray(ct[k].values)[wm]))
    pn = sim.interventions.pn
    dy = pd.DataFrame(pn.trace_events, columns=['ti', 'index', 'partner', 'notified', 'attended'])
    tx = pd.DataFrame(tracer.tx_events, columns=['ti', 'uid', 'outcome'])
    tr = pd.DataFrame(tracer.trans_events, columns=['ti', 'source', 'target', 'src_cat'])
    chains, tree = m.reconstruct(dy, tx, tr, 100, 12)
    return dict(
        ct_prev_end=float(ct.prevalence.values[-1]),
        ct_prev_mean=float(np.nanmean(np.asarray(ct.prevalence.values)[wm])),
        ct_inc=wsum('new_infections'),
        ct_tx_total=wsum('new_treated'),
        ct_tx_success=wsum('new_treated_success'),
        ct_tx_unnecessary=wsum('new_treated_unnecessary'),
        cohort_reinf=float(chains.A_reinfected.mean()) if len(chains) else None,
        tree=tree,
    )


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    draw = pick_draw()
    used = pd.read_csv(DRAWS)
    sp = row_to_sim_pars(used[used.draw_idx == draw].iloc[0].to_dict())
    print(f'[poc_story] draw={draw} seed={SEED}', flush=True)
    res = {'draw': draw, 'seed': SEED, 'arms': {}}
    for arm in ('SOC', 'POC'):
        print(f'[poc_story] running {arm}...', flush=True)
        tracer = STIChainTracer(disease='ct', tx_name='ct_tx', window=WINDOW)
        sim = build(arm, sp, tracer)
        sim.init()
        sim.interventions.pn.trace_events = []
        sim.run()
        res['arms'][arm] = extract(sim, tracer)
        a = res['arms'][arm]
        print(f'[poc_story] {arm}: prev={a["ct_prev_mean"]:.3f} inc={a["ct_inc"]:,.0f} '
              f'success={a["ct_tx_success"]:,.0f} unnec={a["ct_tx_unnecessary"]:,.0f}', flush=True)
    (OUT / 'poc_alone_results.json').write_text(json.dumps(res, indent=2))
    print(f'[poc_story] wrote {OUT/"poc_alone_results.json"}')


if __name__ == '__main__':
    main()
