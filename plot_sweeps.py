"""
Prelim plots for the three orthogonal scenario sweeps.

  Top row: PN sweep, care-seeking sweep, dx×PN sweep — partner notifications
           reached (mechanism).
  Bottom row: same three sweeps — cumulative HIV infections (proximal impact),
              cumulative LBW (distal birth-outcome impact).

Reads results/sweeps.df produced by run_sweeps.py.
"""

import numpy as np
import pandas as pd
import sciris as sc
import matplotlib.pyplot as plt


PN_ORDER  = ['none', 'low', 'med', 'high']
CS_ORDER  = ['cs_x1', 'cs_x1.25', 'cs_x1.5', 'cs_x2']
DX_ORDER  = [f'{dx}_{pn}' for dx in ('soc', 'poc') for pn in PN_ORDER]


def _agg(df, sweep, metric, scen_order):
    """Mean ± min/max across seeds for one metric, in scenario order."""
    sub = df[df.sweep == sweep]
    grp = sub.groupby('scen')[metric].sum().reset_index()
    seed_grp = sub.groupby(['scen', 'seed'])[metric].sum().reset_index()
    out = []
    for s in scen_order:
        vals = seed_grp.loc[seed_grp.scen == s, metric].values
        if len(vals) == 0:
            continue
        out.append(dict(scen=s, mean=float(vals.mean()),
                        lo=float(vals.min()), hi=float(vals.max())))
    return pd.DataFrame(out)


def _bar(ax, agg, title, ylabel, color='C0'):
    x = np.arange(len(agg))
    ax.bar(x, agg['mean'], color=color, edgecolor='white', alpha=0.9)
    ax.errorbar(x, agg['mean'],
                yerr=[agg['mean'] - agg['lo'], agg['hi'] - agg['mean']],
                fmt='none', ecolor='black', capsize=3, lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(agg['scen'], rotation=20, fontsize=9)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.spines[['top', 'right']].set_visible(False)


def plot_sweeps(df, savepath='figures/sweeps.png', show=False):
    sc.makepath('figures')
    fig, axes = plt.subplots(2, 3, figsize=(15, 8))

    # Mechanism row: partners attending PN
    _bar(axes[0, 0], _agg(df, 'pn_coverage',  'pn_attending', PN_ORDER),
         'PN sweep: partners attending', 'Total partners attending')
    _bar(axes[0, 1], _agg(df, 'care_seeking', 'pn_attending', CS_ORDER),
         'Care-seeking sweep: partners attending', 'Total partners attending', color='C2')
    _bar(axes[0, 2], _agg(df, 'dx_x_pn',      'pn_attending', DX_ORDER),
         'Dx × PN sweep: partners attending', 'Total partners attending', color='C3')

    # Impact row: HIV new infections (proximal) -- single most-sensitive metric here
    _bar(axes[1, 0], _agg(df, 'pn_coverage',  'hiv_inf', PN_ORDER),
         'PN sweep: cumulative HIV infections', 'New HIV infections')
    _bar(axes[1, 1], _agg(df, 'care_seeking', 'ng_tx', CS_ORDER),
         'Care-seeking sweep: NG treatments', 'NG treatments', color='C2')
    _bar(axes[1, 2], _agg(df, 'dx_x_pn',      'hiv_inf', DX_ORDER),
         'Dx × PN sweep: cumulative HIV infections', 'New HIV infections', color='C3')

    fig.suptitle('Phase 1 prelim: scenario sweeps (uncalibrated, 3 seeds)',
                 fontsize=13, y=1.00)
    sc.figlayout()
    fig.savefig(savepath, dpi=120, bbox_inches='tight')
    if show:
        plt.show()
    print(f'Saved {savepath}')
    return fig


if __name__ == '__main__':
    df = sc.loadobj('results/sweeps.df')
    plot_sweeps(df)
