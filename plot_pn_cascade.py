"""House-style CT partner-notification figure, arms A and B, 9.7w x 5h.

Two distinct axes per arm:
  * PN cascade (left)  — index treated -> told a partner -> partner attended ->
    partner treated, with the drop-off at each step.
  * 12-month outcome (right) — stacked bar: did the index stay clear, and if
    reinfected, where did the cascade break? Four failure points:
      did not tell a partner; told but partner did not attend; partner attended
      but not treated; partner treated but index reinfected anyway.

Reads per-index chain flags from archive/04_soc_vs_poc_pn_wiring/outputs/chains_{A,B}.csv.

  figures/fig_pn_cascade.png

Run from the repo root:
  python plot_pn_cascade.py
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import sciris as sc
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch

HERE = Path(__file__).resolve().parent
OUT = HERE / 'archive' / '04_soc_vs_poc_pn_wiring' / 'outputs'
FIG = HERE / 'figures'
FONT = '/Users/robynstuart/gf/syph_dx_zim/assets/LibertinusSans-Regular.otf'

ARM_TITLE = {'A': 'arm A — SOC + baseline PN', 'B': 'arm B — POC + PN×3'}

# cascade stages (left to right) and a deepening blue
CASC_COLORS = ['#cfe8ff', '#a9d3f5', '#7fb8e8', '#5a9bd4']
CX = [0.02, 0.21, 0.40, 0.59]            # cascade box left edges (axes coords)
CW, CH, CY = 0.16, 0.40, 0.52            # box width, height, centre y

# outcome categories, stacked bottom -> top, with colours and labels
CLEAR = '#9ed9a6'
OUTCOME = [
    ('clear',  CLEAR,     'remained clear'),
    ('f4',     '#f7d358', 'partner treated, reinfected anyway'),
    ('f3',     '#f0a860', 'partner attended, not treated'),
    ('f2',     '#e8743b', 'told, partner did not attend'),
    ('f1',     '#c0392b', 'did not tell a partner'),
]
BAR_X, BAR_W = 0.80, 0.12


def arm_numbers(arm):
    c = pd.read_csv(OUT / f'chains_{arm}.csv')
    notif, att, ptx, re = c.notified_any, c.attended_any, c.partner_cured, c.A_reinfected
    return dict(
        n=len(c),
        cascade=[len(c), int(notif.sum()), int(att.sum()), int(ptx.sum())],
        clear=int((~re).sum()),
        f1=int((~notif & re).sum()),
        f2=int((notif & ~att & re).sum()),
        f3=int((att & ~ptx & re).sum()),
        f4=int((att & ptx & re).sum()),
    )


def _casc_box(ax, x, name, count, color):
    ax.add_patch(FancyBboxPatch((x, CY - CH / 2), CW, CH,
                                boxstyle='round,pad=0.006,rounding_size=0.03',
                                linewidth=0.9, edgecolor='#444', facecolor=color))
    cx = x + CW / 2
    ax.text(cx, CY + 0.085, name, ha='center', va='center', fontsize=6.6, color='#222')
    ax.text(cx, CY - 0.055, str(count), ha='center', va='center', fontsize=11,
            fontweight='bold', color='#222')


def _arrow(ax, x0, x1, lost):
    ax.add_patch(FancyArrowPatch((x0, CY), (x1, CY), arrowstyle='-|>',
                                 mutation_scale=9, color='#999', lw=1.0, zorder=1))
    ax.text((x0 + x1) / 2, CY + 0.165, f'−{lost}', ha='center', va='bottom',
            fontsize=6.5, color='#a11')


def draw_arm(ax, arm, d):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis('off')
    names = ['index treated', 'told a partner', 'partner attended', 'partner treated']
    casc = d['cascade']

    for x, name, cnt, col in zip(CX, names, casc, CASC_COLORS):
        _casc_box(ax, x, name, cnt, col)
    for i in range(3):
        _arrow(ax, CX[i] + CW, CX[i + 1], casc[i] - casc[i + 1])

    # stacked outcome bar
    y0, H, tot = 0.10, 0.80, d['n']
    y = y0
    for key, col, _ in OUTCOME:
        v = d[key]
        h = H * v / tot
        ax.add_patch(Rectangle((BAR_X, y), BAR_W, h, facecolor=col,
                               edgecolor='#444', lw=0.8))
        if h >= 0.07:
            ax.text(BAR_X + BAR_W / 2, y + h / 2, str(v), ha='center', va='center',
                    fontsize=7.5, color='#222')
        y += h
    reinf = d['f1'] + d['f2'] + d['f3'] + d['f4']
    ax.text(BAR_X + BAR_W / 2, y0 + H + 0.03,
            f'{reinf} reinfected', ha='center', va='bottom', fontsize=7,
            color='#a11', fontweight='bold')

    ax.text(0.30, -0.04, ARM_TITLE[arm], ha='center', va='top', fontsize=9,
            fontweight='bold', color='#333', clip_on=False)


def main():
    sc.fonts(add=FONT)
    sc.options(font='Libertinus Sans', fontsize=11)

    data = {arm: arm_numbers(arm) for arm in 'AB'}

    fig = plt.figure(figsize=(9.7, 5))
    axA = fig.add_axes([0.0, 0.50, 0.79, 0.40])
    axB = fig.add_axes([0.0, 0.08, 0.79, 0.40])
    draw_arm(axA, 'A', data['A'])
    draw_arm(axB, 'B', data['B'])

    # section headers (figure coords above arm A)
    fig.text(0.79 * (CX[0] + CW * 2 + 0.05), 0.95, 'partner-notification cascade',
             ha='center', fontsize=8.5, fontweight='bold', color='#555')
    fig.text(0.79 * (BAR_X + BAR_W / 2), 0.95, '12-month\noutcome', ha='center',
             va='top', fontsize=8.5, fontweight='bold', color='#555', linespacing=0.95)

    # shared legend with per-arm counts
    handles = [mpatches.Patch(facecolor=col, edgecolor='#444') for _, col, _ in OUTCOME]
    labels = [f'{lab}\nA {data["A"][k]}   B {data["B"][k]}' for k, _, lab in OUTCOME]
    fig.legend(handles, labels, loc='center left', bbox_to_anchor=(0.80, 0.5),
               frameon=False, fontsize=6.8, handlelength=1.1, handleheight=1.3,
               labelspacing=0.9, title='index outcome at 12 mo', title_fontsize=7.5)

    fig.text(0.40, 0.015, 'draw 773, 1 seed, 12-month follow-up; −n = index cases '
             'lost at each cascade step', ha='center', fontsize=7, color='#888')

    FIG.mkdir(parents=True, exist_ok=True)
    p = FIG / 'fig_pn_cascade.png'
    fig.savefig(p, dpi=200)
    plt.close(fig)
    print(f'wrote {p}')


if __name__ == '__main__':
    main()
