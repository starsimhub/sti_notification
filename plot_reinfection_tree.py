"""
Reinfection branching diagram (small, vertical) for the STI undertreatment story.

One cohort of women cured of chlamydia, branched by 12-month outcome and, for
the reinfected, by source. Reinfection is dominated by the woman's own
concurrent partners (reachable by partner notification). Data read live from
exp 04 (SOC arm, chains_A.csv). Preliminary: draw 773, single seed.
"""
import sciris as sc
import numpy as np
import pandas as pd
import matplotlib.pyplot as pl
from matplotlib.patches import FancyArrowPatch

FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'
CHAINS_CSV = 'experiments/04_soc_vs_poc_pn_wiring/outputs/chains_A.csv'
FIGURES_DIR = 'figures'

# Colour encodes one variable only: 12-month status.
# blue = still clear, red = reinfected (both source nodes share the red;
# node size carries the own-vs-new split). Root is neutral.
C_CLEAR = '#4a90d9'
C_REINF = '#c0392b'
C_PARTNER = '#c0392b'
C_NEW = '#c0392b'
C_INK = '#15202b'
C_MUTE = '#888888'


def set_font(size=None):
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=size)


def read_counts():
    ch = pd.read_csv(CHAINS_CSV)
    n = len(ch)
    reinf = int(ch.A_reinfected.sum())
    r = ch[ch.A_reinfected]
    by_partner = int(r.reinf_by_partner.sum())
    return dict(n=n, clear=n - reinf, reinf=reinf,
                by_partner=by_partner, by_new=reinf - by_partner)


def node(ax, x, y, count, label, color):
    r = 0.03 + 0.085 * np.sqrt(count / 100)
    ax.add_patch(pl.Circle((x, y), r, color=color, zorder=3))
    ax.text(x, y, f'{count}', ha='center', va='center', color='white',
            fontsize=11, fontweight='bold', zorder=4)
    ax.text(x, y - r - 0.025, label, ha='center', va='top', fontsize=9,
            color=C_INK, zorder=4)


def branch(ax, x0, y0, x1, y1, count, color):
    lw = 0.6 + 5 * (count / 100)
    ax.add_patch(FancyArrowPatch((x0, y0), (x1, y1), arrowstyle='-',
                                 lw=lw, color=color, alpha=0.45, zorder=1))


if __name__ == '__main__':
    sc.makepath(FIGURES_DIR)
    set_font()
    c = read_counts()

    fig, ax = pl.subplots(1, 1, figsize=(3.83, 4.25))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    root = (0.50, 0.90)
    n_clear = (0.27, 0.58)
    n_reinf = (0.72, 0.58)
    n_partner = (0.55, 0.20)
    n_new = (0.88, 0.20)

    branch(ax, *root, *n_clear, c['clear'], C_CLEAR)
    branch(ax, *root, *n_reinf, c['reinf'], C_REINF)
    branch(ax, *n_reinf, *n_partner, c['by_partner'], C_PARTNER)
    branch(ax, *n_reinf, *n_new, c['by_new'], C_NEW)

    node(ax, *root, c['n'], 'cured', C_INK)
    node(ax, *n_clear, c['clear'], 'clear', C_CLEAR)
    node(ax, *n_reinf, c['reinf'], 'reinfected', C_REINF)
    node(ax, *n_partner, c['by_partner'], 'own partner', C_PARTNER)
    node(ax, *n_new, c['by_new'], 'new partner', C_NEW)

    fig.text(0.5, 0.015, 'SOC arm, 12 month follow-up', fontsize=8,
             color=C_MUTE, ha='center')
    out = f'{FIGURES_DIR}/fig_reinfection_tree_soc.png'
    pl.savefig(out, dpi=200, bbox_inches='tight')
    print(f'counts: {c}')
    print(f'Saved {out}')
