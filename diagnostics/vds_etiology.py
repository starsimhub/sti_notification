"""VDS etiology diagnostic (single draw/seed; heavy-ish analyzer, diagnostic use only).

Runs one calibrated draw with the VDSEtiology analyzer and reports, pooled over a
window: (1) vaginal-discharge prevalence among adult women, (2) the etiology
marginals (share of VDS women carrying NG/CT/TV/BV; sum >1 under coinfection),
and (3) the 15 mutually-exclusive infection combinations (sum to 100%).

    conda run -n starsim python diagnostics/vds_etiology.py

Env: DRAW (default = median-n_pass draw of the active ensemble), SEED (0),
N_AGENTS (10000), WINDOW ("2030-2040"). Prints tables and saves a figure to
figures/diag_vds_etiology.png.
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / 'calibration' / 'artifacts' / 'scripts'
for p in (str(REPO), str(SCRIPTS)):
    sys.path.insert(0, p)
os.chdir(REPO)

from _pipeline import row_to_sim_pars, set_pars_local, SYMP_TEST_CSV  # noqa
from model import make_sim                                            # noqa
from interventions import ANC_PROBS_REALISTIC                         # noqa
from analyzers import VDSEtiology                                     # noqa

CALIB = REPO / 'experiments' / '06_2026-06-24_kseed_calibration' / 'outputs'
DRAWS = CALIB / 'draws_used.csv'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

MARGINALS = VDSEtiology.MARGINALS
COMBOS = VDSEtiology.COMBOS


def pick_draw():
    if os.environ.get('DRAW'):
        return int(os.environ['DRAW'])
    used = pd.read_csv(DRAWS).sort_values('retention_rank').reset_index(drop=True)
    return int(used.iloc[len(used) // 2].draw_idx)


def pooled(res, mask, key):
    return float(np.nansum(np.asarray(res[key].values)[mask]))


def main():
    draw = pick_draw()
    seed = int(os.environ.get('SEED', 0))
    n_agents = int(os.environ.get('N_AGENTS', 10_000))
    lo, hi = (int(x) for x in os.environ.get('WINDOW', '2030-2040').split('-'))

    sp = row_to_sim_pars(pd.read_csv(DRAWS).query('draw_idx == @draw').iloc[0].to_dict())
    print(f'[vds] draw={draw} seed={seed} n_agents={n_agents} window={lo}-{hi}', flush=True)

    sim = make_sim(seed=seed, start=1985, stop=2040, n_agents=n_agents,
                   poc=None, pn_pars=None, fetal_health=False, verbose=-1,
                   syph_symp_test_prob=pd.read_csv(SYMP_TEST_CSV),
                   syph_anc_probs=ANC_PROBS_REALISTIC)
    set_pars_local(sim, sp)
    sim.pars['analyzers'] = list(sim.pars['analyzers']) + [VDSEtiology()]
    sim.run()

    res = sim.results['vds_etiology']
    yv = np.array([t.year for t in sim.t.timevec])
    m = (yv >= lo) & (yv <= hi)

    n_women = pooled(res, m, 'n_women')
    n_vds = pooled(res, m, 'n_vds')
    vds_prev = n_vds / n_women if n_women else np.nan
    marg = {p: pooled(res, m, f'marg_{p}') / n_vds for p in MARGINALS}
    combo = {c: pooled(res, m, c) / n_vds for c in COMBOS}

    print(f'\n=== VDS diagnostics (draw {draw}, women {lo}-{hi}, pooled person-steps) ===')
    print(f'Vaginal-discharge prevalence among adult women: {vds_prev:.1%}')
    print('\nEtiology marginals (share of VDS women carrying each; sum >1 under coinfection):')
    for p in MARGINALS:
        print(f'  {p.upper():3s}  {marg[p]:6.1%}')
    print(f'  (sum {sum(marg.values()):.1%})')
    print('\nInfection combinations among VDS women (mutually exclusive, sum to 100%):')
    for c in COMBOS:
        if combo[c] > 0:
            print(f'  {c:14s}  {combo[c]:6.1%}')
    print(f'  (sum {sum(combo.values()):.1%})')

    # tidy CSV
    OUT = REPO / 'results'
    OUT.mkdir(exist_ok=True)
    pd.DataFrame({'metric': ['vds_prev'] + [f'marg_{p}' for p in MARGINALS] + list(COMBOS),
                  'value': [vds_prev] + [marg[p] for p in MARGINALS] + [combo[c] for c in COMBOS]
                  }).to_csv(OUT / 'vds_etiology.csv', index=False)

    # figure: marginals + combinations
    sc.fonts(add=FONT); sc.options(font='Libertinus Sans', fontsize=10)
    fig, (axm, axc) = pl.subplots(1, 2, figsize=(9.7, 5), gridspec_kw={'width_ratios': [1, 2.1]})
    axm.bar(range(len(MARGINALS)), [marg[p] * 100 for p in MARGINALS], color='#4a90d9')
    axm.set_xticks(range(len(MARGINALS))); axm.set_xticklabels([p.upper() for p in MARGINALS])
    axm.set_ylabel('% of VDS women carrying pathogen')
    axm.set_title(f'Etiology marginals (VDS prev {vds_prev:.1%})', fontsize=11, color='#4a90d9')
    present = [(c, combo[c] * 100) for c in COMBOS if combo[c] > 0]
    axc.barh(range(len(present)), [v for _, v in present], color='#c0504d')
    axc.set_yticks(range(len(present))); axc.set_yticklabels([c for c, _ in present], fontsize=8)
    axc.invert_yaxis(); axc.set_xlabel('% of VDS women (mutually exclusive)')
    axc.set_title('Infection combinations', fontsize=11, color='#c0504d')
    for ax in (axm, axc):
        ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    fig.text(0.5, 0.02, f'Single calibrated draw {draw}, women {lo}-{hi}, syndromic arm. '
             'Marginals overlap (coinfection); combinations partition the VDS population.',
             ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.09, right=0.985, top=0.9, bottom=0.13, wspace=0.3)
    p = REPO / 'figures' / 'diag_vds_etiology.png'
    fig.savefig(p, dpi=200)
    print(f'\nSaved {p}\nSaved {OUT / "vds_etiology.csv"}')


if __name__ == '__main__':
    main()
