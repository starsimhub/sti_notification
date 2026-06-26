"""PN-intensity ladder figure (CT, draw 773, POC arm).

Story: scaling partner notification under POC diagnostics finds and treats more
infections and lowers prevalence, but incidence does not fall because reinfection
through ongoing partnerships refills the susceptible pool.

3-panel causal chain, house style (Libertinus Sans), 9.7w x 5h, no secondary axes.
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl

HERE = Path(__file__).resolve().parent
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

BLUE = '#4a90d9'   # the lever working / progress
GREY = '#9aa0a6'   # stuck
RED = '#c0504d'    # the problem persists
EPTC = '#7a7a7a'

PANELS = [
    ('ct_tx_success_window', 1e-6, 'CT infections cured, 2030-34 (millions)',
     'More infections treated', BLUE),
    ('ct_prev_window_mean', 1.0, 'CT prevalence, 2030-34 mean',
     'Prevalence falls', BLUE),
    ('ct_new_inf_window', 1e-6, 'CT new infections, 2030-34 (millions)',
     'Incidence does not', RED),
]


def set_font(size=11):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def main():
    set_font(11)
    df = pd.read_csv(HERE / 'outputs' / 'ladder.csv')
    lad = df[df.rung != 'EPT'].copy()
    ept = df[df.rung == 'EPT']
    x = lad.mean_notified_per_index.values

    fig, axes = pl.subplots(1, 3, figsize=(9.7, 5))
    for ax, (col, scale, ylab, title, color) in zip(axes, PANELS):
        y = lad[col].values * scale
        ax.plot(x, y, 'o-', color=color, lw=2, ms=6, zorder=3)
        if len(ept):
            ax.plot(ept.mean_notified_per_index, ept[col] * scale, 'D',
                    color=EPTC, ms=8, zorder=4, label='EPT (attend 1.0)')
        ax.set_xlabel('Partners notified per index case', fontsize=9)
        ax.set_ylabel(ylab, fontsize=9.5)
        ax.set_title(title, fontsize=11, color=color, pad=8)
        ax.set_ylim(bottom=0)
        ax.tick_params(labelsize=8.5)
        ax.margins(x=0.08)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    axes[2].legend(fontsize=8, frameon=False, loc='lower right')

    fig.text(0.5, 0.955,
             'Partner notification lowers chlamydia prevalence but not incidence',
             ha='center', fontsize=13)
    fig.text(0.5, 0.028,
             'Single calibrated draw (773), POC diagnostic arm. As notification scales, more infections '
             'are found and cured and\nprevalence falls, but reinfection through ongoing partnerships '
             'keeps incidence flat. EPT approximates the x5 rung.',
             ha='center', fontsize=7.5, color='#666666')
    fig.subplots_adjust(left=0.07, right=0.985, top=0.86, bottom=0.18, wspace=0.34)

    (HERE / 'figures').mkdir(exist_ok=True)
    p = HERE / 'figures' / 'fig1_pn_ladder.png'
    fig.savefig(p, dpi=200)  # no bbox trim: keep exactly 9.7x5
    print('wrote', p)


if __name__ == '__main__':
    main()
