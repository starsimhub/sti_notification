"""House-style CT partner-notification cascade, arms A and B in one 9.7w x 5h
figure. Each panel traces 100 treated index cases through the PN chain to a net
12-month outcome (clear vs reinfected), shown as a stacked bar at the far right.

Reads chain leaves from archive/04_soc_vs_poc_pn_wiring/outputs/chain_tree_{A,B}.json
and net cohort reinfection from .../arm_comparison.csv.

  figures/fig_pn_cascade.png

Run from the repo root:
  python plot_pn_cascade.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import sciris as sc
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = Path(__file__).resolve().parent
OUT = HERE / 'archive' / '04_soc_vs_poc_pn_wiring' / 'outputs'
FIG = HERE / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

ARM_TITLE = {'A': 'arm A — SOC + baseline PN', 'B': 'arm B — POC + PN×3'}
REINF, CLEAR = '#ff9e9e', '#d7d7d7'

W, BH = 0.175, 0.185                         # box width, height (axes coords)
XS = [0.005, 0.215, 0.425, 0.635]            # column left edges
ROWS = [0.90, 0.65, 0.40, 0.15]              # four shared row centres
BAR_X, BAR_W = 0.875, 0.10                   # net-outcome stacked bar
HEADERS = ['index cured', 'told a partner?', 'partner attended?',
           'partner cured? /\nindex reinfected?', 'net outcome\nat 12 mo']


def _box(ax, x, y, name, num, color, note=None, hi=False, note_color='#666'):
    ax.add_patch(FancyBboxPatch((x, y - BH / 2), W, BH,
                                boxstyle='round,pad=0.006,rounding_size=0.03',
                                linewidth=0.9, edgecolor='#444', facecolor=color))
    cx = x + W / 2
    ax.text(cx, y + (0.050 if note else 0.038), name, ha='center', va='center',
            fontsize=6.2, color='#222')
    ax.text(cx, y - (0.018 if note else 0.038), str(num), ha='center', va='center',
            fontsize=9, fontweight='bold', color='#a11' if hi else '#222')
    if note:
        ax.text(cx, y - 0.062, note, ha='center', va='center', fontsize=5.0,
                color=note_color)


def _link(ax, i, y0, j, y1):
    """Elbow connector from right edge of column i to left edge of column j."""
    x0, x1 = XS[i] + W, XS[j]
    xm = (x0 + x1) / 2
    ax.plot([x0, xm, xm, x1], [y0, y0, y1, y1], color='#bbb', lw=0.9, zorder=0)


def _outcome_bar(ax, reinf, total=100):
    """Stacked bar at far right: index cases clear vs reinfected at 12 mo."""
    clear = total - reinf
    y0, H = 0.10, 0.80
    hc = H * clear / total
    hr = H * reinf / total
    cx = BAR_X + BAR_W / 2
    ax.add_patch(Rectangle((BAR_X, y0), BAR_W, hc, facecolor=CLEAR,
                           edgecolor='#444', lw=0.9))
    ax.add_patch(Rectangle((BAR_X, y0 + hc), BAR_W, hr, facecolor=REINF,
                           edgecolor='#444', lw=0.9))
    ax.text(cx, y0 + hc / 2, f'clear\n{clear}', ha='center', va='center', fontsize=7)
    ax.text(cx, y0 + hc + hr / 2, f'reinfected\n{reinf}', ha='center', va='center',
            fontsize=7, color='#a11', fontweight='bold')


def draw_tree(ax, arm, reinf_total):
    t = json.loads((OUT / f'chain_tree_{arm}.json').read_text())
    n, nn, no = t['cohort'], t['not_notified'], t['notified']
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')

    y_index, y_yes, y_no = 0.5, 0.75, 0.25
    y_att, y_natt, y_reinf, y_clear = ROWS

    _box(ax, XS[0], y_index, f'index cases ({arm})', n, '#cfe8ff')
    _link(ax, 0, y_index, 1, y_yes)
    _link(ax, 0, y_index, 1, y_no)

    _box(ax, XS[1], y_yes, 'notified ≥1 partner', no['total'], '#c9f0d2')
    _box(ax, XS[1], y_no, 'did NOT notify', nn['total'], '#ffe0c2',
         note=f"no partner {nn['no_partner']}, silent {nn['had_partner_silent']}")
    _link(ax, 1, y_yes, 2, y_att)
    _link(ax, 1, y_yes, 2, y_natt)
    _link(ax, 1, y_no, 2, y_reinf)
    _link(ax, 1, y_no, 2, y_clear)

    att_reinf = reinf_total - nn['reinfected'] - no['notattend_reinf_index']
    _box(ax, XS[2], y_att, 'partner attended', no['partner_attended'], '#a9e3ba',
         note=f'{att_reinf} index reinfected anyway', note_color='#a11')
    _box(ax, XS[2], y_natt, 'partner did NOT attend', no['partner_not_attended'], '#ffd0a0')
    _box(ax, XS[2], y_reinf, 'index REINFECTED', nn['reinfected'], REINF, hi=True)
    _box(ax, XS[2], y_clear, 'index stayed clear', nn['stayed_clear'], CLEAR)
    _link(ax, 2, y_att, 3, ROWS[0])
    _link(ax, 2, y_att, 3, ROWS[1])
    _link(ax, 2, y_natt, 3, ROWS[2])
    _link(ax, 2, y_natt, 3, ROWS[3])

    _box(ax, XS[3], ROWS[0], 'partner CURED', no['attended_partner_cured'], '#7fd496')
    _box(ax, XS[3], ROWS[1], 'partner not cured', no['attended_partner_not_cured'], '#ffd0a0')
    _box(ax, XS[3], ROWS[2], 'index REINFECTED', no['notattend_reinf_index'], REINF,
         note=f"by that partner {no['notattend_reinf_by_that_partner']}", hi=True)
    _box(ax, XS[3], ROWS[3], 'index clear', no['notattend_clear'], CLEAR)

    _outcome_bar(ax, reinf_total)

    ax.text(0.5, -0.05, ARM_TITLE[arm], ha='center', va='top', fontsize=9,
            fontweight='bold', color='#333', clip_on=False)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    comp = pd.read_csv(OUT / 'arm_comparison.csv', index_col='arm')
    fig, (axA, axB) = plt.subplots(2, 1, figsize=(9.7, 5))
    draw_tree(axA, 'A', int(comp.loc['A', 'cohort_reinfected']))
    draw_tree(axB, 'B', int(comp.loc['B', 'cohort_reinfected']))

    left, right = 0.01, 0.99
    hx = [x + W / 2 for x in XS] + [BAR_X + BAR_W / 2]
    for x, txt in zip(hx, HEADERS):
        fig.text(left + x * (right - left), 0.955, txt, ha='center', va='top',
                 fontsize=7.5, fontweight='bold', color='#555', linespacing=0.95)

    fig.text(0.5, 0.02, 'draw 773, 1 seed, 12-month follow-up; red counts (incl. the '
             'attended-branch note) sum to the net reinfected total',
             ha='center', fontsize=7, color='#888')
    fig.subplots_adjust(left=left, right=right, top=0.90, bottom=0.10, hspace=0.55)

    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / 'fig_pn_cascade.png'
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f'wrote {p}')


if __name__ == '__main__':
    main()
