"""Slide 4: VDS etiology upset in isolation at 4.25 x 5.88 inches (portrait).

Reuses the upset_panels function from plot_result1 so both figures stay
in sync -- if the upset definition changes, both update together. Sized
to sit alongside a PPV/NPV/FDR/FOR table on Slide 4.

  conda run -n starsim python plot_slide4_etiology.py
"""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import sciris as sc
import matplotlib.pyplot as pl
from matplotlib.gridspec import GridSpec

from plot_result1 import upset_panels, VDS_PATHS, COMBOS, FONT

REPO = Path(__file__).resolve().parent
VDS_CSV = REPO / 'results' / 'vds_etiology.csv'
FIGS = REPO / 'figures'


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    vd = dict(zip(*[pd.read_csv(VDS_CSV)[c] for c in ('metric', 'value')]))
    vds_prev = vd['vds_prev']
    marg = {p: vd[f'marg_{p}'] for p in VDS_PATHS}
    combo = {c: vd[c] for c in COMBOS}

    # 4.25 x 5.88 inches -- portrait. Bars on top (larger), matrix + set on
    # bottom. Bar row taller than matrix row for readability of the tall
    # first bar (~62% BV-only).
    fig = pl.figure(figsize=(4.25, 5.88))
    gs = GridSpec(2, 2, figure=fig,
                  width_ratios=[0.85, 5], height_ratios=[3.6, 1.6],
                  left=0.16, right=0.985, top=0.94, bottom=0.11,
                  hspace=0.06, wspace=0.14)
    ax_bar = fig.add_subplot(gs[0, 1])
    ax_mat = fig.add_subplot(gs[1, 1], sharex=ax_bar)
    ax_set = fig.add_subplot(gs[1, 0], sharey=ax_mat)

    upset_panels(ax_bar, ax_mat, ax_set, marg, combo, vds_prev, fs=11)
    ax_bar.set_title('VDS etiology (2030–40)', fontsize=12, pad=6)

    FIGS.mkdir(exist_ok=True)
    p = FIGS / 'fig_slide4_etiology.png'
    fig.savefig(p, dpi=200)
    print('wrote', p)


if __name__ == '__main__':
    main()
