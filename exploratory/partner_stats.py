"""
Partnership statistics for women aged 15-30, for the partner-notification slide.
Snapshot of the StructuredSexual network from a SOC sim (draw 773).
Reports concurrent-partner counts by edge type, plus FSW share.
"""
import os, sys
os.environ.setdefault('OMP_NUM_THREADS', '1')
from pathlib import Path
import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(REPO), str(REPO / 'calibration/artifacts/scripts')]
os.chdir(REPO)
from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV
from model import make_sim
from interventions import ANC_PROBS_REALISTIC

draws = pd.read_csv('experiments/01_2026-06-15_calibration_rc1.5.7/outputs/draws_used.csv')
sp = row_to_sim_pars(draws[draws.draw_idx == 773].iloc[0].to_dict())
sim = make_sim(seed=0, start=1985, stop=2020, n_agents=10_000, poc=None,
               pn_pars=None, fetal_health=False, verbose=0,
               syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
               syph_anc_probs=ANC_PROBS_REALISTIC)
set_pars_local(sim, sp)
sim.run()

ppl = sim.people
nw = sim.networks.structuredsexual
print('edge_types:', dict(nw.edge_types))

age = ppl.age.values
female = ppl.female.values
alive = ppl.alive.values
auid = ppl.auids  # active uids
# women 15-30 alive
mask = female & alive & (age >= 15) & (age < 30)
women = ppl.uid[mask]
wset = set(int(u) for u in women)
nwomen = len(women)

p1 = np.asarray(nw.p1); p2 = np.asarray(nw.p2)
et = np.asarray(nw.edges.edge_type) if 'edge_type' in nw.edges else np.full(len(p1), -1)
int2name = {int(v): k for k, v in nw.edge_types.items()}

deg = {int(u): 0 for u in women}
deg_by = {name: {int(u): 0 for u in women} for name in nw.edge_types}
for a, b, e in zip(p1, p2, et):
    for endpoint in (int(a), int(b)):
        if endpoint in wset:
            deg[endpoint] += 1
            nm = int2name.get(int(e))
            if nm in deg_by:
                deg_by[nm][endpoint] += 1

d = np.array(list(deg.values()))
def stats(arr):
    return dict(mean=round(float(arr.mean()), 2),
                median=float(np.median(arr)),
                iqr=(round(float(np.percentile(arr, 25)), 2), round(float(np.percentile(arr, 75)), 2)),
                pct_0=round(float((arr == 0).mean()) * 100, 1),
                pct_ge2=round(float((arr >= 2).mean()) * 100, 1),
                max=int(arr.max()))

print(f'\nWomen 15-30 alive at 2020: {nwomen}')
print('Concurrent partners (all):', stats(d))
# among sexually active (>=1 partner)
da = d[d >= 1]
print('Concurrent partners (active only, >=1):', stats(da) if len(da) else 'none')
for name in nw.edge_types:
    arr = np.array(list(deg_by[name].values()))
    if arr.sum() > 0:
        print(f'  type "{name}": mean={arr.mean():.2f} share-with>=1={(arr>=1).mean()*100:.1f}%')
# FSW share among women 15-30
if hasattr(nw, 'fsw'):
    fsw = np.asarray(nw.fsw)
    fsw_w = np.array([bool(fsw[int(u)]) for u in women])
    print(f'FSW share among women 15-30: {fsw_w.mean()*100:.1f}%')
